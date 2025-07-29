
import streamlit as st
import pandas as pd
import numpy as np

st.title("🔋 Battery-as-a-Service Optimizer")

st.markdown("Upload your Excel file with **Inputs** and **8760_Load** sheets.")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file, engine="openpyxl")
    inputs_df = xls.parse("Inputs").set_index("Parameter")
    load_df = xls.parse("8760_Load")

    # Read assumptions
    inputs = inputs_df["Value"].to_dict()
    capacity_kwh = inputs["Battery Capacity (kWh)"]
    power_kw = inputs["Power (kW)"]
    capex_per_kwh = inputs["CAPEX (€/kWh)"]
    capex_total = capacity_kwh * capex_per_kwh
    lifetime_years = int(inputs["Project Lifetime (years)"])
    irr_target = inputs["Target IRR"]
    dod = inputs["DoD (%)"] / 100
    cycles_total = inputs["Cycles"]
    eol_pct = inputs["EOL Capacity (%)"] / 100

    # Model capacity degradation and throughput
    cycles_per_year = cycles_total / lifetime_years
    results = []
    cumulative_throughput = 0

    for year in range(1, lifetime_years + 1):
        degradation = 1 - ((1 - eol_pct) / (lifetime_years - 1)) * (year - 1)
        capacity = capacity_kwh * degradation
        usable_energy = capacity * dod
        annual_throughput = usable_energy * cycles_per_year
        cumulative_throughput += annual_throughput
        discount_factor = 1 / ((1 + irr_target) ** year)
        discounted_energy = annual_throughput * discount_factor
        results.append([year, capacity, usable_energy, annual_throughput, cumulative_throughput, discounted_energy])

    df_results = pd.DataFrame(results, columns=[
        "Year", "Capacity (kWh)", "Usable Energy (kWh)", "Annual Throughput (kWh)", 
        "Cumulative Throughput (kWh)", "Discounted Energy (kWh)"
    ])

    total_discounted_energy = df_results["Discounted Energy (kWh)"].sum()
    lcos_irr = capex_total / total_discounted_energy

    # Calculate grid baseline cost
    load_df["Grid Cost (€)"] = load_df["Load (kWh)"] * load_df["Grid Price (€/kWh)"]
    baseline_cost = load_df["Grid Cost (€)"].sum()

    # Calculate customer BaaS cost
    energy_billed = df_results["Annual Throughput (kWh)"].sum()
    customer_baas_cost = energy_billed * lcos_irr
    net_savings = baseline_cost - customer_baas_cost

    # Show summary
    st.subheader("📊 Results Summary")
    st.write({
        "Target IRR": f"{irr_target * 100:.1f}%",
        "LCOS (€/kWh)": round(lcos_irr, 4),
        "Total CAPEX (€)": round(capex_total, 2),
        "Discounted Energy (kWh)": round(total_discounted_energy),
        "Customer Grid Cost (€)": round(baseline_cost, 2),
        "Customer BaaS Cost (€)": round(customer_baas_cost, 2),
        "Customer Net Savings (€)": round(net_savings, 2)
    })

    # Show annual degradation table
    st.subheader("🔄 Battery Degradation Over Time")
    st.dataframe(df_results.style.format(precision=2))
