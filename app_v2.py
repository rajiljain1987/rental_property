import streamlit as st
import pandas as pd
import numpy as np
import json, os, requests

st.set_page_config(page_title="RE Deal Analyzer", layout="wide")

# ==========================================
# RENTCAST API
# ==========================================

RENTCAST_BASE = "https://api.rentcast.io/v1"

MOCK_LISTINGS = [
    {"id": "1", "formattedAddress": "125 Wayne St, Jersey City, NJ 07302",
     "price": 875_000, "bedrooms": 4, "bathrooms": 2, "squareFootage": 1800,
     "propertyType": "Multi Family", "yearBuilt": 1965,
     "rentEstimate": 7_200, "propertyTaxes": 11_400, "hoa": 0,
     "latitude": 40.7178, "longitude": -74.0431},
    {"id": "2", "formattedAddress": "340 Manila Ave, Jersey City, NJ 07302",
     "price": 1_050_000, "bedrooms": 6, "bathrooms": 3, "squareFootage": 2400,
     "propertyType": "Multi Family", "yearBuilt": 1955,
     "rentEstimate": 9_400, "propertyTaxes": 13_800, "hoa": 0,
     "latitude": 40.7145, "longitude": -74.0512},
    {"id": "3", "formattedAddress": "58 Storms Ave, Jersey City, NJ 07306",
     "price": 699_000, "bedrooms": 3, "bathrooms": 2, "squareFootage": 1400,
     "propertyType": "Multi Family", "yearBuilt": 1972,
     "rentEstimate": 5_800, "propertyTaxes": 9_200, "hoa": 0,
     "latitude": 40.7234, "longitude": -74.0678},
    {"id": "4", "formattedAddress": "211 Duncan Ave, Jersey City, NJ 07306",
     "price": 1_250_000, "bedrooms": 8, "bathrooms": 4, "squareFootage": 3200,
     "propertyType": "Multi Family", "yearBuilt": 1948,
     "rentEstimate": 11_200, "propertyTaxes": 16_500, "hoa": 0,
     "latitude": 40.7198, "longitude": -74.0598},
    {"id": "5", "formattedAddress": "78 Lembeck Ave, Jersey City, NJ 07305",
     "price": 580_000, "bedrooms": 3, "bathrooms": 2, "squareFootage": 1250,
     "propertyType": "Multi Family", "yearBuilt": 1968,
     "rentEstimate": 4_900, "propertyTaxes": 7_800, "hoa": 0,
     "latitude": 40.7089, "longitude": -74.0723},
]

def fetch_listings(api_key, city, state, limit=20):
    if not api_key:
        return MOCK_LISTINGS, True  # True = is_mock
    try:
        resp = requests.get(
            f"{RENTCAST_BASE}/listings/sale",
            headers={"X-Api-Key": api_key},
            params={"city": city, "state": state, "propertyType": "Multi Family",
                    "status": "Active", "limit": limit},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            listings = data if isinstance(data, list) else data.get("listings", [])
            return listings, False
        else:
            st.warning(f"Rentcast API error {resp.status_code} — showing mock data.")
            return MOCK_LISTINGS, True
    except Exception as e:
        st.warning(f"Could not reach Rentcast — showing mock data. ({e})")
        return MOCK_LISTINGS, True

def fetch_rent_estimate(api_key, address, bedrooms, bathrooms):
    if not api_key:
        return None
    try:
        resp = requests.get(
            f"{RENTCAST_BASE}/avm/rent/long-term",
            headers={"X-Api-Key": api_key},
            params={"address": address, "bedrooms": bedrooms, "bathrooms": bathrooms},
            timeout=8
        )
        if resp.status_code == 200:
            return resp.json().get("rent")
    except:
        pass
    return None

# ==========================================
# SMART DEFAULTS
# ==========================================

def smart_defaults(listing):
    price      = listing.get("price", 800_000)
    rent       = listing.get("rentEstimate") or int(price * 0.008)  # 0.8% rule fallback
    taxes      = listing.get("propertyTaxes") or int(price * 0.014)  # ~1.4% NJ rate
    hoa        = listing.get("hoa") or 0
    insurance  = int(price * 0.005)        # ~0.5% of value
    utils      = 3_000                     # flat default
    maint      = int(price * 0.01)         # 1% of value
    rehab      = int(price * 0.04)         # 4% light reno estimate
    closing    = int(price * 0.03)
    return {
        "purchase_price":  price,
        "monthly_rent":    rent,
        "exp_taxes":       taxes,
        "exp_hoa":         hoa,
        "exp_ins":         insurance,
        "exp_utils":       utils,
        "exp_other":       maint,
        "rehab_budget":    rehab,
        "closing_costs":   closing,
    }

# ==========================================
# CALCULATION ENGINE (carried from v1)
# ==========================================

SCENARIOS_FILE = "scenarios.json"

def load_all_scenarios():
    if os.path.exists(SCENARIOS_FILE):
        with open(SCENARIOS_FILE) as f:
            return json.load(f)
    return {}

def save_all_scenarios(data):
    with open(SCENARIOS_FILE, "w") as f:
        json.dump(data, f, indent=2)

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
            rate = nr; break
        rate = nr
    return rate * 100 if -0.99 < rate < 100 else None

fmt_d = lambda x: f"${x:,.0f}"

# ==========================================
# SESSION STATE INIT
# ==========================================

if "selected_listing" not in st.session_state:
    st.session_state.selected_listing = None
if "inputs" not in st.session_state:
    st.session_state.inputs = {}

# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar.expander("🔑 Rentcast API", expanded=True):
    api_key = st.text_input("API Key", type="password", placeholder="Paste your Rentcast key",
                             help="Get a free key at rentcast.io — 50 calls/month free")
    if not api_key:
        st.caption("🟡 No key — showing mock Jersey City data")
    else:
        st.caption("🟢 Live data mode")

with st.sidebar.expander("🔍 Search", expanded=True):
    city  = st.text_input("City", value="Jersey City")
    state = st.text_input("State", value="NJ")
    limit = st.slider("Max listings", 5, 50, 20)
    search_btn = st.button("Search listings", type="primary")

all_scenarios = load_all_scenarios()
with st.sidebar.expander("💾 Scenarios", expanded=False):
    scenario_names = list(all_scenarios.keys())
    if scenario_names:
        load_name = st.selectbox("Load scenario", ["— select —"] + scenario_names, key="load_sel")
        if load_name != "— select —" and st.button("Load", key="btn_load"):
            st.session_state.inputs = all_scenarios[load_name]
            st.rerun()
    else:
        st.caption("No saved scenarios yet.")
    save_name = st.text_input("Scenario name", placeholder="e.g. 125 Wayne St", key="save_name")
    if st.button("Save current inputs", key="btn_save"):
        if save_name.strip() and st.session_state.inputs:
            all_scenarios[save_name.strip()] = st.session_state.inputs
            save_all_scenarios(all_scenarios)
            st.success(f"Saved: {save_name.strip()}")
    if scenario_names:
        del_name = st.selectbox("Delete", ["— select —"] + scenario_names, key="del_sel")
        if del_name != "— select —" and st.button("Delete", key="btn_del"):
            del all_scenarios[del_name]
            save_all_scenarios(all_scenarios)
            st.rerun()

# ==========================================
# SEARCH & LISTING SELECTION
# ==========================================

st.title("🏘️ Real Estate Deal Analyzer")
st.caption("Search multi-family listings, select one, and instantly run your full investment analysis.")

if search_btn or "listings" not in st.session_state:
    with st.spinner("Fetching listings..."):
        listings, is_mock = fetch_listings(api_key, city, state, limit)
        st.session_state.listings = listings
        st.session_state.is_mock  = is_mock

listings = st.session_state.get("listings", MOCK_LISTINGS)
is_mock  = st.session_state.get("is_mock", True)

if is_mock:
    st.info("📌 Showing mock Jersey City listings — add your Rentcast API key for live data.")

if listings:
    # Build display table
    rows = []
    for l in listings:
        rent_est = l.get("rentEstimate") or "—"
        rows.append({
            "Address":      l.get("formattedAddress", l.get("address", "Unknown")),
            "Price":        fmt_d(l.get("price", 0)),
            "Beds/Baths":   f"{l.get('bedrooms','?')}bd / {l.get('bathrooms','?')}ba",
            "Sq Ft":        f"{l.get('squareFootage', '?'):,}" if l.get('squareFootage') else "—",
            "Est. Rent/mo": fmt_d(rent_est) if isinstance(rent_est, (int, float)) else rent_est,
            "Year Built":   l.get("yearBuilt", "—"),
            "_idx":         listings.index(l),
        })

    df_list = pd.DataFrame(rows)
    st.subheader(f"{'Mock' if is_mock else 'Live'} Listings — {city}, {state}")

    # Clickable selection
    sel = st.dataframe(
        df_list.drop(columns=["_idx"]),
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="listing_table"
    )

    selected_rows = sel.selection.rows if sel and sel.selection else []

    if selected_rows:
        idx = selected_rows[0]
        listing = listings[idx]
        defaults = smart_defaults(listing)

        # Merge with any existing session inputs for this listing
        inp = {**defaults, **{k: v for k, v in st.session_state.inputs.items() if k in defaults}}

        st.session_state.selected_listing = listing
        st.session_state.inputs = inp

# ==========================================
# ANALYSIS DASHBOARD
# ==========================================

listing = st.session_state.selected_listing
inp     = st.session_state.inputs

if not listing:
    st.markdown("---")
    st.markdown("### 👆 Select a listing above to run the analysis")
    st.stop()

st.markdown("---")
addr = listing.get("formattedAddress", listing.get("address", "Selected Property"))
st.header(f"📊 {addr}")

beds  = listing.get("bedrooms", "?")
baths = listing.get("bathrooms", "?")
sqft  = listing.get("squareFootage")
yr    = listing.get("yearBuilt", "?")
ptype = listing.get("propertyType", "")
st.caption(f"{ptype} · {beds} bed / {baths} bath" +
           (f" · {sqft:,} sq ft" if sqft else "") +
           f" · Built {yr}")

# ---- Editable inputs in two columns ----
st.subheader("Inputs — edit any field")
with st.expander("📋 Property & Financing", expanded=True):
    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        purchase_price   = st.number_input("Purchase Price ($)", value=int(inp.get("purchase_price", 800_000)), step=25_000)
        down_payment_pct = st.slider("Down Payment (%)", 10, 40, 25)
        closing_costs    = st.number_input("Closing Costs ($)", value=int(inp.get("closing_costs", 24_000)), step=1_000)
        rehab_budget     = st.number_input("Renovation Budget ($)", value=int(inp.get("rehab_budget", 32_000)), step=5_000)
    with ic2:
        int_rate      = st.number_input("Mortgage Rate (%)", 0.0, 20.0, 6.5, 0.25)
        loan_term_yrs = st.selectbox("Loan Term (yrs)", [30, 20, 15])
        land_value_pct= st.slider("Land Value (% of purchase)", 5, 50, 20,
                                   help="Land is not depreciable.")
        hold_years    = st.selectbox("Hold Period (yrs)", [5, 7, 10], index=1)
    with ic3:
        monthly_rent  = st.number_input("Monthly Rent ($)", value=int(inp.get("monthly_rent", 7_500)), step=250)
        vacancy_rate  = st.slider("Vacancy Rate (%)", 0, 15, 5)
        appreciation_rate = st.slider("Annual Appreciation (%)", 0.0, 10.0, 3.0, 0.5)
        selling_costs_pct = st.slider("Selling Costs at Exit (%)", 1.0, 8.0, 5.0, 0.5)

with st.expander("📝 Annual Expenses", expanded=False):
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        exp_taxes    = st.number_input("Property Taxes ($)", value=int(inp.get("exp_taxes", 9_600)), step=500)
        exp_utils    = st.number_input("Utilities ($)", value=int(inp.get("exp_utils", 3_000)), step=250)
    with ec2:
        exp_ins      = st.number_input("Insurance ($)", value=int(inp.get("exp_ins", 1_800)), step=200)
        exp_hoa      = st.number_input("HOA Fees ($)", value=int(inp.get("exp_hoa", 0)), step=500)
    with ec3:
        exp_mgmt_pct = st.number_input("Mgmt Fee (%)", value=8, step=1)
        exp_other    = st.number_input("Maintenance ($)", value=int(inp.get("exp_other", 3_600)), step=250)

with st.expander("📈 Growth Assumptions", expanded=False):
    gc1, gc2 = st.columns(2)
    with gc1:
        rent_growth = st.slider("Rent Growth (%/yr)", 0.0, 10.0, 3.0, 0.5)
        g_taxes = st.number_input("Tax Growth",   value=2.0, step=0.5, key="g_taxes")
        g_utils = st.number_input("Utils Growth", value=3.0, step=0.5, key="g_utils")
        g_ins   = st.number_input("Ins Growth",   value=4.0, step=0.5, key="g_ins")
    with gc2:
        g_hoa   = st.number_input("HOA Growth",   value=0.0, step=0.5, key="g_hoa")
        g_mgmt  = st.number_input("Mgmt Growth",  value=3.0, step=0.5, key="g_mgmt")
        g_other = st.number_input("Maint Growth", value=2.5, step=0.5, key="g_other")

with st.expander("🏗️ Cost Segregation", expanded=False):
    marginal_tax_rate  = st.slider("Marginal Tax Rate (%)", 10, 50, 35)
    costseg_study_cost = st.number_input("Study Cost ($)", value=2_000, step=500)
    enable_costseg     = st.checkbox("Apply cost segregation")
    costseg_year       = st.selectbox("Applied in Year", [1, 2]) if enable_costseg else 1
    costseg_5yr_pct    = st.slider("5-yr property (%)", 0, 30, 15) if enable_costseg else 0
    costseg_15yr_pct   = st.slider("15-yr property (%)", 0, 20, 10) if enable_costseg else 0
    costseg_bonus_pct  = st.slider("Bonus depreciation (%)", 0, 100, 60) if enable_costseg else 0

# Save inputs to session
st.session_state.inputs = {
    "purchase_price": purchase_price, "monthly_rent": monthly_rent,
    "exp_taxes": exp_taxes, "exp_utils": exp_utils, "exp_ins": exp_ins,
    "exp_hoa": exp_hoa, "exp_mgmt_pct": exp_mgmt_pct, "exp_other": exp_other,
    "rehab_budget": rehab_budget, "closing_costs": closing_costs,
    "marginal_tax_rate": marginal_tax_rate, "costseg_study_cost": costseg_study_cost,
}

# ==========================================
# CALCULATIONS
# ==========================================

down_payment  = purchase_price * (down_payment_pct / 100)
loan_amount   = purchase_price - down_payment
total_cash_in = down_payment + closing_costs + rehab_budget
building_value= (purchase_price + rehab_budget) * (1 - land_value_pct / 100)
annual_depr_std = building_value / 27.5

if enable_costseg:
    cs5b  = building_value * (costseg_5yr_pct  / 100)
    cs15b = building_value * (costseg_15yr_pct / 100)
    rem_b = building_value - cs5b - cs15b
    bd5   = cs5b  * (costseg_bonus_pct / 100)
    bd15  = cs15b * (costseg_bonus_pct / 100)
    ad5   = (cs5b  - bd5)  / 5
    ad15  = (cs15b - bd15) / 15
    ad39  = rem_b / 27.5
    total_bonus = bd5 + bd15
else:
    total_bonus = ad5 = ad15 = ad39 = 0

def get_depreciation(yr):
    if not enable_costseg:
        return annual_depr_std, 0.0
    reg = ad5 + ad15 + ad39
    if yr == costseg_year:
        return reg, total_bonus
    elif yr < costseg_year:
        return annual_depr_std, 0.0
    return reg, 0.0

def sale_proceeds_at(row):
    sp = row["Property Value"]
    return sp - sp * (selling_costs_pct / 100) - row["Loan Balance"]

c_rent_base = monthly_rent * 12
init_monthly_pmt = monthly_payment(loan_amount, int_rate, loan_term_yrs)

def build_rows(loan_amt, rate, term, hold, start_prop_value):
    annual_ds = monthly_payment(loan_amt, rate, term) * 12
    prop_val  = start_prop_value
    cr = c_rent_base
    ct = exp_taxes; cu = exp_utils; ci = exp_ins; ch = exp_hoa; co = exp_other
    rows_out  = []; months_paid = 0
    for yr in range(1, hold + 1):
        eff_gross  = cr * (1 - vacancy_rate / 100)
        mgmt_cost  = eff_gross * (exp_mgmt_pct / 100)
        total_opex = ct + cu + ci + ch + mgmt_cost + co
        noi        = eff_gross - total_opex
        cash_flow  = noi - annual_ds
        std_d, cs_d  = get_depreciation(yr)
        total_d    = std_d + cs_d
        prop_val  *= (1 + appreciation_rate / 100)
        months_paid += 12
        loan_bal   = remaining_balance(loan_amt, rate, term, months_paid)
        rows_out.append({
            "Gross Rent":           cr,
            "Vacancy Loss":         cr * (vacancy_rate / 100),
            "Eff. Gross Income":    eff_gross,
            "Operating Expenses":   total_opex,
            "NOI":                  noi,
            "Debt Service":         annual_ds,
            "Net Cash Flow":        cash_flow,
            "Std. Depreciation":    std_d,
            "Cost Seg Bonus Depr":  cs_d,
            "Total Depreciation":   total_d,
            "Net Income / (Loss)":  cash_flow - total_d,
            "Property Value":       prop_val,
            "Loan Balance":         loan_bal,
            "Equity Value":         prop_val - loan_bal,
            "_cf_irr":              cash_flow,
        })
        cr *= (1 + rent_growth / 100)
        ct *= (1 + g_taxes / 100); cu *= (1 + g_utils / 100)
        ci *= (1 + g_ins   / 100); ch *= (1 + g_hoa   / 100)
        co *= (1 + g_other / 100)
    return rows_out

base_rows = build_rows(loan_amount, int_rate, loan_term_yrs, hold_years, purchase_price)
labels    = [f"Yr {i}" for i in range(1, hold_years + 1)]

base_cfs = [-total_cash_in] + [r["_cf_irr"] for r in base_rows]
cum_irrs = []
for k in range(1, hold_years + 1):
    sp  = sale_proceeds_at(base_rows[k - 1])
    val = irr_newton(base_cfs[:k] + [base_cfs[k] + sp])
    cum_irrs.append(f"{val:.1f}%" if val is not None else "N/A")
for i, row in enumerate(base_rows):
    row["Cum. IRR (if sold)"] = cum_irrs[i]

full_sp      = sale_proceeds_at(base_rows[-1])
full_irr_val = irr_newton(base_cfs[:-1] + [base_cfs[-1] + full_sp])
full_irr     = f"{full_irr_val:.1f}%" if full_irr_val is not None else "N/A"

# ==========================================
# DISPLAY
# ==========================================

st.markdown("---")

# KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"IRR ({hold_years}-yr hold)", full_irr)
k2.metric("Total Cash In",  fmt_d(total_cash_in))
k3.metric("Down Payment",   fmt_d(down_payment))
k4.metric("Loan Amount",    fmt_d(loan_amount))

st.markdown("---")
st.subheader(f"Annual Cash Flow Projection ({hold_years} Years)")

def make_display_df(rows, lbl):
    cols = [
        "Gross Rent","Vacancy Loss","Eff. Gross Income","Operating Expenses",
        "NOI","Debt Service","Net Cash Flow",
        "Std. Depreciation",
    ]
    if enable_costseg:
        cols += ["Cost Seg Bonus Depr","Total Depreciation"]
    cols += ["Net Income / (Loss)","Property Value","Equity Value","Cum. IRR (if sold)"]
    df = pd.DataFrame(rows, index=lbl)[cols].copy()
    for c in [x for x in cols if x != "Cum. IRR (if sold)"]:
        df[c] = df[c].apply(fmt_d)
    return df

st.dataframe(make_display_df(base_rows, labels), use_container_width=True)
csv_base = make_display_df(base_rows, labels).to_csv()
st.download_button("⬇ Download CSV", csv_base, "cashflow.csv", "text/csv")

st.markdown("---")
st.subheader("Trends")
ch1, ch2 = st.columns(2)
with ch1:
    st.caption("Net Cash Flow ($)")
    st.bar_chart(pd.DataFrame({"Net Cash Flow": [r["Net Cash Flow"] for r in base_rows]}, index=labels))
with ch2:
    st.caption("Net Income / (Loss) ($)")
    st.bar_chart(pd.DataFrame({"Net Income / (Loss)": [r["Net Income / (Loss)"] for r in base_rows]}, index=labels))

# ---- Refinance ----
st.markdown("---")
st.subheader("Refinance Analysis")
rf1, rf2, rf3, rf4, rf5 = st.columns(5)
with rf1: refi_year  = st.selectbox("Refi in Year", list(range(2, hold_years + 1)))
with rf2: refi_ltv   = st.slider("LTV (%)", 60, 80, 70, key="refi_ltv")
with rf3: refi_rate  = st.number_input("Rate (%)", 0.0, 20.0, 6.0, 0.25, key="refi_rate")
with rf4: refi_term  = st.selectbox("Term (yrs)", [30, 20, 15], key="refi_term")
with rf5: refi_fees  = st.slider("Fees (%)", 0.5, 3.0, 1.5, 0.25, key="refi_fees")

bal_before  = remaining_balance(loan_amount, int_rate, loan_term_yrs, (refi_year - 1) * 12)
pv_at_refi  = purchase_price * ((1 + appreciation_rate / 100) ** (refi_year - 1))
new_loan    = pv_at_refi * (refi_ltv / 100)
refi_fees_abs = new_loan * (refi_fees / 100)
cash_out    = new_loan - bal_before - refi_fees_abs
new_pmt     = monthly_payment(new_loan, refi_rate, refi_term)

rm1, rm2, rm3, rm4 = st.columns(4)
rm1.metric("Property Value at Refi", fmt_d(pv_at_refi))
rm2.metric("Old Loan Balance",       fmt_d(bal_before))
rm3.metric("New Loan",               fmt_d(new_loan))
rm4.metric("Net Cash-Out",           fmt_d(cash_out),
           delta=f"Fees: {fmt_d(refi_fees_abs)}", delta_color="inverse")
pm1, pm2 = st.columns(2)
pm1.metric("Old Monthly P&I", fmt_d(init_monthly_pmt) + "/mo")
pm2.metric("New Monthly P&I", fmt_d(new_pmt) + "/mo",
           delta=fmt_d(new_pmt - init_monthly_pmt) + "/mo", delta_color="inverse")

def build_post_refi_rows(loan_amt, rate, term, hold, start_pv, yr_offset):
    annual_ds = monthly_payment(loan_amt, rate, term) * 12
    prop_val  = start_pv
    cr = c_rent_base; ct = exp_taxes; cu = exp_utils; ci = exp_ins; ch = exp_hoa; co = exp_other
    for _ in range(yr_offset):
        cr *= (1 + rent_growth / 100)
        ct *= (1 + g_taxes / 100); cu *= (1 + g_utils / 100)
        ci *= (1 + g_ins   / 100); ch *= (1 + g_hoa   / 100); co *= (1 + g_other / 100)
    rows_out = []; months_paid = 0
    for yr_abs in range(yr_offset + 1, yr_offset + hold + 1):
        eff_gross  = cr * (1 - vacancy_rate / 100)
        mgmt_cost  = eff_gross * (exp_mgmt_pct / 100)
        total_opex = ct + cu + ci + ch + mgmt_cost + co
        noi        = eff_gross - total_opex
        cash_flow  = noi - annual_ds
        std_d, cs_d = get_depreciation(yr_abs)
        total_d    = std_d + cs_d
        prop_val  *= (1 + appreciation_rate / 100)
        months_paid += 12
        loan_bal   = remaining_balance(loan_amt, rate, term, months_paid)
        rows_out.append({
            "Gross Rent":          cr, "Vacancy Loss": cr * (vacancy_rate / 100),
            "Eff. Gross Income":   eff_gross, "Operating Expenses": total_opex,
            "NOI":                 noi, "Debt Service": annual_ds,
            "Net Cash Flow":       cash_flow, "Std. Depreciation": std_d,
            "Cost Seg Bonus Depr": cs_d, "Total Depreciation": total_d,
            "Net Income / (Loss)": cash_flow - total_d,
            "Property Value":      prop_val, "Loan Balance": loan_bal,
            "Equity Value":        prop_val - loan_bal, "_cf_irr": cash_flow,
        })
        cr *= (1 + rent_growth / 100)
        ct *= (1 + g_taxes / 100); cu *= (1 + g_utils / 100)
        ci *= (1 + g_ins   / 100); ch *= (1 + g_hoa   / 100); co *= (1 + g_other / 100)
    return rows_out

post_rows  = build_post_refi_rows(new_loan, refi_rate, refi_term,
                                   hold_years - (refi_year - 1), pv_at_refi, refi_year - 1)
refi_rows  = list(base_rows[:refi_year - 1]) + list(post_rows)

refi_cfs = [-total_cash_in]
for i, r in enumerate(refi_rows):
    refi_cfs.append(r["_cf_irr"] + (cash_out if i + 1 == refi_year else 0))

refi_cum_irrs = []
for k in range(1, hold_years + 1):
    sp  = sale_proceeds_at(refi_rows[k - 1])
    val = irr_newton(refi_cfs[:k] + [refi_cfs[k] + sp])
    refi_cum_irrs.append(f"{val:.1f}%" if val is not None else "N/A")
for i, row in enumerate(refi_rows):
    row["Cum. IRR (if sold)"] = refi_cum_irrs[i]

refi_sp      = sale_proceeds_at(refi_rows[-1])
refi_irr_val = irr_newton(refi_cfs[:-1] + [refi_cfs[-1] + refi_sp])
refi_irr     = f"{refi_irr_val:.1f}%" if refi_irr_val is not None else "N/A"

ic1, ic2 = st.columns(2)
ic1.metric(f"Base IRR ({hold_years}-yr)",      full_irr)
ic2.metric(f"Post-Refi IRR ({hold_years}-yr)", refi_irr,
           delta=f"{(refi_irr_val or 0) - (full_irr_val or 0):.1f}pp vs base"
           if refi_irr_val and full_irr_val else "")

refi_labels = labels.copy()
refi_labels[refi_year - 1] = f"Yr {refi_year} ⟳"
st.markdown("##### Restated Cash Flow (with Refi)")
st.dataframe(make_display_df(refi_rows, refi_labels), use_container_width=True)
st.download_button("⬇ Download refi CSV", make_display_df(refi_rows, refi_labels).to_csv(),
                   "cashflow_refi.csv", "text/csv", key="dl_refi")

st.markdown("##### Change vs Base")
delta_cols = ["Net Cash Flow","Debt Service","Net Income / (Loss)","Equity Value","Loan Balance"]
delta_data = {c: [fmt_d(refi_rows[i][c] - base_rows[i][c]) for i in range(hold_years)] for c in delta_cols}
st.dataframe(pd.DataFrame(delta_data, index=labels), use_container_width=True)

# ---- Cost Seg Impact ----
if enable_costseg:
    st.markdown("---")
    st.subheader("🏗️ Cost Segregation Impact")
    st.caption(f"Marginal tax rate: {marginal_tax_rate}% · Study cost: {fmt_d(costseg_study_cost)}")

    def std_after_tax_cf(row):
        cf = row["Net Cash Flow"]
        taxable = cf - annual_depr_std
        tax = taxable * (marginal_tax_rate / 100) if taxable > 0 else 0
        shield = abs(min(0, taxable)) * (marginal_tax_rate / 100)
        return cf - tax + shield

    cs_rows = []
    cum_benefit = 0
    for i, row in enumerate(base_rows):
        cf = row["Net Cash Flow"]; td = row["Total Depreciation"]
        taxable_cs = cf - td
        tax_cs     = taxable_cs * (marginal_tax_rate / 100) if taxable_cs > 0 else 0
        shield_cs  = abs(min(0, taxable_cs)) * (marginal_tax_rate / 100)
        atcf_cs    = cf - tax_cs + shield_cs
        atcf_std   = std_after_tax_cf(row)
        benefit    = atcf_cs - atcf_std
        cum_benefit += benefit
        cs_rows.append({
            "Year":                  labels[i],
            "Total Depreciation":    fmt_d(td),
            "vs Std Depreciation":   fmt_d(annual_depr_std),
            "Extra Depr":            fmt_d(td - annual_depr_std),
            "Net Income / (Loss)":   fmt_d(row["Net Income / (Loss)"]),
            "After-Tax CF (w/ CS)":  fmt_d(atcf_cs),
            "After-Tax CF (no CS)":  fmt_d(atcf_std),
            "Annual Tax Benefit":    fmt_d(benefit),
        })

    st.dataframe(pd.DataFrame(cs_rows).set_index("Year"), use_container_width=True)
    sb1, sb2, sb3 = st.columns(3)
    sb1.metric(f"Bonus Depr (Yr {costseg_year})", fmt_d(total_bonus))
    sb2.metric("Cumulative Tax Benefit",           fmt_d(cum_benefit))
    sb3.metric("Net Benefit after Study Cost",     fmt_d(cum_benefit - costseg_study_cost),
               delta="vs $0 without cost seg", delta_color="normal")

# ---- Assumptions ----
st.markdown("---")
with st.expander("Model assumptions"):
    a1, a2 = st.columns(2)
    with a1:
        st.write(f"- Vacancy: **{vacancy_rate}%** · Rent growth: **{rent_growth}%/yr**")
        st.write(f"- Appreciation: **{appreciation_rate}%/yr** (used as sale price for IRR)")
        st.write(f"- Mortgage: **{int_rate}%**, {loan_term_yrs}-yr · Monthly P&I: **{fmt_d(init_monthly_pmt)}**")
        st.write(f"- Building value: **{fmt_d(building_value)}** · Std depr: **{fmt_d(annual_depr_std)}/yr**")
    with a2:
        st.write(f"- Tax: **{g_taxes}%/yr** · Utils: **{g_utils}%/yr** · Ins: **{g_ins}%/yr**")
        st.write(f"- Maintenance: **{g_other}%/yr** · Mgmt: **{g_mgmt}%/yr**")
        st.write(f"- Selling costs at exit: **{selling_costs_pct}%**")
        if enable_costseg:
            st.write(f"- Cost seg bonus: **{fmt_d(total_bonus)}** applied Yr {costseg_year}")
