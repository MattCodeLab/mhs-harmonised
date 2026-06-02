"""Parser script for table 1.26: SRR and liquidity-ratio change history."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from pipeline.parsers import core


def parse(
    *,
    raw: pd.DataFrame,
    path: Path,
    table_id: str,
) -> tuple[pd.DataFrame | None, str | None]:
    institutions = [
        ("commercial_banks", 2, 3),
        ("finance_companies", 4, 5),
        ("merchant_banks", 6, 7),
    ]
    records: list[dict] = []
    current_year = None

    for row_idx in range(8, raw.shape[0]):
        row = raw.iloc[row_idx]
        first = row.iloc[0] if raw.shape[1] > 0 else None
        if pd.notna(first):
            text = str(first).strip().lower()
            if text.startswith(("nota", "note", "sumber", "source")):
                break
            if core._is_year(first):
                current_year = int(float(first))

        if current_year is None:
            continue

        date_change = row.iloc[1] if raw.shape[1] > 1 and pd.notna(row.iloc[1]) else None
        values: dict = {}
        has_value = False
        parenthetical = False
        for prefix, srr_col, liq_col in institutions:
            srr, srr_alt, srr_paren = _parse_numeric_pair(row.iloc[srr_col] if srr_col < raw.shape[1] else None)
            liq, liq_alt, liq_paren = _parse_numeric_pair(row.iloc[liq_col] if liq_col < raw.shape[1] else None)
            if date_change is None:
                srr, srr_alt, srr_neg = _abs_parenthetical_values(srr, srr_alt)
                liq, liq_alt, liq_neg = _abs_parenthetical_values(liq, liq_alt)
                parenthetical = parenthetical or srr_neg or liq_neg
            values[f"{prefix}_srr"] = srr
            values[f"{prefix}_srr_alt"] = srr_alt
            values[f"{prefix}_liquidity_ratio"] = liq
            values[f"{prefix}_liquidity_ratio_alt"] = liq_alt
            has_value = has_value or any(v is not None for v in (srr, srr_alt, liq, liq_alt))
            parenthetical = parenthetical or srr_paren or liq_paren

        if not has_value:
            continue

        records.append({
            "date": pd.Timestamp(current_year, 1, 1),
            "frequency": "Event",
            "year": current_year,
            "date_change": None if date_change is None else str(date_change).strip(),
            "parenthetical_row": parenthetical,
            **values,
        })

    if not records:
        return None, "1.26: no SRR/liquidity-ratio rows extracted"
    return pd.DataFrame(records), None


def _parse_numeric_pair(value) -> tuple[float | None, float | None, bool]:
    if pd.isna(value):
        return None, None, False
    if isinstance(value, (int, float)):
        return float(value), None, False

    text = str(value).strip()
    if core._GARBAGE_RE.match(text):
        return None, None, False

    parenthetical = text.startswith("(") and ")" in text
    numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", text.replace(",", ""))
    if not numbers:
        return None, None, parenthetical

    primary = float(numbers[0])
    secondary = None
    if re.search(r"\b(dan|and)\b", text, re.IGNORECASE) and len(numbers) > 1:
        secondary = float(numbers[1])
    return primary, secondary, parenthetical


def _abs_parenthetical_values(primary, secondary) -> tuple:
    changed = False
    if primary is not None and primary < 0:
        primary = abs(primary)
        changed = True
    if secondary is not None and secondary < 0:
        secondary = abs(secondary)
        changed = True
    return primary, secondary, changed

