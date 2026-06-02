"""Parser script for table 2.4.1: tender results."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pipeline.parsers import core


def parse(
    *,
    raw: pd.DataFrame,
    path: Path,
    table_id: str,
) -> tuple[pd.DataFrame | None, str | None]:
    records: list[dict] = []
    instrument = None

    for row_idx in range(raw.shape[0]):
        row = raw.iloc[row_idx]
        first = row.iloc[0] if raw.shape[1] > 0 else None
        stock = row.iloc[2] if raw.shape[1] > 2 else None

        if pd.notna(first) and pd.isna(stock):
            text = core._clean_text(str(first))
            if text and not core._is_number_like(text) and "stock code" not in text.lower():
                instrument = text
            continue

        issue_date = pd.to_datetime(row.iloc[3] if raw.shape[1] > 3 else None, errors="coerce")
        if pd.isna(stock) or pd.isna(issue_date):
            continue

        records.append({
            "date": issue_date,
            "frequency": "Tender",
            "instrument": instrument,
            "period_days": first if core._is_number_like(first) else None,
            "period_label": None if core._is_number_like(first) else first,
            "stock_code": stock,
            "issue_date": issue_date,
            "maturity_date": pd.to_datetime(row.iloc[4] if raw.shape[1] > 4 else None, errors="coerce"),
            "amount_alloted_rm_million": row.iloc[5] if raw.shape[1] > 5 else None,
            "amount_applied_rm_million": row.iloc[6] if raw.shape[1] > 6 else None,
            "weighted_average_yield_percent": row.iloc[7] if raw.shape[1] > 7 else None,
            "lowest_bid_percent": row.iloc[8] if raw.shape[1] > 8 else None,
            "highest_bid_percent": row.iloc[9] if raw.shape[1] > 9 else None,
        })

    if not records:
        return None, "2.4.1: no tender rows extracted"
    df = pd.DataFrame(records)
    df = df.dropna(subset=["date"]).reset_index(drop=True)
    return df, None

