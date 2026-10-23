# 02 · PySpark Learning Roadmap (2026 Edition, Spark 4.x)

A step-by-step path from "I did a Spark 3 course years ago" to "I can build, tune, test and ship modern Spark 4 pipelines". It reuses the 21 course modules in this repo as the fundamentals track and adds the topics that came after the course.

- **Target version:** Apache Spark **4.2.x** (PySpark 4.2), Python 3.12/3.13, Java 21
- **Total time:** roughly **12–16 weeks** at 6–10 hours/week. Phases 1–4 go quickly because you've seen them before.
- **Where things are:** the original course modules (`01-HelloSpark` … `21-BucketJoinDemo`) now live in `old_code_2024/`. The new notes and code will follow the layout in [13](13_new_folder_structure_and_workflow_plan.md).
- **How to use this:** do the phases in order. Each phase lists goals, topics, which repo modules and docs to use, hands-on exercises, and a "done when" checklist. Don't move on until the checklist passes.

---

## Map of the whole journey

```
Phase 0  Prerequisites refresh ............ (skip/skim)  ~3 h
Phase 1  Modern environment + architecture  modules 01–03  week 1
Phase 2  Data sources, schemas, sinks ..... modules 04–06  week 2
Phase 3  Transformations + ANSI mode ...... modules 07–12  week 3
Phase 4  Aggregations + windows ........... modules 13–16  week 4
Phase 5  Joins + performance + AQE ........ modules 17–21  weeks 5–6
Phase 6  Modern Python on Spark ........... (new)          week 7
Phase 7  Modern Spark SQL ................. (new)          week 8
Phase 8  Spark Connect + deployment ....... (new)          week 9
Phase 9  Structured Streaming ............. (new)          weeks 10–11
Phase 10 Lakehouse table formats .......... (new)          week 12
Phase 11 Declarative Pipelines + prod eng . (new)          weeks 13–14
Phase 12 Capstone + certification ......... (new)          weeks 15–16
```

| Phase | Repo modules | Docs |
|---|---|---|
| 1 | 01, 02, 03 | [03](03_environment_setup_2026.md), [04](04_migrating_course_code_to_spark_4.md) |
| 2 | 04, 05, 06 | [04](04_migrating_course_code_to_spark_4.md), [12](12_lakehouse_table_formats.md) (preview) |
| 3 | 07–12 | [05](05_ansi_mode_and_sql_behavior_changes.md) |
| 4 | 13–16 | [08](08_new_sql_features.md) (QUALIFY, pipe syntax) |
| 5 | 17–21 | [09](09_joins_performance_and_aqe.md) |
| 6 | 11 (revisited) | [07](07_modern_python_udfs_udtfs_datasources.md) |
| 7 | 03, 13 (revisited) | [08](08_new_sql_features.md) |
| 8 | all (run in Connect mode) | [06](06_spark_connect.md) |
| 9 | — | [10](10_structured_streaming_modern.md) |
| 10 | 06, 21 (revisited) | [12](12_lakehouse_table_formats.md) |
| 11 | — | [11](11_declarative_pipelines.md) |

---

## Phase 0 · Prerequisites refresh (skim if confident)

**Goal:** make sure the non-Spark foundations aren't slowing you down.

- **Python:** comprehensions, generators (`yield`, which you need for UDTFs and Data Sources), decorators (`@udf`, `@dp.table`), type hints (pandas UDFs depend on them), context managers, virtual environments.
- **SQL:** `GROUP BY`/`HAVING`, all join types, window functions (`ROW_NUMBER`, `RANK`, `LAG`, frames), CTEs, `CASE`, NULL semantics (`NULL = NULL` is NULL).
- **CLI & Git:** run scripts with args, env vars (`JAVA_HOME`, `PYSPARK_PYTHON`), basic git.
- **Distributed systems vocabulary:** partitioning, shuffling, data skew, serialization, idempotency, at-least-once vs exactly-once.
- **pandas & Arrow basics:** `pd.Series`, `pd.DataFrame`, and what a columnar format is. Phase 6 builds on this.

**Done when:** you can write a SQL query with a CTE, a window function and a LEFT JOIN without looking anything up, and you can explain what a Python generator is.

---

## Phase 1 · Modern environment + Spark architecture (Week 1)

**Goal:** get the course code running on Spark 4.2, and refresh the mental model of how Spark executes.

### 1.1 Set up the environment
- Install Java 21 and Python 3.12/3.13, create a venv with `uv` or `venv`, and install `pyspark==4.2.*`. Full steps in [03](03_environment_setup_2026.md).
- Replace Log4j 1.x configs with `log4j2.properties` ([04 §2](04_migrating_course_code_to_spark_4.md)).
- Set the IDE interpreter (PyCharm/VS Code) to the new venv. The `.idea` folders still point to "Python 3.8 (2)".

### 1.2 Architecture refresh
- Driver vs executors vs cluster manager (local, Standalone, YARN, Kubernetes; **Mesos was removed in 4.0**).
- **Spark Classic vs Spark Connect.** In Classic, your Python process drives a local JVM driver through Py4J. In Connect, your Python is a thin gRPC client talking to a remote driver. Concept only for now; it's hands-on in Phase 8.
- Lazy evaluation: transformations build a plan, actions (`count`, `collect`, `show`, `write`) execute it.
- Job → Stage → Task. A stage boundary means a shuffle.
- Narrow vs wide transformations.
- Catalyst optimizer (logical plan → optimized → physical) and the Tungsten execution engine.
- The **Spark UI** at http://localhost:4040: Jobs, Stages, SQL/DataFrame, Storage, Environment, Executors tabs.

### 1.3 Course modules
- **01-HelloSpark:** config loading from `spark.conf`, logging, unit tests. Port the tests to `pytest` ([03 §6](03_environment_setup_2026.md)).
- **02-HelloRDD:** run it once to understand `map`/`filter`/`reduceByKey`, then stop. RDDs are legacy for application code and aren't the API to invest in.
- **03-HelloSparkSQL:** temp views + `spark.sql`.

### Exercises
1. Run 01-HelloSpark on Spark 4.2 with logs going to `app-logs/` through the new `log4j2.properties`.
2. Rewrite 02-HelloRDD's logic in three ways (RDD, DataFrame API, SQL) and compare `explain()` output for the last two. The plans should be identical.
3. Open the Spark UI while 01 runs. Find how many stages it had and explain *why* (hint: `repartition(2)` + `groupBy`).
4. Run 01 with `spark.sql.adaptive.enabled=false` and then `true`, and compare the number of tasks in the last stage.

### Done when
- [ ] All 21 modules at least start on Spark 4.2 (fix them as you reach each phase)
- [ ] You can explain driver/executor/task/stage/shuffle in your own words
- [ ] You can say in one sentence what Spark Connect changes

---

## Phase 2 · Data sources, schemas and sinks (Week 2)

**Goal:** read and write data reliably and with explicit schemas.

### Topics
- `DataFrameReader`: `format`, `option`, `schema`, `load`. CSV, JSON, Parquet, ORC, Avro, text, and **XML (built in since 4.0)**.
- Schema: `StructType` vs DDL string, `inferSchema` cost, `samplingRatio`, why to avoid inference in production.
- Read modes: `PERMISSIVE` (with `columnNameOfCorruptRecord`), `DROPMALFORMED`, `FAILFAST`.
- Date/time formats: Spark 3+ datetime patterns (`yyyy-MM-dd`, `M/d/y`). The parser policy default is now `CORRECTED`.
- `DataFrameWriter`: `mode` (`append`/`overwrite`/`ignore`/`errorifexists`), `partitionBy`, `bucketBy` + `sortBy` (tables only), `maxRecordsPerFile`, compression codecs.
- Partition discovery and partition pruning.
- **The small-files problem** and how `repartition`/`coalesce`/`maxRecordsPerFile` affect it.
- Managed vs external tables, `saveAsTable`, the catalog API (`spark.catalog.*`).
- `DataFrameWriterV2` (`df.writeTo("t").using("parquet").createOrReplace()`).
- New: reading JSON/CSV/XML **from a DataFrame column** (4.2). Preview of **VARIANT** for semi-structured data.

### Course modules
- **04-SparkSchema**, **05-DataSinkDemo** (fix the Avro package), **06-SparkSQLTableDemo**.

### Exercises
1. In 04, add one malformed row to the CSV and observe all three read modes. In `PERMISSIVE`, capture the bad row with `_corrupt_record`.
2. In 05, write the same data as Parquet (snappy), Parquet (zstd), ORC and Avro, and compare directory sizes and file counts.
3. In 05, change `partitionBy("OP_CARRIER", "ORIGIN")` to `partitionBy("OP_CARRIER")`, then read back with a filter on `OP_CARRIER` and confirm partition pruning in `explain()` (`PartitionFilters`).
4. In 06, list tables via `spark.catalog.listTables()` and run `DESCRIBE TABLE EXTENDED` and `DESCRIBE TABLE … AS JSON` (4.0+).

### Done when
- [ ] You never rely on `inferSchema` for production-style code
- [ ] You can explain when to use `partitionBy` vs `bucketBy` vs neither
- [ ] You can explain why 10,000 tiny files are bad and how to avoid them

---

## Phase 3 · Transformations and ANSI mode (Week 3)

**Goal:** write clean, correct column transformations under Spark 4's stricter SQL semantics.

### Topics
- Column references: `col`, `F.col`, string names, `df["x"]`, `expr`, `selectExpr`.
- `withColumn` vs `withColumns` (multiple at once, avoids long plan chains), `withColumnRenamed`/`withColumnsRenamed`, `drop`, `cast`.
- `when`/`otherwise`, `coalesce`, string functions (`regexp_extract`, `regexp_replace`, `split`, `substring_index`), date functions.
- Rows and `createDataFrame` from Python lists, from pandas, and from Arrow tables.
- `dropDuplicates`, `distinct`, `monotonically_increasing_id` (unique but not consecutive), and the new `DataFrame.zipWithIndex` (4.2) for consecutive ids.
- **ANSI mode** (default since 4.0): what now throws, the `try_*` family, and the `spark.sql.ansi.enabled` escape hatch. See [05](05_ansi_mode_and_sql_behavior_changes.md).
- Built-in functions vs UDFs: always try built-ins first.
- Import style: `from pyspark.sql import functions as F` (avoids shadowing Python's `sum`, `max`, `round`).

### Course modules
- **07-transformation**, **08-RowDemo**, **09-LogFileDemo**, **10-ExploringColumns**, **11-UDF_Demo**, **12-miscDemo**.

### Exercises
1. In 12-miscDemo, add the row `("Bad", "xx", "5", "81")` and run with ANSI on. Watch it fail, then fix it with `try_cast`.
2. In 07/08, add the date `"13/45/2020"` and handle it with `try_to_date` (4.0+). Write a test that asserts it becomes NULL.
3. Rewrite 11's `parse_gender` UDF using only `F.when(F.lower(col).rlike(...))` and compare speed on the full `survey.csv` in the Spark UI.
4. In 09, extract the HTTP status code and bytes, and compute the top 10 IPs by bytes served.

### Done when
- [ ] You can list five operations that throw under ANSI mode and their `try_*` alternatives
- [ ] You use `F.` imports consistently
- [ ] You can explain why a Python UDF is slower than a built-in function

---

## Phase 4 · Aggregations and window functions (Week 4)

**Goal:** master grouping, multi-level aggregation and analytical windows.

### Topics
- `groupBy().agg()`, `count` vs `count(col)` vs `count_distinct` vs `approx_count_distinct`.
- `rollup`, `cube`, **`groupingSets`** (DataFrame API in 4.0), `grouping_id`.
- `pivot`/`unpivot` (`melt`).
- Window specs: `partitionBy`, `orderBy`, `rowsBetween` vs `rangeBetween`, `unboundedPreceding`.
- Ranking: `row_number`, `rank`, `dense_rank`, `percent_rank`, `ntile`. Offsets: `lag`, `lead`. Aggregates over windows.
- **`QUALIFY`** (4.2): filter on window results in SQL without a subquery.
- **SQL pipe syntax** (4.0): `FROM t |> WHERE … |> AGGREGATE … GROUP BY …`.
- `IGNORE NULLS` for `array_agg`/`collect_list`/`collect_set` (4.2). Sketches and `approx_top_k` (4.1).

### Course modules
- **13-AggDemo**, **14-GroupingDemo**, **15-WindowingDemo**, **16-RankingDemo**.

### Exercises
1. Fix 15-WindowingDemo so `RunningTotal` is a true running total (`Window.unboundedPreceding`). Keep the 3-week version as `MovingSum3W`.
2. Add week-over-week change with `lag`.
3. Rewrite 16-RankingDemo in SQL with `QUALIFY dense_rank() OVER (...) = 1`.
4. Rewrite 13's `summary_sql` with pipe syntax.
5. Use `rollup("Country", "WeekNumber")` to add subtotals and a grand total.

### Done when
- [ ] You can explain `ROWS` vs `RANGE` frames with an example
- [ ] You know when `row_number` vs `rank` vs `dense_rank` gives different results
- [ ] You can write the same aggregation in DataFrame API, classic SQL and pipe SQL

---

## Phase 5 · Joins, performance and AQE (Weeks 5–6)

**Goal:** understand *how* Spark executes joins and aggregations, and tune them. This is the most important "senior" skill.

### Topics
- Join types: inner, left/right/full outer, left semi, left anti, cross. Lateral joins (4.0). Ambiguous columns and how to resolve them (aliases, `on="col"` list syntax).
- Physical join strategies: **Broadcast Hash Join**, **Shuffle Hash Join**, **Sort-Merge Join**, Broadcast Nested Loop, Cartesian.
- `spark.sql.autoBroadcastJoinThreshold` (default 10 MB). Join hints: `broadcast`, `merge`, `shuffle_hash`, `shuffle_replicate_nl`.
- **AQE** (on by default): partition coalescing, runtime join-strategy switching, **skew-join handling**, `advisoryPartitionSizeInBytes`.
- Bucketing (module 21) vs **storage-partitioned joins** (V2 tables like Iceberg).
- Reading plans: `explain()`, `explain("formatted")`, `explain("cost")`. Spotting `Exchange` (shuffle) and `BroadcastExchange`.
- Partitioning: `repartition(n)` vs `repartition(col)` vs `coalesce(n)`, `spark.sql.shuffle.partitions`, `spark.sql.files.maxPartitionBytes`.
- Caching: `cache`/`persist`, storage levels, when caching *hurts*, `unpersist`.
- Skew: diagnosing in the UI (one long task), salting, AQE skew join.
- Memory: executor memory layout (execution vs storage, overhead), spills, OOM causes, `collect()` dangers.
- Serialization costs (Python ↔ JVM) and why Arrow matters.
- Event logs + **History Server** instead of `input("press a key")`.

### Course modules
- **17-SparkJoinDemo**, **18-OuterJoinDemo**, **19-ShuffleJoinDemo**, **20-BroadcastingDemo**, **21-BucketJoinDemo**.

### Exercises
1. Run 19 with AQE **off** and then **on**, and record the physical plan and the number of reduce tasks each time.
2. Run 20 without the `broadcast()` hint: does AQE broadcast anyway? Then set `spark.sql.autoBroadcastJoinThreshold=-1` and `spark.sql.adaptive.autoBroadcastJoinThreshold=-1`.
3. Build a skewed dataset (90% of rows with one key), join it, find the straggler in the UI, then fix it with AQE skew join and separately with salting.
4. In 21, confirm there's **no `Exchange`** in the plan for the bucketed join. Then change one table to 4 buckets and observe what happens.
5. Enable `spark.eventLog.enabled=true`, start the History Server, and review a finished app's stages.

### Done when
- [ ] You can predict which join strategy Spark will choose and force a different one
- [ ] You can find the shuffle boundaries in any `explain()` output
- [ ] You can diagnose skew from the Spark UI and fix it in two ways
- [ ] You know the difference between `repartition` and `coalesce`, and when each causes a shuffle

---

## Phase 6 · Modern Python on Spark (Week 7)

**Goal:** extend Spark in Python *efficiently*. This area changed the most since the course.

### Topics ([07](07_modern_python_udfs_udtfs_datasources.md))
- Cost model: row-at-a-time Python UDF vs Arrow-optimized UDF (default in 4.2) vs pandas UDF vs Arrow UDF.
- `@udf(useArrow=True)`, `@pandas_udf` (Series→Series, Iterator, grouped agg), `@arrow_udf` (4.1).
- `applyInPandas`, `mapInPandas`, `applyInArrow`, `mapInArrow`.
- **Python UDTFs** (`@udtf`): table-valued functions, `LATERAL` usage, `spark.udtf.register`.
- **Python Data Source API**: custom batch/streaming readers and writers in pure Python, with filter pushdown (4.1).
- **SQL UDFs:** `CREATE FUNCTION f(x INT) RETURNS INT RETURN x + 1`. No Python overhead.
- Pandas API on Spark (`import pyspark.pandas as ps`) and when it fits.
- `toPandas()` / `createDataFrame(pandas_df)` / `toArrow()` and Arrow transfer.
- DataFrame **plotting** (`df.plot.line(...)`, Plotly backend, 4.0).
- Python profiling: `spark.profile.show()` / `render()`.
- Structured logging with `pyspark.logger.PySparkLogger`.

### Exercises
1. Implement `parse_gender` four ways (built-in, Python UDF, pandas UDF, Arrow UDF), time each on a 10× duplicated `survey.csv`, and use `spark.profile` on the slowest.
2. Write a UDTF that splits Apache log lines (module 09) into one row per query-string parameter.
3. Write a Python Data Source that reads a public REST API (or a local JSON folder) and use it with `spark.read.format("yoursource")`.
4. Replace a simple Python UDF with a SQL UDF and compare plans.

### Done when
- [ ] You can rank UDF types by performance and say why
- [ ] You've written and registered a UDTF and a Python Data Source
- [ ] You know when *not* to use a UDF at all

---

## Phase 7 · Modern Spark SQL (Week 8)

**Goal:** use the SQL language features added in 4.0–4.2.

### Topics ([08](08_new_sql_features.md), [05](05_ansi_mode_and_sql_behavior_changes.md))
- ANSI semantics in depth, type coercion, error classes and SQLSTATE codes.
- **VARIANT**: `parse_json`, `variant_get`, `try_variant_get`, `:` path syntax (4.1), shredding.
- **SQL pipe syntax** `|>`.
- **SQL scripting** (GA in 4.1): `BEGIN … END`, `DECLARE`, `IF`, `WHILE`, `FOR`, handlers.
- Session variables (`DECLARE VARIABLE`, `SET VAR`), `EXECUTE IMMEDIATE`, parameterized queries (`spark.sql(q, args={...})`).
- **Recursive CTEs** (4.1), `QUALIFY` (4.2), `TABLESAMPLE`.
- **Collations** (`COLLATE UTF8_LCASE`) for case-insensitive compare/sort.
- `MERGE INTO` (needs a table format that supports it, see Phase 10).
- Geospatial `GEOMETRY`/`GEOGRAPHY` + `ST_*` functions (4.2). Vector distance functions (4.2).
- Change Data Capture `CHANGES` clause (4.2, for tables that support it).

### Exercises
1. Load a nested JSON API response into VARIANT, extract five fields with `variant_get`, and compare with a `from_json` + explicit schema approach.
2. Write an org-chart query with a recursive CTE (employee → manager chain).
3. Write a SQL script that loops over the weeks in module 14's data and inserts per-week summaries into a table.
4. Use `COLLATE UTF8_LCASE` to group survey `Country` values case-insensitively.

### Done when
- [ ] You can choose between VARIANT and a typed struct for a given JSON workload
- [ ] You can write a recursive CTE and a SQL script from memory

---

## Phase 8 · Spark Connect and deployment (Week 9)

**Goal:** run Spark the way modern platforms run it, and ship real jobs.

### Topics ([06](06_spark_connect.md))
- Spark Connect architecture (gRPC + protobuf plans + Arrow results), `sc://` URIs, `pyspark-client` (~1.5 MB, no JVM).
- `spark.api.mode=connect` vs `classic`, and what isn't available under Connect (`sparkContext`, RDDs, `spark._jvm`).
- Running a local Connect server and pointing scripts at it.
- `spark-submit`: `--master`, `--deploy-mode`, `--py-files`, `--packages`, `--conf`, `--archives` (for venvs).
- Packaging Python dependencies: wheel + `--py-files`, packed venvs (`venv-pack`/conda-pack), Docker images.
- Cluster managers: Standalone, YARN, **Kubernetes** (Spark operator), and managed services (Databricks, AWS EMR / EMR Serverless, Google Dataproc / Serverless, Azure Synapse/Fabric). Learn one deeply; recognize the others.
- Configuration precedence: code `SparkConf` > `spark-submit --conf` > `spark-defaults.conf`.
- Dynamic allocation, executor sizing rules of thumb.

### Exercises
1. Run modules 13–16 under Spark Connect (`.remote("local[*]")` or `spark.api.mode=connect`). Fix whatever breaks (the `Log4J` helper will).
2. Package module 01 as a wheel and run it with `spark-submit --py-files`.
3. Run module 13 in a Docker container (the official `apache/spark` image or `spark:4.2.0-python3`; check Docker Hub for current tags).
4. Optional: run on a free-tier managed Spark (Databricks Free Edition or similar) and compare the experience.

### Done when
- [ ] Your code runs in both Classic and Connect mode
- [ ] You can submit a packaged PySpark job with third-party dependencies

---

## Phase 9 · Structured Streaming (Weeks 10–11)

**Goal:** build reliable streaming jobs. Not in the original course at all.

### Topics ([10](10_structured_streaming_modern.md))
- The micro-batch model: unbounded table, triggers (`processingTime`, `availableNow`, and **`realTime`** in 4.1/4.2), output modes (append/update/complete).
- Sources (file, Kafka, rate, Python streaming data sources) and sinks (file, Kafka, console, `foreachBatch`, tables).
- Checkpointing and exactly-once guarantees, idempotent sinks.
- Event time, **watermarks**, late data, tumbling/sliding/session windows.
- Stateful processing: streaming aggregations, `dropDuplicatesWithinWatermark`, stream-stream joins, **`transformWithState` / `transformWithStateInPandas`** (4.0) with ValueState/ListState/MapState and timers.
- **State Data Source** (`format("statestore")`) for debugging state.
- RocksDB state store, state store checksums and auto snapshot repair (4.2).
- **Named sources/sinks** (4.2) for checkpoint-safe evolution.
- Monitoring: `StreamingQueryListener`, `query.lastProgress`, the Structured Streaming UI tab.

### Exercises
1. File-source stream: drop CSV chunks of `invoices.csv` into a folder and maintain a running per-country revenue table.
2. Kafka (local via Docker): produce JSON events, parse them, use a 10-minute watermark and 5-minute tumbling windows, and write to Parquet.
3. Use `transformWithStateInPandas` to detect sessions per user with a 30-minute inactivity timeout.
4. Kill and restart the query and verify no duplicates (checkpoint recovery). Inspect the state with the `statestore` reader.

### Done when
- [ ] You can explain watermarks and output modes, and which combinations are allowed
- [ ] You can recover a streaming query from its checkpoint without data loss or duplicates

---

## Phase 10 · Lakehouse table formats (Week 12)

**Goal:** store data the way modern platforms do. "Parquet files in folders" is no longer the end state.

### Topics ([12](12_lakehouse_table_formats.md))
- Why table formats: ACID, schema evolution, time travel, MERGE/UPDATE/DELETE, concurrent writers.
- **Delta Lake 4.x** (pairs with Spark 4.x): setup, `MERGE`, time travel, `OPTIMIZE`, liquid clustering (`CLUSTER BY`), Change Data Feed, Deletion Vectors, UniForm.
- **Apache Iceberg** (Spark 4 runtime): catalogs (Hadoop, REST, Nessie/Polaris/Unity), hidden partitioning, partition evolution, snapshots, storage-partitioned joins.
- Catalogs: Hive metastore vs Unity Catalog OSS vs Iceberg REST catalogs.
- Spark 4 features that need these formats: `MERGE INTO`, `DataFrame.mergeInto`, `INSERT … WITH SCHEMA EVOLUTION` (4.2), the `CHANGES` clause (4.2).
- Medallion architecture (bronze/silver/gold) as a design pattern.

### Exercises
1. Convert module 06's bucketed table to a Delta table with `CLUSTER BY (OP_CARRIER, ORIGIN)`.
2. Implement an SCD Type 2 customer dimension with `MERGE`.
3. Time-travel to the previous version after a bad update and restore it.
4. Do the same exercise in Iceberg and note the differences.

### Done when
- [ ] You can explain what a table format adds over plain Parquet
- [ ] You can write an idempotent upsert pipeline with MERGE

---

## Phase 11 · Declarative Pipelines + production engineering (Weeks 13–14)

**Goal:** build maintainable pipelines with tests, quality checks and observability.

### Topics ([11](11_declarative_pipelines.md))
- **Spark Declarative Pipelines (SDP)** (4.1+): `from pyspark import pipelines as dp`, `@dp.materialized_view`, `@dp.table` (streaming table), `@dp.temporary_view`, `@dp.append_flow`, `dp.create_sink`, the `spark-pipeline.yml` spec, and the `spark-pipelines init / dry-run / run` CLI. Auto CDC for SCD1 (4.2).
- Project layout: `src/` package, `jobs/` entry points, config per environment, no hard-coded paths.
- Testing pyramid: pure-function unit tests, `assertDataFrameEqual` transformation tests, small end-to-end tests. Use `pytest` session fixtures for one SparkSession.
- Data quality: assertions in code, `Observation` metrics, expectation libraries (e.g. Great Expectations, Soda, pydantic-style schema checks), quarantine tables.
- Logging (`PySparkLogger`, JSON logs) and metrics (Prometheus endpoint, on by default since 4.0).
- CI: lint (`ruff`), type-check (`mypy`/`pyright`), and run tests against `local[2]` in GitHub Actions.
- Orchestration: Airflow / Dagster / Databricks Workflows: when you need an orchestrator vs when SDP is enough.
- Cost and performance hygiene: right-sizing, avoiding `collect`, file-size management, AQE settings.

### Exercises
1. Rebuild modules 13 → 14 → 16 as a Declarative Pipeline: bronze (raw invoices) → silver (typed, cleaned) → gold (weekly summary + top week per country).
2. Add `pytest` tests for each transformation function, plus a GitHub Actions workflow running them.
3. Add a data-quality gate that fails the pipeline if more than 1% of rows have NULL `InvoiceNo`.

### Done when
- [ ] `spark-pipelines dry-run` and `run` pass
- [ ] CI runs your tests automatically on every push

---

## Phase 12 · Capstone and certification (Weeks 15–16)

### Capstone options (pick one, build end to end)

1. **Web log analytics platform.** Stream synthetic Apache logs (like module 09) into Kafka → Structured Streaming → Delta bronze/silver/gold → dashboard. Covers streaming, watermarks, VARIANT for user-agent JSON, MERGE, SDP.
2. **Retail sales lakehouse.** Use `invoices.csv` (modules 13–16) scaled ×1000 with a generator → Iceberg tables → SCD2 customers → weekly/rolling KPIs with windows → tuned joins with a product dimension. Covers performance tuning, AQE, skew handling and testing.
3. **Flight delay analytics.** Use the flight-time data from modules 04/05/19–21 plus public BTS data → partitioned/clustered tables → join tuning → plotting with `df.plot`. Run it under Spark Connect.

**Capstone requirements:** explicit schemas, ANSI-safe parsing, at least one UDTF or Python Data Source, tests in CI, `explain()`-backed tuning notes, a README with architecture diagram, and runs in Connect mode.

### Certification (optional)
- **Databricks Certified Associate Developer for Apache Spark** is the most recognized Spark-specific cert. Check the Databricks certification page for the *current* exam guide; the exam tracks recent Spark versions and the topic weights change.
- The cert covers Phases 1–5 heavily, plus parts of 6, 8 and 9.

### Interview-ready topics checklist
- [ ] Narrow vs wide transformations; stages and shuffles
- [ ] All join strategies + when each is chosen
- [ ] AQE features; skew handling
- [ ] `repartition` vs `coalesce`; partition-count tuning
- [ ] `cache` vs `persist` and storage levels
- [ ] Driver OOM vs executor OOM causes
- [ ] UDF performance tiers
- [ ] Watermarks, output modes, checkpoints
- [ ] Table formats and MERGE
- [ ] Spark Connect vs Classic
- [ ] ANSI mode effects

---

## Resources

**Official (always current)**
- Spark docs (latest): https://spark.apache.org/docs/latest/
- PySpark API reference: https://spark.apache.org/docs/latest/api/python/reference/index.html
- PySpark user guide & upgrade guide: https://spark.apache.org/docs/latest/api/python/user_guide/index.html, https://spark.apache.org/docs/latest/api/python/migration_guide/pyspark_upgrade.html
- SQL reference: https://spark.apache.org/docs/latest/sql-ref.html
- Structured Streaming guide: https://spark.apache.org/docs/latest/streaming/index.html
- Declarative Pipelines guide: https://spark.apache.org/docs/latest/declarative-pipelines-programming-guide.html
- Tuning guide: https://spark.apache.org/docs/latest/sql-performance-tuning.html
- Release news: https://spark.apache.org/news/

**Table formats**
- Delta Lake: https://delta.io/ · docs: https://docs.delta.io/
- Apache Iceberg: https://iceberg.apache.org/

**Books** (check for editions covering Spark 4)
- *Learning Spark, 2nd ed.* (O'Reilly): great conceptual base, written for Spark 3.0.
- *Spark: The Definitive Guide* (O'Reilly): deep internals, older but still useful for fundamentals.

**Practice**
- Keep a `playground/` folder in this repo with one script per exercise, numbered like the docs.

---

## Weekly rhythm that works

1. **Day 1:** read the doc for the phase, skim official docs for the same topic.
2. **Days 2–3:** run and modify the course modules, and do the exercises.
3. **Day 4:** write a short note in your own words (add it to `docs/` as the next numbered file).
4. **Day 5:** open the Spark UI and `explain()` output for everything you built that week. Can you explain every stage?
