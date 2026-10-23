# 12 · Lakehouse Table Formats: Delta Lake and Apache Iceberg

Modules 05, 06 and 21 write **plain files** (Parquet/Avro/JSON/CSV) and **Hive-metastore tables** with `bucketBy`. That's still how Spark works at the lowest level, but in 2026 almost every production platform stores tables in an **open table format** on top of Parquet: **Delta Lake** or **Apache Iceberg** (and sometimes Apache Hudi).

---

## 1. Why table formats exist

Plain Parquet folders have no transactions. A failed job leaves half-written files, two writers corrupt each other, there's no `UPDATE`/`DELETE`/`MERGE`, and schema changes are risky.

A table format adds a **transaction log / metadata layer** next to the Parquet files:

```
my_table/
├── part-0001.parquet  part-0002.parquet ...     ← data (still Parquet)
└── _delta_log/  (Delta)   or   metadata/ (Iceberg)
    ├── 000000.json   ← "added files A,B"
    ├── 000001.json   ← "removed A, added C"  (an UPDATE)
    └── ...           ← readers see a consistent snapshot
```

| Capability | Plain Parquet | Delta / Iceberg |
|---|---|---|
| ACID transactions, concurrent writers | ✗ | ✓ |
| `MERGE` / `UPDATE` / `DELETE` | ✗ | ✓ |
| Time travel (query older versions) | ✗ | ✓ |
| Safe schema evolution | risky | ✓ |
| Partition evolution / hidden partitioning | ✗ | Iceberg ✓ (Delta: liquid clustering) |
| Data skipping via file statistics | limited | ✓ |
| Change feed / CDC | ✗ | ✓ |

Spark 4.x features that **need** such a format: `MERGE INTO` and `DataFrame.mergeInto`, row-level `UPDATE`/`DELETE`, `INSERT … WITH SCHEMA EVOLUTION` (4.2), the `CHANGES` clause (4.2), and storage-partitioned joins (Iceberg).

---

## 2. Delta Lake (pairs with Spark 4.x)

Versions as of Oct 2026: the Delta Lake **4.x** line targets Spark 4. Delta 4.1 dropped Spark 3.5 support and started putting the Spark version in the artifact name (e.g. `io.delta:delta-spark_4.1_2.13:4.1.0`). The newest releases (4.4.x, Aug 2026) are built for Spark 4.2. **Check the compatibility table at https://docs.delta.io/ before choosing coordinates.**

### Local setup with pip

```bash
pip install "pyspark==4.2.0" delta-spark      # pick the delta-spark version matching your Spark
```

```python
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

builder = (SparkSession.builder.master("local[3]").appName("delta")
           .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
           .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"))
spark = configure_spark_with_delta_pip(builder).getOrCreate()
```

### Core operations

```python
flights = spark.read.parquet("old_code_2024/06-SparkSQLTableDemo/dataSource/")

# module 06, the modern way: Delta + liquid clustering instead of bucketBy
spark.sql("CREATE DATABASE IF NOT EXISTS airline_db")
(flights.writeTo("airline_db.flights")
        .using("delta")
        .clusterBy("OP_CARRIER", "ORIGIN")      # liquid clustering (DataFrameWriterV2.clusterBy)
        .createOrReplace())

# UPDATE / DELETE
spark.sql("UPDATE airline_db.flights SET CANCELLED = 0 WHERE CANCELLED IS NULL")
spark.sql("DELETE FROM airline_db.flights WHERE DISTANCE <= 0")

# MERGE (upsert): SQL
spark.sql("""
MERGE INTO airline_db.flights t
USING updates s
ON t.FL_DATE = s.FL_DATE AND t.OP_CARRIER = s.OP_CARRIER AND t.OP_CARRIER_FL_NUM = s.OP_CARRIER_FL_NUM
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
""")

# MERGE: DataFrame API (Spark 4.0+)
from pyspark.sql import functions as F
(updates_df.alias("s")
   .mergeInto("airline_db.flights",
              F.expr("airline_db.flights.FL_DATE = s.FL_DATE AND "
                     "airline_db.flights.OP_CARRIER_FL_NUM = s.OP_CARRIER_FL_NUM"))
   .whenMatched().updateAll()
   .whenNotMatched().insertAll()
   .whenNotMatchedBySource().delete()      # optional: remove target rows missing from source
   .merge())

# Time travel
spark.sql("DESCRIBE HISTORY airline_db.flights").show()
spark.read.option("versionAsOf", 0).table("airline_db.flights")
spark.sql("RESTORE TABLE airline_db.flights TO VERSION AS OF 0")

# Maintenance
spark.sql("OPTIMIZE airline_db.flights")          # compaction + clustering
spark.sql("VACUUM airline_db.flights RETAIN 168 HOURS")
```

Other Delta features to learn: **Change Data Feed** (`delta.enableChangeDataFeed=true`, read with `readChangeFeed`), **Deletion Vectors** (fast deletes), **UniForm** (readable as Iceberg too), schema enforcement and `mergeSchema`, and the Delta **Kernel** for non-Spark engines.

---

## 3. Apache Iceberg

Iceberg's strengths are **engine neutrality** (Spark, Trino, Flink, Snowflake, DuckDB, …), **hidden partitioning** and **partition evolution**, and **REST catalogs** (Apache Polaris, Unity Catalog, Nessie, AWS Glue, …).

As of Oct 2026, Iceberg **1.12.0** (Sept 30, 2026) is the latest release, and Spark 4 runtimes are published as `iceberg-spark-runtime-4.x_2.13`. Pick the artifact matching your Spark minor version from https://iceberg.apache.org/releases/ or Maven Central.

```python
spark = (SparkSession.builder.master("local[3]")
         .config("spark.jars.packages",
                 "org.apache.iceberg:iceberg-spark-runtime-<spark-minor>_2.13:<iceberg-version>")
         .config("spark.sql.extensions",
                 "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
         .config("spark.sql.catalog.local", "org.apache.iceberg.spark.SparkCatalog")
         .config("spark.sql.catalog.local.type", "hadoop")
         .config("spark.sql.catalog.local.warehouse", "file:///tmp/iceberg-warehouse")
         .getOrCreate())

spark.sql("""
CREATE TABLE local.db.flights (FL_DATE DATE, OP_CARRIER STRING, ORIGIN STRING, DISTANCE INT, id BIGINT)
USING iceberg
PARTITIONED BY (days(FL_DATE), bucket(16, id))       -- hidden partitioning: queries just filter on FL_DATE
""")

spark.sql("SELECT * FROM local.db.flights.snapshots").show()            # metadata tables
spark.sql("SELECT * FROM local.db.flights VERSION AS OF <snapshot_id>")  # time travel
spark.sql("ALTER TABLE local.db.flights ADD PARTITION FIELD months(FL_DATE)")  # partition evolution
spark.sql("CALL local.system.rewrite_data_files('db.flights')")          # compaction
```

**Storage-partitioned join** (the modern version of module 21's bucket join): two Iceberg tables both `PARTITIONED BY (bucket(16, id))` can be joined on `id` **without a shuffle** when `spark.sql.sources.v2.bucketing.enabled=true` (default) and the related settings are configured. See [09 §8](09_joins_performance_and_aqe.md).

---

## 4. Delta vs Iceberg: quick decision

| If… | Lean towards |
|---|---|
| You're on Databricks, or mostly Spark | Delta |
| Many engines (Trino, Flink, Snowflake…) must read and write the same tables | Iceberg |
| You need partition evolution | Iceberg (or Delta liquid clustering) |
| You want both | Delta UniForm, or Iceberg REST catalogs that expose both |

Learn **one deeply** (MERGE, time travel, maintenance, schema evolution) and the other enough to read and write it. The concepts transfer.

---

## 5. Catalogs in one paragraph

A **catalog** maps table names to table metadata. The course uses the embedded **Hive metastore** (the `metastore_db/` Derby folder). Production uses a shared catalog: Hive Metastore service, **AWS Glue**, **Unity Catalog** (open source, multi-format), Iceberg **REST** catalogs (Polaris, Nessie, Lakekeeper…). Spark addresses them with `spark.sql.catalog.<name>=…` and three-part names `catalog.schema.table`.

---

## 6. Medallion architecture (design pattern)

```
 sources ─► BRONZE (raw, append-only, as received)
              │  try_cast / try_to_date, dedupe, conform types
              ▼
            SILVER (clean, typed, deduplicated, joined to keys)
              │  business aggregates, dimensional models
              ▼
            GOLD (reporting tables, features, KPIs)
```

It maps directly onto [11](11_declarative_pipelines.md) (one decorated function per table) and onto the course modules: 04/05 → bronze, 07–12 → silver, 13–16 → gold.

---

## 7. Exercises

1. Rebuild module 06's `flight_data_tbl` as a Delta table with `clusterBy("OP_CARRIER", "ORIGIN")`, run `OPTIMIZE`, and compare file counts with the bucketed CSV table.
2. Implement an SCD Type 2 customer dimension with `MERGE` (columns `valid_from`, `valid_to`, `is_current`).
3. Corrupt the table with a bad `UPDATE`, then fix it with `RESTORE … TO VERSION AS OF`.
4. Repeat 1 and 3 in Iceberg, and try partition evolution.
5. Rebuild module 21 with two Iceberg tables bucketed on `id` and look for the absence of `Exchange` in the join plan.

---

## Sources

- Delta Lake docs & releases: https://docs.delta.io/ · https://delta.io/blog/ (4.0.1, 4.1.0 and later release posts)
- Apache Iceberg releases & Spark docs: https://iceberg.apache.org/releases/ · https://iceberg.apache.org/docs/latest/spark-getting-started/
- Iceberg 1.12.0 overview (Dremio): https://www.dremio.com/blog/apache-iceberg-1-12-0-whats-new-breaking-changes-and-upgrade-guide
- Spark storage-partitioned join configs: https://spark.apache.org/docs/latest/sql-performance-tuning.html#storage-partition-join
- Spark 4.0 `DataFrame.mergeInto`, `clusterBy`: https://spark.apache.org/releases/spark-release-4-0-0.html
