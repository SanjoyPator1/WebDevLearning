import sys
from collections import namedtuple

from pyspark import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.functions import spark_partition_id
from pyspark.sql.types import StructType, StructField, DateType, StringType, IntegerType

from lib.logger import Log4J

SurveyRecord = namedtuple("SurveyRecord", ["Age", "Gender", "Country", "State"])

if __name__ == "__main__":

    conf = SparkConf() \
        .setMaster("local[3]") \
        .setAppName("SparkSQLTableDemo") \
        .set("spark.driver.extraJavaOptions",
             f"-Dlog4j.configuration=file:log4j.properties -Dlogfile.name=hello-spark -Dspark.yarn.app.container.log.dir=app-logs") \
        .set("spark.jars.packages", "org.apache.spark:spark-avro_2.12:3.5.0")

    # sc = SparkContext(conf=conf)

    spark = SparkSession \
        .builder \
        .config(conf = conf)    \
        .enableHiveSupport() \
        .getOrCreate()

    logger = Log4J(spark)

    flightTimeParquetDF = spark.read \
        .format("parquet") \
        .load("dataSource/")

    spark.sql("CREATE DATABASE IF NOT EXISTS AIRLINE_DB")
    spark.catalog.setCurrentDatabase("AIRLINE_DB")

    flightTimeParquetDF.write \
        .format("csv")  \
        .mode("overwrite") \
        .bucketBy(5, "OP_CARRIER", "ORIGIN") \
        .sortBy("OP_CARRIER", "ORIGIN") \
        .saveAsTable("flight_data_tbl")

    logger.info(spark.catalog.listTables("AIRLINE_DB"))