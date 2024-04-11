# POSTGRES-KAFKA-ICEBERG-PIPELINE

Stream changes from databases as iceberg records.

## Contents
```sh
├── docker-compose.yaml                        -> Compose file to launch postgres and kafka
├── data                                       -> Data from containers will be mounted to this path Configured in docker-compose file.
├── kafka
│   ├── config
│   │   ├── connect-file-sink.properties       -> File Sink
│   │   ├── connect-postgres-source.json       -> Postgres Source via debezium
│   │   └── connect-standalone.properties      -> Standalone kafka conenct config
│   └── plugins
│       └── debezium-connector-postgres        -> Debezium connector jars will be downloaded to this folder
└── postgres
    ├── postgresql.conf                        -> Config with logical replication enabled
    └── scripts
        ├── manual
        │   ├── 001_insert.sql
        │   ├── 002_update.sql
        │   └── 003_delete.sql
        └── seed                               -> SQL scripts that will be run the first time the db is created i.e. when the data directory is empty
            ├── 000_init.sql                   -> SQL scripts to create schemas and tables
            └── 001_insert.sql                 -> SQL scripts 
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
    docker compose -f docker-compose.yaml up
    ```

3. Create and start the connectors.
    ```sh
    docker container exec -d kafka-standalone \
      /opt/kafka/bin/connect-standalone.sh \
      /opt/kafka/config-cdc/connect-standalone.properties \
      /opt/kafka/config-cdc/connect-postgres-source.json \
      /opt/kafka/config-cdc/connect-file-sink.properties
    ```

## Helpful Commands for Debugging

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
