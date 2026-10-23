# 13 · New Folder Structure & Learning Workflow (Plan)

> Status: **plan only**. No notes or code have been written yet. This doc fixes the layout and conventions, so that when chapters get written later they all follow the same shape.
>
> Modelled on the WebDevLearning LLM folders:
> - `S06-Large Language Models/B04-AI_Agents/code/ch01`: notebooks, `template / solutions / solved`
> - `S06-Large Language Models/B05 - AI Agents in Action/code/ch02/from_scratch`: `.py` files + `PROBLEM_STATEMENT.md`, same three folders

---

## 1. Top-level layout

```text
WebDevLearning-pyspark/                     (git: branch "pyspark")
│
├── docs/                    ← ALWAYS at root. Numbered 01_…, 02_…, 03_… (this file is 13)
│
├── old_code_2024/           ← the original Spark 3.5 course, untouched (moved here 2026-10-23)
│   ├── 01-HelloSpark/ … 21-BucketJoinDemo/
│
├── notes/                   ← one deep markdown note per chapter (bash/ASCII diagrams)
│   ├── ch01-spark-architecture-and-setup.md
│   ├── ch02-…md
│   └── …
│
├── code/
│   ├── README.md            ← folder guide: what template / solutions / solved mean
│   ├── _shared/             ← reused by every chapter (session builder, logger, paths, checks)
│   │   ├── spark_session.py
│   │   ├── logger.py
│   │   ├── paths.py         ← resolves data/ and output/ from any file location
│   │   ├── checks.py        ← verify helpers (assertDataFrameEqual wrappers, PASS/FAIL printing)
│   │   └── log4j2.properties
│   ├── ch01/
│   │   ├── PROBLEM_STATEMENT.md
│   │   ├── template/        ← pristine stubs with TODOs, written once, never edited
│   │   ├── solutions/       ← MY working copy (copied from template, I hand-write the code)
│   │   ├── solved/          ← complete reference answer
│   │   └── own_practice/    ← optional: PROBLEM_STATEMENT.md only, no stub, build from nothing
│   ├── ch02/ …
│
├── data/                    ← shared datasets (copied once from old_code_2024/*/data + new ones)
│   ├── survey/  invoices/  flights/  apache_logs/  summary/  …
│
├── output/                  ← everything jobs write (gitignored)
├── projects/                ← capstones: P01-…, P02-… (each its own mini repo layout)
│
├── pyproject.toml           ← pinned deps: pyspark[sql,connect,pipelines]==4.2.*, pytest, ruff
├── .gitignore
└── README.md                ← entry point: links docs/02 roadmap + notes/ + code/README.md
```

Why `data/` is shared: the old course copied the same CSVs into many folders. One `data/` folder plus `_shared/paths.py` means every `template`, `solutions` and `solved` file reads the same input, whichever folder it sits in.

---

## 2. The three code folders (same meaning everywhere)

```text
          write once                 copy once                 compare after trying
 ┌─────────────────────┐   cp -n   ┌─────────────────────┐    ┌─────────────────────┐
 │      template/      │ ────────► │     solutions/      │ ◄─►│       solved/       │
 │ stub + TODO markers │           │ I hand-write code   │    │ full reference code │
 │ NEVER edited        │           │ (my attempt)        │    │ written by Claude   │
 └─────────────────────┘           └─────────────────────┘    └─────────────────────┘
        ▲                                   │
        └──── to redo an exercise: copy the template again (cp -f) ────┘
```

| Folder | Who writes it | Content |
|---|---|---|
| `template/` | generated once | header block, setup code that's given, `# TODO(n)` stubs, the verification block. Runs, but the verify step fails until the TODOs are done. |
| `solutions/` | **me** | starts as an exact copy of `template/`, then I fill in the TODOs by hand |
| `solved/` | generated | the same file, fully implemented. Verify prints `PASS` |
| `own_practice/` | me | only a `PROBLEM_STATEMENT.md`: a new scenario combining the chapter, with no stub |

Workflow commands:

```bash
# start a chapter (copies only files that don't exist yet, never overwrites my work)
cp -n code/ch05/template/*.py code/ch05/solutions/

# run my attempt
python code/ch05/solutions/02_safe_casting.py

# compare with the reference after trying
diff -u code/ch05/solutions/02_safe_casting.py code/ch05/solved/02_safe_casting.py

# redo one exercise from scratch
cp -f code/ch05/template/02_safe_casting.py code/ch05/solutions/
```

When a chapter is generated, `template/` and `solved/` are written together and `template/` is copied into `solutions/` once, just like B04/B05.

---

## 3. Decision: `.py` files or notebooks?

**Recommendation: `.py` files as the default, plus a small number of notebooks where exploration is the point.**

| Factor | `.py` scripts | Jupyter notebooks |
|---|---|---|
| SparkSession lifecycle (one session, clean `stop()`) | ✓ natural | ✗ sessions linger across cells and kernels; stale config is a classic Spark confusion |
| Spark UI / History Server inspection | ✓ run, then inspect event logs | ~ works, but the UI dies with the kernel |
| `spark-submit`, Spark Connect, `spark-pipelines` (needs `.py`/`.sql` files) | ✓ required | ✗ not usable |
| Structured Streaming (long-running queries) | ✓ | ✗ awkward |
| Verification with `pytest` + `assertDataFrameEqual` | ✓ direct | ~ via assert cells only |
| `diff solutions/ solved/` | ✓ clean line diffs | ✗ JSON diffs are unreadable |
| Git history | ✓ clean | ✗ outputs bloat commits |
| Exploring data, `df.show()`, plotting with `df.plot` | ~ fine | ✓ nicer |
| Matches the B05 `from_scratch` pattern | ✓ | — |

**So:**
- **Every exercise is a `.py` file** with a numbered name (`01_…py`, `02_…py`), like B05.
- **One optional `00_explore.ipynb` per chapter**, only where looking at data interactively helps (VARIANT, plotting, explain plans). It isn't part of template/solutions/solved and has no TODOs.
- VS Code / PyCharm "Run current file" with `cwd` set to the repo root runs everything. `# %%` cell markers in `.py` files give notebook-style interactive runs in VS Code when wanted.

---

## 4. Conventions for a `.py` exercise file

```text
# ============================================================
# LISTING:  code/ch09/template/02_weekly_summary.py
# BUILDING: weekly invoice summary per country (groupBy + agg + weekofyear)
# REF:      notes/ch09-aggregations-and-grouping.md, section 4
# OLD:      old_code_2024/14-GroupingDemo/GroupingDemo.py
# DOCS:     docs/05 (ANSI-safe dates), docs/08 (pipe syntax alternative)
# ============================================================

imports            → stdlib, pyspark, then code._shared helpers
spark = build_spark("ch09-02")                 ← from _shared, same everywhere
input given        → reads from data/ via paths.data("invoices/invoices.csv")

def weekly_summary(df):                        ← the function I implement
    # TODO(1): parse InvoiceDate safely with try_to_date (format dd-MM-yyyy H.mm)
    # TODO(2): keep only 2010
    # TODO(3): groupBy Country, WeekNumber → NumInvoices, TotalQuantity, InvoiceValue
    raise NotImplementedError("TODO")

# ---------------- verification (given, don't edit) ----------------
verify(...)        → assertDataFrameEqual against expected rows → prints PASS / precise FAIL
spark.stop()
```

Rules:
- **Logic lives in functions** (`def weekly_summary(df) -> DataFrame`), so the same function can be tested, reused by later chapters, and dropped into a Declarative Pipeline.
- `TODO(n)` markers are numbered and each maps to a step in the chapter's `PROBLEM_STATEMENT.md`.
- Verification is **built into the file** (run it → `PASS`) and also collected by `pytest code/chNN/solutions` through a tiny `test_*.py` per chapter.
- No hard-coded absolute paths. Use `_shared/paths.py`.
- Every file runs in **Classic and Connect** mode (no `sparkContext`, no `_jvm`), except files that teach Classic-only internals, which say so in the header.

---

## 5. Conventions for `notes/chNN-<topic>.md`

Same style as `B04-AI_Agents/notes/ch01-agent-landscape.md`:

```text
# Chapter N: <Title>

## Table of Contents                       numbered, linked sections

# 1: Why This Chapter Exists               what problem, how it links to the previous chapter
# 2..k: <Concept sections>
    ## The Intuition                        a real-world analogy first
    ## <The mechanism, named precisely>     the actual Spark behavior
    ```text                                 ← ASCII / bash-box diagrams:
    driver ──► stage 1 ──(shuffle)──► stage 2   plans, partitions, shuffles, DAGs,
    ```                                         memory layout, streaming state
    ## Code                                 short snippets (full exercises live in code/)
    ## Key Takeaways for Section k
    *Next: one-line bridge to the next section*
# k+1: Dry-Run                              trace an example BY HAND: partitions, rows per task,
                                            what the shuffle moves, what explain() will print
# k+2: Key Takeaways + Master Decision Table
```

Each note ends with a **"Run it"** pointer: `code/chNN/PROBLEM_STATEMENT.md` → template files, in order.

---

## 6. `PROBLEM_STATEMENT.md` per chapter

Same as `B05 …/ch02/from_scratch/PROBLEM_STATEMENT.md`:

```text
# Chapter N: Problem Statements
## Table of Contents
## 1: <Exercise title>
**File:** `01_xxx.py`
### The Intuition
### What You're Building        numbered steps = TODO(1), TODO(2), …
### Example                     input rows → expected output rows (a small table)
### Hints (optional)            which functions/docs to look at, never the answer
```

---

## 7. Planned chapter map

Old modules are folded into the new chapters. "New" means it wasn't in the 2024 course.

| Ch | Folder / note name | Covers | From old_code_2024 | Docs |
|---|---|---|---|---|
| ch01 | `spark-architecture-and-setup` | Spark 4.2 setup, driver/executors, lazy eval, jobs/stages/tasks, Spark UI, Classic vs Connect | 01 | 03, 06 |
| ch02 | `rdd-to-dataframe` | why DataFrames, RDD internals (read-only), DataFrame vs SQL plans | 02, 03 | 06 |
| ch03 | `schemas-and-data-sources` | readers, StructType vs DDL, read modes, CSV/JSON/Parquet/Avro/XML | 04 | 04 |
| ch04 | `writing-data-and-tables` | writers, partitionBy, file sizing, catalog, managed tables | 05, 06 | 04 |
| ch05 | `column-transformations` | col/expr/selectExpr, withColumns, when, dates, Rows | 07, 08, 10, 12 | 04 |
| ch06 | `ansi-mode-and-safe-parsing` | ANSI rules, try_* family, quarantine pattern, error classes | 07, 12 (new angle) | 05 |
| ch07 | `text-and-regex-processing` | regexp_extract, log parsing, string functions | 09 | — |
| ch08 | `udfs-pandas-and-arrow` | built-in first, SQL UDF, @udf, @pandas_udf, @arrow_udf, profiling | 11 | 07 |
| ch09 | `aggregations-and-grouping` | groupBy/agg, rollup/cube/groupingSets, pivot | 13, 14 | 08 |
| ch10 | `window-functions` | frames, running totals, ranking, lag/lead, QUALIFY | 15, 16 | 08 |
| ch11 | `joins` | join types, semi/anti, ambiguity, lateral joins | 17, 18 | 09 |
| ch12 | `join-strategies-and-aqe` | BHJ/SHJ/SMJ, hints, AQE, bucket join → SPJ, explain plans | 19, 20, 21 | 09 |
| ch13 | `performance-tuning` | partitioning, caching, skew + salting, memory, History Server | — (new) | 09 |
| ch14 | `modern-spark-sql` | pipe syntax, VARIANT, scripting, variables, recursive CTE, collations | — (new) | 08 |
| ch15 | `udtfs-and-python-data-sources` | @udtf, @arrow_udtf, table args, Python Data Source API | — (new) | 07 |
| ch16 | `spark-connect-and-deployment` | Connect mode, pyspark-client, spark-submit, packaging, Docker | — (new) | 06 |
| ch17 | `structured-streaming-basics` | triggers, output modes, watermarks, windows, Kafka, checkpoints | — (new) | 10 |
| ch18 | `stateful-streaming` | transformWithState, state data source, RTM, named sources | — (new) | 10 |
| ch19 | `lakehouse-delta-and-iceberg` | MERGE, time travel, clustering, SPJ, medallion | 06, 21 (modern redo) | 12 |
| ch20 | `declarative-pipelines` | SDP decorators, spec, CLI, auto CDC | — (new) | 11 |
| ch21 | `testing-and-production` | pytest fixtures, assertDataFrameEqual, logging, CI, data quality | 01, 08 (tests) | 03, 04 |
| P01… | `projects/` capstones | the 3 capstone options from the roadmap | — | 02 |

Numbering rule: chapters are `ch01…ch21`, exercise files inside a chapter are `01_…py, 02_…py`, docs stay `NN_name.md` at the root.

---

## 8. `_shared/` contents (planned)

| File | Purpose |
|---|---|
| `spark_session.py` | `build_spark(app_name, mode="classic"\|"connect", **conf)`: local[3], small shuffle partitions, log4j2, event logs on, optional Delta/Iceberg extensions |
| `logger.py` | Classic → Log4j 2, Connect → `PySparkLogger` (from [04 §2c](04_migrating_course_code_to_spark_4.md)) |
| `paths.py` | `data(rel)`, `output(rel)`: absolute paths from the repo root, wherever the script lives |
| `checks.py` | `verify_df(actual, expected, msg)`, `verify_true(cond, msg)`: print `PASS …` or a precise `FAIL …` and exit non-zero |
| `log4j2.properties` | one shared logging config (console WARN for Spark, INFO for course loggers, file to `output/logs/`) |
| `conftest.py` (at `code/`) | session-scoped `spark` fixture for `pytest code/chNN/solutions` |

---

## 9. Order of work when we start generating

1. Root scaffolding: `pyproject.toml`, `.gitignore`, `README.md`, `code/README.md`, `code/_shared/*`, `data/` (copied from `old_code_2024`).
2. Then **one chapter at a time**, in this order: `notes/chNN-….md` → `code/chNN/PROBLEM_STATEMENT.md` → `solved/*.py` (and run it to confirm it works) → `template/*.py` (solved with the TODOs stripped out) → copy into `solutions/`.
3. After each chapter: run every `solved/` file and confirm `PASS`, and run every `template/` file and confirm it fails *only* at the TODO verify step.

---

## 10. Open choices (defaults chosen, change any time)

| Choice | Default in this plan | Alternative |
|---|---|---|
| Archive folder name | `old_code_2024/` (the course ran on Spark 3.5.4 in Dec 2024) | `previous/` |
| File format | `.py` + optional `00_explore.ipynb` | all notebooks (B04 style) |
| Data location | shared `data/` | per-chapter `data/` folders |
| Second code track per chapter (like B05's `openai_sdk`) | none: one track. Where useful, files show **DataFrame API and SQL** side by side as `NNa_…_df.py` / `NNb_…_sql.py` | separate `dataframe_api/` and `sql/` subfolders |
