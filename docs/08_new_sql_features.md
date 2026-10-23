# 08 · New Spark SQL Features (4.0 → 4.2)

The course's SQL (modules 03, 06, 13) is standard SELECT/GROUP BY, which is all still valid. Spark 4.x added a lot of language features. This doc covers each one with an example on the course data where possible. All of them run through `spark.sql("...")` in PySpark.

Setup used in the examples:

```python
invoice_df = spark.read.option("header", True).option("inferSchema", True).csv("old_code_2024/13-AggDemo/data/invoices.csv")
invoice_df.createOrReplaceTempView("sales")
spark.read.parquet("old_code_2024/15-WindowingDemo/data/summary.parquet").createOrReplaceTempView("summary")
```

---

## 1. SQL pipe syntax `|>` (4.0)

Write queries **top-down in execution order** instead of SELECT-first. Each `|>` step takes the previous result as input. It mixes freely with normal SQL.

Module 13's summary query, classic:
```sql
SELECT Country, InvoiceNo, sum(Quantity) AS TotalQuantity,
       round(sum(Quantity * UnitPrice), 2) AS InvoiceValue
FROM sales
GROUP BY Country, InvoiceNo
```

Same query with pipes, plus a top-10 filter:
```sql
FROM sales
|> WHERE Quantity > 0
|> EXTEND Quantity * UnitPrice AS LineValue
|> AGGREGATE sum(Quantity) AS TotalQuantity, round(sum(LineValue), 2) AS InvoiceValue
   GROUP BY Country, InvoiceNo
|> ORDER BY InvoiceValue DESC
|> LIMIT 10
```

Operators: `SELECT`, `EXTEND` (add columns), `SET` (replace a column), `DROP`, `AS` (alias the intermediate table), `WHERE`, `AGGREGATE … [GROUP BY …]`, `[LEFT|…|LATERAL] JOIN`, `ORDER BY`, `LIMIT/OFFSET`, `UNION/INTERSECT/EXCEPT`, `PIVOT/UNPIVOT`, `TABLESAMPLE`.

Why use it: it reads like a DataFrame chain, avoids nested subqueries, and you can debug by deleting trailing steps.

---

## 2. `QUALIFY` (4.2): filter on window functions

Module 16 (top week per country), no subquery needed:

```sql
SELECT Country, WeekNumber, InvoiceValue,
       dense_rank() OVER (PARTITION BY Country ORDER BY InvoiceValue DESC) AS rnk
FROM summary
QUALIFY rnk = 1
ORDER BY Country
```

---

## 3. VARIANT: semi-structured data without a schema (4.0, GA 4.1)

`VARIANT` stores JSON-like data in an efficient binary form. You don't need to declare a schema up front, and querying it is much faster than re-parsing JSON strings.

```python
from pyspark.sql import functions as F

events = spark.createDataFrame(
    [('{"user": {"id": 7, "country": "IN"}, "items": [{"sku": "A1", "qty": 2}]}',),
     ('{"user": {"id": 9}, "items": [], "coupon": "NEW10"}',)],
    "raw string")

v = events.select(F.parse_json("raw").alias("v"))      # try_parse_json → NULL on bad JSON

v.select(
    F.variant_get("v", "$.user.id", "int").alias("user_id"),
    F.try_variant_get("v", "$.user.country", "string").alias("country"),
    F.variant_get("v", "$.items[0].sku", "string").alias("first_sku"),
    F.schema_of_variant("v").alias("schema"),
).show(truncate=False)
```

SQL, including the `:` path syntax (4.1):
```sql
SELECT v:user.id::int AS user_id, v:coupon::string AS coupon
FROM (SELECT parse_json(raw) AS v FROM events)
```

| Approach | Use when |
|---|---|
| `from_json(col, schema)` → STRUCT | schema is known and stable; best compression and pruning |
| `VARIANT` | schema varies, evolves, or is deeply nested and sparse |
| JSON string + `get_json_object` | legacy; avoid for new code |

4.1 added **shredding** when writing VARIANT to Parquet: frequently used fields are stored as real columns, so reads get columnar speed. It also added Parquet Variant logical-type reads and CSV/XML scans into VARIANT.

---

## 4. SQL scripting (4.0 preview, GA + on by default in 4.1)

Procedural SQL: variables, control flow and error handlers, all inside `BEGIN … END`.

```python
spark.sql("""
BEGIN
  DECLARE week INT DEFAULT 48;
  CREATE TABLE IF NOT EXISTS weekly_uk (WeekNumber INT, InvoiceValue DOUBLE) USING parquet;

  WHILE week <= 51 DO
    INSERT INTO weekly_uk
      SELECT WeekNumber, InvoiceValue FROM summary
      WHERE Country = 'United Kingdom' AND WeekNumber = week;
    SET week = week + 1;
  END WHILE;

  SELECT * FROM weekly_uk ORDER BY WeekNumber;
END
""").show()
```

Available statements: `DECLARE` (several variables at once since 4.1), `SET`, `IF/ELSEIF/ELSE`, `CASE`, `WHILE`, `REPEAT`, `LOOP`, `FOR row AS (query) DO …`, `LEAVE`, `ITERATE`, cursors (`OPEN`/`FETCH`/`CLOSE`), `EXECUTE IMMEDIATE`, and condition handlers:

```sql
BEGIN
  DECLARE EXIT HANDLER FOR DIVIDE_BY_ZERO
    BEGIN SELECT 'division failed, using default' AS msg; END;
  SELECT 10 / 0;
END
```

(`CONTINUE HANDLER` was added in 4.1.)

---

## 5. Session variables, parameters and `EXECUTE IMMEDIATE` (4.0)

```sql
DECLARE VARIABLE min_qty INT DEFAULT 10;
SET VAR min_qty = 20;
SELECT * FROM sales WHERE Quantity >= min_qty;

DECLARE VARIABLE stmt STRING DEFAULT 'SELECT count(*) FROM sales WHERE Quantity > ?';
EXECUTE IMMEDIATE stmt USING 10;
```

From Python, prefer **parameterized queries** (safe against SQL injection):

```python
spark.sql("SELECT * FROM sales WHERE Country = :c AND Quantity > :q",
          args={"c": "France", "q": 10}).show()
```

---

## 6. SQL user-defined functions (4.0)

```sql
CREATE OR REPLACE TEMPORARY FUNCTION line_value(q INT, p DOUBLE)
RETURNS DOUBLE
RETURN round(q * p, 2);

SELECT InvoiceNo, sum(line_value(Quantity, UnitPrice)) FROM sales GROUP BY InvoiceNo;
```

Table-valued SQL functions use `RETURNS TABLE (col type, …) RETURN SELECT …`. See [07 §3](07_modern_python_udfs_udtfs_datasources.md) for why SQL UDFs beat Python UDFs.

---

## 7. Recursive CTEs (4.1)

```sql
WITH RECURSIVE weeks(n) AS (
  SELECT 1
  UNION ALL
  SELECT n + 1 FROM weeks WHERE n < 52
)
SELECT w.n AS WeekNumber, coalesce(s.InvoiceValue, 0) AS InvoiceValue
FROM weeks w LEFT JOIN summary s ON s.WeekNumber = w.n AND s.Country = 'France'
ORDER BY w.n
```

Typical uses: hierarchies (employee → manager, category trees), graph walks, generating sequences with gaps filled.

---

## 8. Collations (4.0): case/accent-insensitive strings

```sql
SELECT 'Spark' = 'SPARK' COLLATE UTF8_LCASE;          -- true

SELECT Country COLLATE UTF8_LCASE AS c, count(*)       -- groups 'france', 'France', 'FRANCE'
FROM sales GROUP BY 1;

SHOW COLLATIONS;                                        -- list available collations
```

Collations also exist for ICU locales (e.g. `UNICODE_CI`, language-specific sorting).

---

## 9. Other additions worth knowing

| Feature | Version | Example / note |
|---|---|---|
| `MERGE INTO` (SQL + `df.mergeInto(...)`) | 4.0 | Needs a table format that supports row-level ops (Delta, Iceberg), see [12](12_lakehouse_table_formats.md) |
| Lateral joins in DataFrame API | 4.0 | `df.lateralJoin(...)` |
| `groupingSets` in DataFrame API | 4.0 | `df.groupingSets([["Country"], ["Country", "WeekNumber"]], "Country", "WeekNumber").agg(...)` |
| `df.transpose()` | 4.0 | swap rows/columns of small results |
| `DESCRIBE TABLE … AS JSON` | 4.0 | machine-readable table metadata |
| Built-in XML data source | 4.0 | `spark.read.option("rowTag", "book").xml(path)` |
| `WITH (option=…)` dynamic table options | 4.0 | per-query reader options in SQL |
| `try_to_date`, `uuid`, `random`, `chr` | 4.0/4.1 | more `try_*` + utility functions |
| Sketches: KLL quantiles, Theta, `approx_top_k` | 4.1 | `kll_sketch_agg_double`, `theta_sketch_agg`; mergeable approximate aggregates |
| `IGNORE NULLS` for `array_agg`/`collect_list`/`collect_set` | 4.2 | `collect_list(x) IGNORE NULLS` |
| `time_bucket` | 4.2 | bucket timestamps into fixed intervals |
| `TABLESAMPLE SYSTEM` | 4.2 | block-level sampling with pushdown |
| `INSERT INTO … WITH SCHEMA EVOLUTION` | 4.2 | auto-add new columns (format permitting) |
| `CHANGES` clause / `df.changes()` | 4.2 | read change data from tables that support CDC |
| `NEAREST BY` top-K ranking join | 4.2 | nearest-neighbor style joins |
| Geospatial `GEOMETRY(srid)` / `GEOGRAPHY(srid)` | 4.2 | Basic so far: `ST_GeomFromWKB`, `ST_GeogFromWKB`, `ST_AsBinary`, `ST_Srid`, `ST_SetSrid`, plus Parquet read/write |
| Metric views `CREATE VIEW … WITH METRICS` | 4.2 | semantic-layer style metric definitions |
| Search path `SET PATH` / `current_path()` | 4.2 | opt-in (`spark.sql.path.enabled`) |
| `system.builtin` / `system.session` namespaces | 4.2 | qualify built-ins and temp objects explicitly |

---

## 10. Exercises

1. Rewrite modules 13 and 14's queries in pipe syntax.
2. Solve module 16 with `QUALIFY` and confirm the result matches the DataFrame version using `assertDataFrameEqual`.
3. Generate fake nested JSON events (e.g. with Python's `json` and `random`), load them as VARIANT, and compute revenue per country using `variant_get`. Then repeat with `from_json` + a schema and compare the plans.
4. Write a SQL script that creates one table per country for the top 3 countries by revenue, using a `FOR` loop and `EXECUTE IMMEDIATE`.
5. Use a recursive CTE to fill missing weeks with zeros (§7) and compute a running total over the filled series.

---

## Sources

- SQL pipe syntax: https://spark.apache.org/docs/latest/sql-pipe-syntax.html
- SQL scripting: https://spark.apache.org/docs/latest/sql-ref-scripting.html
- QUALIFY: https://spark.apache.org/docs/latest/sql-ref-syntax-qry-select-qualify.html
- DECLARE VARIABLE: https://spark.apache.org/docs/latest/sql-ref-syntax-ddl-declare-variable.html
- CREATE SQL FUNCTION: https://spark.apache.org/docs/latest/sql-ref-syntax-ddl-create-sql-function.html
- Geospatial types: https://spark.apache.org/docs/latest/sql-ref-geospatial-types.html
- Release notes 4.0 / 4.1 / 4.2: https://spark.apache.org/releases/spark-release-4-0-0.html · https://spark.apache.org/releases/spark-release-4.1.0.html · https://spark.apache.org/releases/spark-release-4-2-0.html
