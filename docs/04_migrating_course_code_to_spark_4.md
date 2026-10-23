# 04 · Migrating the Course Code to Spark 4.x

Concrete, file-by-file changes that make the 21 modules run cleanly on Spark 4.2. The concepts in the course stay the same; these are the mechanical fixes. Background on *why* is in [01](01_course_audit_and_whats_changed.md) and [05](05_ansi_mode_and_sql_behavior_changes.md).

> Tip: before re-running any module, delete the stale local state left by Spark 3.5:
> ```bash
> find . -name metastore_db -type d -prune -exec rm -rf {} +
> find . -name spark-warehouse -type d -prune -exec rm -rf {} +
> find . -name derby.log -delete
> find . -name __pycache__ -type d -prune -exec rm -rf {} +
> ```
> The Derby metastore written by Spark 3.5 usually still opens on 4.x, but starting clean avoids confusing errors. (Modules 06 and 21 will recreate their tables. Remember to un-comment the table-creation block in 21 the first time.)

---

## 1. One shared SparkSession builder (optional but recommended)

Every module repeats the same `SparkConf` block. A small helper keeps things consistent and makes the Classic → Connect switch easy later:

```python
# lib/spark_session.py
import os
from pyspark.sql import SparkSession


def build_spark(app_name: str, master: str = "local[3]", **extra_conf) -> SparkSession:
    log4j2 = os.path.abspath("log4j2.properties")
    builder = (
        SparkSession.builder
        .appName(app_name)
        .master(master)
        .config("spark.driver.extraJavaOptions",
                f"-Dlog4j.configurationFile=file:{log4j2} "
                "-Dlogfile.name=hello-spark -Dspark.yarn.app.container.log.dir=app-logs")
    )
    for key, value in extra_conf.items():
        builder = builder.config(key.replace("__", "."), value)
    return builder.getOrCreate()
```

Usage:

```python
spark = build_spark("AggDemo")
# with extra configs (use __ for dots):
spark = build_spark("DataSinkDemo", spark__jars__packages="org.apache.spark:spark-avro_2.13:4.2.0")
```

If you prefer to keep the original `SparkConf` style, the only line that must change is the `-Dlog4j.configuration=…` option (see §2).

---

## 2. Logging: Log4j 1.x → Log4j 2

### 2a. Replace `log4j.properties` with `log4j2.properties`

Drop this file into each module (next to the old one, or replacing it). It reproduces the original setup: console + rolling file `app-logs/hello-spark.log`, with your `guru.learningjournal.spark.examples` logger at INFO.

```properties
# log4j2.properties (Log4j 2 syntax, Spark 3.3+)
status = warn

# Root logger: INFO to console + file (same as the course). Use "warn" to cut Spark's noise.
rootLogger.level = info
rootLogger.appenderRef.console.ref = console
rootLogger.appenderRef.file.ref = file

# Console appender
appender.console.type = Console
appender.console.name = console
appender.console.target = SYSTEM_OUT
appender.console.layout.type = PatternLayout
appender.console.layout.pattern = %d{yy/MM/dd HH:mm:ss} %p %c{1}: %m%n

# Rolling file appender
appender.file.type = RollingFile
appender.file.name = file
appender.file.fileName = app-logs/hello-spark.log
appender.file.filePattern = app-logs/hello-spark-%i.log
appender.file.layout.type = PatternLayout
appender.file.layout.pattern = %d{yy/MM/dd HH:mm:ss} %p %c{1}: %m%n
appender.file.policies.type = Policies
appender.file.policies.size.type = SizeBasedTriggeringPolicy
appender.file.policies.size.size = 500MB
appender.file.strategy.type = DefaultRolloverStrategy
appender.file.strategy.max = 2

# Application logger (non-additive, like the original)
logger.app.name = guru.learningjournal.spark.examples
logger.app.level = info
logger.app.additivity = false
logger.app.appenderRef.console.ref = console
logger.app.appenderRef.file.ref = file
```

### 2b. Point Spark at it

Old (Log4j 1.x property):
```python
.set("spark.driver.extraJavaOptions",
     "-Dlog4j.configuration=file:log4j.properties -Dlogfile.name=hello-spark ...")
```

New (Log4j 2 property):
```python
.set("spark.driver.extraJavaOptions",
     f"-Dlog4j.configurationFile=file:{os.path.abspath('log4j2.properties')} -Dlogfile.name=hello-spark ...")
```

For **01-HelloSpark**, change the line in `spark.conf` and the one in `lib/utils.py`:

```ini
# spark.conf
spark.driver.extraJavaOptions=-Dlog4j.configurationFile=file:log4j2.properties -Dlogfile.name=hello-spark -Dspark.yarn.app.container.log.dir=app-logs
```
```python
# lib/utils.py
log4j_path = os.path.abspath("log4j2.properties")
spark_conf.set("spark.driver.extraJavaOptions", f"-Dlog4j.configurationFile=file:{log4j_path}")
```

> Why did the old file work on 3.5.4? Log4j 2 has an *experimental* Log4j 1.x compatibility layer that kicks in when it sees `log4j.configuration`. Don't rely on it: the Spark migration guide asks you to rewrite configs in Log4j 2 syntax.

### 2c. Replace the `Log4J` helper (`lib/logger.py`)

The original helper calls `spark._jvm.org.apache.log4j`, the Log4j 1.x API through the bridge, and needs a local JVM. It **breaks under Spark Connect** because there is no `_jvm`. This version uses Log4j 2 directly in Classic mode and falls back to PySpark's structured Python logger in Connect mode, with the same `info/warn/error/debug` interface so no module code changes:

```python
# lib/logger.py
import logging

ROOT_CLASS = "guru.learningjournal.spark.examples"


class Log4J:
    def __init__(self, spark):
        app_name = spark.conf.get("spark.app.name")
        name = f"{ROOT_CLASS}.{app_name}"
        try:
            # Spark Classic: log through the driver's Log4j 2 so messages land in app-logs/
            self._logger = spark._jvm.org.apache.logging.log4j.LogManager.getLogger(name)
            self._jvm = True
        except Exception:
            # Spark Connect (no JVM in this process): structured JSON logging in Python
            from pyspark.logger import PySparkLogger
            self._logger = PySparkLogger.getLogger(name)
            self._logger.setLevel(logging.INFO)
            self._jvm = False

    def info(self, message):
        self._logger.info(str(message))

    def warn(self, message):
        (self._logger.warn if self._jvm else self._logger.warning)(str(message))

    def error(self, message):
        self._logger.error(str(message))

    def debug(self, message):
        self._logger.debug(str(message))
```

Notes:
- `str(message)` matters: the course passes non-strings (e.g. `logger.info(count_df.collect())`).
- `spark.conf.get("spark.app.name")` works in both modes, unlike `spark.sparkContext.getConf()`, which is Classic-only.
- If you'd rather use pure Python logging everywhere, `PySparkLogger` (Spark 4.0+) writes JSON lines with `ts`, `level`, `logger`, `msg` and a `context` dict built from keyword arguments:
  ```python
  from pyspark.logger import PySparkLogger
  log = PySparkLogger.getLogger("AggDemo")
  log.info("Loaded invoices", rows=541909, source="data/invoices.csv")
  ```

---

## 3. Avro package coordinates (05-DataSinkDemo, 06-SparkSQLTableDemo)

```python
# old: Scala 2.12, Spark 3.5.0
.set("spark.jars.packages", "org.apache.spark:spark-avro_2.12:3.5.0")

# new: Scala 2.13, must match your Spark version exactly
import pyspark
.set("spark.jars.packages", f"org.apache.spark:spark-avro_2.13:{pyspark.__version__}")
```

The rule for **any** Spark-module package (`spark-avro`, `spark-sql-kafka-0-10`, `spark-protobuf`, …): **Scala `_2.13` + exact Spark version**.

---

## 4. ANSI-mode fixes

ANSI mode is on by default in Spark 4. Clean data behaves the same; dirty data now **raises** instead of silently becoming NULL. Full explanation in [05](05_ansi_mode_and_sql_behavior_changes.md).

### 07-transformation & 08-RowDemo: `to_date`

The demo data (`04/05/2020`, `4/5/2020`, …) all parse with `M/d/y`, so the code works as-is. To make `to_date_df` safe for bad input:

```python
from pyspark.sql import functions as F

def to_date_df(df, fmt, fld):
    """Convert string date field to date type; unparsable values become NULL."""
    return df.withColumn(fld, F.try_to_date(F.col(fld), fmt))   # PySpark 4.0+
```

On Spark 3.5, use `F.to_date(F.try_to_timestamp(F.col(fld), F.lit(fmt)))` instead (note: `try_to_timestamp` takes the format as a Column, `try_to_date` as a plain string). Add a test case:

```python
def test_bad_date_becomes_null(spark):
    df = spark.createDataFrame([("1", "13/45/2020")], "ID string, EventDate string")
    assert to_date_df(df, "M/d/y", "EventDate").first()["EventDate"] is None
```

### 12-miscDemo: `cast`

```python
# strict: raises CAST_INVALID_INPUT for values like "xx"
.withColumn("day", F.col("day").cast("int"))

# tolerant: returns NULL for bad values
.withColumn("day", F.col("day").try_cast("int"))     # Column.try_cast, Spark 4.0+
.withColumn("day", F.expr("try_cast(day AS INT)"))   # SQL form, works on 3.2+
```

The `to_date(concat(day,'/',month,'/',year), 'd/M/y')` expression is fine under ANSI. If it might see impossible dates (e.g. day 31 in February), wrap it in `try_to_date`.

### 14-GroupingDemo: `to_date` with `dd-MM-yyyy H.mm`

Works on the sample `invoices.csv`. For safety:

```python
.withColumn("InvoiceDate", F.try_to_date(F.col("InvoiceDate"), "dd-MM-yyyy H.mm"))
```

---

## 5. Imports (10-ExploringColumns, 11-UDF_Demo, 12-miscDemo …)

Spark 4.0 changed `from pyspark.sql.functions import *` so it **only exports functions**. The current files are fine because they also do `from pyspark.sql import *` and `from pyspark.sql.types import *`. The recommended style is still:

```python
from pyspark.sql import SparkSession, Window, Row
from pyspark.sql import functions as F
from pyspark.sql import types as T
```

Benefits: no shadowing of Python built-ins (`sum`, `max`, `round`, `filter`), and readers can tell which names are Spark's.

---

## 6. 11-UDF_Demo: safer UDF + a no-UDF version

The UDF crashes on NULL `Gender` (`None.lower()`). Under 4.2 it also runs Arrow-optimized by default, so return types are checked strictly.

```python
import re
from pyspark.sql import functions as F

FEMALE = r"^f$|f.m|w.m"
MALE = r"^m$|ma|m.l"


@F.udf(returnType="string")
def parse_gender_udf(gender):
    if gender is None:
        return "Unknown"
    g = gender.lower()
    if re.search(FEMALE, g):
        return "Female"
    if re.search(MALE, g):
        return "Male"
    return "Unknown"


# Better: the same logic with built-ins (no Python serialization at all)
g = F.lower(F.col("Gender"))
gender_expr = (F.when(g.rlike(FEMALE), "Female")
                .when(g.rlike(MALE), "Male")
                .otherwise("Unknown"))
survey_df.withColumn("Gender", gender_expr).show(10)
```

> Note `rlike` uses Java regex and Python's `re` uses Python regex. These simple patterns behave the same in both, but check complex ones.

More UDF styles (pandas, Arrow, UDTF) are in [07](07_modern_python_udfs_udtfs_datasources.md).

---

## 7. 15-WindowingDemo: the "running total" is a moving sum

```python
# what the course code computes: sum of current + 2 previous weeks (a 3-week moving sum)
moving_3w = Window.partitionBy("Country").orderBy("WeekNumber").rowsBetween(-2, Window.currentRow)

# a true running (cumulative) total
running = Window.partitionBy("Country").orderBy("WeekNumber") \
                .rowsBetween(Window.unboundedPreceding, Window.currentRow)

summary_df \
    .withColumn("MovingSum3W", F.sum("InvoiceValue").over(moving_3w)) \
    .withColumn("RunningTotal", F.sum("InvoiceValue").over(running)) \
    .show()
```

---

## 8. 16-RankingDemo: tidy-ups

```python
rank_window = Window.partitionBy("Country").orderBy(F.col("InvoiceValue").desc())
# ranking functions ignore/require their own frame, so rowsBetween is unnecessary

(summary_df
    .withColumn("Rank", F.dense_rank().over(rank_window))
    .where(F.col("Rank") == 1)
    .sort("Country", "WeekNumber")
    .show())          # don't assign .show(): it returns None
```

SQL alternative with `QUALIFY` (Spark 4.2):

```python
summary_df.createOrReplaceTempView("summary")
spark.sql("""
    SELECT * FROM summary
    QUALIFY dense_rank() OVER (PARTITION BY Country ORDER BY InvoiceValue DESC) = 1
    ORDER BY Country, WeekNumber
""").show()
```

---

## 9. 19/20/21 join demos: AQE awareness and no more `input()`

- **AQE is on by default.** In 19-ShuffleJoinDemo you set `spark.sql.shuffle.partitions=3`, but AQE may coalesce or switch the join to a broadcast at runtime. To reproduce the course's "textbook" shuffle-join picture:
  ```python
  spark.conf.set("spark.sql.adaptive.enabled", "false")
  ```
  Then turn it back on and compare. That comparison *is* the lesson ([09](09_joins_performance_and_aqe.md)).
- **21-BucketJoinDemo** also disables `spark.sql.autoBroadcastJoinThreshold`. With AQE on, also set `spark.sql.adaptive.autoBroadcastJoinThreshold=-1` if you want to be sure no broadcast happens.
- **Replace `input("press a key to stop...")`** with event logs + History Server so you can inspect runs after they finish:
  ```python
  .config("spark.eventLog.enabled", "true")
  .config("spark.eventLog.dir", "file:///tmp/spark-events")
  ```
  ```bash
  mkdir -p /tmp/spark-events
  # needs the sbin/ scripts from a Spark distribution download (spark.apache.org/downloads.html)
  SPARK_HISTORY_OPTS="-Dspark.history.fs.logDirectory=file:///tmp/spark-events" \
    $SPARK_HOME/sbin/start-history-server.sh     # UI at http://localhost:18080 (SPARK_HOME = a Spark download)
  ```
  Keeping `input()` is fine for quick local experiments.

---

## 10. Repo hygiene

Add a `.gitignore` at the repo root:

```gitignore
.venv/
__pycache__/
*.pyc
app-logs/
metastore_db/
spark-warehouse/
derby.log
dataSink/
output/
.idea/workspace.xml
```

---

## Migration checklist

- [ ] Java 21 + Python 3.12/3.13 + PySpark 4.2 installed ([03](03_environment_setup_2026.md))
- [ ] `log4j2.properties` in each module; `-Dlog4j.configurationFile=` everywhere
- [ ] `lib/logger.py` replaced (works in Classic and Connect)
- [ ] Avro coordinates → `spark-avro_2.13:<spark version>`
- [ ] `to_date`/`cast` on untrusted data → `try_to_date` / `try_cast`
- [ ] `from pyspark.sql import functions as F` style
- [ ] UDF handles NULL; built-in alternative tried
- [ ] Window demo naming fixed
- [ ] Tests ported to pytest + `assertDataFrameEqual`
- [ ] Stale `metastore_db/`, `spark-warehouse/`, `__pycache__/` removed

## Sources

- Spark Core migration guide (Log4j 2): https://spark.apache.org/docs/latest/core-migration-guide.html
- PySpark logging (`PySparkLogger`): https://spark.apache.org/docs/latest/api/python/development/logger.html
- PySpark upgrade guide (wildcard import change, Arrow UDF defaults): https://spark.apache.org/docs/latest/api/python/migration_guide/pyspark_upgrade.html
- SQL migration guide (ANSI default, parser policy): https://spark.apache.org/docs/latest/sql-migration-guide.html
- Spark monitoring / History Server: https://spark.apache.org/docs/latest/monitoring.html
