# 03 · Environment Setup for Spark 4.x (macOS, 2026)

This replaces the course's original setup (Python 3.8 + Java 11 + Spark 3.5 + PyCharm). Your Mac currently has **Python 3.14.7** and **no Java runtime**, so Java is step 1.

---

## 1. Version matrix: pick these

| Component | Recommended | Allowed range (Spark 4.2) | Notes |
|---|---|---|---|
| Java | **21 (LTS)** | 17, 21, 25 | Spark 4.0 dropped Java 8/11. 4.2 added Java 25 support. |
| Python | **3.12 or 3.13** | 3.10+ | 3.14 works with PySpark 4.1+, but some optional wheels (pyarrow, grpcio) can lag behind brand-new Pythons. 3.12/3.13 is the safe choice. |
| PySpark | **4.2.0** | — | `pip install "pyspark[sql]==4.2.0"` |
| pandas | ≥ 2.2, < 3 | — | Only needed for pandas UDFs, `toPandas`, pandas-on-Spark |
| PyArrow | ≥ 18 | — | Needed for Arrow UDFs, `toPandas`, Spark Connect |
| Scala (for `--packages`) | **2.13** | 2.13 only | Use `_2.13` artifacts, never `_2.12` |

---

## 2. Install Java

```bash
# Homebrew
brew install openjdk@21

# Make it visible to macOS java wrappers (brew prints this command too)
sudo ln -sfn /opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk \
  /Library/Java/JavaVirtualMachines/openjdk-21.jdk

# Add to ~/.zshrc
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH="$JAVA_HOME/bin:$PATH"

# Verify
java -version        # should print 21.x
```

Alternatives: Eclipse Temurin (`brew install --cask temurin@21`) or SDKMAN (`sdk install java 21-tem`). Any OpenJDK 21 build is fine.

---

## 3. Create a Python environment

### Option A: `uv` (fast, recommended)

```bash
brew install uv
cd ~/Downloads/WebDevLearning-pyspark
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install "pyspark[sql]==4.2.0" pytest ruff
```

### Option B: plain venv + pip

```bash
brew install python@3.12
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install "pyspark[sql]==4.2.0" pytest ruff
```

### PySpark install extras (choose what you need)

| Command | What you get |
|---|---|
| `pip install pyspark` | Core PySpark (bundles the Spark JVM jars) |
| `pip install "pyspark[sql]"` | + pandas, pyarrow (pandas UDFs, `toPandas`, Arrow) |
| `pip install "pyspark[pandas_on_spark]" plotly` | + pandas API on Spark + plotting |
| `pip install "pyspark[connect]"` | + grpcio etc. for Spark Connect |
| `pip install "pyspark[pipelines]"` | + Declarative Pipelines (`spark-pipelines` CLI) |
| `pip install "pyspark[ml]"` | + numpy for MLlib |
| `pip install pyspark-client` | **Only** the thin Spark Connect client, no JVM needed (connects to `sc://` servers) |
| `pip install pyspark-connect` | pyspark + Connect deps, Connect as default mode |

Pin your versions in a `requirements.txt` or `pyproject.toml`:

```toml
# pyproject.toml
[project]
name = "pyspark-course"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
  "pyspark[sql]==4.2.0",
]

[dependency-groups]
dev = ["pytest>=8", "ruff"]

[tool.pytest.ini_options]
testpaths = ["."]
addopts = "-q"
```

---

## 4. Smoke test

```bash
python - <<'EOF'
import pyspark
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder.master("local[2]").appName("smoke").getOrCreate()
print("PySpark", pyspark.__version__, "| Spark", spark.version)
print("ANSI mode:", spark.conf.get("spark.sql.ansi.enabled"))
print("AQE:", spark.conf.get("spark.sql.adaptive.enabled"))
spark.range(5).withColumn("sq", F.col("id") * F.col("id")).show()
spark.stop()
EOF
```

Expected: `PySpark 4.2.0 | Spark 4.2.0`, `ANSI mode: true`, `AQE: true`, and a 5-row table.

### Common macOS issues

| Symptom | Fix |
|---|---|
| `Unable to locate a Java Runtime` | Java not installed or `JAVA_HOME` not set (step 2) |
| `JAVA_GATEWAY_EXITED` | Wrong Java version (needs 17+) or `JAVA_HOME` points to an old JDK |
| `WARN Utils: Your hostname … resolves to a loopback address` | Harmless. Silence it with `export SPARK_LOCAL_IP=127.0.0.1` |
| Python worker version mismatch | `export PYSPARK_PYTHON=$(which python)` and `PYSPARK_DRIVER_PYTHON=$(which python)` |
| `Unsupported class file major version` | You're running an older Spark with a newer Java. Use a matching pair |

---

## 5. IDE setup

**PyCharm:** the `.idea/misc.xml` files in each module point at `"Python 3.8 (2)"`. Go to *Settings → Project → Python Interpreter → Add → Existing → `.venv/bin/python`*. Mark each module folder as a *Sources Root* so `from lib.logger import …` resolves.

**VS Code:** select the interpreter `.venv/bin/python` (Cmd+Shift+P → *Python: Select Interpreter*). The course scripts use relative paths like `data/…`, so add `"cwd": "${fileDirname}"` to your launch config:

```jsonc
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run current Spark module",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "cwd": "${fileDirname}",
      "args": ["data/sample.csv"],
      "env": { "SPARK_LOCAL_IP": "127.0.0.1" }
    }
  ]
}
```

---

## 6. Testing setup (replaces `unittest.TestCase`)

The course uses `unittest` with a class-level SparkSession. Modern practice is **pytest with a session-scoped fixture** and Spark's built-in DataFrame assertions (since 3.5).

```python
# conftest.py (put at repo root or inside each module)
import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    spark = (
        SparkSession.builder
        .master("local[2]")
        .appName("tests")
        .config("spark.sql.shuffle.partitions", "2")   # small data → few partitions → fast tests
        .config("spark.ui.enabled", "false")           # no UI needed in tests
        .getOrCreate()
    )
    yield spark
    spark.stop()
```

```python
# 01-HelloSpark/test_utils.py, rewritten with pytest
from pyspark.testing import assertDataFrameEqual
from lib.utils import load_survey_df, count_by_country


def test_datafile_loading(spark):
    df = load_survey_df(spark, "data/sample.csv")
    assert df.count() == 9


def test_country_count(spark):
    df = load_survey_df(spark, "data/sample.csv")
    expected = spark.createDataFrame(
        [("United States", 4), ("Canada", 2), ("United Kingdom", 1)],
        "Country string, count long",
    )
    actual = count_by_country(df).where("Country in ('United States','Canada','United Kingdom')")
    assertDataFrameEqual(actual, expected)   # order-insensitive by default
```

Useful assertion helpers in `pyspark.testing`:

| Helper | Use |
|---|---|
| `assertDataFrameEqual(actual, expected, checkRowOrder=False, rtol=…, atol=…)` | Compare DataFrames (also accepts lists of Rows) with readable diffs |
| `assertSchemaEqual(actual.schema, expected.schema)` | Compare schemas only |

Run with:

```bash
cd 01-HelloSpark && pytest
```

---

## 7. Optional: run Spark in Docker

Useful for trying a different Spark version without touching your venv:

```bash
# replace <tag> with a real tag from Docker Hub, e.g. one like 4.2.0-python3
docker run -it --rm -v "$PWD":/work -w /work apache/spark:<tag> /opt/spark/bin/pyspark
```

Image names and tags change over time. Check Docker Hub for the official `apache/spark` image (the old `apache/spark-py` image is outdated) and pick a tag with an exact Spark version and Python, never `latest`.

---

## Sources

- PySpark installation (Python 3.10+, Java 17+, extras): https://spark.apache.org/docs/latest/api/python/getting_started/install.html
- Spark 4.0 release notes (Java 17 default, Python 3.8 dropped): https://spark.apache.org/releases/spark-release-4-0-0.html
- Spark 4.1 release notes (Python 3.10 minimum, Python 3.14 support): https://spark.apache.org/releases/spark-release-4.1.0.html
- Spark 4.2 release notes (Java 25): https://spark.apache.org/releases/spark-release-4-2-0.html
- PySpark testing utilities: https://spark.apache.org/docs/latest/api/python/reference/pyspark.testing.html
