"""Stage 1 — Ingest: Excel → DuckDB raw tables.

Scans the Excel directory, parses every .xlsx/.xls file using the
table-specific parser (falling back to the generic parser), and loads
each DataFrame into DuckDB.

Returns an IngestResult with per-table summaries for downstream logging.
"""

from __future__ import annotations

import json
import re
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import pandas as pd

from pipeline import db as db_mod
from pipeline.catalog import get_meta
from pipeline.log import RunLogger
from pipeline.parsers.core import parse_bnm_excel


# ── data classes ───────────────────────────────────────────────────────────────

@dataclass
class TableResult:
    table_id: str
    source_file: str
    status: str          # loaded | parse_error | load_error | input_skipped
    stage: str           # discover | parse | load | complete
    row_count: int = 0
    col_count: int = 0
    date_min: str | None = None
    date_max: str | None = None
    frequencies: str = ""
    error: str | None = None
    duration_s: float = 0.0
    exception_type: str | None = None
    tb: str | None = None


@dataclass
class IngestResult:
    ok: list[TableResult] = field(default_factory=list)
    errors: list[TableResult] = field(default_factory=list)
    skipped: list[TableResult] = field(default_factory=list)

    @property
    def all(self) -> list[TableResult]:
        return self.ok + self.errors + self.skipped


# ── public API ─────────────────────────────────────────────────────────────────

def run(
    excel_dir: Path,
    con: duckdb.DuckDBPyConnection,
    logger: RunLogger,
) -> IngestResult:
    """Parse all Excel files and load them into DuckDB raw tables."""
    logger.section("Stage 1 — Ingest")

    files, skipped = _discover(excel_dir, logger)
    result = IngestResult(skipped=skipped)

    for i, (table_id, fp) in enumerate(files, 1):
        prefix = f"[{i:>3}/{len(files)}] {table_id:<18}"
        t0 = time.time()

        # ── parse ──────────────────────────────────────────────────────────────
        try:
            df, err = parse_bnm_excel(str(fp), table_id)
        except Exception as exc:
            _record_error(result, logger, table_id, fp, "parse_error", "parse", exc, t0)
            db_mod.record_error(table_id, str(exc), con)
            print(f"{prefix}  PARSE_ERR  {exc}")
            continue

        if err:
            db_mod.record_error(table_id, err, con)
            r = TableResult(
                table_id=table_id, source_file=str(fp),
                status="parse_error", stage="parse", error=err,
                duration_s=round(time.time() - t0, 3),
            )
            result.errors.append(r)
            logger.event("ingest", "parse_error", table_id=table_id, error=err)
            print(f"{prefix}  SKIP  {err}")
            continue

        # ── load ───────────────────────────────────────────────────────────────
        try:
            summary = db_mod.load_raw_table(df, table_id, con)
        except Exception as exc:
            _record_error(result, logger, table_id, fp, "load_error", "load", exc, t0)
            db_mod.record_error(table_id, str(exc), con)
            print(f"{prefix}  LOAD_ERR   {exc}")
            continue

        freqs = summary["frequencies"].strip("[]").replace('"', "").replace(", ", ",")
        r = TableResult(
            table_id=table_id,
            source_file=str(fp),
            status="loaded",
            stage="complete",
            row_count=summary["row_count"],
            col_count=len(json.loads(summary["columns"])),
            date_min=summary["date_min"],
            date_max=summary["date_max"],
            frequencies=freqs,
            duration_s=round(time.time() - t0, 3),
        )
        result.ok.append(r)
        logger.event(
            "ingest", "loaded",
            table_id=table_id,
            row_count=r.row_count,
            col_count=r.col_count,
            date_min=r.date_min,
            date_max=r.date_max,
        )
        print(f"{prefix}  OK    {r.row_count:>6} rows  {r.date_min or '?'}..{r.date_max or '?'}  [{freqs}]")

    print(
        f"\nIngest complete: {len(result.ok)} loaded, "
        f"{len(result.errors)} errors, {len(result.skipped)} skipped"
    )
    return result


# ── internals ──────────────────────────────────────────────────────────────────

def _discover(
    excel_dir: Path,
    logger: RunLogger,
) -> tuple[list[tuple[str, Path]], list[TableResult]]:
    """Scan directory; return canonical (table_id, path) pairs and skipped entries."""
    candidates: list[tuple[str, Path, bool]] = []
    skipped: list[TableResult] = []

    for fp in sorted(excel_dir.glob("*.xls*")):
        if fp.name.startswith(("~$", ".")):
            skipped.append(TableResult(
                table_id=fp.stem, source_file=str(fp),
                status="input_skipped", stage="discover",
                error="Ignored temporary or hidden workbook",
            ))
            logger.event("ingest", "skipped", file=fp.name, reason="temp/hidden")
            continue

        canonical = re.sub(r"\s+\(\d+\)$", "", fp.stem).strip()
        is_copy = canonical != fp.stem
        candidates.append((canonical, fp, is_copy))

    results: list[tuple[str, Path]] = []
    seen: dict[str, Path] = {}
    for table_id, fp, is_copy in sorted(candidates, key=lambda x: (x[0], x[2], x[1].name)):
        if table_id in seen:
            msg = f"Duplicate skipped; already using {seen[table_id].name}"
            skipped.append(TableResult(
                table_id=table_id, source_file=str(fp),
                status="input_skipped", stage="discover", error=msg,
            ))
            logger.event("ingest", "skipped", file=fp.name, reason=msg)
            continue
        seen[table_id] = fp
        results.append((table_id, fp))

    return results, skipped


def _record_error(
    result: IngestResult,
    logger: RunLogger,
    table_id: str,
    fp: Path,
    status: str,
    stage: str,
    exc: Exception,
    t0: float,
) -> None:
    r = TableResult(
        table_id=table_id, source_file=str(fp),
        status=status, stage=stage, error=str(exc),
        exception_type=type(exc).__name__,
        tb="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        duration_s=round(time.time() - t0, 3),
    )
    result.errors.append(r)
    logger.event("ingest", status, table_id=table_id, error=str(exc))
