# POSTGRES-KAFKA-ICEBERG-PIPELINE

Example pipeline to stream the data changes from RDBMS to Apache Iceberg tables under two approaches.

1. Manually processing the Kafka messages via Spark
2. Using Kafka Sink Connector for Iceberg from [iceberg-kafka-connect](https://github.com/tabular-io/iceberg-kafka-connect/) repo

https://github.com/waiyan1612/postgres-kafka-iceberg-pipeline/assets/8967715/91d59de8-60e2-4e4c-b54a-47c1d36039a3

## Contents
```sh
├── docker-compose.yaml                        -> Compose file to launch postgres, kafka and spark containers
├── kafka
│   ├── config
│   │   ├── connect-file-sink.properties       -> File sink connector
│   │   ├── connect-iceberg-sink.properties    -> Iceberg Sink connector
│   │   ├── connect-postgres-source.json       -> Postgres source connector
│   │   └── connect-standalone.properties      -> Standalone kafka conenct config
│   └── plugins
│       └── debezium-connector-postgres        -> Debezium connector jars should be downloaded to this folder
│       └── iceberg-kafka-connect              -> Iceberg kafka connect jars should be downloaded to this folder
├── postgres
│   ├── postgresql.conf                        -> Config with logical replication enabled
│   └── scripts
│       ├── manual
│       └── seed                               -> SQL scripts that will be run the first time the db is created i.e. when the data directory is empty
└── spark
    ├── .ivy                                   -> Kafka and iceberg dependency jars will be downloaded to this folder
    └── scripts
        ├── consumer.py                        -> Pyspark script to consume kafka messages and stream to console and iceberg sinks
        └── print_iceberg_tables.py            -> Pyspark script to query the tables created by Spark/Iceberg Sink Kafka connector

```
Moreover, these folders will be created and mounted so that docker containers can write back to the host file system.
```sh
├── data                                       -> Data from containers will be mounted to this path Configured in docker-compose file.
│   ├── kafka
│   │   └── out
│   │      ├── cdc.commerce.sink.txt           -> Output of Kafka File sink connector
│   │      └── iceberg/warehouse               -> Storage location used by Kafka Iceberg sink for each table data + metadata
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

    TMP_FOLDER=/tmp/iceberg-kafka-connect
    mkdir -p $TMP_FOLDER
    # See https://github.com/tabular-io/iceberg-kafka-connect/releases to get the download link.
    wget -qO- https://github.com/tabular-io/iceberg-kafka-connect/releases/download/v0.6.15/iceberg-kafka-connect-runtime-0.6.15.zip | tar -xvz -C $TMP_FOLDER
    cp $TMP_FOLDER/iceberg-kafka-connect-runtime-0.6.15/lib/*.jar $PWD/kafka/plugins/iceberg-kafka-connect && rm -rf $TMP_FOLDER
    # Download hadoop dependencies that are not included
    wget -P $PWD/kafka/plugins/iceberg-kafka-connect https://repo1.maven.org/maven2/org/apache/commons/commons-configuration2/2.0/commons-configuration2-2.0.jar
    wget -P $PWD/kafka/plugins/iceberg-kafka-connect https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-auth/3.3.6/hadoop-auth-3.3.6.jar
    ```

2. Run Docker compose. This will 
    1. Start the Postgres database and also run the scripts under `postgres/scripts/seed`.
    2. Start the Kafka in KRaft mode. The plugins from the previosuly step will be loaded.
    3. Start a spark container that will run the pyspark script from `spark/scripts/consumer.py`. This container will also be used to visualize the created iceberg tables.
    ```sh
    docker compose up
    ```

3. If we are running for the first time, spark container will need to download the required dependencies. We need to wait for the downloads to complete before we can proceed. We can monitor the stdout to see if the downloads are completed. Alternatively, we can also query to see the spark streaming app is already running.
    ```sh
    docker container exec kafka-spark curl -s http://localhost:4040/api/v1/applications | jq
    ```
    **Reponse**
    ```json
    [
      {
        "id": "local-1713191253855",
        "name": "cdc-consumer",
        "attempts": [
          {
            "startTime": "2024-04-15T14:27:32.908GMT",
            "endTime": "1969-12-31T23:59:59.999GMT",
            "lastUpdated": "2024-04-15T14:27:32.908GMT",
            "duration": 455827,
            "sparkUser": "root",
            "completed": false,
            "appSparkVersion": "3.5.1",
            "startTimeEpoch": 1713191252908,
            "endTimeEpoch": -1,
            "lastUpdatedEpoch": 1713191252908
          }
        ]
      }
    ]
    ```

4. Create and start the kafka connectors for postgres source and iceberg sink in detached mode.
    ```sh
    docker container exec -d kafka-standalone \
      /opt/kafka/bin/connect-standalone.sh \
      /opt/kafka/config-cdc/connect-standalone.properties \
      /opt/kafka/config-cdc/connect-postgres-source.json \
      /opt/kafka/config-cdc/connect-iceberg-sink.json
    ```
    Note: If we are facing issues with the iceberg sink connector, we can use the file sink connector to debug.
    ```sh
    docker container exec -d kafka-standalone \
      /opt/kafka/bin/connect-standalone.sh \
      /opt/kafka/config-cdc/connect-standalone.properties \
      /opt/kafka/config-cdc/connect-postgres-source.json \
      /opt/kafka/config-cdc/connect-file-sink.properties
    ```

5. We can monitor the console to see if the connectors are ready. Alternatively, we can also query to see the status of the connectors.
    ```sh
    curl -s localhost:8083/connectors/dbz-pg-source/status | jq
    curl -s localhost:8083/connectors/iceberg-sink/status | jq
    ```
    **Responses**
    ```json
    {
      "name": "dbz-pg-source",
      "connector": {
        "state": "RUNNING",
        "worker_id": "172.21.0.2:8083"
      },
      "tasks": [
        {
          "id": 0,
          "state": "RUNNING",
          "worker_id": "172.21.0.2:8083"
        }
      ],
      "type": "source"
    }
    ```
    ```json
    {
      "name": "iceberg-sink",
      "connector": {
        "state": "RUNNING",
        "worker_id": "172.21.0.2:8083"
      },
      "tasks": [
        {
          "id": 0,
          "state": "RUNNING",
          "worker_id": "172.21.0.2:8083"
        }
      ],
      "type": "sink"
    }
    ```

5. Check the Iceberg tables from the sinks.
    1. Check the iceberg tables created by Spark. 
        ```sh
        docker container exec kafka-spark \
          /opt/spark/bin/spark-submit \
          --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0 \
          --conf spark.driver.extraJavaOptions="-Divy.cache.dir=/.ivy -Divy.home=/.ivy" \
          /scripts/print_iceberg_tables.py spark
        ```
        **Output**
        ```
        +------+-----------------------------------------------------------------------+---+
        |before|after                                                                  |op |
        +------+-----------------------------------------------------------------------+---+
        |NULL  |{"user_id":1,"email":"alice@example.com","created_at":1713192083639740}|r  |
        |NULL  |{"user_id":2,"email":"bob@example.com","created_at":1713192083639740}  |r  |
        |NULL  |{"user_id":3,"email":"carol@example.com","created_at":1713192083639740}|r  |
        +------+-----------------------------------------------------------------------+---+

        +------+----------------------------------------------------------------------------------------+---+
        |before|after                                                                                   |op |
        +------+----------------------------------------------------------------------------------------+---+
        |NULL  |{"product_id":1,"product_name":"Live Edge Dining Table","created_at":1713192083641523}  |r  |
        |NULL  |{"product_id":2,"product_name":"Simple Teak Dining Chair","created_at":1713192083641523}|r  |
        +------+----------------------------------------------------------------------------------------+---+
        ```
    2. Check the iceberg tables created by Iceberg sink kafka connector. 
        ```sh
        docker container exec kafka-spark \
        /opt/spark/bin/spark-submit \
          --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0 \
          --conf spark.driver.extraJavaOptions="-Divy.cache.dir=/.ivy -Divy.home=/.ivy" \
          /scripts/print_iceberg_tables.py kafka
        ```
        **Output**
        ```
        +-------+-----------------+----------------+------------------------------------------------------------------------+
        |user_id|email            |created_at      |_cdc                                                                    |
        +-------+-----------------+----------------+------------------------------------------------------------------------+
        |1      |alice@example.com|1713192083639740|{I, 2024-04-15 14:43:04.407, 0, commerce.account, commerce.account, {1}}|
        |2      |bob@example.com  |1713192083639740|{I, 2024-04-15 14:43:04.411, 1, commerce.account, commerce.account, {2}}|
        |3      |carol@example.com|1713192083639740|{I, 2024-04-15 14:43:04.411, 2, commerce.account, commerce.account, {3}}|
        +-------+-----------------+----------------+------------------------------------------------------------------------+

        +----------+------------------------+----------------+------------------------------------------------------------------------+
        |product_id|product_name            |created_at      |_cdc                                                                    |
        +----------+------------------------+----------------+------------------------------------------------------------------------+
        |1         |Live Edge Dining Table  |1713192083641523|{I, 2024-04-15 14:43:04.417, 0, commerce.product, commerce.product, {1}}|
        |2         |Simple Teak Dining Chair|1713192083641523|{I, 2024-04-15 14:43:04.417, 1, commerce.product, commerce.product, {2}}|
        +----------+------------------------+----------------+------------------------------------------------------------------------+
        ```
    3. We can also run the pyspark shell to debug or run further analysis.
        ```sh
        docker container exec -it kafka-spark /opt/spark/bin/pyspark \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0 \
        --conf spark.driver.extraJavaOptions="-Divy.cache.dir=/.ivy -Divy.home=/.ivy"
        ```
6. Run the CUD operations on postgres. Repeat step 5-6.

## Helpful Commands for Debugging

### One-liner to wipe data directory while keeping .gitkeep files
```sh
find ./data ! -name .gitkeep -delete
```

### List kafka topics
```sh
/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
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

# Pause, resume, restart, stop or delete connectors
curl -X PUT localhost:8083/connectors/dbz-pg-source/pause
curl -X PUT localhost:8083/connectors/dbz-pg-source/resume
curl -X PUT localhost:8083/connectors/dbz-pg-source/restart
curl -X PUT localhost:8083/connectors/dbz-pg-source/stop
curl -X DELETE localhost:8083/connectors/dbz-pg-source
```
