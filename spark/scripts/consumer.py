import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, get_json_object
from pyspark.sql.types import StringType

# This is the same KAFKA_ADVERTISED_LISTENERS defined in docker-compose.yaml
KAFKA_BOOTSTRAP_SERVER = 'kafka-standalone:19092'
KAFKA_TOPICS = 'cdc.commerce.*'

SPARK_ICEBERG_WAREHOUSE_PATH = '/out-spark/iceberg/warehouse' 
ICEBERG_CHECKPOINT_PATH = '/out/spark/checkpoint/iceberg'
CATALOG_NAME = 'iceberg'

# Configure spark catalogs. Note: Iceberg does not work with Spark's default hive metastore - https://github.com/apache/iceberg/issues/7847
conf = (pyspark.SparkConf()
    .set('spark.sql.shuffle.partitions', '2')
    .set('spark.sql.extensions', 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions')
    .set('spark.sql.catalog.spark_catalog', 'org.apache.iceberg.spark.SparkSessionCatalog')
    .set('spark.sql.catalog.spark_catalog.type', 'hive')
    .set(f'spark.sql.catalog.{CATALOG_NAME}', 'org.apache.iceberg.spark.SparkCatalog')
    .set(f'spark.sql.catalog.{CATALOG_NAME}.type', 'hadoop')
    .set(f'spark.sql.catalog.{CATALOG_NAME}.warehouse', SPARK_ICEBERG_WAREHOUSE_PATH)
)

spark = (SparkSession.builder
    .master('local')
    .appName('cdc-consumer')
    .config(conf=conf)
    .getOrCreate()
)

kafka_stream = (spark.readStream
    .format('kafka')
    .option('kafka.bootstrap.servers', KAFKA_BOOTSTRAP_SERVER)
    .option('subscribePattern', KAFKA_TOPICS)
    .option('startingOffsets', 'earliest')
    .load()
)

cdc_stream = kafka_stream.select(
    col('value').cast(StringType()).alias('val_str'),
    get_json_object(col('val_str'),'$.payload.before').alias('before'),
    get_json_object(col('val_str'),'$.payload.after').alias('after'),
    get_json_object(col('val_str'),'$.payload.op').alias('op'),
    col('topic'),
).drop('val_str')


# Console sinks for visualizing the streams
kafka_stream.writeStream.format('console').outputMode('update').start()
cdc_stream.writeStream.format('console').outputMode('update').option('truncate', False).start()


"""
Split the stream into individual DataFrames since we are listening to multiple topics.
"""
def split_by_topic(df, epoch_id):
    topics = df.select('topic').distinct().rdd.flatMap(list).collect()
    print(f'Found topics: {topics}')
    for topic in topics:
        topic_df = df.filter(col('topic') == topic).drop('topic')
        db, schema, table = topic.split('.')    
        iceberg_full_table_name = f'{CATALOG_NAME}.{db}.{schema}_{table}'
        if spark.catalog.tableExists(iceberg_full_table_name):
            topic_df.writeTo(iceberg_full_table_name).option('mergeSchema','true').append() # TODO: Switch to MERGE INTO.
        else:
            topic_df.writeTo(iceberg_full_table_name).tableProperty('write.spark.accept-any-schema', 'true').create()

# Iceberg sink
cdc_stream.writeStream.option('checkpointLocation', ICEBERG_CHECKPOINT_PATH).foreachBatch(split_by_topic).start()

spark.streams.awaitAnyTermination()

