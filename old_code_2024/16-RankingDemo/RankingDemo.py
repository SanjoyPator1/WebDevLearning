import re

from pyspark import SparkConf
from pyspark.sql import *
from pyspark.sql import functions as f

from lib.logger import Log4J

if __name__ == "__main__":
    conf = SparkConf() \
        .setMaster("local[3]") \
        .setAppName("GroupingDemo") \
        .set("spark.driver.extraJavaOptions",
             f"-Dlog4j.configuration=file:log4j.properties -Dlogfile.name=hello-spark -Dspark.yarn.app.container.log.dir=app-logs")

    spark = SparkSession \
        .builder \
        .config(conf=conf) \
        .enableHiveSupport() \
        .getOrCreate()

    logger = Log4J(spark)

    summary_df = spark.read.parquet("data/summary.parquet")

    summary_df.sort("Country", "WeekNumber").show()

    rank_window = Window.partitionBy("Country") \
        .orderBy(f.col("InvoiceValue").desc()) \
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)

    df = summary_df.withColumn("Rank", f.dense_rank().over(rank_window)) \
        .where(f.col("Rank") == 1) \
        .sort("Country", "WeekNumber") \
        .show()