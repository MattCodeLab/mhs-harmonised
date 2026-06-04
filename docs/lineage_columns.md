# Stage 2 Harmonised — Column-Level Lineage

One entry per output file under `outputs/stage2_harmonised/`. Each entry shows:
- The BNM source table(s) and how they were processed before export
- Every column in the output, tagged with the BNM table it came from

**Pipeline notation used below:**
| Tag | Meaning |
|-----|---------|
| `m_` | Column-mapped — raw Excel ingested and columns renamed |
| `s_` | Stitched — UNION of multiple `m_` editions, deduped by `(date, frequency)` |
| `[key]` | Join / partition key, not a measure |
| `[rows]` | This BNM table contributes historical **rows** only; column schema comes from the primary |

---

## Monetary System — Money Supply

### `monthly_monetary_aggregates_m1_m2_m3`
**Source:** `m_1_3_monetary_aggregates` (BNM **1.3** — Monetary Aggregates: M1, M2 and M3)  
**Processing:** Direct (column-map only)

| Column | Source |
|--------|--------|
| `date` | BNM 1.3 `[key]` |
| `frequency` | BNM 1.3 `[key]` |
| `m3` | BNM 1.3 |
| `m2` | BNM 1.3 |
| `m1` | BNM 1.3 |
| `currency_in_circulation` | BNM 1.3 |
| `demand_deposits` | BNM 1.3 |
| `narrow_quasi_money` | BNM 1.3 |
| `savings_deposits` | BNM 1.3 |
| `fixed_deposits` | BNM 1.3 |
| `nids` | BNM 1.3 |
| `repos` | BNM 1.3 |
| `fx_deposits` | BNM 1.3 |
| `other_deposits` | BNM 1.3 |
| `deposits_placed_other_banking_inst` | BNM 1.3 |

---

### `monthly_broad_money_m3`
**Source:** `m_1_3_1_broad_money_m3` (BNM **1.3.1** — Broad Money, M3)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.3.1 `[key]` |
| `frequency` | BNM 1.3.1 `[key]` |
| `m3_total` | BNM 1.3.1 |
| `transaction_balances` | BNM 1.3.1 |
| `currency_in_circulation` | BNM 1.3.1 |
| `demand_deposits` | BNM 1.3.1 |
| `broad_quasi_money` | BNM 1.3.1 |
| `savings_deposits` | BNM 1.3.1 |
| `fixed_deposits` | BNM 1.3.1 |
| `nids` | BNM 1.3.1 |
| `repos` | BNM 1.3.1 |
| `fx_deposits` | BNM 1.3.1 |
| `other_deposits` | BNM 1.3.1 |

---

### `monthly_factors_affecting_m3`
**Source:** `m_1_3_2_factors_affecting_m3` (BNM **1.3.2** — Factors Affecting M3)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.3.2 `[key]` |
| `frequency` | BNM 1.3.2 `[key]` |
| `m3_total` | BNM 1.3.2 |
| `net_claims_on_gov_total` | BNM 1.3.2 |
| `claims_on_gov` | BNM 1.3.2 |
| `gov_deposits` | BNM 1.3.2 |
| `claims_on_private_sector_total` | BNM 1.3.2 |
| `loans` | BNM 1.3.2 |
| `securities` | BNM 1.3.2 |
| `net_foreign_assets_total` | BNM 1.3.2 |
| `bnm` | BNM 1.3.2 |
| `banking_system` | BNM 1.3.2 |
| `other_influences` | BNM 1.3.2 |

---

## Monetary System — Currency in Circulation

### `monthly_currency_in_circulation_by_denomination`
### `annual_currency_in_circulation_by_denomination`
**Source:** `m_1_2_currency_circulation_by_denom` (BNM **1.2** — Currency in Circulation by Denomination)  
**Processing:** Direct — filtered by `frequency = 'Monthly'` / `'Annual'` respectively

Both outputs share identical columns:

| Column | Source |
|--------|--------|
| `date` | BNM 1.2 `[key]` |
| `frequency` | BNM 1.2 `[key]` |
| `currency_by_denomination` | BNM 1.2 `[key]` |
| `currency_in_circulation` | BNM 1.2 |
| `rm1` | BNM 1.2 |
| `rm2` | BNM 1.2 |
| `rm5` | BNM 1.2 |
| `rm10` | BNM 1.2 |
| `rm20` | BNM 1.2 |
| `rm50` | BNM 1.2 |
| `rm100` | BNM 1.2 |
| `rm500` | BNM 1.2 |
| `rm1000` | BNM 1.2 |
| `notes_others` | BNM 1.2 |
| `1_sen` | BNM 1.2 |
| `5_sen` | BNM 1.2 |
| `10_sen` | BNM 1.2 |
| `20_sen` | BNM 1.2 |
| `50_sen` | BNM 1.2 |
| `rm1_coins` | BNM 1.2 |
| `coins_total` | BNM 1.2 |
| `others` | BNM 1.2 |

---

## Monetary System — BNM Balance Sheet

### `bnm_statement_of_assets_capital_and_liabilities`
**Source:** `s_bnm_capital_liabilities` — STITCH of:
- BNM **1.5** — BNM: Statement of Capital and Liabilities (primary, current edition)
- BNM **1.5.1** — BNM: Statement of Capital and Liabilities (prev) `[rows]`

Column schema comes from BNM 1.5; historical rows are filled from BNM 1.5.1.

| Column | Source |
|--------|--------|
| `date` | BNM 1.5 `[key]` |
| `frequency` | BNM 1.5 `[key]` |
| `bank_negara_malaysia_statement_of_capital_and_liabilities` | BNM 1.5 |
| `paid_up_capital` | BNM 1.5 |
| `reserves` | BNM 1.5 |
| `currency_in_circulation` | BNM 1.5 |
| `financial_institutions` | BNM 1.5 |
| `federal_government` | BNM 1.5 |
| `deposits_others` | BNM 1.5 |
| `bank_negara_bills_and_bonds` | BNM 1.5 |
| `allocation_of_special_drawing_rights` | BNM 1.5 |
| `other_liabilities` | BNM 1.5 |
| `total_liabilities` | BNM 1.5 |

---

## Monetary System — Liquidity & Reserves

### `reserve_money`
**Source:** `m_1_1_reserve_money` (BNM **1.1** — Reserve Money)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.1 `[key]` |
| `frequency` | BNM 1.1 `[key]` |
| `reserve_money` | BNM 1.1 |
| `currency_in_circulation` | BNM 1.1 |
| `required_reserves` | BNM 1.1 |
| `excess_reserves` | BNM 1.1 |
| `deposits_of_the_private_sector` | BNM 1.1 |
| `net_claims_on_government` | BNM 1.1 |
| `claims_on_government` | BNM 1.1 |
| `government_deposits` | BNM 1.1 |
| `claims_on_private_sector` | BNM 1.1 |
| `external_operations` | BNM 1.1 |
| `other_influences` | BNM 1.1 |

---

### `statutory_reserve_requirement_and_liquidity_ratio`
**Source:** `m_1_26_statutory_reserve_liquidity` (BNM **1.26** — Statutory Reserve Requirement and Liquidity Ratio)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.26 `[key]` |
| `frequency` | BNM 1.26 `[key]` |
| `year` | BNM 1.26 |
| `date_change` | BNM 1.26 |
| `parenthetical_row` | BNM 1.26 |
| `commercial_banks_srr` | BNM 1.26 |
| `commercial_banks_srr_alt` | BNM 1.26 |
| `commercial_banks_liquidity_ratio` | BNM 1.26 |
| `commercial_banks_liquidity_ratio_alt` | BNM 1.26 |
| `finance_companies_srr` | BNM 1.26 |
| `finance_companies_srr_alt` | BNM 1.26 |
| `finance_companies_liquidity_ratio` | BNM 1.26 |
| `finance_companies_liquidity_ratio_alt` | BNM 1.26 |
| `merchant_banks_srr` | BNM 1.26 |
| `merchant_banks_srr_alt` | BNM 1.26 |
| `merchant_banks_liquidity_ratio` | BNM 1.26 |
| `merchant_banks_liquidity_ratio_alt` | BNM 1.26 |

---

### `statutory_reserve_and_liquid_asset_requirement`
**Source:** `m_1_27_statutory_reserve_liquid_asset` (BNM **1.27** — Statutory Reserve and Liquid Asset Requirement)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.27 `[key]` |
| `frequency` | BNM 1.27 `[key]` |
| `statutory_reserve` | BNM 1.27 |
| `rm_eligible_liabilities` | BNM 1.27 |
| `ibs_statutory_reserve` | BNM 1.27 |
| `ibs_rm_eligible_liabilities` | BNM 1.27 |
| `inv_banks_statutory_reserve` | BNM 1.27 |
| `inv_banks_rm_eligible_liabilities` | BNM 1.27 |

---

### `new_liquidity_framework`
**Source:** `m_1_28_new_liquidity_framework` (BNM **1.28** — New Liquidity Framework)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.28 `[key]` |
| `frequency` | BNM 1.28 `[key]` |
| `compliance_requirement` | BNM 1.28 |
| `compliance_req_le_1_week` | BNM 1.28 |
| `net_compliance_surplus` | BNM 1.28 |
| `compliance_req_1w_to_1m` | BNM 1.28 |
| `compliance_req_1w_to_1m_1` | BNM 1.28 |
| `net_surplus_1w_to_1m` | BNM 1.28 |
| `compliance_req_le_1_week_1` | BNM 1.28 |
| `ibs_compliance_req_le_1_week` | BNM 1.28 |
| `net_surplus_le_1_week` | BNM 1.28 |
| `ibs_compliance_req_1w_to_1m` | BNM 1.28 |
| `ibs_compliance_req_1w_to_1m_1` | BNM 1.28 |
| `net_surplus_1w_to_1m_1` | BNM 1.28 |
| `compliance_req_le_3_days` | BNM 1.28 |
| `compliance_req_le_3_days_1` | BNM 1.28 |
| `net_surplus_le_3_days` | BNM 1.28 |
| `compliance_req_3d_to_1m` | BNM 1.28 |
| `compliance_req_3d_to_1m_1` | BNM 1.28 |
| `net_surplus_3d_to_1m` | BNM 1.28 |

---

### `liquidity_coverage_ratio`
**Source:** `m_1_28a_liquidity_coverage_ratio` (BNM **1.28a** — Liquidity Coverage Ratio)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.28a `[key]` |
| `frequency` | BNM 1.28a `[key]` |
| `lcr` | BNM 1.28a |
| `hqla_stock` | BNM 1.28a |
| `net_cash_outflows` | BNM 1.28a |
| `cb_lcr` | BNM 1.28a |
| `cb_hqla_stock` | BNM 1.28a |
| `cb_net_cash_outflows` | BNM 1.28a |
| `ibs_lcr` | BNM 1.28a |
| `ibs_hqla_stock` | BNM 1.28a |
| `ibs_net_cash_outflows` | BNM 1.28a |
| `inv_banks_lcr` | BNM 1.28a |
| `inv_banks_hqla_stock` | BNM 1.28a |
| `inv_banks_net_cash_outflows` | BNM 1.28a |

---

## Banking System — Balance Sheets

### `assets_capital_and_liabilities_banking_system`
**Source:** `s_banking_capital_liabilities` — STITCH of:
- BNM **1.9** — Banking System: Statement of Capital and Liabilities (primary)
- BNM **1.9a** — Banking System: Capital and Liabilities (prev) `[rows]`

Column schema from BNM 1.9; historical rows from BNM 1.9a.

| Column | Source |
|--------|--------|
| `date` | BNM 1.9 `[key]` |
| `frequency` | BNM 1.9 `[key]` |
| `equities_and_liabilities` | BNM 1.9 |
| `total_equities` | BNM 1.9 |
| `deposits_under_the_new_investment_fund` | BNM 1.9 |
| `special_account` | BNM 1.9 |
| `domestic_banks_deposits_others` | BNM 1.9 |
| `residents_bank_negara_malaysia` | BNM 1.9 |
| `residents_commercial_banks` | BNM 1.9 |
| `residents_islamic_banks` | BNM 1.9 |
| `residents_investment_banks` | BNM 1.9 |
| `residents_other_banking_institutions` | BNM 1.9 |
| `non_residents` | BNM 1.9 |
| `investment_account_of_customers` | BNM 1.9 |
| `investment_account_due_to_designated_financial_institutions` | BNM 1.9 |
| `acceptances_payable` | BNM 1.9 |
| `residents` | BNM 1.9 |
| `bills_payable_non_residents` | BNM 1.9 |
| `other_liabilities` | BNM 1.9 |
| `bank_domestic_banks_total_equities_and_liabilities` | BNM 1.9 |
| `bank_foreign_banks_total_equities` | BNM 1.9 |
| `total_deposits_under_the_new_investment_fund` | BNM 1.9 |
| `total_deposits_special_account` | BNM 1.9 |
| `foreign_banks_deposits_others` | BNM 1.9 |
| `amount_due_to_designated_financial_institutions_residents_*` | BNM 1.9 |
| `total_investment_account_*` | BNM 1.9 |
| `bills_payable_residents` | BNM 1.9 |
| `total_liabilities_bills_payable_non_residents` | BNM 1.9 |
| `bills_payable_other_liabilities` | BNM 1.9 |
| `bank_foreign_banks_total_equities_and_liabilities` | BNM 1.9 |
| `rm_million_total_equities_and_liabilities` | BNM 1.9 |

---

### `assets_capital_and_liabilities_islamic_banking_system`
**Source:** `m_1_7_1_islamic_banking_assets` (BNM **1.7.1** — Islamic Banking System: Statement of Assets)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.7.1 `[key]` |
| `frequency` | BNM 1.7.1 `[key]` |
| `assets` | BNM 1.7.1 |
| `cash_and_cash_equivalents` | BNM 1.7.1 |
| `balances_in_current_account_with_bank_negara_malaysia` | BNM 1.7.1 |
| `other_deposits_placed_and_reverse_repos` | BNM 1.7.1 |
| `statutory_deposits_with_bnm` | BNM 1.7.1 |
| `bank_negara_malaysia` | BNM 1.7.1 |
| `commercial_banks` | BNM 1.7.1 |
| `islamic_banks` | BNM 1.7.1 |
| `investment_banks` | BNM 1.7.1 |
| `other_banking_institutions` | BNM 1.7.1 |
| `non_residents` | BNM 1.7.1 |
| `investment_account_due_from_designated_financial_institutions` | BNM 1.7.1 |
| `negotiable_instrument_deposits_held` | BNM 1.7.1 |
| `treasury_bills` | BNM 1.7.1 |
| `government_securities` | BNM 1.7.1 |
| `other_securities` | BNM 1.7.1 |
| `loans_and_advances` | BNM 1.7.1 |
| `property_plant_and_equipment` | BNM 1.7.1 |
| `other_assets` | BNM 1.7.1 |
| `total_assets` | BNM 1.7.1 |

---

## Banking System — Credit & Financing

### `credit_to_the_private_sector`
**Source:** `m_2_18_credit_to_private_sector` (BNM **2.18** — Credit to the Private Non-Financial Sector)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 2.18 `[key]` |
| `frequency` | BNM 2.18 `[key]` |
| `outstanding_rm_million` | BNM 2.18 |
| `of_which_household_a` | BNM 2.18 |
| `of_which_business_b` | BNM 2.18 |
| `outstanding_corporate_bonds_issued_by_private_non_financial_sector` | BNM 2.18 |
| `total_credit_to_private_non_financial_sector` | BNM 2.18 |
| `credit_to_businesses` | BNM 2.18 |
| `annual_growth` | BNM 2.18 |
| `outstanding_loans_to_the_private_non_financial_sector_of_which_household_a` | BNM 2.18 |
| `outstanding_loans_to_the_private_non_financial_sector_of_which_business_b` | BNM 2.18 |
| `outstanding_corporate_bonds_issued_by_private_non_financial_sector_1` | BNM 2.18 |
| `total_credit_to_private_non_financial_sector_1` | BNM 2.18 |
| `credit_to_businesses_1` | BNM 2.18 |

---

### `msme_loan_and_financing_by_sector`
**Source:** `m_1_33_sme_loans_by_sector` (BNM **1.33** — Financial Institution: SME Loan/Financing by Sector)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.33 `[key]` |
| `frequency` | BNM 1.33 `[key]` |
| `sector` | BNM 1.33 `[key]` |
| `agriculture_forestry_and_fishing` | BNM 1.33 |
| `mining_and_quarrying` | BNM 1.33 |
| `manufacturing` | BNM 1.33 |
| `electricity_gas_steam_and_air_conditioning_supply` | BNM 1.33 |
| `water_supply_sewerage_waste_management_and_remediation_activities` | BNM 1.33 |
| `construction` | BNM 1.33 |
| `wholesale_retail_motor_trade_total` | BNM 1.33 |
| `wholesale_trade_except_of_motor_vehicles_and_motorcycles` | BNM 1.33 |
| `retail_trade_except_of_motor_vehicles_and_motorcycles` | BNM 1.33 |
| `wholesale_retail_motor_trade_others` | BNM 1.33 |
| `accommodation_and_food_service_activities` | BNM 1.33 |
| `transportation_storage` | BNM 1.33 |
| `information_communication` | BNM 1.33 |
| `financial_and_insurance_takaful_activities` | BNM 1.33 |
| `real_estate_activities` | BNM 1.33 |
| `professional_scientific_and_technical_activities` | BNM 1.33 |
| `administrative_and_support_service_activities` | BNM 1.33 |
| `education_health_and_others` | BNM 1.33 |
| `other_sector` | BNM 1.33 |
| `total_outstanding_loan_financing` | BNM 1.33 |

---

### `msme_loan_and_financing_by_purpose`
**Source:** `m_1_34_sme_loans_by_purpose` (BNM **1.34** — Financial Institutions: SME Loan/Financing by Purpose)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.34 `[key]` |
| `frequency` | BNM 1.34 `[key]` |
| `purpose` | BNM 1.34 `[key]` |
| `purchase_of_securities` | BNM 1.34 |
| `fixed_assets_non_property_total` | BNM 1.34 |
| `transport_vehicles_total` | BNM 1.34 |
| `purchase_of_passenger_cars` | BNM 1.34 |
| `transport_vehicles_others` | BNM 1.34 |
| `fixed_assets_non_property_others` | BNM 1.34 |
| `purchase_of_residential_property` | BNM 1.34 |
| `purchase_of_non_residential_property` | BNM 1.34 |
| `construction` | BNM 1.34 |
| `working_capital` | BNM 1.34 |
| `other_purposes` | BNM 1.34 |
| `financing` | BNM 1.34 |
| `memo_item_credit_card` | BNM 1.34 |

---

### `msme_loan_and_financing_by_msme_size`
**Source:** `m_1_35_sme_loans_by_size` (BNM **1.35** — Financial Institution: SME Loan/Financing by SME Size)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.35 `[key]` |
| `frequency` | BNM 1.35 `[key]` |
| `sme_size` | BNM 1.35 `[key]` |
| `individual_for_business` | BNM 1.35 |
| `micro` | BNM 1.35 |
| `small` | BNM 1.35 |
| `medium` | BNM 1.35 |
| `financing` | BNM 1.35 |

---

### `msme_loan_and_financing_by_loan_size`
**Source:** `m_1_36_sme_loans_by_loan_size` (BNM **1.36** — Financial Institution: SME Loan/Financing by Loan Size)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.36 `[key]` |
| `frequency` | BNM 1.36 `[key]` |
| `loan_size` | BNM 1.36 `[key]` |
| `rm` | BNM 1.36 |
| `rm1_million` | BNM 1.36 |
| `rm1_rm5_million` | BNM 1.36 |
| `rm5_million` | BNM 1.36 |
| `total_outstanding_loan_financing` | BNM 1.36 |

---

## Banking System — Deposits & Funding

### `banking_deposits_by_type`
**Source:** `m_1_24_total_deposits_by_type` (BNM **1.24** — Banking System: Total Deposits by Type)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.24 `[key]` |
| `frequency` | BNM 1.24 `[key]` |
| `demand_deposits` | BNM 1.24 |
| `fixed_investment_deposits` | BNM 1.24 |
| `saving_deposits` | BNM 1.24 |
| `nids_issued` | BNM 1.24 |
| `foreign_currency_deposit` | BNM 1.24 |
| `tawarruq_fixed_deposits` | BNM 1.24 |
| `others_deposit_accepted` | BNM 1.24 |
| `total_deposits` | BNM 1.24 |
| `repurchase_agreements` | BNM 1.24 |
| `total_deposits_repos` | BNM 1.24 |

---

### `banking_deposits_by_holder`
**Source:** `m_1_25_total_deposits_by_holder` (BNM **1.25** — Banking System: Total Deposits by Holder)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.25 `[key]` |
| `frequency` | BNM 1.25 `[key]` |
| `federal_government` | BNM 1.25 |
| `state_government` | BNM 1.25 |
| `statutory_agency` | BNM 1.25 |
| `financial_institution` | BNM 1.25 |
| `business_enterprises` | BNM 1.25 |
| `individuals` | BNM 1.25 |
| `others` | BNM 1.25 |
| `total` | BNM 1.25 |

---

### `islamic_banking_deposits_by_type`
**Source:** `m_1_24_1_islamic_deposits_by_type` (BNM **1.24.1** — Islamic Banking: Deposits by Type)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.24.1 `[key]` |
| `frequency` | BNM 1.24.1 `[key]` |
| `ibs_deposits_by_type` | BNM 1.24.1 `[key]` |
| `rm_special_investment_deposits` | BNM 1.24.1 |
| `fx_special_investment_deposits` | BNM 1.24.1 |
| `rm_general_investment_deposits` | BNM 1.24.1 |
| `fx_general_investment_deposits` | BNM 1.24.1 |
| `rm_demand_deposits` | BNM 1.24.1 |
| `fx_demand_deposits` | BNM 1.24.1 |
| `rm_saving_deposits` | BNM 1.24.1 |
| `fx_saving_deposits` | BNM 1.24.1 |
| `nids_issued` | BNM 1.24.1 |
| `rm_tawarruq_fixed_deposits` | BNM 1.24.1 |
| `fx_tawarruq_fixed_deposits` | BNM 1.24.1 |
| `rm_others_deposit` | BNM 1.24.1 |
| `fx_others_deposit` | BNM 1.24.1 |
| `total_deposits` | BNM 1.24.1 |

---

### `islamic_banking_deposits_by_holder`
**Source:** `m_1_24_2_islamic_deposits_by_type_holder` (BNM **1.24.2** — Islamic Banking: Deposits by Type & Holder)  
**Processing:** Direct (the stitch `s_islamic_deposits_by_type_holder` is used in `h_7` domain table only; this export draws directly from the current edition)

> This dataset has ~95 columns covering every combination of deposit type (Special Investment, General Investment, Demand, Saving, NIDs, Tawarruq, Others) × currency (RM / FX) × holder (Federal Gov, State Gov, Statutory, Financial Inst, Business, Individuals, Others). The `ibs_deposits_by_type_holder` column is the row-level dimension key.

All columns sourced from **BNM 1.24.2**.

---

## Banking System — Payments

### `credit_card_operations`
**Source:** `m_1_30_credit_card_operations` (BNM **1.30** — Credit Card Operations in Malaysia)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.30 `[key]` |
| `frequency` | BNM 1.30 `[key]` |
| `no_of_card_transactions` | BNM 1.30 |
| `in_malaysia_local_cardholders` | BNM 1.30 |
| `in_malaysia_foreign_cardholders` | BNM 1.30 |
| `abroad_local_cardholders` | BNM 1.30 |
| `total_cash_advances_in_malaysia_local` | BNM 1.30 |
| `total_cash_advances_in_malaysia_foreign` | BNM 1.30 |
| `total_cash_advances_abroad_local` | BNM 1.30 |
| `principal_cards` | BNM 1.30 |
| `supplementary_cards` | BNM 1.30 |
| `credit_line_extended` | BNM 1.30 |
| `current_balances` | BNM 1.30 |
| `past_due_3_months` | BNM 1.30 |
| `past_due_3_to_6_months` | BNM 1.30 |
| `past_due_6_months` | BNM 1.30 |

---

### `debit_card_transactions`
**Source:** `m_1_30_1_debit_card_transactions` (BNM **1.30.1** — Debit Card Transactions)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.30.1 `[key]` |
| `frequency` | BNM 1.30.1 `[key]` |
| `no_of_card_transactions` | BNM 1.30.1 |
| `purchases_in_malaysia` | BNM 1.30.1 |
| `purchases_abroad` | BNM 1.30.1 |
| `pos_cash_withdrawals_in_malaysia` | BNM 1.30.1 |
| `pos_cash_withdrawals_abroad` | BNM 1.30.1 |
| `fund_transfer_in_malaysia` | BNM 1.30.1 |
| `atm_cash_withdrawals_in_malaysia` | BNM 1.30.1 |
| `abroad` | BNM 1.30.1 |

---

### `payment_instruments_cheques`
**Source:** `s_cheques_statistics` — STITCH of:
- BNM **3.5.14** — Selected Statistics on Cheques Cleared and Returned (primary)
- BNM **3.5.14a** — Selected Statistics on Dishonoured Cheques (prev) `[rows]`

Column schema from BNM 3.5.14; historical rows from BNM 3.5.14a.

| Column | Source |
|--------|--------|
| `date` | BNM 3.5.14 `[key]` |
| `frequency` | BNM 3.5.14 `[key]` |
| `no_million` | BNM 3.5.14 |
| `rm_billion` | BNM 3.5.14 |
| `no_000_no_000` | BNM 3.5.14 |
| `rm_milion_rm_million` | BNM 3.5.14 |
| `of_which_returned_cheques_due_to_insufficient_funds_no_000_no_000` | BNM 3.5.14 |
| `of_which_returned_cheques_due_to_insufficient_funds_rm_milion_rm_million` | BNM 3.5.14 |

---

## Banking System — Asset Quality & Provisions

### `mfrs9_financing`
**Source:** `m_1_21_loans_mfrs9_stages_provisions` (BNM **1.21** — Banking System: Loans by MFRS 9 Stages and Provisions)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.21 `[key]` |
| `frequency` | BNM 1.21 `[key]` |
| `industry` | BNM 1.21 `[key]` |
| `total_loan_financing` | BNM 1.21 |
| `stage_1_ecl` | BNM 1.21 |
| `stage_2_ecl_not_impaired` | BNM 1.21 |
| `stage_3_ecl_impaired` | BNM 1.21 |
| `total_provisions` | BNM 1.21 |
| `gross_impaired_ratio` | BNM 1.21 |
| `net_impaired_ratio` | BNM 1.21 |

---

### `mfrs9_financing_islamic`
**Source:** `s_islamic_financing_mfrs9_stages` — STITCH of:
- BNM **1.21.1** — Islamic Banking: Financing by MFRS 9 Stages and Provisions (primary)
- BNM **1.21.1a** — Islamic Banking: NPL/Impaired and Provisions (prev) `[rows]`
- BNM **1.21.1b** — Islamic Banking: Impaired Financing and Provisions (prev2) `[rows]`
- BNM **1.21.1c** — Islamic Banking: Impaired Financing and Provisions (prev3) `[rows]`
- BNM **1.21.1d** — Islamic Banking: Impaired Financing and Provisions (prev4) `[rows]`

Column schema from BNM 1.21.1; 4 historical editions fill earlier rows.

| Column | Source |
|--------|--------|
| `date` | BNM 1.21.1 `[key]` |
| `frequency` | BNM 1.21.1 `[key]` |
| `industry` | BNM 1.21.1 `[key]` |
| `total_financing` | BNM 1.21.1 |
| `stage_1_ecl` | BNM 1.21.1 |
| `stage_2_ecl_not_impaired` | BNM 1.21.1 |
| `stage_3_ecl_impaired` | BNM 1.21.1 |
| `total_provisions` | BNM 1.21.1 |
| `gross_impaired_ratio` | BNM 1.21.1 |
| `net_impaired_ratio` | BNM 1.21.1 |

---

### `impaired_banking_loan_and_financing_by_purpose`
**Source:** `s_impaired_loans_by_purpose` — STITCH of:
- BNM **1.22** — Banking System: Impaired Loan/Financing by Purpose (primary)
- BNM **1.22c** — Banking System: Impaired Loans by Purpose (prev) `[rows]`

| Column | Source |
|--------|--------|
| `date` | BNM 1.22 `[key]` |
| `frequency` | BNM 1.22 `[key]` |
| `purpose` | BNM 1.22 `[key]` |
| `securities` | BNM 1.22 |
| `fixed_assets_non_property_total` | BNM 1.22 |
| `transport_vehicles_total` | BNM 1.22 |
| `passenger_cars` | BNM 1.22 |
| `transport_vehicles_others` | BNM 1.22 |
| `fixed_assets_non_property_others` | BNM 1.22 |
| `residential_property_total` | BNM 1.22 |
| `cost_up_to_300k` | BNM 1.22 |
| `cost_300k_to_500k` | BNM 1.22 |
| `cost_500k_to_1m` | BNM 1.22 |
| `cost_above_1m` | BNM 1.22 |
| `non_residential_property_total` | BNM 1.22 |
| `industrial_buildings_factories` | BNM 1.22 |
| `land_only` | BNM 1.22 |
| `commercial_complexes` | BNM 1.22 |
| `shophouses_shoplots` | BNM 1.22 |
| `other_non_residential_property` | BNM 1.22 |
| `personal_uses_total` | BNM 1.22 |
| `consumer_durable_goods` | BNM 1.22 |
| `personal_uses_others` | BNM 1.22 |
| `credit_card` | BNM 1.22 |
| `construction` | BNM 1.22 |
| `working_capital` | BNM 1.22 |
| `other_purposes` | BNM 1.22 |
| `total_impaired` | BNM 1.22 |

---

### `impaired_banking_loan_and_financing_by_sector`
**Source:** `s_npl_by_sector` — STITCH of:
- BNM **1.23a** — Banking System: NPL/Impaired Loans by Sector (prev) — this is the primary since no current edition exists
- BNM **1.23b** — Banking System: NPL/Impaired Loans by Sector (prev2) `[rows]`

| Column | Source |
|--------|--------|
| `date` | BNM 1.23a `[key]` |
| `frequency` | BNM 1.23a `[key]` |
| `sector` | BNM 1.23a `[key]` |
| `primary_agriculture` | BNM 1.23a |
| `mining_quarrying` | BNM 1.23a |
| `manufacturing_agro_based` | BNM 1.23a |
| `electricity_gas_water` | BNM 1.23a |
| `wholesale_retail_restaurants_hotels` | BNM 1.23a |
| `construction` | BNM 1.23a |
| `transport_storage_communication` | BNM 1.23a |
| `finance_insurance_business` | BNM 1.23a |
| `education_health_others` | BNM 1.23a |
| `household_sector` | BNM 1.23a |
| `other_sector_nec` | BNM 1.23a |
| `impaired_loans` | BNM 1.23a |

---

### `impaired_banking_loan_and_financing_by_type`
**Source:** `m_1_23_6_impaired_loans_by_type` (BNM **1.23.6** — Banking System: Impaired Loan/Financing by Type)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.23.6 `[key]` |
| `frequency` | BNM 1.23.6 `[key]` |
| `type` | BNM 1.23.6 `[key]` |
| `overdraft_facilities` | BNM 1.23.6 |
| `term_loans_total` | BNM 1.23.6 |
| `hire_purchase_receivables_total` | BNM 1.23.6 |
| `passenger_cars` | BNM 1.23.6 |
| `hire_purchase_receivables_others` | BNM 1.23.6 |
| `leasing_receivables` | BNM 1.23.6 |
| `block_discounting_receivables` | BNM 1.23.6 |
| `bridging_loans` | BNM 1.23.6 |
| `factoring_receivables` | BNM 1.23.6 |
| `personal_loans` | BNM 1.23.6 |
| `housing_loans` | BNM 1.23.6 |
| `other_term_loans` | BNM 1.23.6 |
| `trade_bills` | BNM 1.23.6 |
| `trust_receipts` | BNM 1.23.6 |
| `revolving_credit` | BNM 1.23.6 |
| `credit_charge_card` | BNM 1.23.6 |
| `foreign_currency_loans` | BNM 1.23.6 |
| `term_loans_others` | BNM 1.23.6 |
| `total_impaired` | BNM 1.23.6 |

---

### `impaired_sme_loan_financing_by_sector`
**Source:** `m_1_33_5_sme_impaired_loans_by_sector` (BNM **1.33.5** — Financial Institution: Impaired SME Loan/Financing by Sector)  
**Processing:** Direct

All sector breakdown columns sourced from **BNM 1.33.5** (same sector schema as `msme_loan_and_financing_by_sector`, plus a `financing` total).

---

### `impaired_sme_loan_financing_by_sme_size`
**Source:** `m_1_35_3_sme_impaired_loans_by_size` (BNM **1.35.3** — Financial Institution: Impaired SME Loans by Size)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 1.35.3 `[key]` |
| `frequency` | BNM 1.35.3 `[key]` |
| `sme_size` | BNM 1.35.3 `[key]` |
| `individual_for_business` | BNM 1.35.3 |
| `micro` | BNM 1.35.3 |
| `small` | BNM 1.35.3 |
| `medium` | BNM 1.35.3 |
| `financing` | BNM 1.35.3 |

---

## Financial Markets — Interest Rates

### `monthly_interest_rates`
### `annual_interest_rates`
**Source:** `s_interest_rates_banking` — STITCH of:
- BNM **2.1** — Interest Rates: Banking Institutions (primary)
- BNM **2.1a** — Interest Rates: Banking Institutions (prev) `[rows]`

Filtered by `frequency = 'Monthly'` / `'Annual'` respectively. Both outputs share identical columns.

| Column | Source |
|--------|--------|
| `date` | BNM 2.1 `[key]` |
| `frequency` | BNM 2.1 `[key]` |
| `interest_rates_banking_institutions` | BNM 2.1 |
| `fixed_rates_period_in_months` | BNM 2.1 |
| `fixed_rates_period_in_months_1` | BNM 2.1 |
| `commercial_banks_fixed_rates_period_in_months` | BNM 2.1 |
| `commercial_banks_fixed_deposit_rates` | BNM 2.1 |
| `commercial_banks_fixed_deposit_rates_1` | BNM 2.1 |
| `weighted_average_fixed_rates_period_in_months` | BNM 2.1 |
| `weighted_average_fixed_rates_period_in_months_1` | BNM 2.1 |
| `commercial_banks_weighted_average_fixed_rates_period_in_months` | BNM 2.1 |
| `commercial_banks_weighted_avg_fixed_deposit_rates` | BNM 2.1 |
| `commercial_banks_weighted_avg_fixed_deposit_rates_1` | BNM 2.1 |
| `savings_rate` | BNM 2.1 |
| `weighted_average_savings_rate` | BNM 2.1 |
| `base_rate2_br` | BNM 2.1 |
| `weighted_average_br` | BNM 2.1 |
| `base_lending_rate_blr` | BNM 2.1 |
| `weighted_average_blr` | BNM 2.1 |
| `average_lending_rate_alr_on_outstanding_loans` | BNM 2.1 |
| `weighted_alr_on_outstanding_loans` | BNM 2.1 |
| `investment_banks_fixed_rates_period_in_months` | BNM 2.1 |
| `investment_banks_fixed_deposit_rates` | BNM 2.1 |
| `investment_banks_fixed_deposit_rates_1` | BNM 2.1 |
| `investment_banks_fixed_deposit_rates_1_1` | BNM 2.1 |
| `investment_banks_fixed_deposit_rates_2` | BNM 2.1 |
| `average_lending_rate_on_outstanding_loans` | BNM 2.1 |

---

## Financial Markets — Exchange Rates

### `daily_exchange_rates`
**Source:** `m_2_6_1_exchange_rates_myr_daily` (BNM **2.6.1** — Exchange Rates: Malaysian Ringgit (Daily))  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 2.6.1 `[key]` |
| `frequency` | BNM 2.6.1 `[key]` |
| `period_1` | BNM 2.6.1 |
| `june` | BNM 2.6.1 |
| `sdr` | BNM 2.6.1 |
| `end_of_period` | BNM 2.6.1 |
| `gbp` | BNM 2.6.1 |
| `eur` | BNM 2.6.1 |
| `sf` | BNM 2.6.1 |
| `100_hkd` | BNM 2.6.1 |
| `100_jpy` | BNM 2.6.1 |
| `cny` | BNM 2.6.1 |
| `sgd` | BNM 2.6.1 |
| `100_idr` | BNM 2.6.1 |
| `100_thb` | BNM 2.6.1 |

---

### `monthly_exchange_rates`
**Source:** `m_2_6_exchange_rates_myr` (BNM **2.6** — Exchange Rates: Malaysian Ringgit (Monthly))  
**Processing:** Direct — filtered by `frequency = 'Monthly'`

| Column | Source |
|--------|--------|
| `date` | BNM 2.6 `[key]` |
| `frequency` | BNM 2.6 `[key]` |
| `exchange_rates_malaysian_ringgit` | BNM 2.6 |
| `end_of_period` | BNM 2.6 |
| `rm_unit_of_usd` | BNM 2.6 |
| `rm_unit_of_gbp` | BNM 2.6 |
| `rm_unit_of_euro` | BNM 2.6 |
| `rm_unit_of_100_sf` | BNM 2.6 |
| `rm_unit_of_100_hkd` | BNM 2.6 |
| `rm_unit_of_100_jpy` | BNM 2.6 |
| `rm_unit_of_cny` | BNM 2.6 |
| `rm_unit_of_sgd` | BNM 2.6 |
| `rm_unit_of_100_idr` | BNM 2.6 |
| `rm_unit_of_100_thb` | BNM 2.6 |
| `average_for_period` | BNM 2.6 |
| `exchange_rates_malaysian_ringgit_rm_unit_of_*` (×10) | BNM 2.6 |

---

## Financial Markets — Money Market Activity

### `interbank_money_market_transaction_volume`
**Source:** `m_2_7_interbank_money_market_volume` (BNM **2.7** — Volume of Transaction in Interbank Money Market)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 2.7 `[key]` |
| `frequency` | BNM 2.7 `[key]` |
| `of_transactions_in_interbank_money_market` | BNM 2.7 |
| `overnight` through `1_year` (tenor buckets) | BNM 2.7 |
| `bank_of_transactions_in_interbank_money_market_bank_interbank_others` | BNM 2.7 |
| `sub_total` | BNM 2.7 |
| `malaysian_government_securities` | BNM 2.7 |
| `bonds` / `cagamas_bonds` / `malaysian_treasury_bills` / `bank_negara_bills` | BNM 2.7 |
| `cagamas_notes` / `negotiable_instrument_of` / `banker_s_acceptance` | BNM 2.7 |
| `money_market_instrument_sub_total` | BNM 2.7 |
| `total` | BNM 2.7 |

---

### `kl_foreign_exchange_market_interbank_transactions_volume`
**Source:** `m_2_8_kl_fx_market_volume` (BNM **2.8** — Volume of Interbank Transactions in KL FX Market)  
**Processing:** Direct

All currency-pair spot/swap columns (USD/RM, USD/SGD, USD/JPY, GBP/USD, plus RM-million equivalents) sourced from **BNM 2.8**.

---

### `conventional_and_islamic_money_market_turnover`
**Source:** `m_2_14_money_market_turnover` (BNM **2.14** — Turnover of Conventional and Islamic Money Market)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 2.14 `[key]` |
| `frequency` | BNM 2.14 `[key]` |
| `bank_interbank` | BNM 2.14 |
| `corporate` | BNM 2.14 |
| `banker_s_acceptance_bank_interbank` | BNM 2.14 |
| `banker_s_acceptance_corporate` | BNM 2.14 |
| `negotiable_instruments_of_deposit_interbank` | BNM 2.14 |
| `negotiable_instruments_of_deposit_corporate` | BNM 2.14 |
| `deposits_bank_interbank` | BNM 2.14 |
| `deposits_corporate` | BNM 2.14 |
| `commodity_murabahah_deposits_bank_interbank` | BNM 2.14 |
| `commodity_murabahah_deposits_corporate` | BNM 2.14 |
| `wakalah_deposits_bank_interbank` | BNM 2.14 |
| `wakalah_deposits_corporate` | BNM 2.14 |
| `other_bank_interbank` | BNM 2.14 |
| `other_corporate` | BNM 2.14 |
| `islamic_bankers_acceptance_bank_interbank` | BNM 2.14 |
| `islamic_bankers_acceptance_corporate` | BNM 2.14 |
| `islamic_negotiable_instruments_of_deposit_interbank` | BNM 2.14 |
| `rm_million_equivalent_corporate` | BNM 2.14 |

---

### `foreign_currency_market_transactions_turnover`
**Source:** `m_2_17_fx_market_turnover` (BNM **2.17** — Turnover of Foreign Currency Market Transactions)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 2.17 `[key]` |
| `frequency` | BNM 2.17 `[key]` |
| `fx_spot` | BNM 2.17 |
| `fx_swap` | BNM 2.17 |
| `fx_forward` | BNM 2.17 |
| `fx_options` | BNM 2.17 |

---

## Financial Markets — Bond & Sukuk

### `corporate_bond_and_sukuk_issues`
**Source:** `m_2_11_corporate_bond_sukuk_new_issues` (BNM **2.11** — New Issues of Corporate Bond and/or Sukuk)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 2.11 `[key]` |
| `frequency` | BNM 2.11 `[key]` |
| `agriculture_foresty_and_fishing` | BNM 2.11 |
| `construction` | BNM 2.11 |
| `electricity_gas_and_water` | BNM 2.11 |
| `finance_insurance_real_estate_and_business_services` | BNM 2.11 |
| `government_and_other_services` | BNM 2.11 |
| `manufacturing` | BNM 2.11 |
| `mining_and_quarrying` | BNM 2.11 |
| `transport_storage_and_communications` | BNM 2.11 |
| `wholesale_retail_trade_hotels_and_restaurants` | BNM 2.11 |
| `total_new_issues` | BNM 2.11 |

---

### `debt_securities_and_sukuk_turnover`
**Source:** `m_2_16_debt_securities_sukuk_turnover` (BNM **2.16** — Turnover of Debt Securities and Sukuk)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 2.16 `[key]` |
| `frequency` | BNM 2.16 `[key]` |
| `turnover_of_debt_securities_and_sukuk` | BNM 2.16 |
| `bank_negara_monetary_note` | BNM 2.16 |
| `malaysian_treasury_bills` | BNM 2.16 |
| `malaysian_government_securities` | BNM 2.16 |
| `bank_negara_monetary_note_islamic` | BNM 2.16 |
| `malaysian_islamic_treasury_bills` | BNM 2.16 |
| `government_investment_issues` | BNM 2.16 |
| `government_housing_sukuk` | BNM 2.16 |
| `private_sector_conventional_total` | BNM 2.16 |
| `private_sector_sukuk_total` | BNM 2.16 |
| `total_turnover` | BNM 2.16 |

---

### `foreign_holdings_in_debt_securities_and_sukuk`
**Source:** `m_3_2_rentas_foreign_holdings` (BNM **3.2** — RENTAS: Foreign Holdings in Debt Securities and Sukuk)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 3.2 `[key]` |
| `frequency` | BNM 3.2 `[key]` |
| `rentas_foreign_holdings_in_debt_securities_and_sukuk` | BNM 3.2 |
| `bank_negara_monetary_note` | BNM 3.2 |
| `malaysian_treasury_bills` | BNM 3.2 |
| `malaysian_government_securities` | BNM 3.2 |
| `bank_negara_monetary_note_islamic` | BNM 3.2 |
| `malaysian_islamic_treasury_bills` | BNM 3.2 |
| `bank_negara_malaysia_sukuk_ijarah` | BNM 3.2 |
| `malaysian_government_investment_issues` | BNM 3.2 |
| `government_housing_sukuk` | BNM 3.2 |
| `corporate_bonds` | BNM 3.2 |
| `sukuk` | BNM 3.2 |
| `denominated_debt_securities` | BNM 3.2 |
| `denominated_debt_securities_1` | BNM 3.2 |

---

## Financial Markets — Derivatives

### `derivatives_transactions_turnover`
**Source:** `m_2_15_derivatives_turnover` (BNM **2.15** — Turnover of Derivatives Transactions)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 2.15 `[key]` |
| `frequency` | BNM 2.15 `[key]` |
| `warrants` | BNM 2.15 |
| `options` | BNM 2.15 |
| `klibor_futures` | BNM 2.15 |
| `swap` | BNM 2.15 |
| `interest_rate_related_options` | BNM 2.15 |
| `futures` | BNM 2.15 |
| `credit_default_swap` | BNM 2.15 |
| `derivatives_turnover_others` | BNM 2.15 |
| `profit_rate_swap` | BNM 2.15 |

---

## Financial Markets — Capital Raising

### `public_sector_capital_raise`
**Source:** `m_2_9_capital_market_public_sector` (BNM **2.9** — Funds Raised in Capital Market by Public Sector)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 2.9 `[key]` |
| `frequency` | BNM 2.9 `[key]` |
| `funds_raised_in_the_capital_market_by_public_sector` | BNM 2.9 |
| `malaysian_government_securities` | BNM 2.9 |
| `mgs_advanced_subscriptions` | BNM 2.9 |
| `bonds` | BNM 2.9 |
| `malaysian_government_investment_issues` | BNM 2.9 |
| `bon_savings_bonds` | BNM 2.9 |
| `sukuk_government_housing_sukuk` | BNM 2.9 |
| `new_issues_of_debt_securities` | BNM 2.9 |
| `mgs` / `kb` / `mgii` (redemptions) | BNM 2.9 |
| `redemptions_bon_savings_bonds` | BNM 2.9 |
| `redemptions_sukuk_government_housing_sukuk` | BNM 2.9 |
| `less_government_holdings` | BNM 2.9 |
| `net_funds_raised_by_the_public_sector` | BNM 2.9 |

---

### `private_sector_capital_raise`
**Source:** `m_2_10_capital_market_private_sector` (BNM **2.10** — Funds Raised in Capital Market by Private Sector)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 2.10 `[key]` |
| `frequency` | BNM 2.10 `[key]` |
| `initial_public_offers` | BNM 2.10 |
| `rights_issues` | BNM 2.10 |
| `restricted_offer_for_sale` | BNM 2.10 |
| `special_issues` | BNM 2.10 |
| `preference_shares` | BNM 2.10 |
| `warrants` | BNM 2.10 |
| `new_issues_of_shares_war_rants` | BNM 2.10 |
| `straight_bonds` | BNM 2.10 |
| `bonds_with_war_rants` | BNM 2.10 |
| `conver_tible_bonds` | BNM 2.10 |
| `islamic_bonds` | BNM 2.10 |
| `asset_backed_bonds` | BNM 2.10 |
| `medium_term_notes` | BNM 2.10 |
| `bon_cagamas_bonds` | BNM 2.10 |
| `new_issues_of_corporate_bond_and_or_sukuk` | BNM 2.10 |
| `corporate_bond_and_or_sukuk` | BNM 2.10 |
| `redemptions_bon_cagamas_bonds` | BNM 2.10 |
| `net_issues_of_corporate_bond_and_or_sukuk` | BNM 2.10 |
| `net_funds_raised_by_the_private_sector` | BNM 2.10 |

---

## Insurance & Takaful — Balance Sheets

### `insurance_assets_and_liabilities`
**Source:** `m_4_2_insurance_assets_liabilities` (BNM **4.2** — Insurance: Assets and Liabilities)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 4.2 `[key]` |
| `frequency` | BNM 4.2 `[key]` |
| `life_direct_insurers` | BNM 4.2 |
| `paid_up_capital` | BNM 4.2 |
| `premium_share_premium_account` | BNM 4.2 |
| `reserves` | BNM 4.2 |
| `retained_profit_loss` | BNM 4.2 |
| `shareholders_equity_total` | BNM 4.2 |
| `assets_revaluation_reserves` | BNM 4.2 |
| `other_liabilities` | BNM 4.2 |
| `total_liabilities` | BNM 4.2 |
| `property_plant_and_equipment` | BNM 4.2 |
| `loans` | BNM 4.2 |
| `malaysian_government_papers_guaranteed_loans` | BNM 4.2 |
| `corporate_debt_securities` | BNM 4.2 |
| `other_investments` | BNM 4.2 |
| `investments_total` | BNM 4.2 |
| `investment_properties` | BNM 4.2 |
| `cash_and_deposits` | BNM 4.2 |
| `other_assets` | BNM 4.2 |
| `foreign_assets` | BNM 4.2 |
| `total_assets` | BNM 4.2 |

---

### `takaful_assets_and_liabilities`
**Source:** `m_4_3_takaful_assets_liabilities` (BNM **4.3** — Takaful: Assets and Liabilities)  
**Processing:** Direct

Columns mirror the insurance table but for Takaful operators (Islamic finance equivalents: `government_islamic_papers`, `islam_islamic_private_debt_securities_and_equities`, `financing`). All sourced from **BNM 4.3**.

---

### `insurance_capital_adequacy_ratio`
**Source:** `m_4_4_insurance_capital_adequacy` (BNM **4.4** — Insurance: Capital Adequacy Ratio)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 4.4 `[key]` |
| `frequency` | BNM 4.4 `[key]` |
| `life_insurance_companies_total_capital_available` | BNM 4.4 |
| `life_insurance_companies_total_capital_required` | BNM 4.4 |
| `life_insurance_companies_capital_adequacy_ratio` | BNM 4.4 |
| `am_general_insurance_companies_total_capital_available` | BNM 4.4 |
| `am_general_insurance_companies_total_capital_required` | BNM 4.4 |
| `am_general_insurance_companies_capital_adequacy_ratio` | BNM 4.4 |
| `total_capital_available` | BNM 4.4 |
| `total_capital_required` | BNM 4.4 |
| `composite2_insurance_companies_capital_adequacy_ratio` | BNM 4.4 |
| `total_capital_available_1` | BNM 4.4 |
| `total_capital_required_1` | BNM 4.4 |
| `rm_million_capital_adequacy_ratio` | BNM 4.4 |

---

### `takaful_capital_adequacy_ratio`
**Source:** `m_4_5_takaful_capital_adequacy` (BNM **4.5** — Takaful: Capital Adequacy Ratio)  
**Processing:** Direct

Equivalent CAR structure to insurance but for Takaful operators (Family, General, Composite, Consolidated Industry). All sourced from **BNM 4.5**.

---

## Insurance & Takaful — Life & Family

### `life_insurance_funds`
**Source:** `m_4_6_b_life_insurance_fund_assets` (BNM **4.6.b** — Life Insurance: Assets of Life Insurance Funds)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 4.6.b `[key]` |
| `frequency` | BNM 4.6.b `[key]` |
| `business_within_malaysia` | BNM 4.6.b |
| `malaysia_government_papers_guaranteed_loans` | BNM 4.6.b |
| `corporate_debt_securities` | BNM 4.6.b |
| `investments_others` | BNM 4.6.b |
| `investments_total` | BNM 4.6.b |
| `investment_properties` | BNM 4.6.b |
| `mortgages` | BNM 4.6.b |
| `policy` | BNM 4.6.b |
| `loans_others` | BNM 4.6.b |
| `loans_total` | BNM 4.6.b |
| `property_plant_and_equipment` | BNM 4.6.b |
| `other_assets` | BNM 4.6.b |
| `foreign_assets` | BNM 4.6.b |
| `rm_million_total` | BNM 4.6.b |

---

### `family_takaful_funds`
**Source:** `m_4_8_family_takaful_new_business` (BNM **4.8** — Family Takaful: New Business and Business in Force)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 4.8 `[key]` |
| `frequency` | BNM 4.8 `[key]` |
| `sijil_no_of_certificates_unit` | BNM 4.8 |
| `sum_participated_rm_million` | BNM 4.8 |
| `single` | BNM 4.8 |
| `annual` | BNM 4.8 |
| `total` | BNM 4.8 |
| `business_in_force_sijil_no_of_certificates_unit` | BNM 4.8 |
| `business_in_force_sum_participated_rm_million` | BNM 4.8 |
| `contributions` | BNM 4.8 |

---

## Insurance & Takaful — General Insurance & Takaful

### `general_insurance_funds`
**Source:** `m_4_7_b_general_insurance_fund_assets` (BNM **4.7.b** — General Insurance: Assets of General Insurance Funds)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 4.7.b `[key]` |
| `frequency` | BNM 4.7.b `[key]` |
| `business_within_malaysia` | BNM 4.7.b |
| `amount_due_from_clients_intermediaries_reinsurers` | BNM 4.7.b |
| `malaysia_government_papers_and_guaranteed_loans` | BNM 4.7.b |
| `corporate_debt_and_securities` | BNM 4.7.b |
| `others` | BNM 4.7.b |
| `investments_total` | BNM 4.7.b |
| `investment_properties` | BNM 4.7.b |
| `loans` | BNM 4.7.b |
| `property_plant_and_equipment` | BNM 4.7.b |
| `other_assets` | BNM 4.7.b |
| `foreign_assets` | BNM 4.7.b |
| `rm_million_total` | BNM 4.7.b |

---

### `general_insurance_reserves`
**Source:** `m_4_7_c_general_insurance_technical_reserves` (BNM **4.7.c** — General Insurance: Technical Reserves)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 4.7.c `[key]` |
| `frequency` | BNM 4.7.c `[key]` |
| `business_within_malaysia` | BNM 4.7.c |
| `premium_liabilities_premium_percentage_of_net_premium` | BNM 4.7.c |
| `claims_liabilities_rm_million` | BNM 4.7.c |
| `claims_liabilities_premium_percentage_of_net_premium` | BNM 4.7.c |
| `technical_reserves_rm_million` | BNM 4.7.c |
| `technical_reserves_premium_percentage_of_net_premium` | BNM 4.7.c |

---

### `general_insurance_premium`
**Source:** `m_4_7_general_insurance_premium` (BNM **4.7** — General Insurance: Premium Income)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 4.7 `[key]` |
| `frequency` | BNM 4.7 `[key]` |
| `business_within_malaysia` | BNM 4.7 |
| `premium_gross_direct_premiums` | BNM 4.7 |
| `premium_net_premiums` | BNM 4.7 |
| `retention_ratio` | BNM 4.7 |

---

## Institutions & Access — Employment

### `employment_hiring_and_separation_financial_sector`
**Source:** `m_3_5_12a_labour_market_financial_sector` (BNM **3.5.12a** — Labour Market Indicators for the Financial Services Sector)  
**Processing:** Direct

| Column | Source |
|--------|--------|
| `date` | BNM 3.5.12a `[key]` |
| `frequency` | BNM 3.5.12a `[key]` |
| `labour_market_indicators_for_the_financial_services_sector` | BNM 3.5.12a |
| `total_number_of_employees` | BNM 3.5.12a |
| `number_of_job_vacancies` | BNM 3.5.12a |
| `new_job_created` | BNM 3.5.12a |
| `new_hires_and_recalls` | BNM 3.5.12a |
| `labour_market_indicators_for_the_financial_services_sector_separations_total` | BNM 3.5.12a |
| `quits_and_resignation_except_retirement` | BNM 3.5.12a |
| `layoffs_and_discharges` | BNM 3.5.12a |
| `other_separations` | BNM 3.5.12a |
