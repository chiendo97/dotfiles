---
name: duckdb
description: Query local data files (parquet, csv, json) with DuckDB SQL without loading them. Use when the user wants to read, inspect, or query parquet/csv/json/ndjson files with SQL, asks "how do I query this file", or mentions duckdb.
---

# DuckDB on local files

Zero-load SQL: query files directly, no import step.

## Environment

- CLI: `~/.local/bin/duckdb` (installed from GitHub releases).
- The PyPI/`uvx` `duckdb` package has **no executable** — `uvx duckdb` fails. For Python: `uv run --with duckdb python`.

## Recipe

```bash
# interactive (box-drawn tables, tab-complete, .exit)
duckdb -box

# one-shot
duckdb -box -c "SELECT * FROM read_parquet('files/**/*.parquet') LIMIT 10"
```

Working directory matters: paths are relative to the **current shell directory**, not the repo root. If a glob returns "No files found", check `pwd` first.

## Querying files

```sql
SELECT * FROM read_parquet('dir/**/*.parquet');     -- glob OK
SELECT * FROM read_parquet('a.parquet', 'b.parquet', union_by_name=true);  -- mismatched schemas → NULL-pad
SELECT * FROM 'file.csv';                            -- auto-detect
SELECT * FROM read_csv('f.csv', header=true, delim=';');
SELECT * FROM read_json('f.ndjson', format='auto');
```

- `filename` is an auto-exposed column when a glob matches multiple files — filter on it: `WHERE filename ~ 'norm'`.
- Parquet predicates push down: `WHERE di = '2026-09-18'` skips row groups.
- Inspect first: `DESCRIBE SELECT * FROM read_parquet('f.parquet');` or `SUMMARIZE ...` (min/max/nulls per column).

## Output / export

```sql
COPY (SELECT * FROM t) TO 'out.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
COPY t TO 'out.csv' (HEADER);
```

## Gotchas

- Mismatched schemas across a glob fail unless `union_by_name=true` (error names the two files and the missing column).
- String timestamps stay strings — cast: `created_at::TIMESTAMP`.
- timestamptz columns display in local tz.
- One writer per `.duck` DB file; file reads are always safe to share.

## Useful extras

```sql
SELECT * FROM t USING SAMPLE 10%;                                   -- sampling
SELECT * FROM t QUALIFY row_number() OVER (PARTITION BY k ORDER BY ts DESC) = 1;  -- latest per group, no subquery
EXPLAIN ANALYZE SELECT ...;                                          -- actual timings
CREATE MACRO norm(s) AS s.lower()::VARCHAR;                          -- scalar macro
ATTACH './other.duck' AS odb;                                        -- second catalog
```