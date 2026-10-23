# 07 · Modern Python on Spark: UDFs, Arrow, UDTFs and Python Data Sources

Module 11 (UDF_Demo) taught the classic row-at-a-time Python UDF. Since then Spark has added much faster and more capable ways to run Python: Arrow-optimized UDFs (default in 4.2), pandas UDFs, **Arrow UDFs** (4.1), **Python UDTFs** (4.0), **Arrow UDTFs** (4.1), **SQL UDFs** (4.0) and the **Python Data Source API** (4.0).

---

## 1. The decision ladder

Always go down this list and stop at the first option that works:

| # | Option | Python overhead | Use when |
|---|---|---|---|
| 1 | **Built-in functions** (`F.when`, `F.regexp_extract`, `F.transform`, higher-order functions…) | none | almost always possible; check first |
| 2 | **SQL UDF** (`CREATE FUNCTION … RETURN <sql expr>`) | none (inlined into the plan) | reusable logic expressible in SQL |
| 3 | **Arrow UDF** `@arrow_udf` (4.1) | low (columnar, zero-copy) | vectorized logic on `pyarrow.Array` |
| 4 | **pandas UDF** `@pandas_udf` | low (columnar via Arrow) | vectorized logic you'd write in pandas/numpy |
| 5 | **Arrow-optimized Python UDF** `@udf` (Arrow default in 4.2) | medium | scalar logic that only works per row (regex libs, parsing) |
| 6 | **Pickled row-at-a-time Python UDF** (`useArrow=False`) | high | legacy only |

Why Python UDFs are slow: each row (or batch) must be serialized from the JVM, sent to a Python worker process, processed, and sent back. The optimizer also can't see inside the function, so it can't push filters through it or reorder around it.

---

## 2. Scalar UDFs

### 2a. Classic `@udf`, now Arrow-optimized by default (4.2)

```python
from pyspark.sql import functions as F

@F.udf(returnType="string")                  # useArrow defaults to True in 4.2
def initials(name):
    return None if name is None else "".join(p[0] for p in name.split())

@F.udf(returnType="string", useArrow=False)  # force the old pickled path (rarely needed)
def legacy_initials(name): ...
```

What "Arrow-optimized" changes:
- data moves in Arrow batches, which is faster
- **stricter type handling:** returning `1` for a `"string"` UDF, or a float for `"int"`, now errors instead of being silently coerced. Since 4.1, PyArrow's safe conversion is the default (`spark.sql.execution.pandas.convertToArrowArraySafely=true`).

### 2b. pandas UDF (Series → Series)

```python
import pandas as pd
import numpy as np
from pyspark.sql.functions import pandas_udf

@pandas_udf("string")
def parse_gender_vec(g: pd.Series) -> pd.Series:
    s = g.fillna("").str.lower()
    return pd.Series(np.select(
        [s.str.contains(r"^f$|f.m|w.m"), s.str.contains(r"^m$|ma|m.l")],
        ["Female", "Male"], default="Unknown"))

survey_df.withColumn("Gender", parse_gender_vec("Gender"))
```

The type hints define the UDF kind:

| Signature | Kind |
|---|---|
| `(pd.Series, ...) -> pd.Series` | scalar |
| `(Iterator[pd.Series]) -> Iterator[pd.Series]` | scalar iterator: do expensive setup (load a model) **once per partition** |
| `(pd.Series, ...) -> float` (or scalar) | grouped aggregate, usable in `groupBy().agg()` and windows |

```python
from typing import Iterator

@pandas_udf("double")
def score(batches: Iterator[pd.Series]) -> Iterator[pd.Series]:
    model = load_model()            # runs once per partition, not per row
    for s in batches:
        yield pd.Series(model.predict(s.to_numpy().reshape(-1, 1)))

@pandas_udf("double")
def median_price(p: pd.Series) -> float:
    return float(p.median())

invoice_df.groupBy("Country").agg(median_price("UnitPrice").alias("MedianPrice"))
```

Spark 4.2 note: nullable integer columns now arrive as pandas nullable dtypes (`Int64`) instead of `float64`.

### 2c. Arrow UDF (4.1+): pandas-free and zero-copy

```python
import pyarrow as pa
import pyarrow.compute as pc
from pyspark.sql.functions import arrow_udf

@arrow_udf("string")
def to_upper(s: pa.Array) -> pa.Array:
    return pc.ascii_upper(s)

@arrow_udf("double")
def line_total(qty: pa.Array, price: pa.Array) -> pa.Array:
    return pc.multiply(pc.cast(qty, pa.float64()), price)

invoice_df.select(line_total("Quantity", "UnitPrice").alias("LineTotal"))
```

Arrow UDFs also support iterator and grouped-aggregate forms (Spark 4.2 added iterator APIs for grouped aggregation), with `pa.Array` in every type hint.

### 2d. Registering for SQL (module 11's second half)

```python
spark.udf.register("parse_gender_udf", parse_gender_vec)   # works for udf/pandas_udf/arrow_udf
spark.sql("SELECT parse_gender_udf(Gender) FROM survey").show()
```

---

## 3. SQL UDFs (4.0+): zero Python overhead

```python
spark.sql("""
CREATE OR REPLACE TEMPORARY FUNCTION parse_gender(g STRING)
RETURNS STRING
RETURN CASE
  WHEN lower(g) RLIKE '^f$|f.m|w.m' THEN 'Female'
  WHEN lower(g) RLIKE '^m$|ma|m.l'  THEN 'Male'
  ELSE 'Unknown' END
""")
survey_df.selectExpr("parse_gender(Gender) AS Gender").show()
```

The body is inlined into the query plan, so it gets the full optimizer and no serialization. Drop `TEMPORARY` to persist it in the catalog. Table-valued SQL functions (`RETURNS TABLE (...)`) also exist.

---

## 4. DataFrame-level Python functions

| API | Input → output | Typical use |
|---|---|---|
| `df.groupBy(k).applyInPandas(fn, schema)` | one pandas DataFrame per group → pandas DataFrame | per-group modeling, complex group logic |
| `df.mapInPandas(fn, schema)` | iterator of pandas DataFrames → iterator | batch transforms, calling external libs |
| `df.groupBy(k).applyInArrow(fn, schema)` | `pa.Table` per group → `pa.Table` | same, Arrow-native |
| `df.mapInArrow(fn, schema)` | iterator of `RecordBatch` → iterator | same, Arrow-native |
| `df1.groupBy(k).cogroup(df2.groupBy(k)).applyInPandas(fn, schema)` | two groups → one DataFrame | as-of joins, custom merges |

```python
def normalize(pdf: pd.DataFrame) -> pd.DataFrame:
    pdf["z"] = (pdf.InvoiceValue - pdf.InvoiceValue.mean()) / pdf.InvoiceValue.std()
    return pdf

summary_df.groupBy("Country").applyInPandas(
    normalize, schema="Country string, WeekNumber int, NumInvoices long, "
                      "TotalQuantity long, InvoiceValue double, z double")
```

Spark 4.1 caps Arrow batch sizes in `applyInPandas`/`applyInArrow`, which reduces OOMs on big groups.

---

## 5. Python UDTFs: functions that return *tables* (4.0+)

A UDTF yields **zero or more rows per input**, like `explode` but with your own logic.

```python
from pyspark.sql.functions import udtf, lit

@udtf(returnType="word string, length int")
class SplitWords:
    def eval(self, text: str):
        for w in (text or "").split():
            yield w, len(w)

# DataFrame usage
SplitWords(lit("hello modern spark")).show()

# SQL usage (including LATERAL against another table)
spark.udtf.register("split_words", SplitWords)
spark.sql("SELECT * FROM split_words('hello modern spark')").show()
spark.sql("""
  SELECT s.Country, w.word
  FROM survey s, LATERAL split_words(s.comments) w
""").show()
```

Advanced UDTF features:
- `terminate(self)`: emit final rows after all input (aggregating UDTFs).
- `@staticmethod analyze(...)`: compute the output schema dynamically from the arguments.
- **Table arguments**: `SELECT * FROM my_udtf(TABLE(t) PARTITION BY k ORDER BY ts)`, or `MyUDTF(df.asTable())` in Python. Rows are delivered per partition, which is great for sessionization.
- Named arguments: `split_words(text => 'a b')`.

### Arrow UDTF (4.1+)

```python
import pyarrow as pa
from pyspark.sql.functions import arrow_udtf

@arrow_udtf(returnType="x long, doubled long")
class Doubler:
    def eval(self, batch: pa.RecordBatch):
        x = batch.column("x")
        yield pa.table({"x": x, "doubled": pa.compute.multiply(x, 2)})

Doubler(spark.range(5).selectExpr("id AS x").asTable()).show()
```

---

## 6. Python Data Source API (4.0+): custom connectors in pure Python

Before 4.0, a custom source meant writing Scala/Java. Now you can implement readers and writers (batch **and** streaming) in Python:

```python
from pyspark.sql.datasource import DataSource, DataSourceReader, EqualTo
from pyspark.sql.types import StructType


class CountriesSource(DataSource):
    """spark.read.format("countries").option("rows", 5).load()"""

    @classmethod
    def name(cls):
        return "countries"

    def schema(self):
        return "id int, country string"

    def reader(self, schema: StructType):
        return CountriesReader(self.options)


class CountriesReader(DataSourceReader):
    def __init__(self, options):
        self.rows = int(options.get("rows", 3))
        self.only_id = None

    def pushFilters(self, filters):            # 4.1+: optional filter pushdown
        for f in filters:
            if isinstance(f, EqualTo) and f.attribute == ("id",):
                self.only_id = f.value          # handle it ourselves
            else:
                yield f                         # Spark must still apply this one

    def read(self, partition):
        data = ["India", "Canada", "Brazil", "Japan", "Kenya"]
        for i in range(min(self.rows, len(data))):
            if self.only_id is None or i == self.only_id:
                yield (i, data[i])


spark.dataSource.register(CountriesSource)
spark.read.format("countries").option("rows", 5).load().where("id = 2").show()
```

Other pieces of the API:
- `partitions()` returns `InputPartition`s, so reads run in parallel.
- `writer(schema, overwrite)` → `DataSourceWriter.write(iterator)` + `commit(messages)` for batch writes. There's also an Arrow-based writer.
- `streamReader(schema)` / `simpleStreamReader(schema)` for streaming sources with offsets. `streamWriter` for streaming sinks.
- 4.2: Arrow data returned with the wrong types fails with `DATA_SOURCE_RETURN_SCHEMA_MISMATCH`. A simple stream reader must advance its offset.

Ideas: REST APIs, Google Sheets, internal services, synthetic test data generators.

---

## 7. Pandas API on Spark, plotting and profiling

```python
import pyspark.pandas as ps
psdf = ps.read_csv("data/invoices.csv")
psdf.groupby("Country")["Quantity"].sum().sort_values(ascending=False).head(10)
```
Use it when porting pandas code. For new code, prefer the DataFrame API. Since 4.1 it works under ANSI mode by default.

**Native plotting** (4.0+, needs `plotly`):
```python
summary_df.where("Country = 'United Kingdom'").plot.line(x="WeekNumber", y="InvoiceValue")
summary_df.groupBy("Country").sum("InvoiceValue").plot.bar(x="Country", y="sum(InvoiceValue)")
```

**UDF profiling** (4.0+):
```python
spark.conf.set("spark.sql.pyspark.udf.profiler", "perf")   # or "memory"
survey_df.select(parse_gender_vec("Gender")).collect()
spark.profile.show(type="perf")
```

---

## 8. Exercises

1. Implement `parse_gender` as built-in, SQL UDF, `@udf`, `@pandas_udf` and `@arrow_udf`. Run each on `survey.csv` unioned with itself 50 times, and compare wall time plus the SQL tab (look for `ArrowEvalPython` / `BatchEvalPython` nodes).
2. Write a UDTF that takes an Apache log line (module 09) and yields `(param, value)` for each query-string parameter in the request URL.
3. Write a UDTF with `terminate()` that outputs the top 3 longest words seen per partition.
4. Build a Python Data Source for a public JSON API (or a folder of JSON files) with `partitions()` and a filter pushdown.
5. Profile your slowest UDF with `spark.profile.show()`.

---

## Sources

- Python UDFs / Arrow / pandas UDFs: https://spark.apache.org/docs/latest/api/python/tutorial/sql/arrow_pandas.html
- `arrow_udf` reference: https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.functions.arrow_udf.html
- Python UDTFs: https://spark.apache.org/docs/latest/api/python/tutorial/sql/python_udtf.html
- Python Data Source API: https://spark.apache.org/docs/latest/api/python/tutorial/sql/python_data_source.html
- SQL `CREATE FUNCTION`: https://spark.apache.org/docs/latest/sql-ref-syntax-ddl-create-sql-function.html
- PySpark upgrade guide (Arrow defaults in 4.2): https://spark.apache.org/docs/latest/api/python/migration_guide/pyspark_upgrade.html
- PySpark 4.2.0 source (signatures verified): https://github.com/apache/spark/tree/v4.2.0/python/pyspark
