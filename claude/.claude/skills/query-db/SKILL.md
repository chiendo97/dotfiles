---
name: query-db
description: Query genbook project databases (PostgreSQL and ClickHouse) using usql. Use this skill whenever you need to run SQL queries, inspect tables, check data, or investigate database issues in the genbook project. This includes checking if data exists, debugging empty API responses, verifying migrations, inspecting table schemas, or any database exploration. Always use this skill before writing raw usql commands — it knows the correct connection strings for dev vs prod and prevents accidental production queries.
---

# Query Genbook Databases

This skill provides safe access to the genbook project's external databases via `usql`.
The project has **four** database connections — two PostgreSQL instances (dev and prod) and two ClickHouse instances (dev and prod).
Getting the connection wrong means querying or mutating the wrong environment, so this skill enforces environment awareness.

## Connection Strings

The connection strings below are hardcoded for convenience, but the **source of truth** is in the config files:
- `configs/dev-aws.yaml` — dev environment (PostgreSQL `database_url` + `clickhouse_config`)
- `configs/aws.yaml` — prod environment (PostgreSQL `database_url` + `clickhouse_config`)

If these credentials change, read the config files to get the current values.

### PostgreSQL (App Database)

Two separate databases on the same RDS host. They differ by database name and user prefix:

| Environment | Database | User | Config |
|---|---|---|---|
| **Dev** | `dev_genbook` | `dev_genbook_user` | `configs/dev-aws.yaml` |
| **Prod** | `genbook` | `genbook_user` | `configs/aws.yaml` |

```
# Dev PostgreSQL
postgresql://dev_genbook_user:kLUfESBLHpGBW9mGyRZecmFteggjP6yK@genbook-db01.chsacewieknx.ap-southeast-1.rds.amazonaws.com/dev_genbook

# Prod PostgreSQL
postgresql://genbook_user:kLUfESBLHpGBW9mGyRZecmFteggjP6yK@genbook-db01.chsacewieknx.ap-southeast-1.rds.amazonaws.com/genbook
```

### ClickHouse (Analytics/OLAP)

Two separate ClickHouse clusters with different ELB hostnames:

| Environment | Host prefix | Config |
|---|---|---|
| **Dev** | `k8s-devgenbo-clickhou-*` | `configs/dev-aws.yaml` |
| **Prod** | `k8s-genbook-clickhou-*` | `configs/aws.yaml` |

```
# Dev ClickHouse
clickhouse://admin:changeme_admin_password@k8s-devgenbo-clickhou-7eb9c99774-6eef1b5a5b0c9a0f.elb.ap-southeast-1.amazonaws.com/default

# Prod ClickHouse
clickhouse://admin:changeme_admin_password@k8s-genbook-clickhou-fb96ada8c9-22315adfa474c9fe.elb.ap-southeast-1.amazonaws.com/default
```

Both use the same credentials (`admin` / `changeme_admin_password`) and database (`default`), but point to different clusters.

## Environment Rules

**Default to dev for all queries** unless the user explicitly asks for prod. The dev and prod databases look identical in schema — it's easy to accidentally query production.

**Before every query, decide which environment:**

1. If the user says "dev", "test", "local", or **doesn't specify** → use **dev** connections
2. If the user says "prod", "production", or "live" → use **prod** connections, and:
   - For **read** queries: proceed, but mention you're querying prod
   - For **write/mutate** queries (INSERT, UPDATE, DELETE, DROP, ALTER): **stop and confirm** with the user before executing
3. When comparing environments (e.g., "why does dev have no data but prod does?"), query both but label outputs clearly

**How to tell them apart at a glance:**
- PostgreSQL: `dev_genbook` vs `genbook` in the connection string
- ClickHouse: `k8s-devgenbo-` vs `k8s-genbook-` in the hostname

## Query Patterns

Use `usql` with these flags for scripting-friendly output:

```bash
# Standard query (human-readable table output)
usql '<connection-string>' -c "SELECT ..."

# Script-friendly output (no headers, no alignment, pipe-delimited)
usql '<connection-string>' -c "SELECT ..." --no-align --tuples-only

# Inspect table schema (PostgreSQL)
usql '<connection-string>' -c "\d tablename"

# ClickHouse: list tables
usql '<clickhouse-connection>' -c "SHOW TABLES FROM default;"

# ClickHouse: inspect columns
usql '<clickhouse-connection>' -c "SELECT name, type FROM system.columns WHERE table = 'tablename' AND database = 'default' ORDER BY position;"
```

Set a timeout of 15000ms on usql commands to avoid hanging on network issues.

## Common Tables

### PostgreSQL
- `campaign` — marketing campaigns (shop_id, campaign_name, campaign_type, sku, editable)
- `import` — data import records (import_id, shop_id, data_type, status, data_uri, records_count)
- `product` — product catalog (sku, product_name, etc.)
- `shop` — shop records

### ClickHouse
- `import_marketing_spa` / `import_marketing_sbc` / `import_marketing_sda` — marketing data by campaign type
- `import_order` — order data
- `import_settlement` — settlement data
- `marketing_view` — aggregated marketing view

## Example Workflow

When investigating an issue like "why does this API return empty?":

1. Identify the relevant table from the codebase
2. Query **dev** first to check if data exists
3. If dev is empty but the issue was reported on prod, query prod (read-only) to compare
4. Report findings with row counts and sample data
