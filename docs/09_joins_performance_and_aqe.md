# 09 · Joins, Performance and Adaptive Query Execution (Updates to Modules 17–21)

The course's join modules (17 inner, 18 outer, 19 shuffle, 20 broadcast, 21 bucket) teach the right fundamentals. What changed is that **AQE (Adaptive Query Execution)** has been on by default since Spark 3.2 and keeps getting smarter. Spark now **re-plans joins at runtime** using real shuffle statistics, so the plan you see before running isn't always the plan that executes. This doc fills that gap and adds the tuning toolkit.

---

## 1. Join strategies (still the core mental model)

| Strategy | How it works | Chosen when | Shuffle? |
|---|---|---|---|
| **Broadcast Hash Join (BHJ)** | small side is collected and sent to every executor; big side is hashed locally | one side < `spark.sql.autoBroadcastJoinThreshold` (default **10 MB**) or `broadcast()` hint | **no** (big side stays put) |
| **Shuffle Hash Join (SHJ)** | both sides shuffled by key; the smaller partition side is hashed in memory | hint `shuffle_hash`, or AQE converts SMJ when partitions are small | yes |
| **Sort-Merge Join (SMJ)** | both sides shuffled by key, sorted, then merged | default for large equi-joins (`spark.sql.join.preferSortMergeJoin=true`) | yes (+ sort) |
| **Broadcast Nested Loop** | broadcast one side, compare every pair | non-equi joins with a small side | no |
| **Cartesian product** | every pair | non-equi joins, no small side | yes, and very expensive |
| **Storage-Partitioned Join (SPJ)** | uses the tables' existing layout (V2 sources like Iceberg) | both tables partitioned compatibly on the join keys | **no** |
| **Bucketed SMJ** (module 21) | Hive-style bucketed tables with the same bucket count on the join key | both tables bucketed on the join key | **no** |

### Join hints

```python
from pyspark.sql import functions as F

big.join(F.broadcast(small), "id")            # module 20
big.join(small.hint("broadcast"), "id")
big.join(small.hint("merge"), "id")           # force sort-merge
big.join(small.hint("shuffle_hash"), "id")    # force shuffle hash
big.join(small.hint("shuffle_replicate_nl"), "id")
```
```sql
SELECT /*+ BROADCAST(p) */ * FROM orders o JOIN products p ON o.prod_id = p.prod_id
```

Hint priority: `BROADCAST` > `MERGE` > `SHUFFLE_HASH` > `SHUFFLE_REPLICATE_NL`.

### Cleaner join syntax than module 17

```python
# module 17 joins on an expression, then drops the duplicate column:
order_df.join(product_renamed_df, order_df.prod_id == product_df.prod_id, "inner") \
        .drop(product_renamed_df.prod_id)

# equivalent, with no duplicate column to drop:
order_df.join(product_renamed_df, on="prod_id", how="inner")

# when column names collide, use aliases:
o, p = order_df.alias("o"), product_df.alias("p")
o.join(p, F.col("o.prod_id") == F.col("p.prod_id")).select("o.*", F.col("p.prod_name"))
```

Other join types to know: `left_semi` (EXISTS), `left_anti` (NOT EXISTS), `cross`, lateral joins (`df.lateralJoin`, 4.0), and `NEAREST BY` top-K ranking joins (4.2).

---

## 2. Adaptive Query Execution (AQE)

`spark.sql.adaptive.enabled=true` (default). At each shuffle boundary Spark stops, looks at the **actual** sizes of the shuffle output, and re-optimizes what's left of the plan.

| AQE feature | What it does | Key configs |
|---|---|---|
| **Coalesce post-shuffle partitions** | merges many tiny shuffle partitions into fewer, right-sized ones | `spark.sql.adaptive.coalescePartitions.enabled` (true), `spark.sql.adaptive.advisoryPartitionSizeInBytes` (64 MB), `…coalescePartitions.minPartitionSize`, `…coalescePartitions.parallelismFirst` |
| **SMJ → BHJ at runtime** | if one side turns out to be small after filters, switch to broadcast | `spark.sql.adaptive.autoBroadcastJoinThreshold` (defaults to the non-adaptive threshold) |
| **SMJ → SHJ** | if all partitions fit in memory, skip the sort | `spark.sql.adaptive.maxShuffledHashJoinLocalMapThreshold` |
| **Skew join** | splits oversized partitions and replicates the matching side | `spark.sql.adaptive.skewJoin.enabled` (true), `…skewJoin.skewedPartitionFactor` (5), `…skewJoin.skewedPartitionThresholdInBytes` (256 MB), `spark.sql.adaptive.forceOptimizeSkewedJoin` |
| **Local shuffle reader** | after converting to BHJ, read shuffle files locally | `spark.sql.adaptive.localShuffleReader.enabled` |

### How AQE changes the course demos

- **Module 19 (shuffle join):** you set `spark.sql.shuffle.partitions=3`. With AQE on you may see **fewer** than 3 reduce tasks (coalesced), or the join may become a broadcast because the `d1`/`d2` JSON data is tiny. To see the textbook SMJ:
  ```python
  spark.conf.set("spark.sql.adaptive.enabled", "false")
  spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "-1")
  ```
- **Module 20 (broadcast):** the hint still forces BHJ. Remove it and AQE will probably broadcast anyway on this small data.
- **Module 21 (bucket join):** setting `spark.sql.autoBroadcastJoinThreshold=-1` isn't enough with AQE, so also set `spark.sql.adaptive.autoBroadcastJoinThreshold=-1`. Check for the absence of `Exchange` in the plan.

### Reading AQE plans

```python
df = flight_time_df1.join(flight_time_df2, "id")
df.explain("formatted")     # before execution: AdaptiveSparkPlan isFinalPlan=false
df.collect()
df.explain("formatted")     # after: isFinalPlan=true shows what really ran
```
In the Spark UI **SQL / DataFrame** tab, click the query to see the final adaptive plan with runtime metrics (rows, sizes and spill per operator).

`explain` modes: `"simple"`, `"extended"`, `"codegen"`, `"cost"`, `"formatted"` (the most readable).

---

## 3. Partitioning, the #1 tuning lever

| Knob | Default | Notes |
|---|---|---|
| `spark.sql.shuffle.partitions` | 200 | With AQE coalescing, set it *high enough* (AQE only merges, it doesn't split ordinary partitions). Local: 2–8. Clusters: about 2–3× total cores, or let AQE handle it via `…coalescePartitions.initialPartitionNum`. |
| `spark.sql.files.maxPartitionBytes` | 128 MB | input split size when reading files |
| `spark.sql.files.openCostInBytes` | 4 MB | makes Spark pack small files together |
| `df.repartition(n)` / `repartition(col)` | — | full shuffle; balances data or co-locates by key |
| `df.coalesce(n)` | — | merges partitions **without** a shuffle; can only reduce; may create skew |
| `df.repartitionByRange(n, col)` | — | range partitioning, good before sorted writes |
| SQL hints `/*+ REPARTITION(n, col) */`, `/*+ COALESCE(n) */`, `/*+ REBALANCE(col) */` | — | `REBALANCE` lets AQE split skewed write partitions (`spark.sql.adaptive.optimizeSkewsInRebalancePartitions.enabled`) |

Target output partition and file size: **roughly 100 MB – 1 GB** per file for analytics tables.

---

## 4. Data skew

**Symptom:** one task in a stage runs 10× longer than the others (Spark UI → Stages → task duration summary: compare max vs median).

**Fixes, in order of preference:**
1. Let **AQE skew join** handle it. It's on by default, but check the thresholds against your data sizes.
2. **Broadcast** the smaller side, if it fits.
3. **Filter** the hot key out, process it separately, and `union` the results.
4. **Salting:** add a random suffix to the hot key on the big side and replicate the small side N times:

```python
N = 8
big_salted = big.withColumn("salt", (F.rand() * N).cast("int"))
small_salted = small.crossJoin(spark.range(N).withColumnRenamed("id", "salt"))
big_salted.join(small_salted, ["key", "salt"]).drop("salt")
```

---

## 5. Caching

```python
df.cache()                        # = persist(MEMORY_AND_DISK) for DataFrames
df.persist(StorageLevel.DISK_ONLY)
df.count()                        # caching is lazy, so an action materializes it
df.unpersist()
spark.catalog.cacheTable("sales"); spark.catalog.clearCache()
```

Cache **only** when a DataFrame is reused several times *and* is expensive to recompute. Caching a DataFrame used once just adds work. Check the **Storage** tab to see what's cached and how much of it fits.

---

## 6. Memory and common failures

| Failure | Typical cause | Fix |
|---|---|---|
| Driver OOM | `collect()`/`toPandas()` on big data; huge broadcast; too many partitions' metadata | `limit`/write to storage instead; lower the broadcast threshold; raise `spark.driver.memory` |
| Executor OOM / heavy spill | skewed partition; too few shuffle partitions; giant pandas UDF groups | more partitions; fix skew; Arrow batch limits (`spark.sql.execution.arrow.maxRecordsPerBatch`) |
| `Container killed … memory overhead` | Python workers + off-heap usage | raise `spark.executor.memoryOverhead` (Python UDFs live outside the JVM heap) |
| Very slow stage with many tiny tasks | small files | compaction; `openCostInBytes`; table formats with `OPTIMIZE` |
| Broadcast timeout | big "small" side | `spark.sql.broadcastTimeout`; don't hint-broadcast big tables |

Executor memory layout (unified memory manager): heap = **reserved (300 MB)** + **user memory** + **unified region** (`spark.memory.fraction`, default 0.6) shared between execution and storage. On top of that come **overhead** (off-heap, Python workers) and optional `spark.memory.offHeap.size`.

---

## 7. Statistics and the cost-based optimizer

```sql
ANALYZE TABLE flight_data1 COMPUTE STATISTICS;
ANALYZE TABLE flight_data1 COMPUTE STATISTICS FOR COLUMNS id;
```
Enable CBO with `spark.sql.cbo.enabled=true` (+ `spark.sql.cbo.joinReorder.enabled=true`) for better join ordering on catalog tables. Check the effect with `explain("cost")`.

---

## 8. Bucketing (module 21) vs. modern layouts

| Approach | Status in 2026 |
|---|---|
| Hive-style `bucketBy` + `saveAsTable` | Still works (local Derby/Hive metastore). Niche: fragile (bucket counts must match, writes create many files) and not supported by every engine. |
| **Partitioning** (`partitionBy`) | Still standard for low-cardinality columns (date, region). |
| **Storage-Partitioned Join** on V2 tables (Iceberg; `spark.sql.sources.v2.bucketing.*`) | The modern generalization of bucket joins: avoids shuffles using the table's partition transforms (`bucket(16, id)`, `days(ts)`). |
| **Liquid clustering** (Delta `CLUSTER BY`) / Z-ordering / Iceberg sort orders | The modern way to co-locate data for fast filtering and joins without hard bucket counts. |

---

## 9. Seeing runs after they finish (instead of `input()`)

```python
spark = (SparkSession.builder
         .config("spark.eventLog.enabled", "true")
         .config("spark.eventLog.dir", "file:///tmp/spark-events")
         .getOrCreate())
```

Start the History Server from a Spark distribution (`$SPARK_HOME/sbin/start-history-server.sh` with `spark.history.fs.logDirectory=file:///tmp/spark-events`) and browse http://localhost:18080. Since 4.0, event logs are **rolled and compressed by default**. 4.2 adds a Spark Connect tab in the History Server.

The driver also exposes metrics in **Prometheus** format (`spark.ui.prometheus.enabled` is on by default since 4.0) at `/metrics/executors/prometheus`.

---

## 10. Exercises

1. Module 19: run with AQE on/off × broadcast threshold default/-1 (4 runs). Record the join type and reduce task count for each in a table.
2. Make module 19's data skewed (duplicate one `id` 100,000 times), find the straggler task in the UI, and fix it with (a) AQE skew-join thresholds and (b) salting.
3. Module 21: verify no `Exchange` with bucketing. Then rewrite the same tables as Iceberg with `PARTITIONED BY (bucket(3, id))` and look for a storage-partitioned join (see [12](12_lakehouse_table_formats.md)).
4. Cache the summary DataFrame in module 15/16 and measure with and without it when running three different window queries.
5. Trigger a driver OOM on purpose (`spark.driver.memory=512m` + `collect()` on a large `spark.range`), then fix it.

---

## Sources

- Performance tuning (AQE, hints, SPJ): https://spark.apache.org/docs/latest/sql-performance-tuning.html
- Join hints syntax: https://spark.apache.org/docs/latest/sql-ref-syntax-qry-select-hints.html
- Tuning guide (memory): https://spark.apache.org/docs/latest/tuning.html
- Monitoring / History Server / Prometheus: https://spark.apache.org/docs/latest/monitoring.html
- Core migration guide (event-log defaults): https://spark.apache.org/docs/latest/core-migration-guide.html
