# Configurations for the connectors

## connect-postgres-source.json

Debezium postgres connector will create one Kafka topic per one Postgres table. The topics are prefixed by `topic.prefix`, followed by schema name and table name. Example - `cdc.commerce.account`.

## connect-iceberg-sink.json

Here is a brief description of the configs.
- Subscribe to multiple topics using `topics.regex`.
- Transform the debezium records using the provided SMT. This is controlled by `transforms` and `transforms.{xxx}.type`. Since we are using Debezium transformer, we also need to set  `iceberg.tables.cdc-field` and `iceberg.tables.route-field`.
- Set `transforms.debezium.cdc.target.pattern` to `cdc.{db}_{table}` to overwrite the [default](https://github.com/tabular-io/iceberg-kafka-connect/blob/v0.6.15/kafka-connect-transforms/README.md?plain=1#L49) `{db}.{table}`.
    - `cdc` is the `topic.prefix` we used in connect-postgres-source.json.
- Specify where the files will be written to using `iceberg.catalog.warehouse`. 
- Since `iceberg.tables.upsert-mode-enabled` is set, we have to set the `id-columns` for **each** table. 
    ```
        "iceberg.table.cdc.commerce_account.id-columns": "user_id",
        "iceberg.table.cdc.commerce_product.id-columns": "product_id",
    ```

## connect-standalone.properties

Changed `plugin.path` to include additional jars from `/opt/kafka/plugins`.
