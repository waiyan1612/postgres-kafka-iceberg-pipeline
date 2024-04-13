# POSTGRES-KAFKA-ICEBERG-PIPELINE

Example pipeline to stream the data changes from RDBMS to Apache Iceberg tables.

## Contents
```sh
├── docker-compose.yaml                        -> Compose file to launch postgres and kafka
├── kafka
│   ├── config
│   │   ├── connect-file-sink.properties       -> File sink connector
│   │   ├── connect-postgres-source.json       -> Postgres source connector
│   │   └── connect-standalone.properties      -> Standalone kafka conenct config
│   └── plugins
│       └── debezium-connector-postgres        -> Debezium connector jars should be downloaded to this folder
├── postgres
│   ├── postgresql.conf                        -> Config with logical replication enabled
│   └── scripts
│       ├── manual
│       └── seed                               -> SQL scripts that will be run the first time the db is created i.e. when the data directory is empty
└── spark
    └── scripts/consumer.py                    -> Pyspark streaming using kafka source and console sink

```
Moreover, these folders will be created and mounted so that docker containers can write back to the host file system.
```sh
├── data                                       -> Data from containers will be mounted to this path Configured in docker-compose file.
│   ├── kafka
│   │   └── out/cdc.commerce.sink.txt          -> Output of Kafka File sink connector
│   └── spark
│       └── out
│          ├── iceberg/warehouse               -> Storage location used by Spark Iceberg sink for each table data + metadata
│          └── spark/checkpoint                -> Checkpoint location used by Spark structured streaming
```

## Setup Guide

1. Download the connectors and copy them to `kafka/plugins` folder that will be mounted to the docker container.
    
    ```sh
    TMP_FOLDER=/tmp/dbz-pg-connector
    mkdir -p $TMP_FOLDER

    # See https://debezium.io/documentation/reference/stable/install.html to get the download link.
    wget -qO- https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.6.0.Final/debezium-connector-postgres-2.6.0.Final-plugin.tar.gz | tar -xvz -C $TMP_FOLDER
    cp $TMP_FOLDER/debezium-connector-postgres/*.jar $PWD/kafka/plugins/debezium-connector-postgres && rm -rf $TMP_FOLDER
    ```
2. Run Docker compose. This will 
    1. Start the Postgres database and also run the scripts under `postgres/scripts/seed`.
    2. Start the Kafka in KRaft mode and Kafka Conenct in Standalone mode. The plugins from the previosuly step will be loaded

    ```sh
    docker compose up
    ```
    Or if you also want to start the spark container. This will also download the kafka and iceberg dependency jars.
    ```
    docker compose --profile spark up
    ```

3. Create and start the kafka connectors.
    ```sh
    docker container exec -d kafka-standalone \
      /opt/kafka/bin/connect-standalone.sh \
      /opt/kafka/config-cdc/connect-standalone.properties \
      /opt/kafka/config-cdc/connect-postgres-source.json \
      /opt/kafka/config-cdc/connect-file-sink.properties
    ```

4. You can now run the CUD operations on postgres and the changes should be streamed to the sinks.


## Helpful Commands for Debugging

### One-liner to wipe data directory while keeping .gitkeep files
```sh
find ./data ! -name .gitkeep -delete
```

### List kafka topics
```sh
/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### Start Kafka Connect
```sh
/opt/kafka/bin/connect-standalone.sh \
  /opt/kafka/config-cdc/connect-standalone.properties \
  /opt/kafka/config-cdc/connect-postgres-source.json \
  /opt/kafka/config-cdc/connect-file-sink.properties
```

### Kafka Connect Endpoints 
```sh

# Health check
curl localhost:8083

# Check plugins
curl localhost:8083/connector-plugins

# Check connectors - configs, status, topics 
curl localhost:8083/connectors
curl localhost:8083/connectors/dbz-pg-source | jq
curl localhost:8083/connectors/dbz-pg-source/status | jq
curl localhost:8083/connectors/dbz-pg-source/topics | jq
curl localhost:8083/connectors/local-file-sink/topics | jq

# Pause, resume, restart, stop or delete connectors
curl -X PUT localhost:8083/connectors/dbz-pg-source/pause
curl -X PUT localhost:8083/connectors/dbz-pg-source/resume
curl -X PUT localhost:8083/connectors/dbz-pg-source/restart
curl -X PUT localhost:8083/connectors/dbz-pg-source/stop
curl -X DELETE localhost:8083/connectors/dbz-pg-source
```

## Sample Outputs for Spark

### Console sink
```
kafka-spark       | 24/04/13 09:53:25 INFO CodeGenerator: Code generated in 8.356917 ms
kafka-spark       | +--------------------+--------------------+--------------------+---------+------+--------------------+-------------+
kafka-spark       | |                 key|               value|               topic|partition|offset|           timestamp|timestampType|
kafka-spark       | +--------------------+--------------------+--------------------+---------+------+--------------------+-------------+
kafka-spark       | |[7B 22 73 63 68 6...|[7B 22 73 63 68 6...|cdc.commerce.account|        0|     0|2024-04-13 09:42:...|            0|
kafka-spark       | |[7B 22 73 63 68 6...|[7B 22 73 63 68 6...|cdc.commerce.account|        0|     1|2024-04-13 09:42:...|            0|
kafka-spark       | |[7B 22 73 63 68 6...|[7B 22 73 63 68 6...|cdc.commerce.account|        0|     2|2024-04-13 09:42:...|            0|
kafka-spark       | |[7B 22 73 63 68 6...|[7B 22 73 63 68 6...|cdc.commerce.product|        0|     0|2024-04-13 09:42:...|            0|
kafka-spark       | |[7B 22 73 63 68 6...|[7B 22 73 63 68 6...|cdc.commerce.product|        0|     1|2024-04-13 09:42:...|            0|
kafka-spark       | +--------------------+--------------------+--------------------+---------+------+--------------------+-------------+
```
```
kafka-spark       | -------------------------------------------
kafka-spark       | Batch: 0
kafka-spark       | -------------------------------------------
kafka-spark       | 24/04/13 09:53:25 INFO CodeGenerator: Code generated in 11.099875 ms
kafka-spark       | 24/04/13 09:53:25 INFO CodeGenerator: Code generated in 13.485375 ms
kafka-spark       | +------+----------------------------------------------------------------------------------------+---+--------------------+
kafka-spark       | |before|after                                                                                   |op |topic               |
kafka-spark       | +------+----------------------------------------------------------------------------------------+---+--------------------+
kafka-spark       | |NULL  |{"user_id":1,"email":"alice@example.com","created_at":1713000433266098}                 |r  |cdc.commerce.account|
kafka-spark       | |NULL  |{"user_id":2,"email":"bob@example.com","created_at":1713000433266098}                   |r  |cdc.commerce.account|
kafka-spark       | |NULL  |{"user_id":3,"email":"carol@example.com","created_at":1713000433266098}                 |r  |cdc.commerce.account|
kafka-spark       | |NULL  |{"product_id":1,"product_name":"Live Edge Dining Table","created_at":1713000433267807}  |r  |cdc.commerce.product|
kafka-spark       | |NULL  |{"product_id":2,"product_name":"Simple Teak Dining Chair","created_at":1713000433267807}|r  |cdc.commerce.product|
kafka-spark       | +------+----------------------------------------------------------------------------------------+---+--------------------+
```
### Iceberg sink
```
>>> spark.read.table('local.cdc.commerce_account').show(truncate=False)
+------+-----------------------------------------------------------------------+---+
|before|after                                                                  |op |
+------+-----------------------------------------------------------------------+---+
|NULL  |{"user_id":1,"email":"alice@example.com","created_at":1713000433266098}|r  |
|NULL  |{"user_id":2,"email":"bob@example.com","created_at":1713000433266098}  |r  |
|NULL  |{"user_id":3,"email":"carol@example.com","created_at":1713000433266098}|r  |
+------+-----------------------------------------------------------------------+---+

>>> spark.read.table('local.cdc.commerce_product').show(truncate=False)
+------+----------------------------------------------------------------------------------------+---+
|before|after                                                                                   |op |
+------+----------------------------------------------------------------------------------------+---+
|NULL  |{"product_id":1,"product_name":"Live Edge Dining Table","created_at":1713000433267807}  |r  |
|NULL  |{"product_id":2,"product_name":"Simple Teak Dining Chair","created_at":1713000433267807}|r  |
+------+----------------------------------------------------------------------------------------+---+
```
