import sys
import pyspark
from pyspark.sql import SparkSession

catalog_type = sys.argv[1]
if catalog_type == 'kafka':
    warehouse_path = '/out-kafka/iceberg/warehouse'
    account_table = 'iceberg.commerce.account'
    product_table = 'iceberg.commerce.product'
elif catalog_type == 'spark':
    warehouse_path = '/out-spark/iceberg/warehouse'
    account_table = 'iceberg.cdc.commerce_account'
    product_table = 'iceberg.cdc.commerce_product'
else:
    raise ValueError('Invalid catalog type. Use either kafka or spark')

conf = (pyspark.SparkConf()
    .set('spark.sql.extensions', 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions')
    .set('spark.sql.catalog.iceberg', 'org.apache.iceberg.spark.SparkCatalog')
    .set('spark.sql.catalog.iceberg.type', 'hadoop')
    .set('spark.sql.catalog.iceberg.warehouse', warehouse_path)
)

spark = (SparkSession.builder
    .master('local')
    .appName('cdc-consumer')
    .config(conf=conf)
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

spark.read.table(account_table).show(truncate=False)
spark.read.table(product_table).show(truncate=False)
