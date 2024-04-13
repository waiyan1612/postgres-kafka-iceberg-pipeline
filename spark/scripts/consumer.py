from pyspark.sql import SparkSession
from pyspark.sql.functions import col, get_json_object

# This is the same KAFKA_ADVERTISED_LISTENERS defined in docker-compose.yaml
KAFKA_BOOTSTRAP_SERVER = 'kafka-standalone:19092'
KAFKA_TOPICS = 'cdc.commerce.*'


spark = (SparkSession.builder
    .master('local')
    .appName('cdc-consumer')
    .getOrCreate()
)

kafka_df = (spark.readStream
    .format('kafka')
    .option('kafka.bootstrap.servers', KAFKA_BOOTSTRAP_SERVER)
    .option('subscribePattern', KAFKA_TOPICS)
    .option('startingOffsets', 'earliest')
    .load()
)

cdc_df = kafka_df.selectExpr('cast(value as string) as value').select(
    get_json_object(col('value'),'$.payload.before').alias('before'), 
    get_json_object(col('value'),'$.payload.after').alias('after'), 
    get_json_object(col('value'),'$.payload.op').alias('op')
)

stream = (kafka_df.writeStream
    .format('console')
    .outputMode('update')
    .start()
)

cdc_stream = (cdc_df.writeStream
    .format('console')
    .outputMode('update')
    .option('truncate', False)
    .start()
)

stream.awaitTermination()
cdc_stream.awaitTermination()
