# 11 · Spark Declarative Pipelines (SDP), New in 4.1

The course builds jobs **imperatively**: read → transform → `write`, in a script you run by hand, in the right order. **Spark Declarative Pipelines** (4.1+) flip this. You declare *which datasets should exist and how each is defined*, and Spark works out the dependency graph, execution order, parallelism, checkpoints, retries and incremental processing.

If you've heard of Databricks "Delta Live Tables / Lakeflow Declarative Pipelines", SDP is the open-source core of that idea, contributed to Apache Spark.

---

## 1. Concepts

```
            spark-pipeline.yml  (name, libraries, storage, catalog/database, conf)
                     │
      ┌──────────────┴───────────────┐
      ▼                              ▼
 transformations/*.py          transformations/*.sql
      │ (decorated functions)        │ (CREATE MATERIALIZED VIEW / STREAMING TABLE / FLOW)
      └──────────────┬───────────────┘
                     ▼
             dataflow graph  ──►  SDP resolves dependencies, runs flows, manages checkpoints
```

| Term | Meaning |
|---|---|
| **Flow** | the unit of processing: read source → transform → write target |
| **Materialized view** | a table defined by **one batch** flow; recomputed/refreshed on each run |
| **Streaming table** | a table fed by **one or more streaming** flows; only new data is processed each run |
| **Temporary view** | pipeline-scoped intermediate dataset, not persisted or visible outside |
| **Sink** | external target (Kafka, …) fed by an append flow (Python only) |
| **Pipeline** | all of the above + the spec file, executed as one graph |

---

## 2. Setup

```bash
pip install "pyspark[pipelines]==4.2.0"      # adds the spark-pipelines CLI (uses Spark Connect underneath)
spark-pipelines init --name retail_pipeline  # scaffolds spec + example transformations
cd retail_pipeline
```

`spark-pipeline.yml`:

```yaml
name: retail_pipeline
libraries:
  - glob:
      include: transformations/**
storage: file:///Users/<you>/spark-pipelines/retail_pipeline/storage   # absolute path, checkpoints live here
database: retail
configuration:
  spark.sql.shuffle.partitions: "4"
```

---

## 3. Python API

```python
from pyspark import pipelines as dp
```

| Decorator / function | Creates |
|---|---|
| `@dp.materialized_view(name=?, comment=?, partition_cols=?, cluster_by=?, schema=?, table_properties=?)` | batch-defined table |
| `@dp.table(...)` | streaming table (function returns a streaming DataFrame) |
| `@dp.temporary_view(...)` | pipeline-scoped view |
| `dp.create_streaming_table(name, ...)` + `@dp.append_flow(target=name)` | one target fed by several streaming flows |
| `dp.create_sink(name=, format=, options=)` | external sink for an append flow |
| `dp.create_auto_cdc_flow(target, source, keys, sequence_by, apply_as_deletes=?, stored_as_scd_type=1)` | **4.2:** upsert CDC events into a streaming table (SCD Type 1) |

Since **4.2**, `spark` is injected into each pipeline file. You don't need `SparkSession.active()`. (Declare `spark: SparkSession` at module level if your linter complains.)

### The course's modules 13 → 14 → 16 as a pipeline (bronze / silver / gold)

```python
# transformations/retail.py
from pyspark import pipelines as dp
from pyspark.sql import DataFrame, Window, functions as F

RAW = "/abs/path/old_code_2024/13-AggDemo/data/invoices.csv"


@dp.materialized_view(comment="Bronze: raw invoices, all strings")
def invoices_bronze() -> DataFrame:
    return spark.read.option("header", True).csv(RAW)


@dp.materialized_view(comment="Silver: typed and cleaned")
def invoices_silver() -> DataFrame:
    return (spark.read.table("invoices_bronze")
            .select("InvoiceNo", "StockCode", "Country", "CustomerID",
                    F.col("Quantity").try_cast("int").alias("Quantity"),
                    F.col("UnitPrice").try_cast("double").alias("UnitPrice"),
                    F.try_to_date("InvoiceDate", "dd-MM-yyyy H.mm").alias("InvoiceDate"))
            .where("InvoiceDate IS NOT NULL AND Quantity IS NOT NULL"))


@dp.materialized_view(comment="Gold: weekly summary (module 14)")
def weekly_summary() -> DataFrame:
    return (spark.read.table("invoices_silver")
            .where(F.year("InvoiceDate") == 2010)
            .withColumn("WeekNumber", F.weekofyear("InvoiceDate"))
            .groupBy("Country", "WeekNumber")
            .agg(F.count_distinct("InvoiceNo").alias("NumInvoices"),
                 F.sum("Quantity").alias("TotalQuantity"),
                 F.round(F.sum(F.col("Quantity") * F.col("UnitPrice")), 2).alias("InvoiceValue")))


@dp.materialized_view(comment="Gold: best week per country (module 16)")
def best_week() -> DataFrame:
    w = Window.partitionBy("Country").orderBy(F.col("InvoiceValue").desc())
    return (spark.read.table("weekly_summary")
            .withColumn("rnk", F.dense_rank().over(w))
            .where("rnk = 1").drop("rnk"))
```

You never call `write` and never decide the order. SDP sees that `best_week` reads `weekly_summary`, which reads `invoices_silver`, and so on.

### The same in SQL

```sql
-- transformations/gold.sql
CREATE MATERIALIZED VIEW best_week_sql AS
FROM weekly_summary
|> SELECT *, dense_rank() OVER (PARTITION BY Country ORDER BY InvoiceValue DESC) AS rnk
|> WHERE rnk = 1;

CREATE STREAMING TABLE events_st AS SELECT * FROM STREAM events_source;
```

### Streaming + Auto CDC (4.2)

```python
dp.create_streaming_table("customers")

dp.create_auto_cdc_flow(
    target="customers",
    source="customer_changes",          # a streaming dataset of change events
    keys=["CustomerID"],
    sequence_by="event_ts",             # resolves out-of-order events
    apply_as_deletes=F.expr("op = 'DELETE'"),
    stored_as_scd_type=1,
)
```

---

## 4. CLI

| Command | Does |
|---|---|
| `spark-pipelines init --name X` | scaffold a project |
| `spark-pipelines dry-run [--spec path]` | validate syntax, analysis (missing tables/columns) and graph (cycles) **without touching data** |
| `spark-pipelines run` | incremental update of everything |
| `spark-pipelines run --refresh a,b` | refresh selected datasets |
| `spark-pipelines run --full-refresh a,b` | clear data + checkpoints for selected datasets and recompute |
| `spark-pipelines run --full-refresh-all` | recompute the whole graph |
| `spark-pipelines run --remote sc://host:15002` | run against a remote Spark Connect server |

The CLI accepts normal `spark-submit` options (`--conf`, `--driver-memory`, …) except `--class`.

---

## 5. Rules and gotchas

- Dataset functions **must return a DataFrame** and must **not** perform actions or writes (`collect`, `count`, `toPandas`, `save`, `saveAsTable`, `start`, …). SDP may call them several times while planning.
- Keep them side-effect free: no prints-as-logic, no external API calls at definition time.
- Loops that generate datasets (`for country in [...]`) must be driven by additive, deterministic values.
- SQL files don't support `PIVOT` or sinks.
- `storage` must be stable. It holds the streaming checkpoints, so deleting it means reprocessing.

### When to use SDP vs. plain scripts vs. an orchestrator

| Need | Pick |
|---|---|
| A handful of interdependent tables, batch + streaming, inside Spark | **SDP** |
| A one-off transform or ad-hoc analysis | plain script / notebook |
| Cross-system workflows (call APIs, run dbt, send emails, wait on S3 files), schedules, SLAs | orchestrator (Airflow, Dagster, Databricks Workflows), which can *call* `spark-pipelines run` |

---

## 6. Exercises

1. Build the §3 pipeline, run `dry-run`, then `run`. Break it on purpose (typo a column) and see where `dry-run` catches it.
2. Add a data-quality temporary view that counts rejected rows (bronze minus silver) and fail the run if the reject rate exceeds 1% (hint: do the check in a separate job step after the pipeline, since dataset functions can't run actions).
3. Turn bronze into a streaming table reading a folder of CSV drops (`spark.readStream`), and observe that a second `run` only processes new files.
4. Model a customer table with `create_auto_cdc_flow` from a stream of insert/update/delete events.

---

## Sources

- Declarative Pipelines programming guide: https://spark.apache.org/docs/latest/declarative-pipelines-programming-guide.html
- Spark 4.1 release notes: https://spark.apache.org/releases/spark-release-4.1.0.html
- Spark 4.2 release notes (Auto CDC, injected `spark`): https://spark.apache.org/releases/spark-release-4-2-0.html
- PySpark 4.2.0 pipelines API source (signatures verified): https://github.com/apache/spark/blob/v4.2.0/python/pyspark/pipelines/api.py
