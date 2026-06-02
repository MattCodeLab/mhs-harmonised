"""
Core parsing helpers for BNM Monthly Highlights Statistics Excel files.

The public entry point reads the correct worksheet for a table ID, delegates to
that table's parser script under pipeline/table_parsers/tables, then finalises
types and placeholder values for downstream loading/export.

Each parser returns (DataFrame | None, error_str | None).  The DataFrame always
has:
  - date       : datetime64[ns]  (first day of observation period)
  - frequency  : str  per row ("Daily" | "Monthly" | "Quarterly" | "Semi-annual" | "Annual")
  - ... data columns (snake_case identifiers, numeric or str)
"""

import re
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

# ── constants ─────────────────────────────────────────────────────────────────

YEAR_MIN, YEAR_MAX = 1960, 2030

# "Q3 2017" style quarterly strings
_QUARTERLY_STR_RE = re.compile(r"^Q([1-4])\s+(\d{4})$", re.IGNORECASE)

# Table-ID pattern – "1.1", "1.3.1", "4.8.c", etc.  Excluded from column labels.
_TABLE_ID_RE = re.compile(r"^\d+(\.\d+|\.[a-z])+$", re.IGNORECASE)

# Text → identifier helpers
_NONWORD_RE  = re.compile(r"[^\w]+")
_MULTI_US_RE = re.compile(r"_+")

# Separator tokens found in period columns (not actual period values)
_PERIOD_SEP = frozenset({"*", "^", "-", "#", "P", "R", "E", "R/", "P/"})

# Garbage / placeholder values that should become None in numeric columns.
# Matches cells whose *entire* content is: dashes, slashes, backslashes, spaces,
# dots, asterisks, pipes, carets, or well-known NA strings like "n/a", "object".
_GARBAGE_RE = re.compile(
    r"^[\s\-\\/\.\*\|\^~]+$"         # only punctuation / whitespace
    r"|^n\.?a\.?$"                   # n/a, na, n.a.
    r"|^t\.?d\.?$"                   # t.d. / td (legacy placeholder)
    r"|^nil$|^null$|^none$"          # nil / null / none
    r"|^object$"                     # literal "object" (pandas dtype leak)
    r"|^[\s'\-–—…]+$"                # apostrophe, unicode dashes/ellipsis
    r"|^\-+\s*\-+$"                  # "- -", "-- --", etc.
    r"|\\\-"                         # contains "\-" anywhere
    r"|\-\\"                         # contains "-\" anywhere
    r"|/-"                           # contains "/-" anywhere
    r"|\.\.\.",                      # contains "..." anywhere
    re.IGNORECASE,
)

# Period-indicator sets
_SEMI_ANNUAL  = frozenset({"1H", "2H"})
_QUARTERLY    = frozenset({"1Q", "2Q", "3Q", "4Q"})
_PERIOD_KNOWN = _SEMI_ANNUAL | _QUARTERLY

# (period_str → (month, frequency_label))
_PERIOD_MAP = {
    "1H": (1,  "Semi-annual"),
    "2H": (7,  "Semi-annual"),
    "1Q": (1,  "Quarterly"),
    "2Q": (4,  "Quarterly"),
    "3Q": (7,  "Quarterly"),
    "4Q": (10, "Quarterly"),
}


# ── public entry point ────────────────────────────────────────────────────────

def parse_bnm_excel(filepath: str, table_id: str):
    """Parse one BNM MHS Excel file.

    Returns (df, None) on success or (None, error_message) on failure.
    df always has columns:  date | frequency | <data cols …>
    """
    path = Path(filepath)
    if not path.exists():
        return None, f"File not found: {filepath}"

    try:
        raw = _read_workbook_table(path, table_id)
    except Exception as exc:
        return None, f"Read error: {exc}"

    # Strip fully-empty rows and columns
    raw = raw.dropna(how="all", axis=1).reset_index(drop=True)
    raw = raw.dropna(how="all", axis=0).reset_index(drop=True)

    if raw.empty or raw.shape[1] == 0:
        return None, "Empty workbook after dropping fully blank rows/columns"

    from pipeline.parsers.registry import parse_with_table_script

    return _finalize_result(parse_with_table_script(raw, path, table_id))


# ── pattern detectors ─────────────────────────────────────────────────────────

def _read_workbook_table(path: Path, table_id: str) -> pd.DataFrame:
    """Read the worksheet that actually contains the table.

    Several BNM workbooks include an empty technical first sheet (for example
    XMLW/Xt_R) and put the visible table on a sheet named after the table ID.
    """
    engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    excel = pd.ExcelFile(path, engine=engine)

    if table_id in excel.sheet_names:
        return pd.read_excel(excel, sheet_name=table_id, header=None)

    best = None
    best_score = -1
    for sheet_name in excel.sheet_names:
        candidate = pd.read_excel(excel, sheet_name=sheet_name, header=None)
        cleaned = candidate.dropna(how="all", axis=1).dropna(how="all", axis=0)
        score = int(cleaned.shape[0] * cleaned.shape[1])
        if score > best_score:
            best = candidate
            best_score = score

    if best is None:
        return pd.DataFrame()
    return best

def _is_daily(raw: pd.DataFrame) -> bool:
    """Daily files have a 'D2' (or 'D') sentinel in col 0 within the first 30 rows."""
    for i in range(min(30, len(raw))):
        v = str(raw.iloc[i, 0]).strip() if pd.notna(raw.iloc[i, 0]) else ""
        if v in ("D2", "D"):
            return True
    return False


def _is_wide(raw: pd.DataFrame) -> bool:
    """Wide tables have ≥5 calendar-year integers scattered across one header row."""
    for i in range(min(15, len(raw))):
        row = raw.iloc[i]
        n = sum(
            1 for v in row
            if pd.notna(v)
            and isinstance(v, (int, float))
            and YEAR_MIN <= int(v) <= YEAR_MAX
        )
        if n >= 5:
            return True
    return False


def _find_data_start(raw: pd.DataFrame):
    """Return (year_col_index, first_data_row_index) or (0, None)."""
    for col_idx in (0, 1):
        if col_idx >= raw.shape[1]:
            continue
        for row_idx in range(raw.shape[0]):
            val = raw.iloc[row_idx, col_idx]
            if _is_year(val) or (
                pd.notna(val) and _QUARTERLY_STR_RE.match(str(val).strip())
            ):
                return col_idx, row_idx
    return 0, None


def _find_data_end(raw: pd.DataFrame, data_start: int) -> int:
    """Return exclusive end row (stops before footnotes / long trailing blanks).

    Uses *numeric* data in cols 2+ as the signal (so bilingual footnote text
    that spans many columns doesn't extend the range).
    """
    last_data       = data_start
    consecutive_gap = 0

    for i in range(data_start, raw.shape[0]):
        row = raw.iloc[i]

        # Stop on any known footnote/source sentinel in any cell
        for v in row:
            if pd.notna(v):
                t = str(v).strip().lower()
                if any(t.startswith(k) for k in ("nota", "note", "sumber", "source", "p -", "* p")):
                    return last_data + 1

        # Stop if col-0 is a small integer (1-9) — numbered footnote row
        v0 = row.iloc[0]
        if pd.notna(v0):
            try:
                n = int(float(v0))
                if 1 <= n <= 9:
                    return last_data + 1
            except (TypeError, ValueError):
                pass

        # "Has data" = at least one numeric value in the data columns (col 2+)
        data_slice   = row.iloc[min(2, raw.shape[1] - 1):]
        has_numeric  = pd.to_numeric(data_slice, errors="coerce").notna().any()

        if has_numeric:
            last_data       = i
            consecutive_gap = 0
        else:
            consecutive_gap += 1
            if consecutive_gap >= 4 and i > data_start + 4:
                break

    return last_data + 1


def _is_quarterly_strings(raw, year_col, data_start, data_end) -> bool:
    for i in range(data_start, min(data_start + 5, data_end)):
        val = raw.iloc[i, year_col]
        if pd.notna(val) and _QUARTERLY_STR_RE.match(str(val).strip()):
            return True
    return False


# ── header extraction ─────────────────────────────────────────────────────────

def _extract_headers(raw: pd.DataFrame, data_start: int) -> list[str]:
    """Build clean snake_case column names from the header rows above data_start."""
    n_cols = raw.shape[1]
    if data_start == 0:
        return [f"col_{i}" for i in range(n_cols)]

    header_orig = raw.iloc[:data_start]

    # For each column find the first row that has a meaningful original value.
    # Columns with an early anchor should not inherit ffill from later rows.
    first_own_row: dict[int, int] = {}
    for col_idx in range(n_cols):
        for row_idx in range(data_start):
            val = header_orig.iloc[row_idx, col_idx]
            if pd.notna(val):
                s = str(val).strip()
                if not _TABLE_ID_RE.match(s) and _clean_text(s):
                    first_own_row[col_idx] = row_idx
                    break

    # Forward-fill each header row left-to-right so merged-cell spans propagate,
    # but block propagation into columns whose own header appears in an earlier row
    # (those columns are "anchored" at that level and don't belong to the sub-group
    # currently being propagated).
    ffilled: list[list] = []
    for row_idx in range(data_start):
        row = list(header_orig.iloc[row_idx])
        last_val = None
        for col_idx in range(n_cols):
            if pd.notna(row[col_idx]):
                last_val = row[col_idx]
            elif last_val is not None:
                col_anchor = first_own_row.get(col_idx)
                if col_anchor is None or col_anchor > row_idx:
                    row[col_idx] = last_val
        ffilled.append(row)
    header_block = pd.DataFrame(ffilled, columns=header_orig.columns)

    # Build a text path per column from top header row down to the row above data.
    # Skip table-ID tokens; skip consecutive duplicate labels within a path.
    paths: list[list[str]] = []
    for col_idx in range(n_cols):
        path: list[str] = []
        prev = None
        for row_idx in range(data_start):
            val = header_block.iloc[row_idx, col_idx]
            if pd.notna(val):
                raw_str = str(val).strip()
                if _TABLE_ID_RE.match(raw_str):
                    continue
                text = _clean_text(raw_str)
                if text and text != prev:
                    path.append(text)
                    prev = text
        paths.append(path)

    # Count how many times each leaf label appears.
    from collections import Counter
    leaf_freq: Counter = Counter(
        _col_name(p[-1]) for p in paths if p
    )

    # Assign names: resolve duplicates by climbing the path until a unique name is found.
    # Generic leaves (total, subtotal, others, lain_lain, etc.) always start from the
    # full path so they always carry parent context (e.g. indirect_tax_total, not just total).
    names: list[str] = []
    used:  set[str] = set()

    for i, path in enumerate(paths):
        if not path:
            name = _unique_name(f"col_{i}", used)
        else:
            leaf = _col_name(path[-1])

            if leaf in _GENERIC_LABELS and len(path) >= 2:
                # Always use full path for generic labels so parent context is always present
                min_depth = len(path)
            elif leaf_freq[leaf] > 1 and len(path) >= 2:
                # Non-generic duplicates: start from parent+leaf
                min_depth = 2
            else:
                min_depth = 1

            name = None
            for depth in range(min_depth, len(path) + 1):
                candidate = _col_name("_".join(path[-depth:]))
                if candidate not in used:
                    name = candidate
                    break

            if name is None:
                name = _unique_name(_col_name("_".join(path)), used)

        used.add(name)
        names.append(name)

    return names


def _unique_name(base: str, used: set) -> str:
    if base not in used:
        return base
    n = 1
    while f"{base}_{n}" in used:
        n += 1
    return f"{base}_{n}"


_GENERIC_LABELS = frozenset({
    "total", "jumlah", "amount", "value", "number", "others", "other",
    "lain", "lain_lain", "subtotal", "percentage", "peratus", "ratio", "nisbah",
})


# ── standard parser (Annual / Monthly / Semi-annual / Quarterly / Mixed) ──────

def _parse_standard(raw, year_col, data_start, data_end):
    headers = _extend_headers(_extract_headers(raw, data_start), raw.shape[1])

    df = raw.iloc[data_start:data_end].copy().reset_index(drop=True)
    df.columns = headers

    year_col_name = headers[year_col]
    df[year_col_name] = df[year_col_name].ffill()

    # Detect period column
    period_col_name = None
    period_col_idx  = year_col + 1
    if period_col_idx < len(headers):
        period_vals = df.iloc[:, period_col_idx].dropna().unique()
        if _has_period_values(period_vals):
            period_col_name = headers[period_col_idx]
            df[period_col_name] = df[period_col_name].ffill()

    # Build per-row date + frequency
    year_s   = pd.to_numeric(df[year_col_name], errors="coerce")
    period_s = df[period_col_name] if period_col_name else None
    df["date"], df["frequency"] = _build_date_and_freq(year_s, period_s)

    df = df.dropna(subset=["date"]).reset_index(drop=True)

    # Drop year / period helper columns
    drop_set = {year_col_name}
    if period_col_name:
        drop_set.add(period_col_name)
    df = df.drop(columns=list(drop_set), errors="ignore")

    # Coerce data columns to numeric where mostly numeric.
    # First scrub garbage placeholder values (e.g. "- -", "\", "object") so
    # they don't block coercion or contaminate the dtype of the column.
    meta = {"date", "frequency"}
    for c in df.columns:
        if c in meta:
            continue
        df[c] = _scrub_garbage(df[c])
        coerced = pd.to_numeric(_clean_numeric_tokens(df[c]), errors="coerce")
        if coerced.notna().sum() / max(len(df), 1) >= 0.3:
            df[c] = coerced
        else:
            df[c] = df[c].where(df[c].notna(), None)   # keep as str/None

    # Drop rows that are all-NaN in data columns
    data_cols = [c for c in df.columns if c not in meta]
    if data_cols:
        df = df.dropna(subset=data_cols, how="all").reset_index(drop=True)

    other = [c for c in df.columns if c not in meta]
    return df[["date", "frequency"] + other], None


# ── quarterly-string parser ("Q3 2017") ───────────────────────────────────────

def _parse_quarterly_strings(raw, year_col, data_start, data_end):
    headers = _extend_headers(_extract_headers(raw, data_start), raw.shape[1])

    df = raw.iloc[data_start:data_end].copy().reset_index(drop=True)
    df.columns = headers
    period_col = headers[year_col]

    dates = []
    for val in df[period_col]:
        m = _QUARTERLY_STR_RE.match(str(val).strip()) if pd.notna(val) else None
        if m:
            q, yr = int(m.group(1)), int(m.group(2))
            dates.append(pd.Timestamp(yr, (q - 1) * 3 + 1, 1))
        else:
            dates.append(pd.NaT)

    df["date"]      = pd.Series(dates, dtype="datetime64[ns]")
    df["frequency"] = "Quarterly"
    df = df.dropna(subset=["date"]).reset_index(drop=True)
    df = df.drop(columns=[period_col], errors="ignore")

    meta = {"date", "frequency"}
    for c in df.columns:
        if c not in meta:
            df[c] = pd.to_numeric(_clean_numeric_tokens(_scrub_garbage(df[c])), errors="coerce")

    data_cols = [c for c in df.columns if c not in meta]
    if data_cols:
        df = df.dropna(subset=data_cols, how="all").reset_index(drop=True)

    other = [c for c in df.columns if c not in meta]
    return df[["date", "frequency"] + other], None


# ── wide parser (years as column headers) ────────────────────────────────────

def _parse_wide(raw: pd.DataFrame):
    """Convert cross-tab (indicators × years) into long form:
       date | frequency | indicator | value
    """
    # Find the header row that holds calendar years
    year_header_row = None
    for i in range(min(15, raw.shape[0])):
        row = raw.iloc[i]
        n   = sum(
            1 for v in row
            if pd.notna(v) and isinstance(v, (int, float))
            and YEAR_MIN <= int(v) <= YEAR_MAX
        )
        if n >= 5:
            year_header_row = i
            break

    if year_header_row is None:
        return None, "Wide: could not find year header row"

    year_cols: dict[int, int] = {
        col_idx: int(val)
        for col_idx, val in enumerate(raw.iloc[year_header_row])
        if pd.notna(val) and isinstance(val, (int, float)) and YEAR_MIN <= int(val) <= YEAR_MAX
    }

    data_start = year_header_row + 1
    data_end   = _find_data_end(raw, data_start)

    records = []
    for row_idx in range(data_start, data_end):
        row = raw.iloc[row_idx]
        # Build indicator label from leftmost text columns (skip year-value cols)
        label_parts = [
            _clean_text(str(row.iloc[c]))
            for c in range(min(6, raw.shape[1]))
            if c not in year_cols and pd.notna(row.iloc[c])
        ]
        label = " > ".join(p for p in label_parts if p) or None
        if not label:
            continue
        for col_idx, yr in year_cols.items():
            # Value may be in year_col itself (4.10 style) or one column right (4.12 style)
            val = row.iloc[col_idx]
            if pd.isna(val) and col_idx + 1 < raw.shape[1]:
                val = row.iloc[col_idx + 1]
            if pd.notna(val):
                try:
                    records.append({
                        "date":      pd.Timestamp(yr, 1, 1),
                        "frequency": "Annual",
                        "indicator": label,
                        "value":     float(val),
                    })
                except (TypeError, ValueError):
                    pass

    if not records:
        return None, "Wide: no records extracted"

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df, None


# ── daily parser (2.6.1 exchange rates) ──────────────────────────────────────

def _parse_daily(raw: pd.DataFrame):
    """Structure: col0='D2', col1='Month Year', col2=day-of-month, col3+=rates."""
    data_start = next(
        (i for i in range(raw.shape[0]) if str(raw.iloc[i, 0]).strip() in ("D2", "D")),
        None,
    )
    if data_start is None:
        return None, "Daily: could not find data start"

    data_end = _find_data_end(raw, data_start)
    headers  = _extend_headers(_extract_headers(raw, data_start), raw.shape[1])

    df = raw.iloc[data_start:data_end].copy().reset_index(drop=True)
    df.columns = headers

    month_year_col = headers[1]
    day_col        = headers[2]

    dates = []
    for i in range(len(df)):
        my  = str(df[month_year_col].iloc[i]).strip() if pd.notna(df[month_year_col].iloc[i]) else ""
        day = df[day_col].iloc[i]
        try:
            dates.append(pd.to_datetime(f"{my} {int(day):02d}", format="%B %Y %d"))
        except Exception:
            dates.append(pd.NaT)

    df["date"]      = pd.Series(dates, dtype="datetime64[ns]")
    df["frequency"] = "Daily"
    df = df.dropna(subset=["date"]).reset_index(drop=True)

    # Drop the three date-component columns + any column that is entirely NaN
    drop_cols = {headers[0], month_year_col, day_col}
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    df = df.dropna(axis=1, how="all")

    meta = {"date", "frequency"}
    for c in df.columns:
        if c not in meta:
            df[c] = pd.to_numeric(_clean_numeric_tokens(_scrub_garbage(df[c])), errors="coerce")

    data_cols = [c for c in df.columns if c not in meta]
    if data_cols:
        df = df.dropna(subset=data_cols, how="all").reset_index(drop=True)

    other = [c for c in df.columns if c not in meta]
    return df[["date", "frequency"] + other], None


# ── core helpers ──────────────────────────────────────────────────────────────

def _finalize_result(result):
    df, err = result
    if err or df is None:
        return df, err
    return _finalize_frame(df), None


def _finalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise dtypes so downstream DuckDB/export code sees stable columns."""
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "frequency" in df.columns:
        df["frequency"] = df["frequency"].where(df["frequency"].notna(), None)
        df["frequency"] = df["frequency"].map(lambda v: None if v is None else str(v).strip())

    meta = {"date", "frequency"}
    for c in df.columns:
        if c in meta:
            continue
        df[c] = _scrub_garbage(df[c])
        numeric_ready = _clean_numeric_tokens(df[c])

        if pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_datetime64_any_dtype(df[c]):
            continue

        non_null = df[c].notna().sum()
        coerced = pd.to_numeric(numeric_ready, errors="coerce")
        numeric = coerced.notna().sum()
        if non_null and numeric / non_null >= 0.85:
            df[c] = coerced
            continue

        df[c] = df[c].map(
            lambda v: None if pd.isna(v) else str(v).strip()
        )
        df[c] = df[c].where(df[c].map(lambda v: bool(v) if v is not None else False), None)

    return df


def _scrub_garbage(series: pd.Series) -> pd.Series:
    """Replace cells whose entire content matches a garbage/placeholder pattern with NaN."""
    def _is_garbage(v) -> bool:
        if pd.isna(v):
            return False
        if isinstance(v, (int, float)):
            return False
        return bool(_GARBAGE_RE.match(str(v).strip()))

    mask = series.apply(_is_garbage)
    if mask.any():
        series = series.copy()
        series[mask] = float("nan")
    return series


def _clean_numeric_tokens(series: pd.Series) -> pd.Series:
    """Remove commas and trailing footnote markers from otherwise numeric cells."""
    def _clean(v):
        if pd.isna(v) or isinstance(v, (int, float)):
            return v
        text = str(v).strip()
        text = text.replace(",", "")
        m = re.match(r"^\(?\s*([-+]?\d+(?:\.\d+)?)\s*\)?(?:\s+\d+)?$", text)
        if m:
            return m.group(1)
        return v

    return series.map(_clean)


def _is_number_like(value) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _extend_headers(headers: list[str], n_cols: int) -> list[str]:
    """Pad or truncate headers list to exactly n_cols entries."""
    return (headers + [f"col_{i}" for i in range(len(headers), n_cols)])[:n_cols]


def _is_year(val) -> bool:
    if pd.isna(val):
        return False
    try:
        return YEAR_MIN <= int(float(val)) <= YEAR_MAX
    except (TypeError, ValueError):
        return False


def _has_period_values(vals) -> bool:
    """Return True if the column looks like a period column (months, halves, quarters)."""
    non_null = [v for v in vals if pd.notna(v)]
    if not non_null:
        return False

    str_vals = [str(v).strip().upper() for v in non_null]

    # Any known period indicator (1H/2H/1Q-4Q) → yes
    if any(v in _PERIOD_KNOWN for v in str_vals):
        return True

    # Monthly: all non-separator values must be integers 1-12
    valid_months = 0
    for v in str_vals:
        if v in _PERIOD_SEP:
            continue
        try:
            n = int(float(v))
            if 1 <= n <= 12:
                valid_months += 1
            else:
                return False   # out-of-range integer → not a month column
        except (TypeError, ValueError):
            return False       # non-numeric, non-separator → not a period column

    return valid_months > 0


def _build_date_and_freq(year_s: pd.Series, period_s) -> tuple:
    """Return (date_series, frequency_series) built per row.

    Handles mixed annual+monthly files: rows with NaN period in an otherwise
    monthly table are treated as Annual observations dated Jan 1.
    """
    dates: list  = []
    freqs: list  = []

    for i in range(len(year_s)):
        yr = year_s.iloc[i]
        if pd.isna(yr):
            dates.append(pd.NaT);  freqs.append(None);  continue
        try:
            yr = int(yr)
        except (TypeError, ValueError):
            dates.append(pd.NaT);  freqs.append(None);  continue

        # Reject out-of-range years (catches footnote numbers 1-9 etc.)
        if not (YEAR_MIN <= yr <= YEAR_MAX):
            dates.append(pd.NaT);  freqs.append(None);  continue

        # No period column at all → Annual
        if period_s is None:
            dates.append(pd.Timestamp(yr, 1, 1))
            freqs.append("Annual")
            continue

        raw_pval = period_s.iloc[i]

        # NaN period → Annual (historical annual observations in mixed files)
        if pd.isna(raw_pval):
            dates.append(pd.Timestamp(yr, 1, 1))
            freqs.append("Annual")
            continue

        pval = str(raw_pval).strip().upper()

        if pval in _PERIOD_SEP:
            # Separator row – skip
            dates.append(pd.NaT);  freqs.append(None);  continue

        if pval in _PERIOD_MAP:
            month, label = _PERIOD_MAP[pval]
            dates.append(pd.Timestamp(yr, month, 1))
            freqs.append(label)
        else:
            # Try numeric month
            try:
                m = int(float(pval))
                if 1 <= m <= 12:
                    dates.append(pd.Timestamp(yr, m, 1))
                    freqs.append("Monthly")
                else:
                    dates.append(pd.NaT);  freqs.append(None)
            except (TypeError, ValueError):
                dates.append(pd.NaT);  freqs.append(None)

    return (
        pd.Series(dates, dtype="datetime64[ns]"),
        pd.Series(freqs, dtype="object"),
    )


def _clean_text(s: str) -> str:
    """Extract readable (preferably English) label from a potentially bilingual cell.

    Priority: last non-empty segment after splitting on newlines; then take
    the part after ' / ' if the bilingual slash pattern is present.
    """
    # Split on newlines, take last non-empty segment
    parts = [p.strip() for p in s.split("\n") if p.strip()]
    text  = parts[-1] if parts else s.strip()

    # Bilingual " / " separator → take the latter part
    if " / " in text:
        text = text.split(" / ")[-1].strip()

    # Strip trailing footnote digits / punctuation, e.g. "M31" → "M3"
    # Exception: RM denomination columns like "RM1", "RM5", "RM50" must keep their number.
    if not re.match(r"^RM\d+$", text, re.IGNORECASE):
        text = re.sub(r"[\d,]+\s*$", "", text).strip()

    return text


def _col_name(s: str) -> str:
    """Convert display text to a valid snake_case identifier."""
    s = _clean_text(s).lower()
    s = _NONWORD_RE.sub("_", s)
    s = _MULTI_US_RE.sub("_", s)
    s = s.strip("_")
    return s or "col"
