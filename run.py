#!/usr/bin/env python3
"""
MHS Harmonised Pipeline — entry point.

Usage:
    python run.py [options]

Options:
    --excel-dir PATH   Directory containing .xlsx/.xls files  [default: sample-excels]
    --db PATH          DuckDB file path                        [default: mhs.duckdb]
    --stage STAGE      Which stage(s) to run: ingest | harmonise | all  [default: all]
    --no-export-raw    Skip Stage 1 CSV/Parquet export
    --no-export-harm   Skip Stage 2 CSV/Parquet/JSON export

Process flow
────────────
Stage 1 — Ingest
  Scan excel-dir → parse each .xlsx with a table-specific parser (falls back to
  generic) → load into DuckDB as raw tables → export CSV + Parquet to
  outputs/stage1_raw/<table_name>/

Stage 2 — Harmonise
  (a) Apply column renames  → m_<table>  (stable output column names)
  (b) Stitch timeseries     → s_<name>   (union prev/current tables, dedup by date)
  (c) Domain consolidation  → h_<name>   (full-outer-join related tables)
  (d) Dedup suffix columns              (drop _1/_2 cols if they are true duplicates)
  → export CSV + Parquet + JSON to outputs/stage2_harmonised/<domain>/

All events are logged to logs/<run_id>_run.jsonl and logs/<run_id>_summary.txt.
Harmonisation decisions are also stored in the _harmonise_log DuckDB table.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline import db as db_mod
from pipeline import export as export_mod
from pipeline import harmonise as harm_mod
from pipeline import ingest as ingest_mod
from pipeline.log import RunLogger


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BNM MHS harmonised pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--excel-dir",    default="sample-excels", help="Directory with Excel files")
    parser.add_argument("--db",           default="mhs.duckdb",    help="DuckDB file path")
    parser.add_argument("--stage",        default="all",           choices=["ingest", "harmonise", "all"])
    parser.add_argument("--no-export-raw",  action="store_true",   help="Skip Stage 1 exports")
    parser.add_argument("--no-export-harm", action="store_true",   help="Skip Stage 2 exports")
    args = parser.parse_args()

    excel_dir = Path(args.excel_dir)
    db_path   = Path(args.db)

    if args.stage in ("ingest", "all") and not excel_dir.is_dir():
        print(f"Error: excel directory not found: {excel_dir}")
        sys.exit(1)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    t0     = time.time()
    logger = RunLogger(run_id)

    print(f"\nMHS Pipeline — run {run_id}")
    print(f"Excel dir : {excel_dir.resolve()}")
    print(f"Database  : {db_path.resolve()}")
    print(f"Stage     : {args.stage}")

    con = db_mod.connect(db_path)
    db_mod.init_schema(con)

    # ── Stage 1: ingest ────────────────────────────────────────────────────────
    if args.stage in ("ingest", "all"):
        result = ingest_mod.run(excel_dir, con, logger)

        if not args.no_export_raw:
            export_mod.export_raw_tables(con, logger)

    # ── Stage 2: harmonise ─────────────────────────────────────────────────────
    if args.stage in ("harmonise", "all"):
        domain_tables = harm_mod.run(con, logger, run_id)

        if not args.no_export_harm:
            export_mod.export_harmonised_tables(con, domain_tables, logger)

    con.close()

    elapsed = time.time() - t0
    print(f"\n{'═' * 60}")
    print(f"Run {run_id} complete in {elapsed:.1f}s")
    logger.close()


if __name__ == "__main__":
    main()
