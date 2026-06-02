"""Parser script for table 5.1: banking institutions snapshot."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def parse(
    *,
    raw: pd.DataFrame,
    path: Path,
    table_id: str,
) -> tuple[pd.DataFrame | None, str | None]:
    categories = [
        ("commercial_bank", 1, 2),
        ("islamic_bank", 3, 4),
        ("investment_bank", 5, 6),
    ]
    snapshot_date = pd.Timestamp.fromtimestamp(path.stat().st_mtime).normalize()
    records: list[dict] = []

    for row_idx in range(4, raw.shape[0]):
        row = raw.iloc[row_idx]
        for category, rank_col, name_col in categories:
            if name_col >= raw.shape[1]:
                continue
            name = row.iloc[name_col]
            if pd.isna(name) or not str(name).strip():
                continue
            rank = row.iloc[rank_col] if rank_col < raw.shape[1] else None
            records.append({
                "date": snapshot_date,
                "frequency": "Snapshot",
                "category": category,
                "rank": rank,
                "institution_name": str(name).strip(),
            })

    if not records:
        return None, "5.1: no institution rows extracted"
    return pd.DataFrame(records), None

