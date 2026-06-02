"""Export pipeline outputs.

Stage 1 (pre-harmonisation): one CSV + Parquet per raw table
  → outputs/stage1_raw/<table_name>/<table_name>.{csv,parquet}

Stage 2 (post-harmonisation): one file per dataset, organized by datasets.csv structure
  → outputs/stage2_harmonised/<category>/<subcategory>/<dataset>.{csv,parquet,json}

Source tables are individual m_ (column-mapped) or s_ (stitched) tables.
h_ domain tables remain in DuckDB for analysis but are not the primary export source.
"""

from __future__ import annotations

import json
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from pipeline import db as db_mod
from pipeline.log import RunLogger


OUTPUTS_DIR = Path(__file__).resolve().parents[1] / "outputs"

DatasetConfig = namedtuple(
    "DatasetConfig",
    ["category", "subcategory", "dataset", "source", "where"],
    defaults=[None],
)

# One entry per row in datasets.csv where we have a matching source table.
# Rows without a known source (Data Dictionaries, Platform, Kijang Emas, institution
# counts, etc.) are omitted — the pipeline will log them as "no source mapping".
DATASET_CONFIGS: list[DatasetConfig] = [
    # ── Monetary System / Money Supply ─────────────────────────────────────────
    DatasetConfig("monetary_system", "money_supply",
                  "monthly_monetary_aggregates_m1_m2_m3",
                  "m_1_3_monetary_aggregates"),
    DatasetConfig("monetary_system", "money_supply",
                  "monthly_broad_money_m3",
                  "m_1_3_1_broad_money_m3"),
    DatasetConfig("monetary_system", "money_supply",
                  "monthly_factors_affecting_m3",
                  "m_1_3_2_factors_affecting_m3"),
    # ── Monetary System / Currency in Circulation ──────────────────────────────
    DatasetConfig("monetary_system", "currency_in_circulation",
                  "monthly_currency_in_circulation_by_denomination",
                  "m_1_2_currency_circulation_by_denom", "frequency = 'Monthly'"),
    DatasetConfig("monetary_system", "currency_in_circulation",
                  "annual_currency_in_circulation_by_denomination",
                  "m_1_2_currency_circulation_by_denom", "frequency = 'Annual'"),
    # ── Monetary System / BNM Balance Sheet ────────────────────────────────────
    DatasetConfig("monetary_system", "bnm_balance_sheet",
                  "bnm_statement_of_assets_capital_and_liabilities",
                  "s_bnm_capital_liabilities"),
    # ── Monetary System / Liquidity & Reserves ─────────────────────────────────
    DatasetConfig("monetary_system", "liquidity_and_reserves",
                  "reserve_money",
                  "m_1_1_reserve_money"),
    DatasetConfig("monetary_system", "liquidity_and_reserves",
                  "statutory_reserve_requirement_and_liquidity_ratio",
                  "m_1_26_statutory_reserve_liquidity"),
    DatasetConfig("monetary_system", "liquidity_and_reserves",
                  "statutory_reserve_and_liquid_asset_requirement",
                  "m_1_27_statutory_reserve_liquid_asset"),
    DatasetConfig("monetary_system", "liquidity_and_reserves",
                  "new_liquidity_framework",
                  "m_1_28_new_liquidity_framework"),
    DatasetConfig("monetary_system", "liquidity_and_reserves",
                  "liquidity_coverage_ratio",
                  "m_1_28a_liquidity_coverage_ratio"),
    # ── Banking System / Balance Sheets ────────────────────────────────────────
    DatasetConfig("banking_system", "balance_sheets",
                  "assets_capital_and_liabilities_banking_system",
                  "s_banking_capital_liabilities"),
    DatasetConfig("banking_system", "balance_sheets",
                  "assets_capital_and_liabilities_islamic_banking_system",
                  "m_1_7_1_islamic_banking_assets"),
    # ── Banking System / Credit & Financing ────────────────────────────────────
    DatasetConfig("banking_system", "credit_and_financing",
                  "credit_to_the_private_sector",
                  "m_2_18_credit_to_private_sector"),
    DatasetConfig("banking_system", "credit_and_financing",
                  "msme_loan_and_financing_by_msme_size",
                  "m_1_35_sme_loans_by_size"),
    DatasetConfig("banking_system", "credit_and_financing",
                  "msme_loan_and_financing_by_sector",
                  "m_1_33_sme_loans_by_sector"),
    DatasetConfig("banking_system", "credit_and_financing",
                  "msme_loan_and_financing_by_purpose",
                  "m_1_34_sme_loans_by_purpose"),
    DatasetConfig("banking_system", "credit_and_financing",
                  "msme_loan_and_financing_by_loan_size",
                  "m_1_36_sme_loans_by_loan_size"),
    # ── Banking System / Deposits & Funding ────────────────────────────────────
    DatasetConfig("banking_system", "deposits_and_funding",
                  "banking_deposits_by_type",
                  "m_1_24_total_deposits_by_type"),
    DatasetConfig("banking_system", "deposits_and_funding",
                  "banking_deposits_by_holder",
                  "m_1_25_total_deposits_by_holder"),
    DatasetConfig("banking_system", "deposits_and_funding",
                  "islamic_banking_deposits_by_type",
                  "m_1_24_1_islamic_deposits_by_type"),
    DatasetConfig("banking_system", "deposits_and_funding",
                  "islamic_banking_deposits_by_holder",
                  "m_1_24_2_islamic_deposits_by_type_holder"),
    # ── Banking System / Payments ───────────────────────────────────────────────
    DatasetConfig("banking_system", "payments",
                  "credit_card_operations",
                  "m_1_30_credit_card_operations"),
    DatasetConfig("banking_system", "payments",
                  "debit_card_transactions",
                  "m_1_30_1_debit_card_transactions"),
    DatasetConfig("banking_system", "payments",
                  "payment_instruments_cheques",
                  "s_cheques_statistics"),
    # ── Banking System / Asset Quality & Provisions ────────────────────────────
    DatasetConfig("banking_system", "asset_quality_and_provisions",
                  "impaired_banking_loan_and_financing_by_purpose",
                  "s_impaired_loans_by_purpose"),
    DatasetConfig("banking_system", "asset_quality_and_provisions",
                  "impaired_banking_loan_and_financing_by_sector",
                  "s_npl_by_sector"),
    DatasetConfig("banking_system", "asset_quality_and_provisions",
                  "impaired_banking_loan_and_financing_by_type",
                  "m_1_23_6_impaired_loans_by_type"),
    DatasetConfig("banking_system", "asset_quality_and_provisions",
                  "impaired_sme_loan_financing_by_sector",
                  "m_1_33_5_sme_impaired_loans_by_sector"),
    DatasetConfig("banking_system", "asset_quality_and_provisions",
                  "impaired_sme_loan_financing_by_sme_size",
                  "m_1_35_3_sme_impaired_loans_by_size"),
    DatasetConfig("banking_system", "asset_quality_and_provisions",
                  "mfrs9_financing",
                  "m_1_21_loans_mfrs9_stages_provisions"),
    DatasetConfig("banking_system", "asset_quality_and_provisions",
                  "mfrs9_financing_islamic",
                  "s_islamic_financing_mfrs9_stages"),
    # ── Financial Markets / Interest Rates ─────────────────────────────────────
    DatasetConfig("financial_markets", "interest_rates",
                  "monthly_interest_rates",
                  "s_interest_rates_banking", "frequency = 'Monthly'"),
    DatasetConfig("financial_markets", "interest_rates",
                  "annual_interest_rates",
                  "s_interest_rates_banking", "frequency = 'Annual'"),
    # ── Financial Markets / Exchange Rates ─────────────────────────────────────
    DatasetConfig("financial_markets", "exchange_rates",
                  "daily_exchange_rates",
                  "m_2_6_1_exchange_rates_myr_daily"),
    DatasetConfig("financial_markets", "exchange_rates",
                  "monthly_exchange_rates",
                  "m_2_6_exchange_rates_myr", "frequency = 'Monthly'"),
    # ── Financial Markets / Money Market Activity ───────────────────────────────
    DatasetConfig("financial_markets", "money_market_activity",
                  "interbank_money_market_transaction_volume",
                  "m_2_7_interbank_money_market_volume"),
    DatasetConfig("financial_markets", "money_market_activity",
                  "kl_foreign_exchange_market_interbank_transactions_volume",
                  "m_2_8_kl_fx_market_volume"),
    DatasetConfig("financial_markets", "money_market_activity",
                  "conventional_and_islamic_money_market_turnover",
                  "m_2_14_money_market_turnover"),
    DatasetConfig("financial_markets", "money_market_activity",
                  "foreign_currency_market_transactions_turnover",
                  "m_2_17_fx_market_turnover"),
    # ── Financial Markets / Bond & Sukuk ────────────────────────────────────────
    DatasetConfig("financial_markets", "bond_and_sukuk",
                  "corporate_bond_and_sukuk_issues",
                  "m_2_11_corporate_bond_sukuk_new_issues"),
    DatasetConfig("financial_markets", "bond_and_sukuk",
                  "debt_securities_and_sukuk_turnover",
                  "m_2_16_debt_securities_sukuk_turnover"),
    DatasetConfig("financial_markets", "bond_and_sukuk",
                  "foreign_holdings_in_debt_securities_and_sukuk",
                  "m_3_2_rentas_foreign_holdings"),
    # ── Financial Markets / Derivatives ─────────────────────────────────────────
    DatasetConfig("financial_markets", "derivatives",
                  "derivatives_transactions_turnover",
                  "m_2_15_derivatives_turnover"),
    # ── Financial Markets / Capital Raising ─────────────────────────────────────
    DatasetConfig("financial_markets", "capital_raising",
                  "public_sector_capital_raise",
                  "m_2_9_capital_market_public_sector"),
    DatasetConfig("financial_markets", "capital_raising",
                  "private_sector_capital_raise",
                  "m_2_10_capital_market_private_sector"),
    # ── Insurance & Takaful / Balance Sheets ────────────────────────────────────
    DatasetConfig("insurance_and_takaful", "balance_sheets",
                  "insurance_assets_and_liabilities",
                  "m_4_2_insurance_assets_liabilities"),
    DatasetConfig("insurance_and_takaful", "balance_sheets",
                  "takaful_assets_and_liabilities",
                  "m_4_3_takaful_assets_liabilities"),
    DatasetConfig("insurance_and_takaful", "balance_sheets",
                  "insurance_capital_adequacy_ratio",
                  "m_4_4_insurance_capital_adequacy"),
    DatasetConfig("insurance_and_takaful", "balance_sheets",
                  "takaful_capital_adequacy_ratio",
                  "m_4_5_takaful_capital_adequacy"),
    # ── Insurance & Takaful / Life & Family ─────────────────────────────────────
    DatasetConfig("insurance_and_takaful", "life_and_family",
                  "life_insurance_funds",
                  "m_4_6_b_life_insurance_fund_assets"),
    DatasetConfig("insurance_and_takaful", "life_and_family",
                  "family_takaful_funds",
                  "m_4_8_family_takaful_new_business"),
    # ── Insurance & Takaful / General Insurance & Takaful ───────────────────────
    DatasetConfig("insurance_and_takaful", "general_insurance_and_takaful",
                  "general_insurance_funds",
                  "m_4_7_b_general_insurance_fund_assets"),
    DatasetConfig("insurance_and_takaful", "general_insurance_and_takaful",
                  "general_insurance_reserves",
                  "m_4_7_c_general_insurance_technical_reserves"),
    DatasetConfig("insurance_and_takaful", "general_insurance_and_takaful",
                  "general_insurance_premium",
                  "m_4_7_general_insurance_premium"),
    # ── Institutions & Access / Employment ──────────────────────────────────────
    DatasetConfig("institutions_and_access", "employment",
                  "employment_hiring_and_separation_financial_sector",
                  "m_3_5_12a_labour_market_financial_sector"),
]


# ── Stage 1 ────────────────────────────────────────────────────────────────────

def export_raw_tables(
    con: duckdb.DuckDBPyConnection,
    logger: RunLogger,
) -> None:
    """Write one CSV + Parquet for each successfully loaded raw table."""
    logger.section("Export Stage 1 — raw tables")

    raw_tables = con.execute(
        "SELECT table_name FROM _catalog WHERE error IS NULL ORDER BY table_name"
    ).fetchall()

    out_root = OUTPUTS_DIR / "stage1_raw"
    ok = errors = 0

    for (table_name,) in raw_tables:
        if not db_mod.table_exists(con, table_name):
            continue
        try:
            df = con.execute(f'SELECT * FROM "{table_name}" ORDER BY date').fetchdf()
            out_dir = out_root / table_name
            out_dir.mkdir(parents=True, exist_ok=True)
            df.to_csv(out_dir / f"{table_name}.csv", index=False)
            df.to_parquet(out_dir / f"{table_name}.parquet", index=False)
            ok += 1
        except Exception as exc:
            logger.event("export_raw", "error", table=table_name, error=str(exc))
            errors += 1

    logger.event("export_raw", "complete", exported=ok, errors=errors)


# ── Stage 2 ────────────────────────────────────────────────────────────────────

def export_harmonised_tables(
    con: duckdb.DuckDBPyConnection,
    domain_tables: list[str],  # unused — kept for API compat with run.py
    logger: RunLogger,
) -> None:
    """Write CSV + Parquet + JSON for each configured dataset."""
    logger.section("Export Stage 2 — dataset outputs")

    out_root = OUTPUTS_DIR / "stage2_harmonised"
    ok = skipped = errors = 0

    for cfg in DATASET_CONFIGS:
        if not db_mod.table_exists(con, cfg.source):
            logger.event("export_harmonised", "skipped",
                         dataset=cfg.dataset,
                         reason=f"source table {cfg.source!r} not in db")
            skipped += 1
            continue

        out_dir = out_root / cfg.category / cfg.subcategory
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = out_dir / cfg.dataset

        try:
            has_date = "date" in db_mod.table_columns(con, cfg.source)
            sql = f'SELECT * FROM "{cfg.source}"'
            if cfg.where:
                sql += f" WHERE {cfg.where}"
            if has_date:
                sql += ' ORDER BY "date"'

            df = con.execute(sql).fetchdf()

            if df.empty:
                logger.event("export_harmonised", "skipped",
                             dataset=cfg.dataset,
                             reason="0 rows after filter")
                skipped += 1
                continue

            df.to_csv(f"{stem}.csv", index=False)
            df.to_parquet(f"{stem}.parquet", index=False)
            _write_json(df, cfg, stem)

            ok += 1
            logger.event("export_harmonised", "exported",
                         dataset=cfg.dataset,
                         source=cfg.source,
                         rows=len(df),
                         cols=len(df.columns),
                         path=str(out_dir))

        except Exception as exc:
            logger.event("export_harmonised", "error",
                         dataset=cfg.dataset, source=cfg.source, error=str(exc))
            errors += 1

    logger.event("export_harmonised", "complete",
                 exported=ok, skipped=skipped, errors=errors)


# ── helpers ────────────────────────────────────────────────────────────────────

def _write_json(df: pd.DataFrame, cfg: DatasetConfig, stem: Path) -> None:
    date_col = "date" if "date" in df.columns else None
    date_min = df[date_col].min().isoformat()[:10] if date_col and df[date_col].notna().any() else None
    date_max = df[date_col].max().isoformat()[:10] if date_col and df[date_col].notna().any() else None

    df_out = df.copy()
    for col in df_out.columns:
        if df_out[col].dtype.kind == "M":
            df_out[col] = df_out[col].dt.strftime("%Y-%m-%d")
    df_out = df_out.astype(object).where(df_out.notnull(), None)

    payload = {
        "metadata": {
            "category": cfg.category,
            "subcategory": cfg.subcategory,
            "dataset": cfg.dataset,
            "source_table": cfg.source,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_rows": len(df_out),
            "date_min": date_min,
            "date_max": date_max,
            "columns": list(df_out.columns),
            "source": "Bank Negara Malaysia Monthly Highlights Statistics",
            "url": "https://www.bnm.gov.my/publications/mhs",
        },
        "data": df_out.to_dict(orient="records"),
    }

    with open(f"{stem}.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, default=_json_default, indent=2, ensure_ascii=False)


def _json_default(obj):
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()[:10]
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)
