"""Stage 2 — Harmonise: raw tables → domain outputs.

Three sub-steps, all operating on DuckDB tables:

  (a) Map     raw table  →  m_<table>  (apply column renames from column_map.py)
  (b) Stitch  m_ tables  →  s_<name>   (union prev/current timeseries, dedup by date)
  (c) Domain  s_/m_ tables → h_<name>  (full-outer-join related tables into one domain dataset)

After domain tables are created, duplicate suffix columns (_1, _2 …) are
identified and either merged (if they're truly the same data) or kept (if they
carry unique values), with a full audit trail logged to _harmonise_log.

All decisions are logged so you can see exactly what happened.
"""

from __future__ import annotations

import re
from typing import NamedTuple

import duckdb
import pandas as pd

from pipeline import db as db_mod
from pipeline.column_map import output_mapping_for
from pipeline.log import RunLogger


# ── stitch config ──────────────────────────────────────────────────────────────
# Each entry: (output_name, [member_raw_table_ids], key_col_or_None)
# The member tables are union-stitched oldest→newest, deduped by (date, freq, key).
# key_col is the categorical dimension column (e.g. "sector", "purpose", "bank").

STITCH_RULES: list[tuple[str, list[str], str | None]] = [
    # BNM balance sheet
    ("s_bnm_capital_liabilities", ["1_5_bnm_capital_liabilities", "1_5_1_bnm_capital_liabilities_prev"], None),
    # Banking assets/liabilities
    ("s_banking_assets",            ["1_7_banking_assets",           "1_7a_banking_assets_prev"],              None),
    ("s_banking_capital_liabilities", ["1_9_banking_capital_liabilities", "1_9a_banking_capital_liabilities_prev"], None),
    ("s_comm_islamic_liabilities",  ["1_9_2_comm_islamic_banks_liabilities", "1_9_2_1_comm_islamic_banks_liab_prev"], None),
    ("s_finance_cos_liabilities",   ["1_9_5_finance_cos_liabilities", "1_9_5_1_finance_cos_assets_liab_prev"], None),
    # Loans applied/approved/disbursed/repaid by purpose
    ("s_loans_applied_purpose",     ["1_10_loans_applied_by_purpose",  "1_10a_loans_applied_by_purpose_prev"],   "bank"),
    ("s_loans_approved_purpose",    ["1_12_loans_approved",            "1_12a_loans_approved_by_purpose_prev"],  "bank"),
    ("s_loans_disbursed_purpose",   ["1_14_loans_disbursed_by_purpose","1_14a_loans_disbursed_by_purpose_prev"], "purpose"),
    ("s_loans_repaid_purpose",      ["1_16_loans_repaid_by_purpose",   "1_16a_loans_repaid_by_purpose_prev"],    "purpose"),
    # Loans by sector
    ("s_loans_applied_sector",      ["1_11_loans_applied_by_sector",   "1_11a_loans_applied_by_sector_prev"],    "sector"),
    ("s_loans_approved_sector",     ["1_13_loans_approved_by_sector",  "1_13a_loans_approved_by_sector_prev",
                                     "1_13_1_loans_approved_by_sector_prev2"],                                    "sector"),
    ("s_loans_disbursed_sector",    ["1_15_loans_disbursed_by_sector", "1_15a_loans_disbursed_by_sector_prev",
                                     "1_15_1_loans_disbursed_by_sector_prev2"],                                   "sector"),
    ("s_loans_repaid_sector",       ["1_17_loans_repaid_by_sector",    "1_17a_loans_repaid_by_sector_prev",
                                     "1_17_1_loans_repaid_by_sector_prev2"],                                      "sector"),
    # Loans outstanding by type/purpose/sector
    ("s_loans_by_type",             ["1_18_loans_by_type",             "1_18a_loans_by_type_prev"],              "type"),
    ("s_loans_by_purpose",          ["1_19_loans_by_purpose",          "1_19a_loans_by_purpose_prev",
                                     "1_19b_loans_by_purpose_prev2",   "1_19c_loans_by_purpose_prev3"],          "purpose"),
    ("s_loans_by_sector",           ["1_20_loans_by_sector",           "1_20a_loans_by_sector_prev",
                                     "1_20b_loans_by_sector_prev2"],                                              "sector"),
    # Islamic financing
    ("s_islamic_financing_by_type",     ["1_18_1_islamic_financing_by_type",         "1_18_1a_islamic_financing_by_type_prev"],       "type"),
    ("s_islamic_financing_by_shariah",  ["1_18_2_islamic_financing_by_shariah",       "1_18_2a_islamic_financing_by_concept_prev"],    "industry"),
    ("s_islamic_financing_purpose_sector", ["1_19_1_islamic_financing_purpose_sector","1_19_1a_islamic_financing_purpose_sector_prev"],"industry"),
    ("s_household_loans_by_purpose",    ["1_19_6_household_loans_by_purpose",         "1_19_6a_household_loans_by_purpose_prev"],      "purpose"),
    ("s_comm_islamic_loans_by_sector",  ["1_20_1_comm_islamic_loans_by_sector",       "1_20_2_comm_islamic_loans_by_sector_prev"],     "sector"),
    ("s_investment_banks_loans_by_sector", ["1_20_3_investment_banks_loans_by_sector","1_20_4_investment_banks_loans_by_sector_prev"], "sector"),
    # Asset quality / provisions
    ("s_impaired_loans_provisions",     ["1_21b_impaired_loans_provisions_prev",       "1_21c_impaired_loans_provisions_prev2",
                                         "1_21d_impaired_loans_provisions_prev3"],                                None),
    ("s_islamic_financing_mfrs9_stages",["1_21_1_islamic_financing_mfrs9_stages",      "1_21_1a_islamic_npl_impaired_prev",
                                         "1_21_1b_islamic_impaired_provisions_prev",   "1_21_1c_islamic_impaired_provisions_prev2",
                                         "1_21_1d_islamic_impaired_provisions_prev3"],                           "industry"),
    ("s_comm_islamic_npl_impaired",     ["1_21_2_comm_islamic_npl_impaired",           "1_21_2a_comm_islamic_impaired_prev",
                                         "1_21_2b_comm_islamic_impaired_prev2"],                                 None),
    ("s_investment_banks_npl_impaired", ["1_21_3_investment_banks_npl_impaired",       "1_21_3a_investment_banks_impaired_prev",
                                         "1_21_3b_investment_banks_impaired_prev2"],                             None),
    ("s_impaired_loans_by_purpose",     ["1_22_impaired_loans_by_purpose",             "1_22c_impaired_loans_by_purpose_prev"],        "purpose"),
    ("s_npl_by_purpose",                ["1_22a_npl_by_purpose_prev",                  "1_22b_npl_by_purpose_prev2"],                  "purpose"),
    ("s_npl_by_sector",                 ["1_23a_npl_by_sector_prev",                   "1_23b_npl_by_sector_prev2"],                   "sector"),
    # Deposits
    ("s_islamic_deposits_by_type_holder", ["1_24_2_islamic_deposits_by_type_holder",   "1_24_3_islamic_deposits_by_type_holder_prev"], "ibs_deposits_by_type_holder"),
    # Interest rates / cheques
    ("s_interest_rates_banking",        ["2_1_interest_rates_banking",                 "2_1a_interest_rates_banking_prev"],             None),
    ("s_islamic_financing_profit_rates",["2_2_islamic_financing_profit_rates",         "2_2a_islamic_financing_profit_rates_prev"],     None),
    ("s_cheques_statistics",            ["3_5_14_cheques_statistics",                  "3_5_14a_dishonoured_cheques_prev"],              None),
]


# ── domain config ──────────────────────────────────────────────────────────────
# Each entry: (output_name, [(alias, source_table), ...], join_cols)
# join_cols is the COALESCE key set used in full outer joins (usually date + frequency).
# Sources may be raw tables (use their table_name slug) or stitched (s_*) tables.
# The first source is the "primary" — its date/frequency drives the join.

class DomainTable(NamedTuple):
    name: str
    sources: list[tuple[str, str]]    # [(alias, table_name), ...]
    join_cols: list[str]              # partition key cols beyond date & frequency
    select_override: str | None = None  # raw SQL SELECT if sources can't drive it


DOMAIN_RULES: list[DomainTable] = [
    DomainTable("h_1_money_supply", [
        ("t1", "m_1_3_monetary_aggregates"),
        ("t2", "m_1_3_1_broad_money_m3"),
        ("t3", "m_1_3_2_factors_affecting_m3"),
    ], []),
    DomainTable("h_2_currency_in_circulation", [
        ("t1", "m_1_2_currency_circulation_by_denom"),
    ], []),
    DomainTable("h_3_bnm_balance_sheet", [
        ("t1", "m_1_4_bnm_assets"),
        ("t2", "s_bnm_capital_liabilities"),
        ("t3", "m_1_6_bnm_special_funds"),
    ], []),
    DomainTable("h_4_liquidity_reserves", [
        ("t1", "m_1_1_reserve_money"),
        ("t2", "m_1_26_statutory_reserve_liquidity"),
        ("t3", "m_1_27_statutory_reserve_liquid_asset"),
        ("t4", "m_1_28_new_liquidity_framework"),
        ("t5", "m_1_28a_liquidity_coverage_ratio"),
        ("t6", "m_3_8_external_reserves"),
    ], []),
    DomainTable("h_5_banking_balance_sheet", [
        ("t1", "s_banking_assets"),
        ("t2", "s_banking_capital_liabilities"),
        ("t3", "m_1_7_1_islamic_banking_assets"),
        ("t4", "m_1_9_1_islamic_banking_capital_liabilities"),
    ], []),
    DomainTable("h_6a_loans_by_purpose", sources=[
        ("t1", "s_loans_applied_purpose"),
        ("t2", "s_loans_approved_purpose"),
        ("t3", "s_loans_disbursed_purpose"),
        ("t4", "s_loans_repaid_purpose"),
    ], join_cols=["bank"],
    select_override="""
        SELECT
            COALESCE(t1.date, t2.date, t3.date, t4.date) AS date,
            COALESCE(t1.frequency, t2.frequency, t3.frequency, t4.frequency) AS frequency,
            COALESCE(t1.bank, t2.bank, t3.purpose, t4.purpose) AS purpose,
            t1.total_loan_financing_applied,
            t2.total_approved AS total_loan_financing_approved,
            t3.total_disbursed AS total_loan_financing_disbursed,
            t4.total_repaid AS total_loan_financing_repaid
        FROM "s_loans_applied_purpose" t1
        FULL OUTER JOIN "s_loans_approved_purpose" t2
            ON t1.date = t2.date AND t1.frequency = t2.frequency AND t1.bank = t2.bank
        FULL OUTER JOIN "s_loans_disbursed_purpose" t3
            ON COALESCE(t1.date, t2.date) = t3.date
           AND COALESCE(t1.frequency, t2.frequency) = t3.frequency
           AND COALESCE(t1.bank, t2.bank) = t3.purpose
        FULL OUTER JOIN "s_loans_repaid_purpose" t4
            ON COALESCE(t1.date, t2.date, t3.date) = t4.date
           AND COALESCE(t1.frequency, t2.frequency, t3.frequency) = t4.frequency
           AND COALESCE(t1.bank, t2.bank, t3.purpose) = t4.purpose
        ORDER BY date ASC, purpose ASC
    """),
    DomainTable("h_6b_loans_by_sector", sources=[
        ("t1", "s_loans_applied_sector"),
        ("t2", "s_loans_approved_sector"),
        ("t3", "s_loans_disbursed_sector"),
        ("t4", "s_loans_repaid_sector"),
    ], join_cols=["sector"],
    select_override="""
        SELECT
            COALESCE(t1.date, t2.date, t3.date, t4.date) AS date,
            COALESCE(t1.frequency, t2.frequency, t3.frequency, t4.frequency) AS frequency,
            COALESCE(t1.sector, t2.sector, t3.sector, t4.sector) AS sector,
            t1.total_applied,
            t2.total_approved,
            t3.total_disbursed,
            t4.total_repaid
        FROM "s_loans_applied_sector" t1
        FULL OUTER JOIN "s_loans_approved_sector" t2
            ON t1.date = t2.date AND t1.frequency = t2.frequency AND t1.sector = t2.sector
        FULL OUTER JOIN "s_loans_disbursed_sector" t3
            ON t1.date = t3.date AND t1.frequency = t3.frequency AND t1.sector = t3.sector
        FULL OUTER JOIN "s_loans_repaid_sector" t4
            ON t1.date = t4.date AND t1.frequency = t4.frequency AND t1.sector = t4.sector
        ORDER BY date ASC, sector ASC
    """),
    DomainTable("h_6c_sme_loans", sources=[
        ("t1", "m_1_33_sme_loans_by_sector"),
        ("t2", "m_1_33_1_sme_loans_applied_by_sector"),
        ("t3", "m_1_33_2_sme_loans_approved_by_sector"),
        ("t4", "m_1_33_3_sme_loans_disbursed_by_sector"),
        ("t5", "m_1_33_4_sme_loans_repaid_by_sector"),
    ], join_cols=["sector"],
    select_override="""
        SELECT
            COALESCE(t1.date, t2.date, t3.date, t4.date, t5.date) AS date,
            COALESCE(t1.frequency, t2.frequency, t3.frequency, t4.frequency, t5.frequency) AS frequency,
            COALESCE(t1.sector, t2.sector, t3.sector, t4.sector, t5.sector) AS sector,
            t1.total_outstanding_loan_financing AS total_sme_loans,
            t2.financing_applied AS total_sme_loans_applied,
            t3.financing_approved AS total_sme_loans_approved,
            t4.financing_disbursed AS total_sme_loans_disbursed,
            t5.financing_repaid AS total_sme_loans_repaid
        FROM "m_1_33_sme_loans_by_sector" t1
        FULL OUTER JOIN "m_1_33_1_sme_loans_applied_by_sector" t2
            ON t1.date = t2.date AND t1.frequency = t2.frequency AND t1.sector = t2.sector
        FULL OUTER JOIN "m_1_33_2_sme_loans_approved_by_sector" t3
            ON t1.date = t3.date AND t1.frequency = t3.frequency AND t1.sector = t3.sector
        FULL OUTER JOIN "m_1_33_3_sme_loans_disbursed_by_sector" t4
            ON t1.date = t4.date AND t1.frequency = t4.frequency AND t1.sector = t4.sector
        FULL OUTER JOIN "m_1_33_4_sme_loans_repaid_by_sector" t5
            ON t1.date = t5.date AND t1.frequency = t5.frequency AND t1.sector = t5.sector
        ORDER BY date ASC, sector ASC
    """),
    DomainTable("h_7_deposits_funding", sources=[
        ("t1", "m_1_25_total_deposits_by_holder"),
        ("t2", "m_1_24_total_deposits_by_type"),
        ("t3", "s_islamic_deposits_by_type_holder"),
    ], join_cols=[],
    select_override="""
        WITH ibs_total AS (
            SELECT date, frequency,
                (COALESCE("rm_special_investment_total", 0) + COALESCE("fx_special_investment_total", 0)
               + COALESCE("rm_general_investment_total", 0) + COALESCE("fx_general_investment_total", 0)
               + COALESCE("rm_demand_total", 0)            + COALESCE("fx_demand_total", 0)
               + COALESCE("rm_saving_total", 0)            + COALESCE("fx_saving_total", 0)
               + COALESCE("rm_nids_total", 0)              + COALESCE("rm_tawarruq_total", 0)
               + COALESCE("fx_tawarruq_total", 0)          + COALESCE("rm_others_total", 0)
               + COALESCE("fx_others_total", 0)) AS total_deposits_islamic
            FROM "s_islamic_deposits_by_type_holder"
            WHERE "ibs_deposits_by_type_holder" IN ('Jumlah/ Total', 'Jumlah / Total')
        )
        SELECT
            COALESCE(t1.date, t2.date, t3.date) AS date,
            COALESCE(t1.frequency, t2.frequency, t3.frequency) AS frequency,
            t1.total AS total_deposits_banking_system,
            t2.total_deposits_repos AS total_deposits_by_type,
            t3.total_deposits_islamic
        FROM "m_1_25_total_deposits_by_holder" t1
        FULL OUTER JOIN "m_1_24_total_deposits_by_type" t2
            ON t1.date = t2.date AND t1.frequency = t2.frequency
        FULL OUTER JOIN ibs_total t3
            ON COALESCE(t1.date, t2.date) = t3.date
           AND COALESCE(t1.frequency, t2.frequency) = t3.frequency
        ORDER BY date ASC
    """),
    DomainTable("h_8_payments", [
        ("t1", "m_1_30_credit_card_operations"),
        ("t2", "m_1_30_1_debit_card_transactions"),
        ("t3", "s_cheques_statistics"),
    ], []),
    DomainTable("h_9_asset_quality_provisions", [
        ("t1", "m_1_21_loans_mfrs9_stages_provisions"),
        ("t2", "s_impaired_loans_provisions"),
        ("t3", "s_islamic_financing_mfrs9_stages"),
        ("t4", "s_comm_islamic_npl_impaired"),
    ], []),
    DomainTable("h_10_interest_rates", [
        ("t1", "s_interest_rates_banking"),
        ("t2", "s_islamic_financing_profit_rates"),
        ("t3", "s_loans_by_type"),
    ], []),
    DomainTable("h_11_exchange_rates", sources=[
        ("t1", "m_2_6_1_exchange_rates_myr_daily"),
        ("t2", "m_2_6_exchange_rates_myr"),
    ], join_cols=[],
    select_override="""
        SELECT
            COALESCE(t1.date, t2.date) AS date,
            COALESCE(t1.frequency, t2.frequency) AS frequency,
            t1.end_of_period AS daily_myr_usd_rate,
            t2.rm_unit_of_usd AS monthly_myr_usd_rate,
            t2.rm_unit_of_sgd AS monthly_myr_sgd_rate
        FROM "m_2_6_1_exchange_rates_myr_daily" t1
        FULL OUTER JOIN "m_2_6_exchange_rates_myr" t2
            ON t1.date = t2.date AND t1.frequency = t2.frequency
        ORDER BY date ASC
    """),
    DomainTable("h_12_money_market_activity", sources=[
        ("t1", "m_2_14_money_market_turnover"),
        ("t2", "m_2_17_fx_market_turnover"),
    ], join_cols=[],
    select_override="""
        SELECT
            COALESCE(t1.date, t2.date) AS date,
            COALESCE(t1.frequency, t2.frequency) AS frequency,
            (COALESCE(t1.bank_interbank, 0) + COALESCE(t1.corporate, 0)) AS money_market_turnover,
            (COALESCE(t2.fx_spot, 0) + COALESCE(t2.fx_swap, 0)
           + COALESCE(t2.fx_forward, 0) + COALESCE(t2.fx_options, 0)) AS fx_market_turnover
        FROM "m_2_14_money_market_turnover" t1
        FULL OUTER JOIN "m_2_17_fx_market_turnover" t2
            ON t1.date = t2.date AND t1.frequency = t2.frequency
        ORDER BY date ASC
    """),
    DomainTable("h_13_bond_sukuk", sources=[
        ("t1", "m_2_11_corporate_bond_sukuk_new_issues"),
        ("t2", "m_2_16_debt_securities_sukuk_turnover"),
        ("t3", "m_3_2_rentas_foreign_holdings"),
    ], join_cols=[],
    select_override="""
        SELECT
            COALESCE(t1.date, t2.date, t3.date) AS date,
            COALESCE(t1.frequency, t2.frequency, t3.frequency) AS frequency,
            t1.total_new_issues AS corporate_bond_issues,
            t2.total_turnover AS debt_turnover,
            t3.denominated_debt_securities AS foreign_holdings_rentas
        FROM "m_2_11_corporate_bond_sukuk_new_issues" t1
        FULL OUTER JOIN "m_2_16_debt_securities_sukuk_turnover" t2
            ON t1.date = t2.date AND t1.frequency = t2.frequency
        FULL OUTER JOIN "m_3_2_rentas_foreign_holdings" t3
            ON t1.date = t3.date AND t1.frequency = t3.frequency
        ORDER BY date ASC
    """),
    DomainTable("h_14_derivatives", [
        ("t1", "m_2_15_derivatives_turnover"),
    ], []),
    DomainTable("h_15_capital_raising", sources=[
        ("t1", "m_2_9_capital_market_public_sector"),
        ("t2", "m_2_10_capital_market_private_sector"),
    ], join_cols=[],
    select_override="""
        SELECT
            COALESCE(t1.date, t2.date) AS date,
            COALESCE(t1.frequency, t2.frequency) AS frequency,
            t1.funds_raised_in_the_capital_market_by_public_sector AS funds_raised_public,
            (COALESCE(t2.new_issues_of_shares_war_rants, 0)
           + COALESCE(t2.new_issues_of_corporate_bond_and_or_sukuk, 0)) AS funds_raised_private
        FROM "m_2_9_capital_market_public_sector" t1
        FULL OUTER JOIN "m_2_10_capital_market_private_sector" t2
            ON t1.date = t2.date AND t1.frequency = t2.frequency
        ORDER BY date ASC
    """),
    DomainTable("h_16_insurance_balance_sheet", [
        ("t1", "m_4_2_insurance_assets_liabilities"),
        ("t2", "m_4_3_takaful_assets_liabilities"),
        ("t3", "m_4_4_insurance_capital_adequacy"),
        ("t4", "m_4_5_takaful_capital_adequacy"),
    ], []),
    DomainTable("h_17_life_family_insurance", sources=[
        ("t1", "m_4_6_life_insurance_new_business"),
        ("t2", "m_4_8_1_family_takaful_new_certificates"),
    ], join_cols=[],
    select_override="""
        SELECT
            COALESCE(t1.date, t2.date) AS date,
            COALESCE(t1.frequency, t2.frequency) AS frequency,
            t1.business_within_malaysia AS life_new_policies,
            t2.takaful_sijil_takaful_family1_takaful_no_of_new_business_certificates_of_direct_takaful_operators_sijil_no_of_certificates_annuity_total AS family_takaful_new_certificates
        FROM "m_4_6_life_insurance_new_business" t1
        FULL OUTER JOIN "m_4_8_1_family_takaful_new_certificates" t2
            ON t1.date = t2.date AND t1.frequency = t2.frequency
        ORDER BY date ASC
    """),
    DomainTable("h_18_general_insurance_takaful", sources=[
        ("t1", "m_4_7_1_general_insurance_direct_premiums"),
        ("t2", "m_4_7_14_general_insurance_earned_premium"),
    ], join_cols=[],
    select_override="""
        SELECT
            COALESCE(t1.date, t2.date) AS date,
            COALESCE(t1.frequency, t2.frequency) AS frequency,
            t1.general1_insurance_distribution_of_gross_direct_premiums_total AS general_direct_premiums,
            t2.rm_million_total AS general_earned_premiums
        FROM "m_4_7_1_general_insurance_direct_premiums" t1
        FULL OUTER JOIN "m_4_7_14_general_insurance_earned_premium" t2
            ON t1.date = t2.date AND t1.frequency = t2.frequency
        ORDER BY date ASC
    """),
    DomainTable("h_19_intermediaries", [
        ("t1", "m_4_7_a_general_insurance_underwriting_results"),
    ], []),
    DomainTable("h_20_employment", [
        ("t1", "m_3_5_12a_labour_market_financial_sector"),
    ], []),
    DomainTable("h_21_international", sources=[
        ("t1", "m_3_6_7_gross_imports_by_economic_function"),
        ("t2", "m_3_7_external_debt"),
    ], join_cols=[],
    select_override="""
        SELECT
            COALESCE(t1.date, t2.date) AS date,
            COALESCE(t1.frequency, t2.frequency) AS frequency,
            t1.transport_equipment AS gross_imports_transport_equipment,
            t2.medium_and_long_term AS external_debt_medium_long_term
        FROM "m_3_6_7_gross_imports_by_economic_function" t1
        FULL OUTER JOIN "m_3_7_external_debt" t2
            ON t1.date = t2.date AND t1.frequency = t2.frequency
        ORDER BY date ASC
    """),
]

# Known key columns and their canonical values for normalisation during stitch
_BANK_KEY_NORMALISE = {
    "bank", "merchant_investment_banks", "merchant_banks",
    "ibs_investment_merchant_banks", "ibs_deposits_by_type_holder",
    "ibs_deposits_type_holder_prev", "purpose",
}
_BANK_NORMALISE_CASES = """
    CASE
        WHEN CAST("{col}" AS VARCHAR) IN ('Bank-bank perdagangan',
             'Bank-bank perdagangan / Commercial banks',
             'Bank-bank Perdagangan / Commercial Banks')
            THEN 'Bank-bank Perdagangan / Commercial Banks'
        WHEN CAST("{col}" AS VARCHAR) IN ('Bank-bank Islam',
             'Bank-bank Islam / Islamic banks',
             'Bank-bank Islam / Islamic Banks')
            THEN 'Bank-bank Islam / Islamic Banks'
        WHEN CAST("{col}" AS VARCHAR) IN ('Bank-bank saudagar atau pelaburan',
             'Bank-bank saudagar atau pelaburan / Merchant or Investment banks',
             'Bank-bank Pelaburan / Investment Banks')
            THEN 'Bank-bank Pelaburan / Investment Banks'
        WHEN CAST("{col}" AS VARCHAR) = 'Jumlah / Total' THEN 'Jumlah / Total'
        ELSE CAST("{col}" AS VARCHAR)
    END AS "{key_col}"
"""


# ── public API ─────────────────────────────────────────────────────────────────

def run(
    con: duckdb.DuckDBPyConnection,
    logger: RunLogger,
    run_id: str,
) -> list[str]:
    """Run all harmonisation steps. Returns list of created h_ table names."""
    logger.section("Stage 2 — Harmonise")

    available_raw = set(db_mod.list_tables(con))

    # (a) Map raw tables → m_ tables
    logger.section("Step 2a — Column mapping (raw → m_)")
    _apply_column_maps(con, logger, run_id, available_raw)

    # (b) Stitch timeseries → s_ tables
    logger.section("Step 2b — Timeseries stitching (m_ → s_)")
    available_m = set(db_mod.list_tables(con, "m_"))
    _stitch_tables(con, logger, run_id, available_m)

    # (c) Domain consolidation → h_ tables
    logger.section("Step 2c — Domain consolidation (→ h_)")
    available_all = set(db_mod.list_tables(con))
    domain_tables = _build_domain_tables(con, logger, run_id, available_all)

    # (d) Dedup suffix columns within h_ tables
    logger.section("Step 2d — Deduplicating suffix columns")
    _dedup_suffix_columns(con, logger, run_id, domain_tables)

    return domain_tables


# ── step (a): column mapping ───────────────────────────────────────────────────

def _apply_column_maps(
    con: duckdb.DuckDBPyConnection,
    logger: RunLogger,
    run_id: str,
    available_raw: set[str],
) -> None:
    catalog_rows = con.execute("SELECT table_name, table_id FROM _catalog WHERE error IS NULL").fetchall()
    mapped = 0
    for table_name, table_id in catalog_rows:
        if table_name not in available_raw:
            continue
        cols = db_mod.table_columns(con, table_name)
        mapping = output_mapping_for(table_id, cols)

        dropped = [c for c in cols if mapping.get(c) == "drop"]
        select_parts = [
            f'"{c}" AS "{mapping.get(c, c)}"'
            for c in cols
            if mapping.get(c) != "drop"
        ]
        m_name = f"m_{table_name}"
        con.execute(f'CREATE OR REPLACE TABLE "{m_name}" AS SELECT {", ".join(select_parts)} FROM "{table_name}"')
        mapped += 1

        renamed = {src: tgt for src, tgt in mapping.items() if src != tgt and tgt != "drop"}
        if dropped:
            logger.event("harmonise", "column_map_dropped", source=table_name,
                         dropped=dropped)
        if renamed:
            logger.event("harmonise", "column_map", source=table_name, target=m_name,
                         renamed=len(renamed))
            db_mod.log_harmonise_action(con, run_id=run_id, stage="column_map",
                action="renamed", source=table_name, target=m_name,
                detail=str(renamed))

    logger.event("harmonise", "column_map_complete", mapped=mapped)


# ── step (b): stitch ───────────────────────────────────────────────────────────

def _stitch_tables(
    con: duckdb.DuckDBPyConnection,
    logger: RunLogger,
    run_id: str,
    available_m: set[str],
) -> None:
    for output_name, member_ids, key_col in STITCH_RULES:
        m_members = [f"m_{t}" for t in member_ids]
        present = [m for m in m_members if m in available_m]
        missing = [m for m in m_members if m not in available_m]

        if not present:
            logger.event("harmonise", "stitch_skipped", target=output_name, reason="no source tables present")
            continue
        if missing:
            logger.event("harmonise", "stitch_partial", target=output_name,
                         missing=missing, using=present)

        _stitch(con, output_name, present, key_col)
        logger.event("harmonise", "stitched", target=output_name, sources=len(present), key=key_col or "none")
        db_mod.log_harmonise_action(con, run_id=run_id, stage="stitch",
            action="created", target=output_name,
            source=",".join(present), detail=f"key={key_col}")


def _stitch(
    con: duckdb.DuckDBPyConnection,
    output_name: str,
    m_tables: list[str],
    key_col: str | None,
) -> None:
    base_cols: dict[str, str] = {
        r[1]: r[2]
        for r in con.execute(f'PRAGMA table_info("{m_tables[0]}")').fetchall()
    }

    # Semantic key column candidates
    _KEY_CANDIDATES = {
        "bank", "sector", "type", "industry", "size", "purpose",
        "merchant_investment_banks", "ibs_investment_merchant_banks",
        "merchant_banks", "ibs_deposits_by_type_holder", "ibs_deposits_type_holder_prev",
    }

    queries: list[str] = []
    for idx, m in enumerate(m_tables):
        m_cols: dict[str, str] = {
            r[1]: r[2]
            for r in con.execute(f'PRAGMA table_info("{m}")').fetchall()
        }
        parts: list[str] = ['"date"', '"frequency"']

        if key_col is not None:
            m_keys = [k for k in m_cols if k in _KEY_CANDIDATES]
            if m_keys:
                src_key = m_keys[0]
                if src_key in _BANK_KEY_NORMALISE:
                    parts.append(_BANK_NORMALISE_CASES.format(col=src_key, key_col=key_col))
                else:
                    parts.append(f'CAST("{src_key}" AS VARCHAR) AS "{key_col}"')
            else:
                parts.append(f'CAST(NULL AS VARCHAR) AS "{key_col}"')

        for b_name, b_type in base_cols.items():
            if b_name in ("date", "frequency") or b_name == key_col:
                continue
            matched = next(
                (c for c in m_cols if c == b_name or _clean(c) == _clean(b_name)),
                None,
            )
            if matched:
                parts.append(f'"{matched}" AS "{b_name}"')
            else:
                parts.append(f'CAST(NULL AS {b_type}) AS "{b_name}"')

        queries.append(f'SELECT {", ".join(parts)}, {idx} AS _pri FROM "{m}"')

    union_sql = " UNION ALL ".join(queries)
    partition = "date, frequency" + (f', "{key_col}"' if key_col else "")

    con.execute(f"""
        CREATE OR REPLACE TABLE "{output_name}" AS
        WITH ranked AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY {partition} ORDER BY _pri ASC) AS _rn
            FROM ({union_sql})
        )
        SELECT * EXCLUDE (_pri, _rn) FROM ranked WHERE _rn = 1
        ORDER BY date ASC
    """)


# ── step (c): domain tables ────────────────────────────────────────────────────

def _build_domain_tables(
    con: duckdb.DuckDBPyConnection,
    logger: RunLogger,
    run_id: str,
    available: set[str],
) -> list[str]:
    created: list[str] = []

    for rule in DOMAIN_RULES:
        present = [(alias, tbl) for alias, tbl in rule.sources if tbl in available]
        missing = [tbl for _, tbl in rule.sources if tbl not in available]

        if not present:
            logger.event("harmonise", "domain_skipped", target=rule.name, reason="no source tables present")
            continue
        if missing:
            logger.event("harmonise", "domain_partial", target=rule.name, missing=missing)

        try:
            if rule.select_override:
                con.execute(f'CREATE OR REPLACE TABLE "{rule.name}" AS {rule.select_override}')
            else:
                _build_domain_auto(con, rule.name, present)

            row_count = con.execute(f'SELECT COUNT(*) FROM "{rule.name}"').fetchone()[0]
            col_count = len(db_mod.table_columns(con, rule.name))
            logger.event("harmonise", "domain_created", target=rule.name,
                         sources=len(present), rows=row_count, cols=col_count)
            db_mod.log_harmonise_action(con, run_id=run_id, stage="domain",
                action="created", target=rule.name,
                source=",".join(t for _, t in present),
                detail=f"rows={row_count}")
            created.append(rule.name)

        except Exception as exc:
            logger.event("harmonise", "domain_error", target=rule.name, error=str(exc))

    return created


def _build_domain_auto(
    con: duckdb.DuckDBPyConnection,
    output_name: str,
    sources: list[tuple[str, str]],
) -> None:
    """Build a domain table via sequential FULL OUTER JOINs on date + frequency."""
    aliases = [alias for alias, _ in sources]
    tables  = [tbl  for _, tbl  in sources]

    coalesce_date  = ", ".join(f"{a}.date"      for a in aliases)
    coalesce_freq  = ", ".join(f"{a}.frequency" for a in aliases)

    # Collect all data columns (exclude date/frequency), deduping by name
    seen_cols: set[str] = set()
    data_parts: list[str] = []
    for alias, tbl in sources:
        for col in db_mod.table_columns(con, tbl):
            if col in ("date", "frequency") or col in seen_cols:
                continue
            seen_cols.add(col)
            data_parts.append(f'{alias}."{col}"')

    join_sql = f'FROM "{tables[0]}" {aliases[0]}'
    for alias, tbl in sources[1:]:
        prev_aliases = aliases[:aliases.index(alias)]
        coalesce_prev_date = ", ".join(f"{a}.date" for a in prev_aliases)
        coalesce_prev_freq = ", ".join(f"{a}.frequency" for a in prev_aliases)
        join_sql += (
            f'\nFULL OUTER JOIN "{tbl}" {alias}'
            f' ON COALESCE({coalesce_prev_date}) = {alias}.date'
            f' AND COALESCE({coalesce_prev_freq}) = {alias}.frequency'
        )

    con.execute(f"""
        CREATE OR REPLACE TABLE "{output_name}" AS
        SELECT
            COALESCE({coalesce_date}) AS date,
            COALESCE({coalesce_freq}) AS frequency,
            {', '.join(data_parts)}
        {join_sql}
        ORDER BY date ASC
    """)


# ── step (d): dedup suffix columns ────────────────────────────────────────────

def _dedup_suffix_columns(
    con: duckdb.DuckDBPyConnection,
    logger: RunLogger,
    run_id: str,
    tables: list[str],
) -> None:
    """
    For each `col_N` column that has a matching `col` column:
      - If col_N is empty → drop it.
      - If col_N matches col exactly (no conflicts) → merge values into col, drop col_N.
      - If col_N has conflicting values → keep both (log as warning).
    """
    suffix_re = re.compile(r"^(.+)_(\d+)$")

    for table in tables:
        if not db_mod.table_exists(con, table):
            continue

        cols = db_mod.table_columns(con, table)
        col_set = set(cols)
        col_types = {
            r[1]: r[2]
            for r in con.execute(f'PRAGMA table_info("{table}")').fetchall()
        }

        for col in cols:
            m = suffix_re.match(col)
            if not m:
                continue
            base = m.group(1)
            if base not in col_set:
                continue

            # Reload current col list in case we dropped something earlier
            current = set(db_mod.table_columns(con, table))
            if col not in current or base not in current:
                continue

            df = con.execute(
                f'SELECT "{base}", "{col}" FROM "{table}"'
            ).fetchdf()

            base_nn  = df[base].notna()
            cand_nn  = df[col].notna()
            overlap  = (base_nn & cand_nn).sum()
            cand_only = (~base_nn & cand_nn).sum()

            if not cand_nn.any():
                # Candidate is entirely empty — drop it
                con.execute(f'ALTER TABLE "{table}" DROP COLUMN "{col}"')
                col_set.discard(col)
                logger.event("harmonise", "column_dropped_empty",
                             table=table, col_name=col, base=base)
                db_mod.log_harmonise_action(con, run_id=run_id, stage="dedup",
                    action="dropped_empty", target=table, col_name=col)
                continue

            if overlap > 0:
                # Check for conflicts
                conflicts = _count_conflicts(df, base, col)
                if conflicts > 0:
                    logger.event("harmonise", "column_kept_conflict",
                                 table=table, col_name=col, base=base, conflicts=conflicts)
                    db_mod.log_harmonise_action(con, run_id=run_id, stage="dedup",
                        action="kept_conflict", target=table, col_name=col,
                        detail=f"conflicts={conflicts}")
                    continue

            if cand_only > 0:
                # Candidate has extra rows not in base — try to fill
                base_type = col_types.get(base, "VARCHAR")
                con.execute(f"""
                    UPDATE "{table}"
                    SET "{base}" = COALESCE("{base}", TRY_CAST("{col}" AS {base_type}))
                    WHERE "{base}" IS NULL AND "{col}" IS NOT NULL
                """)
                logger.event("harmonise", "column_merged",
                             table=table, col_name=col, base=base, filled=int(cand_only))
                db_mod.log_harmonise_action(con, run_id=run_id, stage="dedup",
                    action="merged", target=table, col_name=col,
                    detail=f"filled={cand_only}")

            con.execute(f'ALTER TABLE "{table}" DROP COLUMN "{col}"')
            col_set.discard(col)
            logger.event("harmonise", "column_dropped_duplicate",
                         table=table, col_name=col, base=base)
            db_mod.log_harmonise_action(con, run_id=run_id, stage="dedup",
                action="dropped_duplicate", target=table, col_name=col)


def _count_conflicts(df: pd.DataFrame, base: str, candidate: str) -> int:
    overlap = df[base].notna() & df[candidate].notna()
    if not overlap.any():
        return 0
    base_num = pd.to_numeric(df.loc[overlap, base], errors="coerce")
    cand_num = pd.to_numeric(df.loc[overlap, candidate], errors="coerce")
    both_numeric = base_num.notna() & cand_num.notna()
    conflicts = 0
    if both_numeric.any():
        conflicts += int(((base_num[both_numeric] - cand_num[both_numeric]).abs() > 1e-9).sum())
    text_mask = ~both_numeric
    if text_mask.any():
        b_str = df.loc[overlap, base][text_mask].astype(str).str.strip()
        c_str = df.loc[overlap, candidate][text_mask].astype(str).str.strip()
        conflicts += int((b_str != c_str).sum())
    return conflicts


def _clean(name: str) -> str:
    """Normalise column name for fuzzy matching across tables."""
    c = re.sub(
        r"^(banking_system|islamic_banking_system|sistem_perbankan|sistem_perbankan_islam"
        r"|sme_loans|financial_institution|takaful_keluarga\d*|general_insurance)"
        r"_[a-z0-9_]*?_rm_(million|juta)_",
        "", name.lower(),
    )
    c = re.sub(
        r"^(banking_system|islamic_banking_system|sistem_perbankan|sistem_perbankan_islam"
        r"|sme_loans|financial_institution|takaful_keluarga\d*|general_insurance)_",
        "", c,
    )
    c = re.sub(r"[^a-z0-9]", "", c)
    return (c.replace("loans", "loan").replace("cards", "card")
             .replace("purposes", "purpose").replace("vehicles", "vehicle")
             .replace("assets", "asset").replace("rates", "rate"))
