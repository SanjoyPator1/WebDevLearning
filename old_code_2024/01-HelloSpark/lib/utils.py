import configparser
from pyspark import SparkConf
import os

def load_survey_df(spark, data_file):
    return spark.read \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .csv(data_file)


def count_by_country(survey_df):
    return survey_df.filter("Age < 40") \
        .select("Age", "Gender", "Country", "state") \
        .groupBy("Country") \
        .count()


def get_spark_app_config():
    spark_conf = SparkConf()
    config = configparser.ConfigParser()

    # Get absolute path to config file
    config_path = os.path.abspath("spark.conf")
    config.read(config_path)

    # Get absolute path to log4j.properties
    log4j_path = os.path.abspath("log4j.properties")

    for (key, val) in config.items("SPARK_APP_CONFIGS"):
        spark_conf.set(key, val)

    # Ensure log4j configuration is properly set
    spark_conf.set("spark.driver.extraJavaOptions", f"-Dlog4j.configuration=file:{log4j_path}")

    return spark_conf