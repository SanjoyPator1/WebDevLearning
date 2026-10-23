# 01 · Course Audit: Is This PySpark Course Still Up to Date?

> Audit date: **2026-10-23** · Current Apache Spark: **4.2.0** (released 2026-07-14)
> Course reviewed: Learning Journal's *"Spark Programming in Python for Beginners"* (21 demo folders in this repo)

---

## TL;DR

| Question | Answer |
|---|---|
| Are the **concepts** still valid? | **Yes, ~90% of them.** DataFrames, schemas, readers/writers, transformations, aggregations, windows, joins, shuffle/broadcast/bucket joins: all of this is still core Spark knowledge. |
| Does the **code run unchanged** on today's Spark? | **No, not as-is.** Your environment (Python 3.8, Java 11, Spark 3.5.4) can't run Spark 4.x, and several files need small edits (logging config, Avro package coordinates, ANSI-mode-sensitive casts and date parsing). |
| Is anything **missing**? | **Yes, a lot.** Spark has had three feature releases since the course (4.0, 4.1, 4.2). They added Spark Connect, ANSI SQL by default, the VARIANT type, Python UDTFs and Data Sources, Arrow UDFs, SQL scripting, pipe syntax, Declarative Pipelines, Real-Time Mode streaming, and more. The course doesn't cover streaming or lakehouse table formats (Delta/Iceberg) at all. |
| Is the original course repo updated? | As far as public sources show, **no**. It still targets Spark 3.x. |

**Recommendation:** keep the course as your fundamentals base. Upgrade your environment ([03](03_environment_setup_2026.md)), apply the code fixes ([04](04_migrating_course_code_to_spark_4.md)), and then work through the new topics in docs 05–12 following the roadmap ([02](02_pyspark_learning_roadmap.md)).

---

## 1. What you ran back then vs. what's current

Taken from your own `app-logs/hello-spark.log` files and `.idea` settings:

| Component | Your course setup (Dec 2024) | Current (Oct 2026) | Impact |
|---|---|---|---|
| Spark | **3.5.4** | **4.2.0** (4.1.3, 4.0.4 also maintained) | Major version jump with behavior changes |
| Python | **3.8** | Spark 4.0 dropped 3.8, 4.1 dropped 3.9 → **3.10+ required** | Must upgrade Python |
| Java | **11** | Spark 4.x needs **Java 17 or 21** (4.2 also runs on Java 25) | Must upgrade Java |
| Scala build | 2.12 (`spark-avro_2.12`) | **2.13 only** | Package coordinates change |
| Logging | Log4j 1.x-style `log4j.properties` | Log4j **2** (since Spark 3.3) | Config file should be rewritten |
| pandas / PyArrow | (any) | pandas ≥ 2.2, PyArrow ≥ 18 (for 4.2 SQL/pandas features) | Upgrade if you use pandas/Arrow |
| Your Mac today | Python 3.14.7, **no Java installed** | Python 3.14 is supported from Spark 4.1 | Install a JDK (see doc 03) |

### Spark release timeline since your course

| Version | Date | Headline |
|---|---|---|
| 3.5.4 | Dec 2024 | ← you were here |
| **4.0.0** | 2025-05-23 | ANSI mode on by default, Spark Connect matured, VARIANT, Python Data Source API, UDTFs, pipe syntax, SQL UDFs, collations, plotting API, `transformWithState` |
| **4.1.0** | 2025-12-16 | Declarative Pipelines, Real-Time Mode streaming, Arrow-native UDFs, SQL Scripting GA, VARIANT GA, recursive CTEs, sketches, Python 3.10 minimum |
| **4.2.0** | 2026-07-14 | Arrow on by default for Python UDFs/`toPandas`, `QUALIFY`, CDC `CHANGES` clause, geospatial types, named streaming sources/sinks, Java 25 support |
| 4.3.0 | planned (Aug 2026 code freeze; not released as of this audit) | First release on the new quarterly cadence |

### Support policy (good to know)

- **3.5.x** is in an extended LTS period (security fixes only) ending **November 2027**. You *can* stay on 3.5 for a while, but you'd be learning a frozen version.
- Feature releases (4.0, 4.1, …) get roughly 6 months of maintenance. **4.2.x** has an 18-month window.
- The **4.x LTS will be 4.5.0**.
- Going forward, feature releases come **quarterly**.

---

## 2. Module-by-module audit

Legend: **OK**: still accurate and runs after the environment upgrade · **Update**: concept fine, code needs a change · **Extend**: concept fine, but there's a newer/better way you should also learn.

| # | Module | Concept still valid? | Status | What changed / what to do |
|---|---|---|---|---|
| 01 | HelloSpark (SparkConf from `spark.conf`, unit tests) | Yes | **Update** | `-Dlog4j.configuration` points at a Log4j 1.x file. Rewrite to `log4j2.properties` ([04 §2](04_migrating_course_code_to_spark_4.md)). Tests: switch to `pytest` + `pyspark.testing.assertDataFrameEqual`. |
| 02 | HelloRDD | Yes (for understanding) | **Extend** | RDDs are still there in Spark Classic but are **not the path forward**: Spark Connect (the modern client) is DataFrame-first. Learn it for internals, don't write new code with it. |
| 03 | HelloSparkSQL (temp views) | Yes | **OK / Extend** | Also learn **SQL pipe syntax** (`FROM t \|> WHERE … \|> AGGREGATE …`) and parameterized `spark.sql(query, args=…)`. |
| 04 | SparkSchema (CSV/JSON/Parquet, StructType vs DDL) | Yes | **OK / Extend** | Still core. New: the **VARIANT** type for semi-structured JSON, a built-in **XML** reader (4.0), and `spark.read.csv/json/xml` accept a DataFrame of strings as input (4.2). Date parsing under ANSI mode throws on bad input instead of returning NULL. |
| 05 | DataSinkDemo (Avro, partitionBy, maxRecordsPerFile) | Yes | **Update** | `spark-avro_2.12:3.5.0` → `spark-avro_2.13:<your Spark version>`, e.g. `4.2.0`. The Avro version **must match** your Spark version. ORC's default codec changed from snappy to **zstd** (4.0). |
| 06 | SparkSQLTableDemo (Hive metastore, bucketBy, saveAsTable) | Yes | **Extend** | Still works locally (embedded Derby metastore). In real projects managed tables are now mostly **Delta Lake / Iceberg** with partitioning or clustering. Bucketing is niche today. `CREATE TABLE` without `USING` now defaults to `spark.sql.sources.default` (parquet), **not Hive** (4.0). |
| 07 | transformation (to_date) | Yes | **Update** | Under ANSI mode (default in 4.0), `to_date` on an unparsable string **raises `CANNOT_PARSE_TIMESTAMP`** instead of returning NULL. Use `try_to_date` (4.0+) or `try_to_timestamp` for dirty data. |
| 08 | RowDemo + unit tests | Yes | **Extend** | Use `pytest` fixtures and `assertDataFrameEqual` / `assertSchemaEqual` (built in since 3.5). |
| 09 | LogFileDemo (regexp_extract) | Yes | **OK** | No changes needed. |
| 10 | ExploringColumns (col, column, selectExpr) | Yes | **OK** | Note: `from pyspark.sql.functions import *` **no longer re-exports non-function names** (like `DataFrame`, `StructType`) in 4.0. Import those explicitly. Prefer `from pyspark.sql import functions as F`. |
| 11 | UDF_Demo (Python UDF, register) | Yes | **Extend** | In 4.2 **Arrow-optimized Python UDFs are the default**. That's faster, with stricter type coercion. Learn `pandas_udf`, `arrow_udf` (4.1), **UDTFs** (4.0) and **SQL UDFs** (`CREATE FUNCTION … RETURN …`). Also: this UDF can be replaced by built-in `when/rlike` with no UDF at all ([07](07_modern_python_udfs_udtfs_datasources.md)). |
| 12 | miscDemo (cast, when, monotonically_increasing_id, dropDuplicates) | Yes | **Update** | `cast` on bad strings **throws** under ANSI. Use `try_cast` for messy input. |
| 13 | AggDemo | Yes | **OK** | Works. Extra: aggregate functions gained `IGNORE NULLS`, sketches, `approx_top_k`. |
| 14 | GroupingDemo (weekofyear, to_date) | Yes | **Update** | Same ANSI `to_date` caveat as 07. `groupingSets` is now in the DataFrame API (4.0). |
| 15 | WindowingDemo | Yes | **OK** (but see note) | Code note: the column is called `RunningTotal`, but `rowsBetween(-2, currentRow)` makes it a **3-week moving sum**. A true running total uses `Window.unboundedPreceding`. |
| 16 | RankingDemo | Yes | **Extend** | Works. New `QUALIFY` clause (4.2) filters on window results directly in SQL. The explicit `rowsBetween` frame on a ranking window isn't needed. (`df = ….show()` assigns `None`, a harmless bug.) |
| 17 | SparkJoinDemo | Yes | **OK** | Still valid. New: lateral joins and `NEAREST BY` top-K join (4.2) exist for special cases. |
| 18 | OuterJoinDemo | Yes | **OK** | No change. |
| 19 | ShuffleJoinDemo | Yes | **Extend** | **AQE** (Adaptive Query Execution, default on since 3.2) coalesces your 3 shuffle partitions and can turn a sort-merge join into a broadcast join *at runtime*. To see the "textbook" plan, turn AQE off temporarily. Learn `explain("formatted")`. |
| 20 | BroadcastingDemo | Yes | **OK / Extend** | `broadcast()` hint still correct. Also: join hints `merge`, `shuffle_hash`, `shuffle_replicate_nl`, and AQE's runtime broadcast threshold. |
| 21 | BucketJoinDemo | Yes | **Extend** | Works on the local Hive metastore. Modern equivalent: **storage-partitioned joins** on V2 tables (Iceberg/Delta). |

**Every demo** also uses `input("press a key to stop...")` to keep the Spark UI alive. A cleaner option today is to enable event logs and use the History Server ([09](09_joins_performance_and_aqe.md)).

---

## 3. Breaking changes that hit *this* code specifically

These are the concrete reasons the repo won't run on Spark 4.x without edits. Fixes are in [04](04_migrating_course_code_to_spark_4.md).

1. **Python 3.8 and Java 11 aren't supported.** You need Python 3.10+ and Java 17/21.
2. **Log4j config.** Every folder ships a Log4j **1.x** `log4j.properties` and passes `-Dlog4j.configuration=file:log4j.properties`. Spark has used Log4j 2 since 3.3. Your logs *did* work on 3.5.4 through Log4j 2's experimental 1.x compatibility layer, but Spark's migration guide says to rewrite configs in Log4j 2 syntax (`log4j2.properties` + `-Dlog4j.configurationFile=`).
3. **The `Log4J` helper uses `spark._jvm`.** That only exists in *Spark Classic*. Under **Spark Connect** (the modern client; `pyspark-client`, Databricks serverless and similar) there is no JVM gateway, so the helper crashes. Use `pyspark.logger.PySparkLogger` (4.0+) or Python's `logging` instead.
4. **The Avro package uses Scala 2.12 and Spark 3.5.0.** On Spark 4 you need `org.apache.spark:spark-avro_2.13:4.2.0` (or whatever matches your Spark).
5. **ANSI SQL mode is on by default** (`spark.sql.ansi.enabled=true`):
   - invalid `CAST` → error (`CAST_INVALID_INPUT`) instead of NULL
   - unparsable `to_date`/`to_timestamp` → error instead of NULL
   - integer overflow and divide-by-zero → error
   - Escape hatches: `try_cast`, `try_to_date`, `try_divide`, `try_add`, … or (not recommended) `spark.sql.ansi.enabled=false`.
6. **Wildcard import change.** `from pyspark.sql.functions import *` no longer pulls in `DataFrame`, `Column`, types, and so on. Your UDF/misc demos also import `from pyspark.sql.types import *`, so they're fine, but it's a common trap.
7. **Python UDFs use Arrow by default (4.2).** Your `parse_gender` UDF still works, but return values that don't match the declared type now fail loudly instead of being silently coerced.

---

## 4. Topics the course never covered (and that matter in 2026)

| Topic | Why it matters now | Doc |
|---|---|---|
| ANSI SQL mode & `try_*` functions | Default behavior since 4.0; affects every cast/parse | [05](05_ansi_mode_and_sql_behavior_changes.md) |
| **Spark Connect** | Client/server Spark: thin Python client, no JVM locally, how Databricks/serverless work | [06](06_spark_connect.md) |
| pandas UDFs, Arrow UDFs, **UDTFs**, **Python Data Sources** | Modern, fast ways to extend Spark in Python | [07](07_modern_python_udfs_udtfs_datasources.md) |
| VARIANT, pipe syntax, SQL scripting, SQL UDFs, recursive CTE, QUALIFY, collations | New SQL language features | [08](08_new_sql_features.md) |
| AQE, join hints, skew, explain plans, History Server | Updates the course's join/performance section | [09](09_joins_performance_and_aqe.md) |
| **Structured Streaming** (+ `transformWithState`, Real-Time Mode) | Not in the course at all | [10](10_structured_streaming_modern.md) |
| **Spark Declarative Pipelines** | New in 4.1: declarative ETL, `spark-pipelines` CLI | [11](11_declarative_pipelines.md) |
| **Lakehouse table formats** (Delta Lake, Iceberg) | How real data platforms store tables today (MERGE, time travel, clustering) | [12](12_lakehouse_table_formats.md) |
| Testing, packaging, logging, CI | Production habits | [03](03_environment_setup_2026.md), [04](04_migrating_course_code_to_spark_4.md) |

---

## 5. Sources

- Spark news & release list: https://spark.apache.org/news/
- Spark 4.0.0 release notes: https://spark.apache.org/releases/spark-release-4-0-0.html
- Spark 4.1.0 release notes: https://spark.apache.org/releases/spark-release-4.1.0.html
- Spark 4.2.0 release notes: https://spark.apache.org/releases/spark-release-4-2-0.html
- PySpark upgrade guide: https://spark.apache.org/docs/latest/api/python/migration_guide/pyspark_upgrade.html
- Spark SQL migration guide: https://spark.apache.org/docs/latest/sql-migration-guide.html
- Spark Core migration guide (Log4j 2 note under 3.2→3.3): https://spark.apache.org/docs/latest/core-migration-guide.html
- Versioning / LTS policy: https://spark.apache.org/versioning-policy.html
- PySpark installation requirements: https://spark.apache.org/docs/latest/api/python/getting_started/install.html
