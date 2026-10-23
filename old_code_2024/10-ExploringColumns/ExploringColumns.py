from pyspark import SparkConf
from pyspark.sql import SparkSession, Row
from lib.logger import Log4J
from pyspark.sql.functions import *

if __name__ == "__main__":
    conf = SparkConf() \
        .setMaster("local[3]") \
        .setAppName("ExploringColumns") \
        .set("spark.driver.extraJavaOptions",
             f"-Dlog4j.configuration=file:log4j.properties -Dlogfile.name=hello-spark -Dspark.yarn.app.container.log.dir=app-logs")

    spark = SparkSession \
        .builder \
        .config(conf=conf) \
        .enableHiveSupport() \
        .getOrCreate()

    logger = Log4J(spark)

    # Read the mental health survey data
    surveyDF = spark.read \
        .format("csv") \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .option("samplingRatio", "1.0") \
        .load("data/sample.csv")

    logger.info("Basic demographics exploration:")
    surveyDF.select("Age", "Gender", "Country", "state").show(10)

    logger.info("Work environment exploration:")
    surveyDF.select(column("tech_company"), col("remote_work"), "no_employees").show(10)

    logger.info("Mental health benefits and programs:")
    surveyDF.select("benefits", "wellness_program", "care_options", "leave").show(10)

    logger.info("Timestamp analysis:")
    surveyDF.selectExpr(
        "Timestamp",
        "to_date(Timestamp, 'yyyy-MM-dd HH:mm:ss') as survey_date",
        "Age",
        "Gender"
    ).show(10)

    logger.info("Mental health impact analysis:")
    surveyDF.select(
        to_date(col("Timestamp"), "yyyy-MM-dd HH:mm:ss").alias("survey_date"),
        "work_interfere",
        "mental_health_consequence",
        "phys_health_consequence"
    ).show(10)

    # Display schema for reference
    logger.info("Dataset Schema:")
    surveyDF.printSchema()

    spark.stop()