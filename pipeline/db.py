"""DuckDB connection and catalog management.

The pipeline uses a single DuckDB file for all tables:
  - Raw ingested tables:    named by catalog slug, e.g. `1_3_1_broad_money_m3`
  - Column-mapped tables:   prefix `m_`,  e.g. `m_1_3_1_broad_money_m3`
  - Stitched tables:        prefix `s_`,  e.g. `s_loans_by_purpose`
  - Harmonised domain tables: prefix `h_`, e.g. `h_1_money_supply`

The `_catalog` table tracks every raw table load (success or error).
The `_harmonise_log` table tracks every harmonisation action.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from pipeline.catalog import get_meta


# ── connection ─────────────────────────────────────────────────────────────────

def connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(db_path))


# ── catalog management ─────────────────────────────────────────────────────────

def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create catalog + harmonise_log tables if they don't exist."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS _catalog (
            table_name  VARCHAR PRIMARY KEY,
            table_id    VARCHAR,
            domain      VARCHAR,
            title       VARCHAR,
            row_count   BIGINT,
            date_min    VARCHAR,
            date_max    VARCHAR,
            frequencies VARCHAR,
            columns     VARCHAR,
            error       VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS _harmonise_log (
            run_id      VARCHAR,
            stage       VARCHAR,
            action      VARCHAR,
            source      VARCHAR,
            target      VARCHAR,
            col_name    VARCHAR,
            detail      VARCHAR
        )
    """)


def load_raw_table(
    df: pd.DataFrame,
    table_id: str,
    con: duckdb.DuckDBPyConnection,
) -> dict:
    """Write df to DuckDB as a raw table. Returns summary dict."""
    meta = get_meta(table_id)
    tname = meta["table_name"]

    if "date" in df.columns:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

    con.execute(f'DROP TABLE IF EXISTS "{tname}"')
    con.register("_tmp", df)
    con.execute(f'CREATE TABLE "{tname}" AS SELECT * FROM _tmp')
    con.unregister("_tmp")

    date_min = df["date"].min().isoformat()[:10] if "date" in df.columns and not df["date"].isna().all() else None
    date_max = df["date"].max().isoformat()[:10] if "date" in df.columns and not df["date"].isna().all() else None
    frequencies = sorted(df["frequency"].dropna().unique().tolist()) if "frequency" in df.columns else []
    columns = [c for c in df.columns if c not in ("date", "frequency")]

    summary = {
        "table_name": tname,
        "table_id": table_id,
        "domain": meta["domain"],
        "title": meta["title"],
        "row_count": len(df),
        "date_min": date_min,
        "date_max": date_max,
        "frequencies": json.dumps(frequencies),
        "columns": json.dumps(columns),
        "error": None,
    }
    _upsert_catalog(summary, con)
    return summary


def record_error(table_id: str, error: str, con: duckdb.DuckDBPyConnection) -> None:
    """Record a parse/load failure in the catalog."""
    meta = get_meta(table_id)
    _upsert_catalog({
        "table_name": meta["table_name"],
        "table_id": table_id,
        "domain": meta["domain"],
        "title": meta["title"],
        "row_count": 0,
        "date_min": None,
        "date_max": None,
        "frequencies": "[]",
        "columns": "[]",
        "error": error,
    }, con)


def log_harmonise_action(
    con: duckdb.DuckDBPyConnection,
    *,
    run_id: str,
    stage: str,
    action: str,
    source: str = "",
    target: str = "",
    col_name: str = "",
    detail: str = "",
) -> None:
    con.execute(
        "INSERT INTO _harmonise_log VALUES (?, ?, ?, ?, ?, ?, ?)",
        [run_id, stage, action, source, target, col_name, detail],
    )


# ── helpers ────────────────────────────────────────────────────────────────────

def table_columns(con: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    return [r[1] for r in con.execute(f'PRAGMA table_info("{table}")').fetchall()]


def table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    result = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [table]
    ).fetchone()
    return bool(result and result[0] > 0)


def list_tables(con: duckdb.DuckDBPyConnection, prefix: str = "") -> list[str]:
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name"
    ).fetchall()
    names = [r[0] for r in rows]
    return [n for n in names if n.startswith(prefix)] if prefix else names


def _upsert_catalog(summary: dict, con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        INSERT OR REPLACE INTO _catalog
            (table_name, table_id, domain, title, row_count,
             date_min, date_max, frequencies, columns, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        summary["table_name"], summary["table_id"], summary["domain"],
        summary["title"], summary["row_count"], summary["date_min"],
        summary["date_max"], summary["frequencies"], summary["columns"],
        summary["error"],
    ])
