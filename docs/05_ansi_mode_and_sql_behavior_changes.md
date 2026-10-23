# 05 · ANSI Mode and Spark SQL Behavior Changes (3.5 → 4.2)

The biggest *silent* difference between the Spark you learned and Spark 4 is **ANSI SQL mode, on by default since 4.0**. Code that "worked" on 3.5 by quietly producing NULLs or wrapped-around numbers now **fails loudly**. This is usually a good thing, because bad data no longer hides, but you need to know the rules.

---

## 1. What ANSI mode changes

Config: `spark.sql.ansi.enabled` (default **`true`** since 4.0). Env var alternative: `SPARK_ANSI_SQL_MODE`.

| Situation | Spark 3.5 (non-ANSI) | Spark 4 (ANSI) | Safe alternative |
|---|---|---|---|
| `CAST('abc' AS INT)` | `NULL` | **error** `CAST_INVALID_INPUT` | `try_cast('abc' AS INT)` / `col.try_cast("int")` |
| `to_date('13/45/2020', 'M/d/y')` | `NULL` | **error** `CANNOT_PARSE_TIMESTAMP` | `try_to_date(...)` / `try_to_timestamp(...)` |
| `2147483647 + 1` (INT overflow) | wraps to `-2147483648` | **error** `ARITHMETIC_OVERFLOW` | `try_add`, or cast to BIGINT first |
| `10 / 0` | `NULL` | **error** `DIVIDE_BY_ZERO` | `try_divide(10, 0)` |
| `array(1,2)[5]` / `element_at(arr, 5)` | `NULL` | **error** `INVALID_ARRAY_INDEX` | `try_element_at(arr, 5)`, `get(arr, 4)` |
| Decimal overflow | `NULL` | **error** | `try_*` arithmetic, or wider precision |
| Implicit string → number in comparisons | lenient | stricter type coercion rules | explicit casts |
| `SUM` result overflows BIGINT | wraps | **error** | `try_sum`, or cast to DECIMAL |

The `try_*` family (all return NULL instead of raising):
`try_cast`, `try_add`, `try_subtract`, `try_multiply`, `try_divide`, `try_mod`, `try_sum`, `try_avg`, `try_element_at`, `try_to_number`, `try_to_timestamp`, `try_to_date`, `try_to_binary`, `try_parse_json`, `try_variant_get`, `try_url_decode`, `try_aes_decrypt`, `try_reflect`, `try_make_timestamp`, …

### PySpark examples

```python
from pyspark.sql import functions as F

df = spark.createDataFrame([("42", "4/5/2020", 10, 0), ("xx", "13/45/2020", 5, 1)],
                           "s string, d string, a int, b int")

df.select(
    F.col("s").try_cast("int").alias("s_int"),              # 42, NULL
    F.try_to_date("d", "M/d/y").alias("d_date"),            # 2020-04-05, NULL
    F.try_divide("a", "b").alias("ratio"),                  # NULL, 5.0
).show()
```

### Should you turn ANSI off?

```python
spark.conf.set("spark.sql.ansi.enabled", "false")   # restores 3.x leniency
```

Only as a **temporary migration step** for legacy jobs. For new code keep ANSI on and use `try_*` at the *boundary* where untrusted data enters (bronze → silver). Everywhere else you *want* errors. They catch bugs that NULLs would hide.

### A useful pattern: quarantine bad rows instead of failing

```python
raw = spark.read.option("header", True).csv("data/invoices.csv")   # all strings

typed = raw.select(
    "*",
    F.col("Quantity").try_cast("int").alias("qty"),
    F.col("UnitPrice").try_cast("double").alias("price"),
    F.try_to_timestamp("InvoiceDate", F.lit("dd-MM-yyyy H.mm")).alias("ts"),
)

is_bad = F.col("qty").isNull() | F.col("price").isNull() | F.col("ts").isNull()
good, bad = typed.where(~is_bad), typed.where(is_bad)
bad.write.mode("append").parquet("quarantine/invoices")             # inspect later
```

---

## 2. Errors now have classes and SQLSTATEs

Spark errors are structured: an **error class** (e.g. `CAST_INVALID_INPUT`), a **SQLSTATE** (e.g. `22018`) and parameters. Catch them precisely in PySpark:

```python
from pyspark.errors import PySparkException, AnalysisException

try:
    spark.sql("SELECT CAST('abc' AS INT)").collect()
except PySparkException as e:
    print(e.getCondition())     # 'CAST_INVALID_INPUT' (older name: getErrorClass())
    print(e.getSqlState())      # '22018'
    print(e.getMessageParameters())
```

Full list: https://spark.apache.org/docs/latest/sql-error-conditions.html

---

## 3. Other SQL behavior changes since 3.5 that can affect you

### 3.5 → 4.0

| Change | Effect | Restore old behavior |
|---|---|---|
| ANSI on | see §1 | `spark.sql.ansi.enabled=false` |
| `CREATE TABLE t (...)` with no `USING`/`STORED AS` | uses `spark.sql.sources.default` (**parquet**), not Hive text format | `spark.sql.legacy.createHiveTableByDefault=true` |
| `spark.sql.legacy.timeParserPolicy` | `EXCEPTION` → **`CORRECTED`**: invalid input errors under ANSI, NULL without ANSI | `…=LEGACY` |
| ORC default codec | snappy → **zstd** | `spark.sql.orc.compression.codec=snappy` |
| `spark.sql.maxSinglePartitionBytes` | now 128 MB (was unlimited) | set higher |
| CTE name precedence | inner CTE shadows outer (`CORRECTED`) | `spark.sql.legacy.ctePrecedencePolicy` |
| `expr ! IN (...)` | now a syntax error, write `NOT IN` | `spark.sql.legacy.bangEqualsNot=true` |
| Map keys `-0.0` | normalized to `0.0` | `spark.sql.legacy.disableMapKeyNormalization=true` |
| `encode`/`decode` charsets | limited to standard UTF/ASCII/ISO-8859-1; malformed input errors | `spark.sql.legacy.javaCharsets`, `spark.sql.legacy.codingErrorAction` |
| Parquet codec name `lz4raw` | removed, use `lz4_raw` | — |
| Hive metastore < 2.0 | unsupported | — |
| JDBC type mappings (Postgres, MySQL, Oracle, MSSQL, DB2) | several types now map more precisely (e.g. MySQL `SMALLINT` → ShortType) | per-database `spark.sql.legacy.<db>.*` flags |

### 4.0 → 4.1

| Change | Effect |
|---|---|
| Pandas API on Spark | works under ANSI mode by default (`compute.ansi_mode_support=True`) |
| SQL Scripting & VARIANT | GA, **enabled by default** |
| `BinaryType` in Python | always `bytes` (was usually `bytearray`) · `spark.sql.execution.pyspark.binaryAsBytes=false` to revert |
| Arrow conversions | **safe by default**: overflow/truncation in pandas/Arrow UDF results raise · `spark.sql.execution.pandas.convertToArrowArraySafely=false` to revert |
| Parquet missing struct fields | nullness decided more accurately · `spark.sql.legacy.parquet.returnNullStructIfAllFieldsMissing=true` |
| Python 3.9 | dropped |

### 4.1 → 4.2

| Change | Effect | Revert |
|---|---|---|
| Arrow for `toPandas`/`createDataFrame(pandas)` | **on by default** | `spark.sql.execution.arrow.pyspark.enabled=false` |
| Arrow-optimized Python UDFs/UDTFs | **on by default** | `spark.sql.execution.pythonUDF.arrow.enabled=false` / `…pythonUDTF.arrow.enabled=false` |
| Pandas UDF nullable ints | arrive as nullable `Int64` etc. instead of `float64` | update UDF code |
| `createDataFrame(numpy_array)` | requires PyArrow; Arrow-based inference | — |
| `system.builtin` / `system.session` namespaces | `builtin.f()` / `session.f()` resolve to system first | `spark.sql.legacy.persistentCatalogFirst=true` |
| Empty-input `GROUP BY GROUPING SETS (())`/`CUBE()`/`ROLLUP()` | returns one grand-total row | `spark.sql.analyzer.lowerEmptyGroupingSetToGlobalAggregate.enabled=false` |
| Duplicate CTE names | rejected case-insensitively | — |
| Shuffle checksums | order-independent checksums on, with auto-retry on mismatch | `spark.sql.shuffle.orderIndependentChecksum.enabled=false` |
| `collect_set` | dedupes NaN and -0.0 by Spark equality | — |
| File-source writes | per-write `.option(...)` now beats session config | — |
| `Observation.get` | raises the underlying error on failure | — |
| Derby JDBC data source | deprecated | — |

---

## 4. How this maps onto the course modules

| Module | ANSI-sensitive code | Risk with the bundled data | Recommended change |
|---|---|---|---|
| 07, 08 | `to_date(col, "M/d/y")` | none (data is clean) | `try_to_date` for robustness + a bad-date test |
| 10 | `to_date(Timestamp, 'yyyy-MM-dd HH:mm:ss')` | none | — |
| 12 | `cast(IntegerType())` on strings | none | `try_cast` if data is untrusted |
| 13 | `sum(Quantity * UnitPrice)` | none (double) | — |
| 14 | `to_date(InvoiceDate, "dd-MM-yyyy H.mm")` | low | `try_to_date` |
| 04 | `FAILFAST` CSV mode + `dateFormat` | — | ANSI is unrelated here; `FAILFAST` was already strict |

---

## 5. Exercises

1. Run `spark.sql("SELECT CAST('abc' AS INT)")` with ANSI on and off, and catch the error with `PySparkException` to print its condition and SQLSTATE.
2. Write `safe_invoice_types(df)` that returns `(good_df, bad_df)` using `try_*` functions, and unit-test it with 3 good and 3 bad rows.
3. Find an integer overflow: `spark.range(1).select((F.lit(2**31 - 1).cast("int") + 1))`. Fix it two ways.
4. Create a table with plain `CREATE TABLE t (id INT)` on 4.x and check `DESCRIBE TABLE EXTENDED t` to see which provider it got.

---

## Sources

- SQL migration guide: https://spark.apache.org/docs/latest/sql-migration-guide.html
- ANSI compliance reference: https://spark.apache.org/docs/latest/sql-ref-ansi-compliance.html
- PySpark upgrade guide: https://spark.apache.org/docs/latest/api/python/migration_guide/pyspark_upgrade.html
- Error conditions: https://spark.apache.org/docs/latest/sql-error-conditions.html
