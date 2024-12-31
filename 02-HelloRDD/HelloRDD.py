import sys
from collections import namedtuple

from pyspark import SparkConf
from pyspark.sql import SparkSession

from lib.logger import Log4J

SurveyRecord = namedtuple("SurveyRecord", ["Age", "Gender", "Country", "State"])

if __name__ == "__main__":

    conf = SparkConf() \
        .setMaster("local[3]") \
        .setAppName("HelloRDD") \
        .set("spark.driver.extraJavaOptions",
             f"-Dlog4j.configuration=file:log4j.properties -Dlogfile.name=hello-spark -Dspark.yarn.app.container.log.dir=app-logs")

    # sc = SparkContext(conf=conf)

    spark = SparkSession \
        .builder \
        .config(conf = conf)    \
        .getOrCreate()

    sc = spark.sparkContext
    logger = Log4J(spark)

    if len(sys.argv) != 2:
        logger.error("Usage: HelloSpark <filename>")
        sys.exit(-1)

    # Read the file into an RDD
    linesRDD = sc.textFile(sys.argv[1])
    partitionedRDD = linesRDD.repartition(2)

    colsRDD = partitionedRDD.map(lambda line: line.replace('"', '').split(","))
    print("colsRDD 5 : ",colsRDD.take(5))  # Print first 5 elements

    selectRDD = colsRDD.map(lambda cols: SurveyRecord(int(cols[1]), cols[2], cols[3], cols[4]))
    print("selectRDD 5 : ",selectRDD.take(5))  # Print first 5 mapped records

    filteredRDD = selectRDD.filter(lambda r: r.Age < 40)
    print("filteredRDD : ",filteredRDD.take(5))  # Print first 5 filtered records

    kvRDD = filteredRDD.map(lambda r: (r.Country, 1))
    print("kvRDD 5 : ",kvRDD.take(5))  # Print first 5 key-value pairs

    countRDD = kvRDD.reduceByKey(lambda v1, v2: v1 + v2)
    print("countRDD : ",countRDD.collect())  # Collect the final output and print

    colsList = countRDD.collect()
    for x in colsList:
        print(x)