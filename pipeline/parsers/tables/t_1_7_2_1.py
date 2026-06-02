"""Parser script for table 1.7.2.1: previous-format asset statement."""

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
    year_col, data_start = core._find_data_start(raw)
    if data_start is None:
        return None, "1.7.2.1: could not detect data-start row"

    data_end = core._find_data_end(raw, data_start)
    df, err = core._parse_standard(raw, year_col, data_start, data_end)
    if err or df is None:
        return df, err

    rename = {}
    for col in df.columns:
        if "payable_in_malaysia_lain_lain_other" in col:
            rename[col] = "trade_bills_payable_in_malaysia_other"
        elif "loans_and_advances_jumlah_total" in col:
            rename[col] = "total_loans_and_advances"
    return df.rename(columns=rename), None

