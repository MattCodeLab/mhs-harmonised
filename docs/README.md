# MHS Harmonised Pipeline

Converts BNM Monthly Highlights Statistics Excel workbooks into clean,
domain-organised Parquet, CSV, and JSON files via a two-stage pipeline backed
by DuckDB.

---

## Quick start

```bash
# Install dependencies (uv recommended)
uv sync

# Run the full pipeline (ingest + harmonise + export)
python run.py --excel-dir ../mhs-automation/sample-excels

# Run only the ingest stage (Excel → DuckDB raw tables + Stage 1 exports)
python run.py --excel-dir ../mhs-automation/sample-excels --stage ingest

# Run only harmonisation (assumes the DB already has raw tables)
python run.py --stage harmonise

# Skip file exports (data stays in DuckDB only)
python run.py --stage all --no-export-raw --no-export-harm
```

---

## Process flow

```
Excel files
    │
    ▼
[Stage 1 — Ingest]
    │  discover_files()   scan excel-dir, deduplicate
    │  parse_bnm_excel()  table-specific or generic parser
    │  load_raw_table()   write to DuckDB as raw table
    │
    ├─► outputs/stage1_raw/<table_name>/<table_name>.csv
    └─► outputs/stage1_raw/<table_name>/<table_name>.parquet
    │
    ▼
[Stage 2a — Column mapping]
    │  Apply renames from pipeline/column_map.py
    │  Creates m_<table> tables in DuckDB
    │
    ▼
[Stage 2b — Timeseries stitching]
    │  UNION prev/current tables, deduplicate by (date, frequency, key_col)
    │  Creates s_<name> tables in DuckDB
    │  Defined by STITCH_RULES in pipeline/harmonise.py
    │
    ▼
[Stage 2c — Domain consolidation]
    │  FULL OUTER JOIN related s_/m_ tables into one domain table
    │  Creates h_<name> tables in DuckDB
    │  Defined by DOMAIN_RULES in pipeline/harmonise.py
    │
    ▼
[Stage 2d — Dedup suffix columns]
    │  Drop _1/_2 columns that are true duplicates of the base column
    │  Merge candidate-only values into base before dropping
    │  Keeps columns with genuine conflicts
    │
    ├─► outputs/stage2_harmonised/<domain>/<slug>.csv
    ├─► outputs/stage2_harmonised/<domain>/<slug>.parquet
    └─► outputs/stage2_harmonised/<domain>/<slug>.json
```

---

## Output structure

### Stage 1 — Pre-harmonisation

```
outputs/stage1_raw/
└── <table_name>/
    ├── <table_name>.csv
    └── <table_name>.parquet
```

Raw tables preserve parser-native column names.

### Stage 2 — Post-harmonisation

```
outputs/stage2_harmonised/
├── monetary_system/
│   ├── money_supply.{csv,parquet,json}
│   ├── currency_in_circulation.{csv,parquet,json}
│   ├── bnm_balance_sheet.{csv,parquet,json}
│   └── liquidity_reserves.{csv,parquet,json}
├── banking_system/
│   ├── banking_balance_sheet.{csv,parquet,json}
│   ├── loans_by_purpose.{csv,parquet,json}
│   ├── loans_by_sector.{csv,parquet,json}
│   ├── sme_loans.{csv,parquet,json}
│   ├── deposits_funding.{csv,parquet,json}
│   ├── payments.{csv,parquet,json}
│   └── asset_quality_provisions.{csv,parquet,json}
├── financial_markets/
│   ├── interest_rates.{csv,parquet,json}
│   ├── exchange_rates.{csv,parquet,json}
│   ├── money_market_activity.{csv,parquet,json}
│   ├── bond_sukuk.{csv,parquet,json}
│   ├── derivatives.{csv,parquet,json}
│   ├── capital_raising.{csv,parquet,json}
│   └── international.{csv,parquet,json}
├── insurance_takaful/
│   ├── insurance_balance_sheet.{csv,parquet,json}
│   ├── life_family_insurance.{csv,parquet,json}
│   ├── general_insurance_takaful.{csv,parquet,json}
│   └── intermediaries.{csv,parquet,json}
└── institutions_access/
    └── employment.{csv,parquet,json}
```

JSON format:
```json
{
  "metadata": {
    "table": "h_1_money_supply",
    "domain": "monetary_system",
    "slug": "money_supply",
    "exported_at": "...",
    "total_rows": 1234,
    "date_min": "1970-01-01",
    "date_max": "2024-12-01",
    "columns": ["date", "frequency", ...],
    "source": "Bank Negara Malaysia Monthly Highlights Statistics",
    "url": "https://www.bnm.gov.my/publications/mhs"
  },
  "data": [{"date": "2024-12-01", ...}, ...]
}
```

---

## DuckDB table layers

| Prefix | Description                          | Example                        |
|--------|--------------------------------------|--------------------------------|
| _(none)_ | Raw ingested tables               | `1_3_1_broad_money_m3`         |
| `m_`   | Column-renamed (mapped)              | `m_1_3_1_broad_money_m3`       |
| `s_`   | Stitched timeseries                  | `s_loans_by_purpose`           |
| `h_`   | Domain-consolidated output tables    | `h_1_money_supply`             |
| `_catalog` | Load metadata per raw table    | —                              |
| `_harmonise_log` | Harmonisation audit trail | —                              |

Query the DuckDB file directly to inspect any layer:

```python
import duckdb
con = duckdb.connect("mhs.duckdb")

# What tables exist?
con.sql("SELECT table_name FROM information_schema.tables ORDER BY 1").show()

# Check the catalog
con.sql("SELECT table_id, domain, row_count, date_min, date_max FROM _catalog LIMIT 20").show()

# Inspect harmonisation decisions
con.sql("SELECT * FROM _harmonise_log WHERE action LIKE '%conflict%'").show()

# Query a domain table
con.sql("SELECT * FROM h_1_money_supply ORDER BY date DESC LIMIT 10").show()
```

---

## Logging

Every run writes:

```
logs/
├── <run_id>_run.jsonl    # one JSON event per line (machine-readable)
└── <run_id>_summary.txt  # human-readable summary with counts and failures
```

Event schema:
```json
{"ts": "2025-01-01T12:00:00", "stage": "ingest", "action": "loaded",
 "table_id": "1.1", "row_count": 500, "col_count": 12, ...}
```

---

## Adding a new parser

1. Add the table ID to `pipeline/catalog.py` `CATALOG` dict.
2. Create `pipeline/parsers/tables/t_<safe_id>.py` with a `parse(raw, path, table_id)` function.
3. Add column renames to `pipeline/column_map.py` `RENAME` dict.
4. If the table should be stitched with previous editions, add a rule to `STITCH_RULES` in `pipeline/harmonise.py`.
5. If the table belongs in an existing domain, add it to the appropriate `DOMAIN_RULES` entry.

---

## Modifying harmonisation

All harmonisation logic is configured in `pipeline/harmonise.py`:

- **`STITCH_RULES`** — list of `(output_name, [member_table_ids], key_col)`.
  Controls which tables are unioned to build a continuous timeseries.

- **`DOMAIN_RULES`** — list of `DomainTable(name, sources, join_cols, select_override)`.
  Controls which tables are joined to build each output domain table.
  If `select_override` is set, that SQL is used verbatim (useful when the join
  logic needs explicit column selection or aggregation).

---

## Dependencies

| Package   | Purpose                       |
|-----------|-------------------------------|
| duckdb    | In-process analytics database |
| pandas    | DataFrame manipulation        |
| openpyxl  | Read .xlsx files              |
| xlrd      | Read legacy .xls files        |
| pyarrow   | Parquet serialisation         |
