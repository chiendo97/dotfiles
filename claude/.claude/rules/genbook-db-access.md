When working on the genbook project, you can use `usql` to access external databases:

- **ClickHouse** (analytics/OLAP): `usql 'clickhouse://admin:changeme_admin_password@k8s-genbook-clickhou-fb96ada8c9-22315adfa474c9fe.elb.ap-southeast-1.amazonaws.com/default'`
- **PostgreSQL** (primary app DB): `usql 'postgresql://genbook_user:kLUfESBLHpGBW9mGyRZecmFteggjP6yK@genbook-db01.chsacewieknx.ap-southeast-1.rds.amazonaws.com/genbook'`
