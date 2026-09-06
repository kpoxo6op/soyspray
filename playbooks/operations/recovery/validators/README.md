# Native restored-data checks

These scripts run only through `validate-durable.yml`, on the disposable restored
claim. The Job uses the corresponding running image digest and has no Kubernetes
token. The restore namespace denies ingress and egress.

MariaDB checks all restored tables through a local socket. PostgreSQL starts the
restored PG17 data and checks heaps and indexes with `pg_amcheck`. Redis validates
the multipart AOF and RDB files. Mosquitto must load its persistence file and remain
running. These operations can update only the disposable restored files.
