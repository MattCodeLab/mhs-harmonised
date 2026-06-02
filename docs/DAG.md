# Pipeline DAG

This document shows the complete dependency graph from source Excel files to
output domain tables.

---

## Stage 1 — Ingest

Each Excel file produces one raw DuckDB table.  Table names follow the pattern
`{id_with_underscores}_{slug}`, e.g. `1_3_1_broad_money_m3`.

```
sample-excels/
├── 1.1.xlsx   ──► 1_1_reserve_money
├── 1.2.xlsx   ──► 1_2_currency_circulation_by_denom
├── 1.3.xlsx   ──► 1_3_monetary_aggregates
├── 1.3.1.xlsx ──► 1_3_1_broad_money_m3
├── 1.3.2.xlsx ──► 1_3_2_factors_affecting_m3
├── ...
└── 5.2.xlsx   ──► 5_2_leasing_factoring_assets_liab
```

---

## Stage 2a — Column mapping (raw → m_)

Every raw table gets a column-renamed mirror with prefix `m_`.

```
1_1_reserve_money  ──column_map──►  m_1_1_reserve_money
1_3_monetary_aggregates  ────────►  m_1_3_monetary_aggregates
...
```

---

## Stage 2b — Timeseries stitching (m_ → s_)

Previous-edition tables are unioned with current tables to produce continuous
timeseries. Rows are deduplicated by `(date, frequency[, key_col])` with the
most recent edition taking priority.

```
m_1_5_bnm_capital_liabilities
m_1_5_1_bnm_capital_liabilities_prev  ──UNION──►  s_bnm_capital_liabilities

m_1_10_loans_applied_by_purpose
m_1_10a_loans_applied_by_purpose_prev  ─────────►  s_loans_applied_purpose  (key=bank)

m_1_13_loans_approved_by_sector
m_1_13a_loans_approved_by_sector_prev
m_1_13_1_loans_approved_by_sector_prev2  ────────►  s_loans_approved_sector  (key=sector)

m_1_19_loans_by_purpose
m_1_19a_loans_by_purpose_prev
m_1_19b_loans_by_purpose_prev2
m_1_19c_loans_by_purpose_prev3  ─────────────────►  s_loans_by_purpose  (key=purpose)

m_2_1_interest_rates_banking
m_2_1a_interest_rates_banking_prev  ─────────────►  s_interest_rates_banking
```

*(Full list in `STITCH_RULES` in `pipeline/harmonise.py`)*

---

## Stage 2c — Domain consolidation (→ h_)

Related tables are joined on `(date, frequency)` via FULL OUTER JOIN to produce
one wide table per domain dataset.

### Monetary System

```
m_1_3_monetary_aggregates ─────┐
m_1_3_1_broad_money_m3 ────────┤ FULL OUTER JOIN ──► h_1_money_supply
m_1_3_2_factors_affecting_m3 ──┘

m_1_2_currency_circulation_by_denom ──────────────► h_2_currency_in_circulation

m_1_4_bnm_assets ──────────────┐
s_bnm_capital_liabilities ─────┤ ──────────────────► h_3_bnm_balance_sheet
m_1_6_bnm_special_funds ───────┘

m_1_1_reserve_money ───────────┐
m_1_26_statutory_reserve_liquidity
m_1_27_statutory_reserve_liquid_asset
m_1_28_new_liquidity_framework ┤ ──────────────────► h_4_liquidity_reserves
m_1_28a_liquidity_coverage_ratio
m_3_8_external_reserves ───────┘
```

### Banking System

```
s_banking_assets ────────────────┐
s_banking_capital_liabilities ───┤ ──────────────────► h_5_banking_balance_sheet
m_1_7_1_islamic_banking_assets ──┤
m_1_9_1_islamic_banking_cap_liab ┘

s_loans_applied_purpose ──┐
s_loans_approved_purpose ─┤ FULL OUTER JOIN ──────────► h_6a_loans_by_purpose
s_loans_disbursed_purpose ┤ (key = purpose/bank)
s_loans_repaid_purpose ───┘

s_loans_applied_sector ───┐
s_loans_approved_sector ──┤ ──────────────────────────► h_6b_loans_by_sector
s_loans_disbursed_sector ─┤ (key = sector)
s_loans_repaid_sector ────┘

m_1_33_sme_loans_by_sector ────────┐
m_1_33_1_sme_loans_applied_by_sector
m_1_33_2_sme_loans_approved_by_sector ─────────────►  h_6c_sme_loans
m_1_33_3_sme_loans_disbursed_by_sector
m_1_33_4_sme_loans_repaid_by_sector ──┘

m_1_25_total_deposits_by_holder ─┐
m_1_24_total_deposits_by_type ───┤ ──────────────────► h_7_deposits_funding
s_islamic_deposits_by_type_holder┘

m_1_30_credit_card_operations ───┐
m_1_30_1_debit_card_transactions ┤ ──────────────────► h_8_payments
s_cheques_statistics ────────────┘

m_1_21_loans_mfrs9_stages_provisions ─┐
s_impaired_loans_provisions ──────────┤ ─────────────► h_9_asset_quality_provisions
s_islamic_financing_mfrs9_stages ─────┤
s_comm_islamic_npl_impaired ──────────┘
```

### Financial Markets

```
s_interest_rates_banking ────────┐
s_islamic_financing_profit_rates ┤ ──────────────────► h_10_interest_rates
s_loans_by_type ─────────────────┘

m_2_6_1_exchange_rates_myr_daily ─┐ ────────────────► h_11_exchange_rates
m_2_6_exchange_rates_myr ─────────┘

m_2_14_money_market_turnover ─┐ ─────────────────────► h_12_money_market_activity
m_2_17_fx_market_turnover ────┘

m_2_11_corporate_bond_sukuk_new_issues ─┐
m_2_16_debt_securities_sukuk_turnover ──┤ ──────────► h_13_bond_sukuk
m_3_2_rentas_foreign_holdings ──────────┘

m_2_15_derivatives_turnover ──────────────────────────► h_14_derivatives

m_2_9_capital_market_public_sector ─┐ ──────────────► h_15_capital_raising
m_2_10_capital_market_private_sector┘
```

### Insurance & Takaful

```
m_4_2_insurance_assets_liabilities ─┐
m_4_3_takaful_assets_liabilities ───┤ ──────────────► h_16_insurance_balance_sheet
m_4_4_insurance_capital_adequacy ───┤
m_4_5_takaful_capital_adequacy ─────┘

m_4_6_life_insurance_new_business ───┐ ─────────────► h_17_life_family_insurance
m_4_8_1_family_takaful_new_certificates┘

m_4_7_1_general_insurance_direct_premiums ─┐ ───────► h_18_general_insurance_takaful
m_4_7_14_general_insurance_earned_premium ─┘

m_4_7_a_general_insurance_underwriting_results ─────► h_19_intermediaries
```

### Institutions & Access / International

```
m_3_5_12a_labour_market_financial_sector ───────────► h_20_employment

m_3_6_7_gross_imports_by_economic_function ─┐ ──────► h_21_international
m_3_7_external_debt ────────────────────────┘
```

---

## Stage 2d — Dedup suffix columns

After domain tables are built, columns named `col_N` (where `col` also exists)
are evaluated:

| Condition                          | Action                      |
|------------------------------------|-----------------------------|
| `col_N` is entirely NULL           | Drop `col_N`                |
| `col_N` matches `col` (no conflicts) + has extra rows | Fill `col` from `col_N`, drop `col_N` |
| `col_N` matches `col` (no conflicts) | Drop `col_N`              |
| `col_N` has conflicting values     | Keep both, log warning      |

Every decision is recorded in the `_harmonise_log` DuckDB table and the run
summary log file.
