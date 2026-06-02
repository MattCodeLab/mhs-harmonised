"""Parser script for table 1.6: SME fund register."""

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
    date_row = 7 if raw.shape[0] > 7 else None
    if date_row is None:
        return None, "1.6: missing as-at date header row"

    measures = [
        ("amount_approved", 4),
        ("no_of_applications_approved", 6),
        ("amount_drawdown", 8),
        ("amount_repaid", 10),
        ("amount_outstanding", 12),
    ]
    records: list[dict] = []
    current_group = None

    for row_idx in range(10, raw.shape[0]):
        row = raw.iloc[row_idx]
        label = core._clean_text(str(row.iloc[0])) if pd.notna(row.iloc[0]) else ""
        if not label:
            continue

        date_established = row.iloc[2] if raw.shape[1] > 2 else None
        has_measure = any(
            pos < raw.shape[1] and pd.notna(row.iloc[pos])
            for _name, start in measures
            for pos in (start, start + 1)
        )
        if not has_measure:
            current_group = label
            continue

        for measure, start in measures:
            for offset in (0, 1):
                col_idx = start + offset
                if col_idx >= raw.shape[1]:
                    continue
                as_at = raw.iloc[date_row, col_idx]
                if pd.isna(as_at):
                    continue
                records.append({
                    "date": pd.to_datetime(as_at, errors="coerce"),
                    "frequency": "Quarterly",
                    "fund_group": current_group,
                    "fund_name": label,
                    "date_established": pd.to_datetime(date_established, errors="coerce"),
                    "fund_allocation": row.iloc[3] if raw.shape[1] > 3 else None,
                    "measure": measure,
                    "value": row.iloc[col_idx],
                })

    if not records:
        return None, "1.6: no fund records extracted"
    df = pd.DataFrame(records)
    df = df.dropna(subset=["date"]).reset_index(drop=True)
    return df, None

