import sys
from collections import namedtuple

from pyspark import SparkConf
from pyspark.sql import SparkSession, Row
from pyspark.sql.functions import to_date, col
from pyspark.sql.types import StructType, StructField, StringType

from lib.logger import Log4J


def to_date_df(df, fmt, fld):
    """Convert string date field to date type"""
    return df.withColumn(fld, to_date(col(fld), fmt))


if __name__ == "__main__":
    conf = SparkConf() \
        .setMaster("local[3]") \
        .setAppName("RowDemo") \
        .set("spark.driver.extraJavaOptions",
             f"-Dlog4j.configuration=file:log4j.properties -Dlogfile.name=hello-spark -Dspark.yarn.app.container.log.dir=app-logs")

    spark = SparkSession \
        .builder \
        .config(conf=conf) \
        .enableHiveSupport() \
        .getOrCreate()

    logger = Log4J(spark)

    # Define schema
    my_schema = StructType([
        StructField("ID", StringType()),
        StructField("EventDate", StringType())
    ])

    # Create sample data
    my_rows = [
        Row("123", "04/05/2020"),
        Row("124", "4/5/2020"),
        Row("125", "04/5/2020"),
        Row("126", "4/05/2020")
    ]

    # Create RDD and DataFrame
    my_rdd = spark.sparkContext.parallelize(my_rows, 2)
    my_df = spark.createDataFrame(my_rdd, my_schema)

    logger.info("Original Schema:")
    my_df.printSchema()
    logger.info("Original Data:")
    my_df.show()

    # Apply date transformation
    new_df = to_date_df(my_df, "M/d/y", "EventDate")

    logger.info("Transformed Schema:")
    new_df.printSchema()
    logger.info("Transformed Data:")
    new_df.show()

    spark.stop()