"""Runtime loader for table-specific parser scripts."""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pandas as pd


def parser_module_name(table_id: str) -> str:
    safe = re.sub(r"[^0-9a-zA-Z]+", "_", table_id).strip("_").lower()
    return f"pipeline.parsers.tables.t_{safe}"


def parse_with_table_script(
    raw: pd.DataFrame,
    path: Path,
    table_id: str,
) -> tuple[pd.DataFrame | None, str | None]:
    module_name = parser_module_name(table_id)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise
        module = importlib.import_module("pipeline.parsers.generic")

    parse = getattr(module, "parse", None)
    if parse is None:
        return None, f"{module_name} does not expose parse(raw, path, table_id)"
    return parse(raw=raw, path=path, table_id=table_id)
