# 10 · Structured Streaming in Spark 4.x

The course doesn't cover streaming at all, and it's a core part of modern Spark work. This doc gives the fundamentals plus everything new in 4.0–4.2: `transformWithState`, the State Data Source, Real-Time Mode, and named sources.

> The old **DStream / `pyspark.streaming`** API is legacy. Use **Structured Streaming** (`spark.readStream` / `df.writeStream`).

---

## 1. Mental model

A stream is an **unbounded table**. You write a normal DataFrame query, and Spark runs it **incrementally** as new data arrives, keeping whatever state it needs (aggregates, dedup keys, join buffers) between runs.

```
source ──► readStream ──► transformations (same DataFrame API) ──► writeStream ──► sink
                                     │                                  │
                                 state store                       checkpoint
                              (RocksDB / HDFS-backed)        (offsets + state + commits)
```

The three things you always choose:

| Choice | Options |
|---|---|
| **Trigger** (when to run) | default (ASAP micro-batches) · `processingTime="1 minute"` · `availableNow=True` (process everything available, then stop; great for scheduled "incremental batch") · `realTime="5 minutes"` (Real-Time Mode, 4.1+/PySpark 4.2) · `continuous` (old experimental mode; RTM replaces it) |
| **Output mode** | `append` (only finalized rows) · `update` (changed rows) · `complete` (whole result each time; small aggregates only) |
| **Checkpoint location** | `option("checkpointLocation", path)`. Required for fault tolerance and exactly-once |

---

## 2. First streaming job (file source → console)

Re-using the course's invoice data: split `invoices.csv` into chunks and drop them into `stream_in/` one at a time.

```python
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder.master("local[3]").appName("StreamDemo")
         .config("spark.sql.shuffle.partitions", "3").getOrCreate())

schema = """InvoiceNo string, StockCode string, Description string, Quantity int,
            InvoiceDate string, UnitPrice double, CustomerID string, Country string"""

invoices = (spark.readStream
            .format("csv").option("header", True).schema(schema)   # streaming file sources need a schema
            .option("maxFilesPerTrigger", 1)
            .load("stream_in/"))

revenue = (invoices
           .withColumn("value", F.col("Quantity") * F.col("UnitPrice"))
           .groupBy("Country").agg(F.round(F.sum("value"), 2).alias("Revenue")))

query = (revenue.writeStream
         .format("console")
         .outputMode("complete")
         .option("checkpointLocation", "chk/revenue")
         .trigger(processingTime="10 seconds")
         .start())

query.awaitTermination()
```

Watch the **Structured Streaming** tab in the Spark UI (input rate, processing rate, batch duration).

---

## 3. Event time, watermarks and windows

```python
events = (invoices
          .withColumn("ts", F.try_to_timestamp("InvoiceDate", F.lit("dd-MM-yyyy H.mm")))
          .withWatermark("ts", "30 minutes"))           # accept data up to 30 min late

per_window = (events
              .groupBy(F.window("ts", "1 hour", "15 minutes"), "Country")   # sliding window
              .agg(F.sum(F.col("Quantity") * F.col("UnitPrice")).alias("Revenue")))
```

| Window | Function |
|---|---|
| tumbling | `F.window("ts", "10 minutes")` |
| sliding | `F.window("ts", "1 hour", "15 minutes")` |
| session | `F.session_window("ts", "30 minutes")` |

**Watermark** = "max event time seen − delay". State older than the watermark is dropped, and in `append` mode a window is emitted only once the watermark passes its end. Without a watermark, aggregation state grows forever.

Other watermark-aware operators: `dropDuplicates` / **`dropDuplicatesWithinWatermark`** (3.5+), stream-stream joins (watermarks on both sides + a time-range condition). 4.2 adds stream-stream non-outer joins in **update** mode.

---

## 4. Sources and sinks

| Sources | Sinks |
|---|---|
| Files (csv/json/parquet/text/orc/xml) | Files (append only) |
| **Kafka** (`spark-sql-kafka-0-10_2.13:<spark version>`) | **Kafka** |
| `rate`, `rate-micro-batch` (testing) | `console`, `memory` (testing) |
| Tables: `spark.readStream.table("t")` | Tables: `writeStream.toTable("t")` |
| **Python streaming data sources** (4.0, see [07 §6](07_modern_python_udfs_udtfs_datasources.md)) | `foreach` / **`foreachBatch`** (arbitrary batch code per micro-batch) |

Kafka example:

```python
import pyspark
spark = (SparkSession.builder
         .config("spark.jars.packages",
                 f"org.apache.spark:spark-sql-kafka-0-10_2.13:{pyspark.__version__}")
         .getOrCreate())

raw = (spark.readStream.format("kafka")
       .option("kafka.bootstrap.servers", "localhost:9092")
       .option("subscribe", "invoices")
       .option("startingOffsets", "earliest")
       .load())

parsed = raw.select(F.from_json(F.col("value").cast("string"), schema).alias("j")).select("j.*")
# or keep it flexible: raw.select(F.parse_json(F.col("value").cast("string")).alias("v"))
```

`foreachBatch` for upserts (idempotent with a table format, see [12](12_lakehouse_table_formats.md)):

```python
def upsert(batch_df, batch_id):
    batch_df.createOrReplaceTempView("updates")
    batch_df.sparkSession.sql("""
        MERGE INTO gold.revenue t USING updates s ON t.Country = s.Country
        WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *""")

revenue.writeStream.foreachBatch(upsert).option("checkpointLocation", "chk/upsert").start()
```

---

## 5. Exactly-once and checkpoints

- Exactly-once end to end = **replayable source** (files, Kafka) + **checkpointed offsets/state** + **idempotent or transactional sink** (file sink, Delta/Iceberg, `MERGE` in `foreachBatch`).
- Never share a checkpoint between two queries. Never delete it unless you mean to reprocess.
- Changing the query (adding aggregations, changing keys) can make an old checkpoint incompatible. Plan for it.
- **Named sources (4.2):** give each source a stable name so you can add, remove or reorder sources without breaking checkpoint compatibility:
  ```python
  orders = spark.readStream.format("kafka").name("orders_src").option(...).load()
  ```
  (`DataStreamReader.name()`. Names must be ASCII letters, digits and underscores. Sink naming exists on the JVM/SQL side in 4.2. Check your PySpark version's `DataStreamWriter` for a Python equivalent.)

---

## 6. Arbitrary stateful processing: `transformWithState` (4.0+)

The new "state API v2" replaces `applyInPandasWithState` / `flatMapGroupsWithState` with a cleaner object model: **multiple named state variables** (Value/List/Map), **timers**, **TTL**, and initial state.

```python
import pandas as pd
from pyspark.sql.streaming import StatefulProcessor, StatefulProcessorHandle

spark.conf.set("spark.sql.streaming.stateStore.providerClass",
               "org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider")


class InvoiceCounter(StatefulProcessor):
    """Per customer: running invoice count, emitted on every batch."""

    def init(self, handle: StatefulProcessorHandle) -> None:
        self.count = handle.getValueState("count", "value long")

    def handleInputRows(self, key, rows, timerValues):
        total = self.count.get()[0] if self.count.exists() else 0
        for pdf in rows:                       # rows: Iterator[pd.DataFrame]
            total += len(pdf)
        self.count.update((total,))
        yield pd.DataFrame({"CustomerID": [key[0]], "invoices": [total]})

    def close(self) -> None:
        pass


counts = (invoices.groupBy("CustomerID")
          .transformWithStateInPandas(
              statefulProcessor=InvoiceCounter(),
              outputStructType="CustomerID string, invoices long",
              outputMode="Update",
              timeMode="None"))               # "ProcessingTime" or "EventTime" to use timers
```

- State variables: `handle.getValueState`, `getListState`, `getMapState`, all with optional `ttlDurationMs`.
- Timers: `handle.registerTimer(ms)` + `handleExpiredTimer(key, timerValues, expiredTimerInfo)`. Use them for session timeouts and "no activity for 30 min" alerts.
- `handleInitialState(...)` seeds state from a batch DataFrame.
- `groupBy(...).transformWithState(...)` is the row-based (non-pandas) variant, needing only pyarrow + protobuf.

---

## 7. Debugging state: the State Data Source (4.0+)

Read a query's state store **as a DataFrame** to see what's actually in it:

```python
state = spark.read.format("statestore").load("chk/revenue")
state.show(truncate=False)

spark.read.format("state-metadata").load("chk/revenue").show()   # operators, partitions, batch ids
```

Options include `batchId`, `operatorId`, `storeName`, `snapshotStartBatchId` / `snapshotPartitionId`, and change-feed reading (`readChangeFeed`).

4.2 state store reliability: **row checksums** to detect corruption, **automatic snapshot repair**, and `forceSnapshotUploadOnLag` on by default.

---

## 8. Real-Time Mode (4.1+, Python trigger in 4.2)

A new execution mode for **millisecond-level latency**. Same API and guarantees, but data flows continuously through long-running tasks instead of waiting for micro-batch boundaries.

```python
(df.writeStream
   .format("kafka")
   .option("checkpointLocation", "chk/rtm")
   .outputMode("update")
   .trigger(realTime="5 minutes")      # the interval is the checkpoint cadence, NOT the latency
   .start())
```

Current limits (check your version's docs): **stateless queries only** (projections, filters, unions, stream-static joins) with Kafka-style sources and sinks. Stateful RTM support is planned for later 4.x releases (the 4.1 notes mention 4.3). Use it when you need sub-second fraud/alerting/routing. Micro-batch is still right for most ETL.

---

## 9. Monitoring

```python
query.status          # is a trigger active, is data available
query.lastProgress    # dict: inputRowsPerSecond, processedRowsPerSecond, durationMs, stateOperators...
query.recentProgress

from pyspark.sql.streaming import StreamingQueryListener

class Printer(StreamingQueryListener):
    def onQueryStarted(self, e): print("started", e.id)
    def onQueryProgress(self, e): print(e.progress.batchId, e.progress.numInputRows)
    def onQueryIdle(self, e): pass
    def onQueryTerminated(self, e): print("terminated", e.id)

spark.streams.addListener(Printer())
```

Key health signals: processing rate ≥ input rate, stable batch duration, state rows not growing unbounded (check your watermark), no growing Kafka consumer lag.

---

## 10. Exercises

1. Run §2 with `availableNow=True` instead of `processingTime`, and explain when you'd schedule a job like this hourly instead of keeping it running.
2. Add the §3 watermark + tumbling window, switch to `append` mode, and observe when windows get emitted.
3. Run Kafka locally (Docker `apache/kafka`), produce JSON invoices from a small Python script, and write per-country revenue to Parquet with exactly-once semantics. Kill and restart the query and verify no duplicates.
4. Extend `InvoiceCounter` with a processing-time timer that emits `"inactive"` for a customer after 2 minutes without invoices.
5. Inspect your query's state with `format("statestore")` before and after the watermark passes.
6. Optional: a stateless Kafka → Kafka filter in Real-Time Mode, measuring end-to-end latency.

---

## Sources

- Structured Streaming programming guide: https://spark.apache.org/docs/latest/streaming/index.html
- Kafka integration: https://spark.apache.org/docs/latest/streaming/structured-streaming-kafka-integration.html
- Spark 4.0 release notes (transformWithState, state data source): https://spark.apache.org/releases/spark-release-4-0-0.html
- Spark 4.1 release notes (Real-Time Mode): https://spark.apache.org/releases/spark-release-4.1.0.html
- Spark 4.2 release notes (named sources/sinks, RTM in PySpark, state store checksums): https://spark.apache.org/releases/spark-release-4-2-0.html
- PySpark 4.2.0 source, `DataStreamWriter.trigger(realTime=...)` and `DataStreamReader.name()`: https://github.com/apache/spark/blob/v4.2.0/python/pyspark/sql/streaming/readwriter.py
