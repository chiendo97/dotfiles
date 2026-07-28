---
name: validate-schema-input
description: |
  Use when validating input documents (design docs, Excel files, BA specs) before generating
  canonical schema markdown. Checks field completeness, source quality, type correctness,
  naming consistency, business rules, and cross-schema alignment.
  Trigger on: "validate schema", "check schema input", "validate input", "pre-check schema",
  or when user provides source material and wants to verify it's ready for schema generation.
---

# Validate Schema Input

Pre-validation skill that checks source material against canonical schema rules
before running `generate-canonical-schema`. Produces a markdown report with
errors, warnings, questions, and suggested fixes.

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Entity name | Yes | The canonical entity being validated (e.g., `Order`, `Shipment`) |
| Source material | Yes | Design doc, Excel file, BA spec, or existing schema to validate |
| Sibling schemas | No | Paths to related canonical schemas for cross-schema checks |

Use the `xleak` skill if the input is an Excel file.

## Output Path

```
./reports/{domain}/{entity-name}-validation-report.md
```

## Workflow

### Step 1: Read Source Material

Read the input document and extract all fields, sources, business rules, and filters.
Identify which format the input uses (design doc format vs canonical schema format).

### Step 2: Run Validation Checks

Apply all checks from the 7 categories below. For each issue found, record:
- Severity: `Error`, `Warning`, or `Question`
- Field name (or `—` for entity-level issues)
- Issue description
- Suggested fix (for Errors and Warnings)

### Step 3: Cross-Schema Checks (if siblings provided)

If the user provided sibling schema paths, read them and compare:
- Join key naming alignment
- Shared field naming consistency

### Step 4: Generate Report

Write the validation report to `./reports/{domain}/{entity-name}-validation-report.md`.

### Step 5: Summarize

Report in conversation:
- Total fields found
- Error / Warning / Question counts
- "Ready for schema generation" verdict
- List of blocking error fields

## Severity Levels

| Level | Meaning | Blocks? |
|-------|---------|---------|
| **Error** | Cannot generate schema — must fix first | Yes |
| **Warning** | Can generate but result may be wrong | No |
| **Question** | Needs human clarification | No |

## Validation Checks

### 1. Field Completeness

| Check | Severity | Suggested Fix Pattern |
|-------|----------|----------------------|
| Field has no name | Error | Flag row number in source |
| Field has no source mapping (blank) | Error | `Specify source: fact.{dataset}.{column} or computed = ...` |
| Field has no required flag | Warning | `Assume required (✔) or optional (—)?` |
| Field has no description | Warning | `Add description for: {FIELD_NAME}` |

### 2. Source Quality

| Check | Severity | Suggested Fix Pattern |
|-------|----------|----------------------|
| Source says "System-generated" with no formula | Error | `Specify: computed = {formula with full dot-notation}` |
| Source says "Derived from..." without table/column | Error | `Specify: fact.{dataset}.{column}` |
| Computed formula uses bare column names | Error | `Use full paths: fact.all_orders.item_price not item_price` |
| Source references a table but no column name | Warning | `Specify column: master.t{NNN}.{column_name}` |
| Multi-hop lookup path unclear | Warning | `Clarify join path: {start} → {intermediate} → {target}` |
| Cross-canonical reference missing entity or field | Warning | `Specify: canonical.{entity}.{field}` |

### 3. Type Validation

| Check | Severity | Suggested Fix Pattern |
|-------|----------|----------------------|
| Field has no type | Error | `Specify type: string, date, decimal(2), integer, enum(...), boolean` |
| Type uses SQL syntax (`VARCHAR`, `DECIMAL(18,2)`, `INT`) | Error | `Use: string, decimal(2), integer` |
| Enum type without listed values | Warning | `List values: enum(A\|B\|C)` |

**Allowed types:** `string`, `date`, `datetime`, `integer`, `decimal(N)`, `enum(A\|B\|C)`, `boolean`

### 4. Structure Validation

| Check | Severity | Suggested Fix Pattern |
|-------|----------|----------------------|
| Extra columns beyond the 6 allowed | Warning | `Remove columns: Sample, Master Data, Note, Ref` |
| No Header/Line level separation | Warning | `Split into Header-Level Fields and Line-Level Fields` |
| No field grouping (Identifiers, Dates, etc.) | Warning | `Add group headers` |

**Required columns:** `#`, `Field`, `Required`, `Type`, `Source`, `Description` — exactly these.

### 5. Naming Consistency

| Check | Severity | Suggested Fix Pattern |
|-------|----------|----------------------|
| Field name not `UPPER_SNAKE_CASE` | Warning | `Rename: {current} → {UPPER_SNAKE_CASE}` |
| Composite key naming doesn't match sibling schemas | Warning | `Rename to match: {sibling_pattern}` |
| Duplicate field name within entity | Error | `Remove duplicate or rename: {FIELD_NAME}` |

### 6. Business Rules

| Check | Severity | Suggested Fix Pattern |
|-------|----------|----------------------|
| Implicit rule without BR code (e.g., "YYYY-MM-DD") | Warning | `Assign BR code: BR{N} — Date Format` |
| Duplicate BR codes | Warning | `Renumber: BR{N} is used twice` |
| BR doesn't reference any field | Warning | `Add Fields column: which fields does BR{N} affect?` |

### 7. Cross-Schema (requires user-specified sibling paths)

| Check | Severity | Suggested Fix Pattern |
|-------|----------|----------------------|
| Join key name doesn't match downstream consumer | Question | `{Entity} uses {KEY_A}, downstream uses {KEY_B} — align?` |
| Shared field name inconsistency across schemas | Question | `This entity uses {NAME_A}, {sibling} uses {NAME_B} — standardize?` |

### Not Enforced

- Master data table/column existence — skipped

## Report Template

```markdown
# Validation Report: {Entity Name}

**Source:** `{input file path}`
**Date:** {YYYY-MM-DD}
**Result:** {X errors, Y warnings, Z questions}

---

## Errors

| # | Field | Issue | Suggested Fix |
|---|-------|-------|---------------|
| 1 | `FIELD` | {issue} | {fix} |

## Warnings

| # | Field | Issue | Suggested Fix |
|---|-------|-------|---------------|
| 1 | `FIELD` | {issue} | {fix} |

## Questions

| # | Field | Question |
|---|-------|----------|
| 1 | `FIELD` | {question} |

---

## Summary

- **Total fields:** {N}
- **Ready for schema generation:** {Yes/No}
- **Blocking issues:** {list of error field names}
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skipping type validation | Every field needs a type — check for SQL types too |
| Not checking computed formula paths | `item_price / quantity` must be `fact.all_orders.item_price / fact.all_orders.quantity` |
| Ignoring structure issues | Input may have 8 columns — flag extra columns for removal |
| Running generate-canonical-schema with errors | Always resolve errors first — warnings are OK to proceed |
