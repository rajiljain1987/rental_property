import streamlit as st
import pandas as pd
import numpy as np
import json, os

SCENARIOS_FILE = "scenarios.json"

def load_all_scenarios():
    if os.path.exists(SCENARIOS_FILE):
        with open(SCENARIOS_FILE) as f:
            return json.load(f)
    return {}

def save_all_scenarios(data):
    with open(SCENARIOS_FILE, "w") as f:
        json.dump(data, f, indent=2)

st.set_page_config(page_title="Property Cash Flow Analyzer", layout="wide")
st.title("Property Cash Flow Analyzer")

# ==========================================
# SIDEBAR — COLLAPSIBLE SECTIONS
# ==========================================

# --- Scenario Manager ---
all_scenarios = load_all_scenarios()

with st.sidebar.expander("💾 Scenarios", expanded=True):
    scenario_names = list(all_scenarios.keys())

    # Load
    if scenario_names:
        load_name = st.selectbox("Load scenario", ["— select —"] + scenario_names, key="load_sel")
        if load_name != "— select —" and st.button("Load", key="btn_load"):
            for k, v in all_scenarios[load_name].items():
                st.session_state[k] = v
            st.success(f"Loaded: {load_name}")
            st.rerun()
    else:
        st.caption("No saved scenarios yet.")

    # Save
    save_name = st.text_input("Scenario name", placeholder="e.g. 123 Main St", key="save_name")
    if st.button("Save current inputs", key="btn_save"):
        if save_name.strip():
            snapshot = {
                "purchase_price": st.session_state.get("purchase_price", 800_000),
                "down_payment_pct": st.session_state.get("down_payment_pct", 25),
                "closing_costs": st.session_state.get("closing_costs", 24_000),
                "rehab_budget": st.session_state.get("rehab_budget", 40_000),
                "land_value_pct": st.session_state.get("land_value_pct", 20),
                "int_rate": st.session_state.get("int_rate", 6.5),
                "loan_term_yrs": st.session_state.get("loan_term_yrs", 30),
                "hold_years": st.session_state.get("hold_years", 7),
                "monthly_rent": st.session_state.get("monthly_rent", 7_500),
                "vacancy_rate": st.session_state.get("vacancy_rate", 5),
                "exp_taxes": st.session_state.get("exp_taxes", 9_600),
                "exp_utils": st.session_state.get("exp_utils", 3_000),
                "exp_ins": st.session_state.get("exp_ins", 1_800),
                "exp_hoa": st.session_state.get("exp_hoa", 0),
                "exp_mgmt_pct": st.session_state.get("exp_mgmt_pct", 8),
                "exp_other": st.session_state.get("exp_other", 3_600),
                "appreciation_rate": st.session_state.get("appreciation_rate", 3.0),
                "selling_costs_pct": st.session_state.get("selling_costs_pct", 5.0),
                "rent_growth": st.session_state.get("rent_growth", 3.0),
                "g_taxes": st.session_state.get("g_taxes", 2.0),
                "g_utils": st.session_state.get("g_utils", 3.0),
                "g_ins": st.session_state.get("g_ins", 4.0),
                "g_hoa": st.session_state.get("g_hoa", 0.0),
                "g_mgmt": st.session_state.get("g_mgmt", 3.0),
                "g_other": st.session_state.get("g_other", 2.5),
                "marginal_tax_rate": st.session_state.get("marginal_tax_rate", 35),
                "costseg_study_cost": st.session_state.get("costseg_study_cost", 2_000),
            }
            all_scenarios[save_name.strip()] = snapshot
            save_all_scenarios(all_scenarios)
            st.success(f"Saved: {save_name.strip()}")
        else:
            st.warning("Enter a scenario name first.")

    # Delete
    if scenario_names:
        del_name = st.selectbox("Delete scenario", ["— select —"] + scenario_names, key="del_sel")
        if del_name != "— select —" and st.button("Delete", key="btn_del"):
            del all_scenarios[del_name]
            save_all_scenarios(all_scenarios)
            st.success(f"Deleted: {del_name}")
            st.rerun()

def sv(key, default):
    """Get value from session state if loaded, else use default."""
    return st.session_state.get(key, default)

with st.sidebar.expander("🏢 Purchase & Financing", expanded=True):
    purchase_price   = st.number_input("Purchase Price ($)", value=sv("purchase_price", 800_000), step=25_000, key="purchase_price")
    down_payment_pct = st.slider("Down Payment (%)", min_value=10, max_value=40, value=sv("down_payment_pct", 25), key="down_payment_pct")
    closing_costs    = st.number_input("Closing Costs ($)", value=sv("closing_costs", int(purchase_price * 0.03)), step=1_000, key="closing_costs")
    rehab_budget     = st.number_input("Renovation Budget ($)", value=sv("rehab_budget", 40_000), step=5_000, key="rehab_budget")
    land_value_pct   = st.slider("Land Value (% of purchase)", min_value=5, max_value=50, value=sv("land_value_pct", 20), key="land_value_pct",
                                  help="Land is not depreciable; only the building portion qualifies.")
    int_rate         = st.number_input("Mortgage Rate (%)", min_value=0.0, max_value=20.0, value=sv("int_rate", 6.5), step=0.25, key="int_rate")
    loan_term_yrs    = st.selectbox("Loan Term (years)", [30, 20, 15], index=[30,20,15].index(sv("loan_term_yrs", 30)), key="loan_term_yrs")
    hold_years       = st.selectbox("Hold Period (years)", [5, 7, 10], index=[5,7,10].index(sv("hold_years", 7)), key="hold_years")

with st.sidebar.expander("💰 Income", expanded=True):
    monthly_rent = st.number_input("Monthly Gross Rent ($)", value=sv("monthly_rent", 7_500), step=250, key="monthly_rent")
    vacancy_rate = st.slider("Vacancy Rate (%)", min_value=0, max_value=15, value=sv("vacancy_rate", 5), key="vacancy_rate")

with st.sidebar.expander("📝 Annual Expenses", expanded=False):
    col1s, col2s = st.columns(2)
    with col1s:
        exp_taxes    = st.number_input("Property Taxes ($)", value=sv("exp_taxes", 9_600), step=500, key="exp_taxes")
        exp_utils    = st.number_input("Utilities ($)", value=sv("exp_utils", 3_000), step=250, key="exp_utils")
        exp_ins      = st.number_input("Insurance ($)", value=sv("exp_ins", 1_800), step=200, key="exp_ins")
    with col2s:
        exp_hoa      = st.number_input("HOA Fees ($)", value=sv("exp_hoa", 0), step=500, key="exp_hoa")
        exp_mgmt_pct = st.number_input("Mgmt Fee (%)", value=sv("exp_mgmt_pct", 8), step=1, key="exp_mgmt_pct")
        exp_other    = st.number_input("Maintenance ($)", value=sv("exp_other", 3_600), step=250, key="exp_other")

with st.sidebar.expander("📈 Future Expectations", expanded=False):
    st.markdown("**Property**")
    appreciation_rate = st.slider("Annual Appreciation (%)", 0.0, 10.0, sv("appreciation_rate", 3.0), 0.5, key="appreciation_rate")
    selling_costs_pct = st.slider("Selling Costs at Exit (%)", 1.0, 8.0, sv("selling_costs_pct", 5.0), 0.5, key="selling_costs_pct",
                                   help="Agent commissions, transfer taxes, legal fees, etc.")
    st.markdown("**Income**")
    rent_growth       = st.slider("Annual Rent Growth (%)", 0.0, 10.0, sv("rent_growth", 3.0), 0.5, key="rent_growth")
    st.markdown("**Expenses (%/yr)**")
    gc1, gc2 = st.columns(2)
    with gc1:
        g_taxes = st.number_input("Taxes",     value=sv("g_taxes", 2.0), step=0.5, key="g_taxes")
        g_utils = st.number_input("Utilities", value=sv("g_utils", 3.0), step=0.5, key="g_utils")
        g_ins   = st.number_input("Insurance", value=sv("g_ins",   4.0), step=0.5, key="g_ins")
    with gc2:
        g_hoa   = st.number_input("HOA",      value=sv("g_hoa",   0.0), step=0.5, key="g_hoa")
        g_mgmt  = st.number_input("Mgmt Fee", value=sv("g_mgmt",  3.0), step=0.5, key="g_mgmt")
        g_other = st.number_input("Maint",    value=sv("g_other", 2.5), step=0.5, key="g_other")

with st.sidebar.expander("🏗️ Cost Segregation", expanded=False):
    st.markdown("Accelerated depreciation via cost seg study.")
    marginal_tax_rate  = st.slider("Marginal Tax Rate (%)", 10, 50, sv("marginal_tax_rate", 35),
                                   help="Your combined federal + state marginal income tax rate.", key="marginal_tax_rate")
    costseg_study_cost = st.number_input("Cost Seg Study Cost ($)", value=sv("costseg_study_cost", 2_000), step=500, key="costseg_study_cost")
    enable_costseg     = st.checkbox("Apply cost segregation")
    costseg_year       = st.selectbox("Applied in Year", [1, 2], index=0) if enable_costseg else 1
    costseg_5yr_pct    = st.slider("5-yr property (% of building value)", 0, 30, 15,
                                    help="Typically electrical, plumbing fixtures, carpeting, etc.") if enable_costseg else 0
    costseg_15yr_pct   = st.slider("15-yr property (% of building value)", 0, 20, 10,
                                    help="Land improvements: parking, landscaping, fencing.") if enable_costseg else 0
    costseg_bonus_pct  = st.slider("Bonus depreciation (%)", 0, 100, 60,
                                    help="Federal bonus depreciation rate (e.g. 60% for 2024).") if enable_costseg else 0

# ==========================================
# CALCULATION ENGINE
# ==========================================

down_payment  = purchase_price * (down_payment_pct / 100)
loan_amount   = purchase_price - down_payment
total_cash_in = down_payment + closing_costs + rehab_budget

# Standard straight-line depreciation (27.5 yr on building)
building_value      = (purchase_price + rehab_budget) * (1 - land_value_pct / 100)
annual_depr_std     = building_value / 27.5

# Cost seg depreciation
if enable_costseg:
    costseg_5yr_basis  = building_value * (costseg_5yr_pct  / 100)
    costseg_15yr_basis = building_value * (costseg_15yr_pct / 100)
    remaining_basis    = building_value - costseg_5yr_basis - costseg_15yr_basis
    # Bonus depreciation taken upfront in costseg_year
    bonus_depr_5yr     = costseg_5yr_basis  * (costseg_bonus_pct / 100)
    bonus_depr_15yr    = costseg_15yr_basis * (costseg_bonus_pct / 100)
    # Remaining after bonus: 5-yr MACRS and 15-yr MACRS (simplified straight-line)
    annual_depr_5yr    = (costseg_5yr_basis  - bonus_depr_5yr)  / 5
    annual_depr_15yr   = (costseg_15yr_basis - bonus_depr_15yr) / 15
    annual_depr_39yr   = remaining_basis / 27.5  # rest stays 27.5yr
    total_bonus        = bonus_depr_5yr + bonus_depr_15yr
else:
    total_bonus = 0
    annual_depr_5yr = annual_depr_15yr = annual_depr_39yr = 0

def get_depreciation(yr):
    """Returns (standard_depr, costseg_extra_depr) for a given year."""
    if not enable_costseg:
        return annual_depr_std, 0.0
    if yr == costseg_year:
        # Bonus + first-year regular on each bucket
        reg = annual_depr_5yr + annual_depr_15yr + annual_depr_39yr
        return reg, total_bonus
    elif yr < costseg_year:
        return annual_depr_std, 0.0
    else:
        # After costseg year: reduced regular depr (5yr + 15yr + 39yr components)
        reg = annual_depr_5yr + annual_depr_15yr + annual_depr_39yr
        return reg, 0.0

def monthly_payment(principal, annual_rate, term_years):
    rm = (annual_rate / 100) / 12
    nm = term_years * 12
    if rm == 0:
        return principal / nm
    return principal * (rm * (1 + rm)**nm) / ((1 + rm)**nm - 1)

def remaining_balance(principal, annual_rate, term_years, months_paid):
    rm = (annual_rate / 100) / 12
    nm = term_years * 12
    if rm == 0:
        return max(0, principal * (1 - months_paid / nm))
    return principal * ((1 + rm)**nm - (1 + rm)**months_paid) / ((1 + rm)**nm - 1)

def irr_newton(cashflows):
    rate = 0.1
    for _ in range(2000):
        npv  = sum(cf / (1 + rate)**t for t, cf in enumerate(cashflows))
        dnpv = sum(-t * cf / (1 + rate)**(t + 1) for t, cf in enumerate(cashflows))
        if abs(dnpv) < 1e-12:
            break
        nr = rate - npv / dnpv
        if abs(nr - rate) < 1e-8:
            rate = nr
            break
        rate = nr
    return rate * 100 if -0.99 < rate < 100 else None

def build_rows(loan_amt, rate, term, hold, start_prop_value):
    init_pmt    = monthly_payment(loan_amt, rate, term)
    annual_ds   = init_pmt * 12
    prop_val    = start_prop_value
    cr = c_rent_base
    ct = exp_taxes; cu = exp_utils; ci = exp_ins; ch = exp_hoa; co = exp_other

    rows_out = []
    months_paid = 0

    for yr in range(1, hold + 1):
        eff_gross  = cr * (1 - vacancy_rate / 100)
        mgmt_cost  = eff_gross * (exp_mgmt_pct / 100)
        total_opex = ct + cu + ci + ch + mgmt_cost + co
        noi        = eff_gross - total_opex
        cash_flow  = noi - annual_ds

        std_depr, costseg_bonus = get_depreciation(yr)
        total_depr  = std_depr + costseg_bonus
        net_income  = cash_flow - total_depr

        # Tax impact
        # Without cost seg: tax on (cash_flow - annual_depr_std)
        base_taxable    = cash_flow - annual_depr_std
        base_tax        = base_taxable * (marginal_tax_rate / 100) if base_taxable > 0 else 0
        base_after_tax  = cash_flow - base_tax

        # With actual depreciation (may include cost seg bonus)
        actual_taxable  = cash_flow - total_depr
        actual_tax      = actual_taxable * (marginal_tax_rate / 100) if actual_taxable > 0 else 0
        # If net income is negative (paper loss), it shelters other income
        tax_shield      = abs(min(0, actual_taxable)) * (marginal_tax_rate / 100)
        tax_savings     = total_depr * (marginal_tax_rate / 100)  # vs paying full tax on cash flow
        after_tax_cf    = cash_flow - actual_tax + tax_shield
        costseg_benefit = after_tax_cf - base_after_tax  # extra benefit from cost seg vs std depr

        prop_val   *= (1 + appreciation_rate / 100)
        months_paid += 12
        loan_bal    = remaining_balance(loan_amt, rate, term, months_paid)
        equity_val  = prop_val - loan_bal

        rows_out.append({
            "Gross Rent":            cr,
            "Vacancy Loss":          cr * (vacancy_rate / 100),
            "Eff. Gross Income":     eff_gross,
            "Operating Expenses":    total_opex,
            "NOI":                   noi,
            "Debt Service":          annual_ds,
            "Net Cash Flow":         cash_flow,
            "Std. Depreciation":     std_depr,
            "Cost Seg Bonus Depr":   costseg_bonus,
            "Total Depreciation":    total_depr,
            "Net Income / (Loss)":   net_income,
            "Tax Savings (Depr)":    tax_savings,
            "Est. Tax Owed":         actual_tax,
            "After-Tax Cash Flow":   after_tax_cf,
            "Cost Seg Extra Benefit":costseg_benefit,
            "Property Value":        prop_val,
            "Loan Balance":          loan_bal,
            "Equity Value":          equity_val,
            "_cf_irr":               cash_flow,
        })

        cr *= (1 + rent_growth / 100)
        ct *= (1 + g_taxes / 100); cu *= (1 + g_utils / 100)
        ci *= (1 + g_ins   / 100); ch *= (1 + g_hoa   / 100)
        co *= (1 + g_other / 100)

    return rows_out

c_rent_base = monthly_rent * 12

init_monthly_pmt = monthly_payment(loan_amount, int_rate, loan_term_yrs)
base_rows = build_rows(loan_amount, int_rate, loan_term_yrs, hold_years, purchase_price)

# Sale proceeds helper — uses appreciated property value directly
def sale_proceeds_at(row):
    sale_price = row["Property Value"]
    return sale_price - sale_price * (selling_costs_pct / 100) - row["Loan Balance"]

# Cumulative IRR (base, no refi)
base_cfs = [-total_cash_in] + [r["_cf_irr"] for r in base_rows]
cum_irrs_base = []
for k in range(1, hold_years + 1):
    sp   = sale_proceeds_at(base_rows[k - 1])
    cfs  = base_cfs[:k] + [base_cfs[k] + sp]
    val  = irr_newton(cfs)
    cum_irrs_base.append(f"{val:.1f}%" if val is not None else "N/A")

for i, row in enumerate(base_rows):
    row["Cum. IRR (if sold)"] = cum_irrs_base[i]

full_sp      = sale_proceeds_at(base_rows[-1])
full_irr_val = irr_newton(base_cfs[:-1] + [base_cfs[-1] + full_sp])
full_irr     = f"{full_irr_val:.1f}%" if full_irr_val is not None else "N/A"

labels = [f"Yr {i}" for i in range(1, hold_years + 1)]

# ==========================================
# DISPLAY
# ==========================================

fmt_d = lambda x: f"${x:,.0f}"
fmt_p = lambda x: f"{x:.2f}%"

# --- Header KPIs ---
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric(f"IRR ({hold_years}-yr hold)", full_irr)
k2.metric("Total Cash In",  fmt_d(total_cash_in))
k3.metric("Down Payment",   fmt_d(down_payment))
k4.metric("Loan Amount",    fmt_d(loan_amount))
k5.metric("Reno Budget",    fmt_d(rehab_budget))

st.markdown("---")

# --- Base Cash Flow Table ---
st.subheader(f"Annual Cash Flow Projection ({hold_years} Years)")

def make_display_df(rows, lbl):
    cols_base = [
        "Gross Rent","Vacancy Loss","Eff. Gross Income","Operating Expenses",
        "NOI","Debt Service","Net Cash Flow",
        "Std. Depreciation","Net Income / (Loss)",
        "Property Value","Equity Value","Cum. IRR (if sold)"
    ]
    cols_cs = [
        "Gross Rent","Vacancy Loss","Eff. Gross Income","Operating Expenses",
        "NOI","Debt Service","Net Cash Flow",
        "Std. Depreciation","Cost Seg Bonus Depr","Total Depreciation","Net Income / (Loss)",
        "Property Value","Equity Value","Cum. IRR (if sold)"
    ]
    cols = cols_cs if enable_costseg else cols_base
    df = pd.DataFrame(rows, index=lbl)[cols].copy()
    for c in [x for x in cols if x != "Cum. IRR (if sold)"]:
        df[c] = df[c].apply(fmt_d)
    return df

st.dataframe(make_display_df(base_rows, labels), use_container_width=True)

csv_base = make_display_df(base_rows, labels).to_csv()
st.download_button("⬇ Download table as CSV", csv_base, "cashflow.csv", "text/csv", key="dl_base")

st.markdown("---")

# --- Charts ---
st.subheader("Trends")
ch1, ch2 = st.columns(2)
with ch1:
    st.caption("Net Cash Flow ($)")
    st.bar_chart(pd.DataFrame({"Net Cash Flow": [r["Net Cash Flow"] for r in base_rows]}, index=labels))
with ch2:
    st.caption("Net Income / (Loss) ($)")
    st.bar_chart(pd.DataFrame({"Net Income / (Loss)": [r["Net Income / (Loss)"] for r in base_rows]}, index=labels))

# ==========================================
# REFINANCE SECTION
# ==========================================

st.markdown("---")
st.subheader("Refinance Analysis")
st.caption("Model a mid-hold refinance and see the full restated cash flow table and IRR impact.")

rf_col1, rf_col2, rf_col3, rf_col4, rf_col5 = st.columns(5)
with rf_col1:
    refi_year    = st.selectbox("Refi in Year", list(range(2, hold_years + 1)), index=0)
with rf_col2:
    refi_ltv     = st.slider("Refi LTV (%)", 60, 80, 70, key="refi_ltv")
with rf_col3:
    refi_rate    = st.number_input("Refi Rate (%)", min_value=0.0, max_value=20.0, value=6.0, step=0.25, key="refi_rate")
with rf_col4:
    refi_term    = st.selectbox("Refi Term (yrs)", [30, 20, 15], index=0, key="refi_term")
with rf_col5:
    refi_fees_pct = st.slider("Refi Fees (%)", 0.5, 3.0, 1.5, 0.25, key="refi_fees")

# Compute refi
bal_before_refi  = remaining_balance(loan_amount, int_rate, loan_term_yrs, (refi_year - 1) * 12)
prop_val_at_refi = purchase_price * ((1 + appreciation_rate / 100) ** (refi_year - 1))
new_loan_refi    = prop_val_at_refi * (refi_ltv / 100)
refi_fees_abs    = new_loan_refi * (refi_fees_pct / 100)
cash_out         = new_loan_refi - bal_before_refi - refi_fees_abs
new_monthly_pmt  = monthly_payment(new_loan_refi, refi_rate, refi_term)

# Summary metrics
rm1, rm2, rm3, rm4 = st.columns(4)
rm1.metric("Property Value at Refi",  fmt_d(prop_val_at_refi))
rm2.metric("Loan Balance Before",     fmt_d(bal_before_refi))
rm3.metric("New Loan",                fmt_d(new_loan_refi))
rm4.metric("Net Cash-Out to You",     fmt_d(cash_out),
           delta=f"Fees: {fmt_d(refi_fees_abs)}", delta_color="inverse")

pm1, pm2 = st.columns(2)
pm1.metric("Old Monthly Payment",     fmt_d(init_monthly_pmt) + "/mo")
pm2.metric("New Monthly Payment",     fmt_d(new_monthly_pmt) + "/mo",
           delta=fmt_d(new_monthly_pmt - init_monthly_pmt) + "/mo",
           delta_color="inverse")

# Build refi cash flow table: pre-refi years unchanged, then new loan from refi_year
# Years 1 to refi_year-1: same as base
pre_rows = base_rows[:refi_year - 1]

# From refi_year onward: rebuild with new loan, but property value already appreciated
post_hold  = hold_years - (refi_year - 1)

# Temporarily adjust c_rent_base for the post-refi period
orig_c_rent = c_rent_base
for _ in range(refi_year - 1):
    orig_c_rent *= (1 + rent_growth / 100)

# We need to rebuild expense state too — monkey-patch via globals
def build_post_refi_rows(loan_amt, rate, term, hold, start_prop_value, yr_offset):
    init_pmt  = monthly_payment(loan_amt, rate, term)
    annual_ds = init_pmt * 12
    prop_val  = start_prop_value
    cr = c_rent_base
    ct = exp_taxes; cu = exp_utils; ci = exp_ins; ch = exp_hoa; co = exp_other
    # Fast-forward income/expense state to yr_offset
    for _ in range(yr_offset):
        cr *= (1 + rent_growth / 100)
        ct *= (1 + g_taxes / 100); cu *= (1 + g_utils / 100)
        ci *= (1 + g_ins   / 100); ch *= (1 + g_hoa   / 100)
        co *= (1 + g_other / 100)
    months_paid = 0
    rows_out = []
    for yr_abs in range(yr_offset + 1, yr_offset + hold + 1):
        eff_gross  = cr * (1 - vacancy_rate / 100)
        mgmt_cost  = eff_gross * (exp_mgmt_pct / 100)
        total_opex = ct + cu + ci + ch + mgmt_cost + co
        noi        = eff_gross - total_opex
        cash_flow  = noi - annual_ds
        std_depr, costseg_bonus = get_depreciation(yr_abs)
        total_depr  = std_depr + costseg_bonus
        net_income  = cash_flow - total_depr
        actual_taxable = cash_flow - total_depr
        actual_tax     = actual_taxable * (marginal_tax_rate / 100) if actual_taxable > 0 else 0
        tax_shield     = abs(min(0, actual_taxable)) * (marginal_tax_rate / 100)
        tax_savings    = total_depr * (marginal_tax_rate / 100)
        base_taxable   = cash_flow - annual_depr_std
        base_tax       = base_taxable * (marginal_tax_rate / 100) if base_taxable > 0 else 0
        base_after_tax = cash_flow - base_tax
        after_tax_cf   = cash_flow - actual_tax + tax_shield
        costseg_benefit= after_tax_cf - base_after_tax
        prop_val  *= (1 + appreciation_rate / 100)
        months_paid += 12
        loan_bal   = remaining_balance(loan_amt, rate, term, months_paid)
        equity_val = prop_val - loan_bal
        rows_out.append({
            "Gross Rent":            cr,
            "Vacancy Loss":          cr * (vacancy_rate / 100),
            "Eff. Gross Income":     eff_gross,
            "Operating Expenses":    total_opex,
            "NOI":                   noi,
            "Debt Service":          annual_ds,
            "Net Cash Flow":         cash_flow,
            "Std. Depreciation":     std_depr,
            "Cost Seg Bonus Depr":   costseg_bonus,
            "Total Depreciation":    total_depr,
            "Net Income / (Loss)":   net_income,
            "Tax Savings (Depr)":    tax_savings,
            "Est. Tax Owed":         actual_tax,
            "After-Tax Cash Flow":   after_tax_cf,
            "Cost Seg Extra Benefit":costseg_benefit,
            "Property Value":        prop_val,
            "Loan Balance":          loan_bal,
            "Equity Value":          equity_val,
            "_cf_irr":               cash_flow,
        })
        cr *= (1 + rent_growth / 100)
        ct *= (1 + g_taxes / 100); cu *= (1 + g_utils / 100)
        ci *= (1 + g_ins   / 100); ch *= (1 + g_hoa   / 100)
        co *= (1 + g_other / 100)
    return rows_out

post_rows = build_post_refi_rows(
    new_loan_refi, refi_rate, refi_term, post_hold,
    prop_val_at_refi, refi_year - 1
)

refi_rows = list(pre_rows) + list(post_rows)

# Cumulative IRR for refi scenario
# Cash flow in refi year gets the cash-out added; initial outflow unchanged
refi_cfs = [-total_cash_in]
for i, r in enumerate(refi_rows):
    yr = i + 1
    cf = r["_cf_irr"] + (cash_out if yr == refi_year else 0)
    refi_cfs.append(cf)

refi_cum_irrs = []
for k in range(1, hold_years + 1):
    sp  = sale_proceeds_at(refi_rows[k - 1])
    cfs = refi_cfs[:k] + [refi_cfs[k] + sp]
    val = irr_newton(cfs)
    refi_cum_irrs.append(f"{val:.1f}%" if val is not None else "N/A")

for i, row in enumerate(refi_rows):
    row["Cum. IRR (if sold)"] = refi_cum_irrs[i]

refi_full_sp      = sale_proceeds_at(refi_rows[-1])
refi_full_irr_val = irr_newton(refi_cfs[:-1] + [refi_cfs[-1] + refi_full_sp])
refi_full_irr     = f"{refi_full_irr_val:.1f}%" if refi_full_irr_val is not None else "N/A"

# IRR comparison
ic1, ic2 = st.columns(2)
ic1.metric(f"Base IRR ({hold_years}-yr)",  full_irr)
ic2.metric(f"Post-Refi IRR ({hold_years}-yr)", refi_full_irr,
           delta=f"{(refi_full_irr_val or 0) - (full_irr_val or 0):.1f}pp vs base" if refi_full_irr_val and full_irr_val else "")

st.markdown("##### Restated Cash Flow Table (with Refi)")
refi_labels = labels.copy()
refi_labels[refi_year - 1] = f"Yr {refi_year} ⟳"
st.dataframe(make_display_df(refi_rows, refi_labels), use_container_width=True)
csv_refi = make_display_df(refi_rows, refi_labels).to_csv()
st.download_button("⬇ Download refi table as CSV", csv_refi, "cashflow_refi.csv", "text/csv", key="dl_refi")

# Delta table
st.markdown("##### Change vs Base (Refi − Base)")
delta_cols = ["Net Cash Flow","Debt Service","After-Tax Cash Flow","Net Income / (Loss)","Equity Value","Loan Balance"]
delta_data = {}
for col in delta_cols:
    delta_data[col] = [
        fmt_d(refi_rows[i][col] - base_rows[i][col]) for i in range(hold_years)
    ]
delta_df = pd.DataFrame(delta_data, index=labels)
st.dataframe(delta_df, use_container_width=True)

# --- Cost Seg Impact Table ---
st.markdown("---")
st.subheader("🏗️ Cost Segregation Impact")
st.caption(f"Assumes {marginal_tax_rate}% marginal tax rate. Study cost: {fmt_d(costseg_study_cost)}.")

# Build a baseline (no cost seg) version for comparison using std depreciation
def get_std_tax_fields(row):
    """Compute tax fields using only straight-line depreciation."""
    cf = row["Net Cash Flow"]
    taxable = cf - annual_depr_std
    tax     = taxable * (marginal_tax_rate / 100) if taxable > 0 else 0
    shield  = abs(min(0, taxable)) * (marginal_tax_rate / 100)
    return cf - tax + shield  # after-tax CF with std depr only

cs_impact_data = []
for i, row in enumerate(base_rows):
    cf           = row["Net Cash Flow"]
    total_depr   = row["Total Depreciation"]
    taxable_cs   = cf - total_depr
    tax_cs       = taxable_cs * (marginal_tax_rate / 100) if taxable_cs > 0 else 0
    shield_cs    = abs(min(0, taxable_cs)) * (marginal_tax_rate / 100)
    after_tax_cs = cf - tax_cs + shield_cs

    after_tax_std = get_std_tax_fields(row)
    benefit       = after_tax_cs - after_tax_std

    cs_impact_data.append({
        "Year":                  labels[i],
        "Total Depreciation":    fmt_d(total_depr),
        "vs Std Depreciation":   fmt_d(annual_depr_std),
        "Extra Depr":            fmt_d(total_depr - annual_depr_std),
        "Net Income / (Loss)":   fmt_d(row["Net Income / (Loss)"]),
        "After-Tax CF (w/ CS)":  fmt_d(after_tax_cs),
        "After-Tax CF (no CS)":  fmt_d(after_tax_std),
        "Annual Tax Benefit":    fmt_d(benefit),
    })

cs_df = pd.DataFrame(cs_impact_data).set_index("Year")
st.dataframe(cs_df, use_container_width=True)

# Summary metrics
total_benefit = sum(
    (lambda cf, td: (cf - max(0, cf - td) * (marginal_tax_rate/100) + abs(min(0, cf-td)) * (marginal_tax_rate/100))
                    - get_std_tax_fields(r))(r["Net Cash Flow"], r["Total Depreciation"], )
    for r in base_rows
)
# Simpler cumulative calc
cum_benefit = 0
for row in base_rows:
    cf = row["Net Cash Flow"]
    td = row["Total Depreciation"]
    taxable_cs  = cf - td
    tax_cs      = taxable_cs * (marginal_tax_rate/100) if taxable_cs > 0 else 0
    shield_cs   = abs(min(0, taxable_cs)) * (marginal_tax_rate/100)
    atcf_cs     = cf - tax_cs + shield_cs
    cum_benefit += atcf_cs - get_std_tax_fields(row)

sb1, sb2, sb3 = st.columns(3)
sb1.metric("Bonus Depr (Yr " + str(costseg_year) + ")", fmt_d(total_bonus) if enable_costseg else "$0")
sb2.metric("Cumulative Tax Benefit",                     fmt_d(cum_benefit))
sb3.metric("Net Benefit after Study Cost",               fmt_d(cum_benefit - costseg_study_cost),
           delta="vs $0 without cost seg", delta_color="normal")

# --- Assumptions ---
st.markdown("---")
with st.expander("Model assumptions"):
    a1, a2 = st.columns(2)
    with a1:
        st.write(f"- Vacancy: **{vacancy_rate}%**, Rent growth: **{rent_growth}%/yr**")
        st.write(f"- Appreciation: **{appreciation_rate}%/yr** (used directly as sale price for IRR)")
        st.write(f"- Mortgage: **{int_rate}%**, {loan_term_yrs}-yr | Monthly P&I: **{fmt_d(init_monthly_pmt)}**")
        st.write(f"- Building value: **{fmt_d(building_value)}** | Std depr: **{fmt_d(annual_depr_std)}/yr** (27.5yr SL)")
        if enable_costseg:
            st.write(f"- Cost seg: 5-yr basis **{fmt_d(costseg_5yr_basis)}**, 15-yr **{fmt_d(costseg_15yr_basis)}**")
            st.write(f"- Bonus depr (**{costseg_bonus_pct}%**) applied Yr {costseg_year}: **{fmt_d(total_bonus)}**")
    with a2:
        st.write(f"- Tax: **{g_taxes}%/yr** | Utilities: **{g_utils}%/yr** | Insurance: **{g_ins}%/yr**")
        st.write(f"- Maintenance: **{g_other}%/yr** | Mgmt: **{g_mgmt}%/yr**")
        st.write(f"- Selling costs at exit: **{selling_costs_pct}%**")
        st.write(f"- Cum. IRR assumes sale at appreciated property value each year")
