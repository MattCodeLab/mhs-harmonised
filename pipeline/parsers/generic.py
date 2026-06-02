"""Reusable generic parser used by table scripts that do not need custom logic."""

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
    if core._is_daily(raw):
        return core._parse_daily(raw)

    if core._is_wide(raw):
        return core._parse_wide(raw)

    year_col, data_start = core._find_data_start(raw)
    if data_start is None:
        return None, "Could not detect data-start row"

    data_end = core._find_data_end(raw, data_start)
    if data_end <= data_start:
        return None, "No data rows found"

    if core._is_quarterly_strings(raw, year_col, data_start, data_end):
        return core._parse_quarterly_strings(raw, year_col, data_start, data_end)

    return core._parse_standard(raw, year_col, data_start, data_end)

