#!/usr/bin/env python3
"""
MHS Harmonised Pipeline — streamlined entry point.

Takes raw Excel files and produces harmonised CSV / Parquet / JSON outputs
directly.  No stage1_raw intermediate files are written.  DuckDB is used
in-memory by default so no .duckdb file is left behind.

Usage
-----
    python run_harmonised.py                        # defaults
    python run_harmonised.py --excel-dir my-excels
    python run_harmonised.py --out-dir  /data/harmonised
    python run_harmonised.py --db       work.duckdb  # keep DB for inspection

Options
-------
    --excel-dir PATH   Directory containing .xlsx / .xls files  [default: sample-excels]
    --out-dir   PATH   Where to write harmonised outputs         [default: outputs/stage2_harmonised]
    --db        PATH   DuckDB path; use ':memory:' to leave no file  [default: :memory:]
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
        description="BNM MHS — Excel → harmonised outputs (no intermediate files)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--excel-dir",
        default="sample-excels",
        metavar="PATH",
        help="Directory containing .xlsx/.xls files (default: sample-excels)",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        metavar="PATH",
        help="Output directory for harmonised files (default: outputs/stage2_harmonised)",
    )
    parser.add_argument(
        "--db",
        default=":memory:",
        metavar="PATH",
        help="DuckDB path — use ':memory:' to leave no file behind (default: :memory:)",
    )
    args = parser.parse_args()

    excel_dir = Path(args.excel_dir)
    out_dir   = Path(args.out_dir) if args.out_dir else None

    if not excel_dir.is_dir():
        print(f"Error: excel directory not found: {excel_dir}")
        sys.exit(1)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    t0     = time.time()
    logger = RunLogger(run_id)

    print(f"\nMHS Harmonised Pipeline — run {run_id}")
    print(f"Excel dir : {excel_dir.resolve()}")
    print(f"Output dir: {(out_dir or Path('outputs/stage2_harmonised')).resolve()}")
    print(f"Database  : {args.db}")

    con = db_mod.connect(Path(args.db))
    db_mod.init_schema(con)

    # ── Ingest: Excel → DuckDB raw tables (no file export) ────────────────────
    ingest_mod.run(excel_dir, con, logger)

    # ── Harmonise: raw → m_ → s_ → h_ ─────────────────────────────────────────
    domain_tables = harm_mod.run(con, logger, run_id)

    # ── Export: h_/s_/m_ → harmonised CSV + Parquet + JSON ────────────────────
    export_mod.export_harmonised_tables(con, domain_tables, logger, out_dir=out_dir)

    con.close()

    elapsed = time.time() - t0
    print(f"\n{'═' * 60}")
    print(f"Run {run_id} complete in {elapsed:.1f}s")
    logger.close()


if __name__ == "__main__":
    main()
