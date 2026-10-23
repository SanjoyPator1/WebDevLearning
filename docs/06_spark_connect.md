# 06 · Spark Connect: The Modern Way to Talk to Spark

The course uses **Spark Classic**: your Python process starts a local JVM driver and controls it through Py4J (`spark._jvm`, `spark.sparkContext`). Since Spark 3.4, and in mature form since **4.0**, there's a second architecture, **Spark Connect**. It's how Databricks serverless, many notebooks and the thin `pyspark-client` package work. Learn both, and write code that runs on both.

---

## 1. Architecture

```
Spark Classic                                  Spark Connect
─────────────                                  ─────────────
┌──────────── your machine ───────────┐        ┌── client ──┐    gRPC     ┌──────── server ─────────┐
│ Python ──Py4J──► JVM driver ──► executors │   │ Python     │ ──────────► │ Spark Connect server    │
│ (same process tree, tight coupling)  │        │ (no JVM)   │ ◄────────── │ = driver ──► executors  │
└──────────────────────────────────────┘        └────────────┘  Arrow      └─────────────────────────┘
                                                  unresolved      results
                                                  plans (protobuf)
```

- The client builds **unresolved logical plans** (DataFrame operations) and sends them as **protobuf** over **gRPC** (default port **15002**).
- The server analyzes, optimizes and executes them, and streams results back as **Arrow** batches.
- The client has **no JVM**. `pip install pyspark-client` is about 1.5 MB.

**Why it matters**
- Client and server upgrade independently, and a crashing client doesn't kill the driver.
- Many users can share one cluster. Notebooks and IDEs connect remotely.
- Spark now has non-Python, non-JVM clients (Go, Rust, Swift as community projects) and a JDBC driver for Connect (4.1).

---

## 2. Running it locally

```bash
pip install "pyspark[connect]==4.2.0"
```

### Option A: let PySpark start a local Connect server for you

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.remote("local[*]").appName("connect-demo").getOrCreate()
print(type(spark))   # <class 'pyspark.sql.connect.session.SparkSession'>
spark.range(5).show()
```

### Option B: flip the API mode (same code, Connect underneath), Spark 4.0+

```python
spark = (SparkSession.builder
         .master("local[*]")
         .config("spark.api.mode", "connect")   # or "classic" (default)
         .getOrCreate())
```

Or without touching code: `export SPARK_API_MODE=connect` (or `SPARK_REMOTE=local[*]`) before running the script.

### Option C: a real server + a thin client

```bash
# on the "server" (needs a Spark distribution download)
$SPARK_HOME/sbin/start-connect-server.sh

# on the client, with only: pip install pyspark-client
python -c "
from pyspark.sql import SparkSession
spark = SparkSession.builder.remote('sc://localhost:15002').getOrCreate()
spark.range(3).show()"
```

`sc://` URIs can also carry params: `sc://host:15002/;user_id=me;token=...;use_ssl=true`.

---

## 3. What works differently under Connect

| Classic-only thing | Used in modules | Connect-friendly replacement |
|---|---|---|
| `spark.sparkContext` / `sc` | 02, 05, 07, 08, 01 (logger) | Use `SparkSession` APIs only |
| RDD API (`sc.textFile`, `map`, `reduceByKey`, `parallelize`) | 02, 07, 08 | DataFrame API: `spark.read.text`, `spark.createDataFrame(list_of_rows, schema)` |
| `df.rdd.getNumPartitions()` | 05 | `df.select(F.spark_partition_id()).distinct().count()` (or keep it Classic-only) |
| `spark._jvm` (Py4J) | every `lib/logger.py` | `PySparkLogger` / `logging` (see [04 §2c](04_migrating_course_code_to_spark_4.md)) |
| `spark.sparkContext.getConf().get(k)` | logger | `spark.conf.get(k)` |
| `sc.broadcast(v)`, accumulators | — | broadcast joins (`F.broadcast(df)`), or ship small lookups as DataFrames; `Observation` for metrics |
| `sc.setLogLevel("WARN")` | — | server-side log4j2 config |
| Eager column validation (`df["typo"]` errors immediately) | — | errors appear at execution/analysis time (since 4.1/4.2 the client no longer validates eagerly) |

Things that **work the same**: DataFrame API, SQL, temp views, catalog, UDFs/pandas UDFs/UDTFs (the server needs a matching Python), Structured Streaming, window functions, joins, reading/writing, `explain()`, MLlib (`pyspark.ml`, Connect GA for Python in 4.1).

### Module 07/08 rewritten without `sparkContext`

```python
from pyspark.sql import Row

my_rows = [Row("123", "04/05/2020"), Row("124", "4/5/2020"),
           Row("125", "04/5/2020"), Row("126", "4/05/2020")]
my_df = spark.createDataFrame(my_rows, my_schema).repartition(2)   # no parallelize needed
```

### Module 02 rewritten as DataFrame code (Connect-compatible)

```python
from pyspark.sql import functions as F

survey = spark.read.option("header", True).option("inferSchema", True).csv(path)
(survey.where("Age < 40")
       .groupBy("Country").count()
       .show())
```

---

## 4. Writing code that runs in both modes

1. Only use `SparkSession`, `DataFrame`, `Column`, `functions`, SQL. Avoid `sparkContext` and `_jvm`.
2. Get configs with `spark.conf.get(...)`.
3. Don't hold Python objects that assume a local JVM (Py4J objects, `JavaObject`s).
4. Test both modes in CI:

```python
# conftest.py
import os, pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="session", params=["classic", "connect"])
def spark(request):
    s = (SparkSession.builder.master("local[2]")
         .config("spark.api.mode", request.param)
         .config("spark.sql.shuffle.partitions", "2")
         .getOrCreate())
    yield s
    s.stop()
```

5. Check the mode at runtime if you must:
```python
from pyspark.sql.utils import is_remote
print("Connect" if is_remote() else "Classic")
```

---

## 5. Exercises

1. Run 13-AggDemo with `SPARK_API_MODE=connect`. What breaks? (The original logger, via `spark._jvm`.) Fix it with the doc 04 logger.
2. Rewrite 02-HelloRDD and 07-transformation so they don't touch `sparkContext`, then run both in Connect mode.
3. Start a Connect server from a Spark distribution and query it from a separate venv that only has `pyspark-client`.
4. Kill your client in the middle of a long query and observe that the server keeps running.

---

## Sources

- Spark Connect overview: https://spark.apache.org/docs/latest/spark-connect-overview.html
- PySpark install (pyspark-client, pyspark-connect): https://spark.apache.org/docs/latest/api/python/getting_started/install.html
- Spark 4.0 release notes (`spark.api.mode`, lightweight client): https://spark.apache.org/releases/spark-release-4-0-0.html
- PySpark upgrade guide (Connect column validation changes): https://spark.apache.org/docs/latest/api/python/migration_guide/pyspark_upgrade.html
