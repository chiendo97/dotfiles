---
name: xleak
description: >
  Read and extract data from Excel files (.xlsx, .xls, .xlsm, .xlsb, .ods) using the xleak CLI tool.
  Use this skill whenever you need to read, inspect, preview, or extract data from spreadsheet files.
  This includes tasks like: analyzing Excel data, converting spreadsheets to JSON/CSV, checking what
  sheets or tables exist in a workbook, previewing rows, or any task involving .xlsx/.xls/.ods files.
  Even if the user doesn't mention "xleak" by name — if they reference an Excel/spreadsheet file
  and want to see or work with its contents, use this skill.
---

# xleak — Excel Data Extraction

`xleak` is a fast Rust-based CLI tool (installed at `~/.cargo/bin/xleak`) that reads Excel and
spreadsheet files without requiring Microsoft Excel or Python. It supports `.xlsx`, `.xls`,
`.xlsm`, `.xlsb`, and `.ods` formats.

## Quick Reference

```bash
# Preview first 50 rows (default) in terminal table format
xleak file.xlsx

# List all sheet names
xleak file.xlsx   # sheet name shown in header

# View a specific sheet (by name or 1-based index)
xleak file.xlsx --sheet "Sheet2"
xleak file.xlsx --sheet 2

# Export as JSON (structured, includes headers and metadata)
xleak file.xlsx --export json

# Export as CSV
xleak file.xlsx --export csv

# List named Excel tables (.xlsx only)
xleak file.xlsx --list-tables

# Extract a specific named table
xleak file.xlsx --table "SalesData" --export json
```

## Important Behavior: Row Limiting

The `-n` flag controls how many rows are displayed in **terminal table mode only**.
It does **NOT** limit output when using `--export json` or `--export csv` — those always
export all rows regardless of `-n`.

To limit exported rows, pipe the output:

```bash
# JSON: use jq to slice the data array
xleak file.xlsx --export json | jq '{sheet, rows, columns, headers, data: .data[:100]}'

# CSV: use head (add 1 for header row)
xleak file.xlsx --export csv | head -n 101   # 100 data rows + 1 header
```

## JSON Output Structure

When using `--export json`, xleak produces:

```json
{
  "sheet": "Sheet1",
  "rows": 18081,
  "columns": 35,
  "headers": ["Col1", "Col2", ...],
  "data": [
    ["val1", 42, null, ...],
    ...
  ]
}
```

- `rows` / `columns`: total counts in the sheet (useful for knowing size before reading all data)
- `headers`: column names from the first row
- `data`: array of arrays, with typed values (strings, numbers, booleans, null)

## Recommended Workflow

1. **Start with a preview** to understand the file structure:
   ```bash
   xleak file.xlsx -n 5
   ```
   This shows a formatted table with sheet name, row/column counts, and sample data.

2. **For programmatic use**, export as JSON and slice if the file is large:
   ```bash
   # Small files (< 1000 rows): export everything
   xleak file.xlsx --export json

   # Large files: slice to what you need
   xleak file.xlsx --export json | jq '{sheet, rows, columns, headers, data: .data[:50]}'
   ```

3. **For multi-sheet workbooks**, check available sheets first:
   ```bash
   xleak file.xlsx -n 1          # shows default sheet info
   xleak file.xlsx --sheet 2 -n 1  # check second sheet
   ```

4. **For named tables** (.xlsx only):
   ```bash
   xleak file.xlsx --list-tables
   xleak file.xlsx --table "TableName" --export json
   ```

## jq Filtering Patterns

When piping xleak JSON through jq, zsh escapes `!=` as `\!=` which breaks jq filters.
This is the most common pitfall when working with xleak output programmatically.

**Safe patterns (work in both bash and zsh):**

```bash
# Filter rows where column index 12 has a value (truthy check — avoids != entirely)
xleak file.xlsx --sheet "Field Dictionary" --export json \
  | jq -r '.data[] | select(.[12]) | [.[1], .[3], .[12]] | @tsv'

# Filter non-null with pipe syntax (zsh-safe alternative to != null)
xleak file.xlsx --export json | jq '.data[] | select(.[5] | . != null)'

# Count non-empty values in a column
xleak file.xlsx --export json | jq '[.data[] | select(.[12])] | length'

# Extract specific columns as CSV-like output
xleak file.xlsx --export json \
  | jq -r '.data[] | [.[0], .[3], .[7]] | @csv'
```

**Patterns to AVOID (break in zsh):**

```bash
# BAD: != gets escaped to \!= by zsh
xleak file.xlsx --export json | jq '.data[] | select(.[12] != null and .[12] != "")'
#                                                        ^^ zsh escapes this

# GOOD: use truthy check instead
xleak file.xlsx --export json | jq '.data[] | select(.[12])'
```

The truthy `select(.[N])` pattern filters out both `null` and `""` in one shot,
so it's both simpler and shell-safe.

## Gotchas

- **jq `!=` breaks in zsh** — see jq Filtering Patterns above. Use `select(.[N])` truthy
  checks or pipe syntax `select(.[N] | . != null)` instead of inline `!=`.
- **Large file JSON export is slow** — `xleak file.xlsx --export json` reads the entire file
  into memory. For files with 10k+ rows, prefer CSV export or use jq to slice early.
- **Column truncation in terminal mode** — columns wider than 30 chars are truncated by default.
  Use `-w 50` to increase, or `--wrap` to wrap text.
- **No write support** — xleak is read-only. To modify Excel files, use other tools.
- **ODS limitations** — `.ods` files don't support named tables or formulas display.
