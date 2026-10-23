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
        .setAppName("DataSinkDemo") \
        .set("spark.driver.extraJavaOptions",
             f"-Dlog4j.configuration=file:log4j.properties -Dlogfile.name=hello-spark -Dspark.yarn.app.container.log.dir=app-logs") \
        .set("spark.jars.packages", "org.apache.spark:spark-avro_2.12:3.5.0")

    # sc = SparkContext(conf=conf)

    spark = SparkSession \
        .builder \
        .config(conf = conf)    \
        .getOrCreate()

    logger = Log4J(spark)

    flightTimeParquetDF = spark.read \
        .format("parquet") \
        .load("dataSource/flight*.parquet")

    logger.info("Num Partitions before: " + str(flightTimeParquetDF.rdd.getNumPartitions()))
    flightTimeParquetDF.groupBy(spark_partition_id()).count().show()

    partitionedDF = flightTimeParquetDF.repartition(5)
    logger.info("Num Partitions after: " + str(partitionedDF.rdd.getNumPartitions()))
    partitionedDF.groupBy(spark_partition_id()).count().show()

    partitionedDF.write \
        .format("avro") \
        .mode("overwrite") \
        .option("path", "dataSink/avro/") \
        .save()

    flightTimeParquetDF.write \
        .format("json") \
        .mode("overwrite") \
        .option("path", "dataSink/json/") \
        .partitionBy("OP_CARRIER", "ORIGIN") \
        .option("maxRecordsPerFile", 10000) \
        .save()