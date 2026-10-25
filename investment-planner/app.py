import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from engine import InvestmentEngine, ASSET_ORDER

st.set_page_config(page_title="Interactive Investment Planning System", layout="wide")

st.title("Interactive Investment Planning System")
st.caption("Illustrative projections - not financial advice. Mutual fund investments are subject to market risks.")

engine = InvestmentEngine()

with st.sidebar:
    st.header("Inputs")
    amount = st.number_input("Investment amount (Rs.)", min_value=1000.0, value=200000.0, step=1000.0)
    horizon_years = st.slider("Investment duration (years)", min_value=1, max_value=30, value=10)
    risk = st.slider("Risk tolerance (1 = Low, 5 = High)", min_value=1, max_value=5, value=3)
    liquidity_pct = st.slider("Liquidity need within 1 year (%)", min_value=0, max_value=100, value=10)

res = engine.allocate(amount, horizon_years, risk, liquidity_pct)
proj = engine.project(res["allocation_pct"], horizon_years)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Recommended Allocation")
    alloc_df = pd.DataFrame([
        {"Asset": k, "Allocation %": round(res["allocation_pct"].get(k,0), 2), "Amount (Rs.)": round(res["allocation_rupees"].get(k,0), 0)}
        for k in ASSET_ORDER if res["allocation_pct"].get(k,0) > 0.01
    ])
    st.dataframe(alloc_df, use_container_width=True, hide_index=True)
    # Donut
    labels = alloc_df["Asset"]
    values = alloc_df["Allocation %"]
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
    fig.update_layout(margin=dict(t=0,b=0,l=0,r=0))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Projection (illustrative)")
    p = proj["monte_carlo"]
    c1,c2,c3 = st.columns(3)
    c1.metric("Pessimistic (approx)", f"Rs. {amount * proj['scenarios']['pessimistic']['fv_per_unit']:,.0f}")
    c2.metric("Base (expected)", f"Rs. {amount * proj['scenarios']['base']['fv_per_unit']:,.0f}")
    c3.metric("Optimistic (approx)", f"Rs. {amount * proj['scenarios']['optimistic']['fv_per_unit']:,.0f}")
    st.write(f"Monte Carlo (1000 paths): P10 = {p['p10']:.2f}x, P50 = {p['p50']:.2f}x, P90 = {p['p90']:.2f}x of amount")
    st.write(f"Inflation-adjusted (P50): {proj['inflation_adjusted_p50_multiple']:.2f}x")
    # Simple bar comparison
    comp = pd.DataFrame({
        "Scenario": ["Pessimistic", "Base", "Optimistic"],
        "Value (Rs.)": [amount*proj['scenarios'][s]['fv_per_unit'] for s in ["pessimistic","base","optimistic"]]
    })
    fig2 = px.bar(comp, x="Scenario", y="Value (Rs.)")
    fig2.update_layout(margin=dict(t=0,b=0,l=0,r=0))
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Explanation")
st.info(res["explanation"])
if res["warnings"]:
    for w in res["warnings"]:
        st.warning(w)

st.caption("Disclaimer: Projections are illustrative and are not financial advice. Past performance does not predict future returns.")
