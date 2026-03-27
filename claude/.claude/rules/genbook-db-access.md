When working on the genbook project, you can use `usql` to access external databases.

Connection strings (with credentials) are stored in the genbook project config files — **never hardcode them here**:

- **Dev**: `configs/dev-aws.yaml` — contains `database_url` (PostgreSQL) and `clickhouse_config` (ClickHouse)
- **Prod**: `configs/aws.yaml` — same keys, prod values

To connect, read the appropriate config file to extract the connection string, then run:

```bash
usql '<connection-string-from-config>'
```
