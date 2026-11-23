"""Streamlit committee dashboard."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

import engine
from engine import NAMES, PILOT_DECISION, Settings, demo_data, evaluate, load_data, performance

st.set_page_config(page_title="Portfolio Committee | FIN 439", layout="wide")


ROOT = Path(__file__).resolve().parent
SAVED = "Saved historical results"
SYNTHETIC = "Interactive synthetic demo"
LOCAL = "Interactive local historical analysis"


@st.cache_data
def scenario(settings, synthetic):
    data = demo_data() if synthetic else load_data()
    return evaluate(*data, settings)


def percent(value):
    return "—" if value is None else f"{value:.2%}"


def show_locked(baseline, locked):
    st.subheader("Saved locked stress test")
    st.write(f"The BIL reserve floor rose from {baseline['settings']['reserve']:.0%} to "
             f"{locked['settings']['reserve']:.0%}. All other inputs were held constant.")
    first = locked["decisions"][0]
    st.error(f"{first['date']}: mandate infeasible. The highest eligible estimated net return "
             f"was {percent(first['best_net_within_risk'])} versus the 5.00% target.")
    st.table(pd.DataFrame([
        {"Rebalance": record["date"], "Status": record["portfolios"][NAMES[2]]["status"]}
        for record in locked["decisions"]
    ]))
    st.caption("The optimizer issued no allocation, so there is no optimized volatility to compare.")
    st.markdown(f"[Original AI-off prediction commit]({locked['prediction_commit']})")


def show_saved_summary(result):
    st.subheader("Historical optimized allocations")
    st.table(pd.DataFrame([
        {"Rebalance": record["date"], **{
            ticker: percent(weight)
            for ticker, weight in record["portfolios"][NAMES[2]]["weights"].items()
        }}
        for record in result["decisions"]
    ]))


def show_results(result, settings, *, reference=None, locked=None, synthetic=False):
    dates = [item["date"] for item in result["decisions"]]
    selected = st.selectbox("Rebalance date", dates, index=len(dates) - 1)
    index = dates.index(selected)
    record = result["decisions"][index]
    optimized = record["portfolios"][NAMES[2]]
    cols = st.columns(4)
    cols[0].metric("Optimizer status", optimized["status"])
    cols[1].metric("Estimated volatility cap", percent(record["risk_cap"]))
    cols[2].metric("Optimized estimated net", percent(optimized.get("estimated_net")))
    cols[3].metric("Optimized estimated volatility", percent(optimized.get("estimated_volatility")))
    st.caption(f"Estimate cutoff {record['asof']} · Snapshot through {result['market_data_through']} · "
               f"{settings.months}-month window · {settings.costs_bps} bps one-way")
    if "weights" not in optimized:
        st.error(f"Optimized process stopped on {optimized['first_failure']}. The mandate was infeasible on the allocation grid.")
        if record["best_net_within_risk"] is not None:
            st.write(f"Highest estimated net return among allocations within the structural and risk limits "
                     f"was {percent(record['best_net_within_risk'])} versus the 5.00% target.")
        elif optimized["status"] == "Mandate infeasible":
            st.write("No allocation satisfied the structural and risk limits together.")

    overview, compliance, stress, methodology = st.tabs(
        ["Portfolio comparison", "Mandate compliance", "Locked 90% BIL result" if locked else "Stress comparison", "Mandate & data"]
    )
    with overview:
        st.subheader("Target allocations at rebalance")
        weights = pd.DataFrame({name: item["weights"] for name, item in record["portfolios"].items()
                                if "weights" in item}).T
        st.bar_chart(weights, stack=True, horizontal=True, y_label="Portfolio weight")
        summaries = []
        for name, item in record["portfolios"].items():
            summaries.append({
                "Portfolio": name, "Verdict": item["status"], "Combined S&P 500": percent(item.get("sp500_weight")),
                "Est. net return": percent(item.get("estimated_net")), "Est. volatility": percent(item.get("estimated_volatility")),
                "Turnover": percent(item.get("turnover")),
                "Trading cost": f"${item['cost_usd']:,.2f}" if "cost_usd" in item else "—",
            })
        st.dataframe(pd.DataFrame(summaries), hide_index=True)
        st.subheader(f"{'Synthetic evaluation' if synthetic else 'Historical evaluation'} · growth of $1, net of modeled costs")
        metrics, growth = performance(result)
        if metrics.empty:
            st.info("There is no completed common holding period for this comparison.")
        else:
            st.line_chart(growth.set_axis(pd.to_datetime(growth.index)))
            st.caption(f"Common comparison period {growth.index[0]} through {growth.index[-1]}. "
                       "Peak-to-trough drawdown is measured at monthly observations, relative to starting capital.")
            st.dataframe(metrics.style.format("{:.2%}", na_rep="—"))

    with compliance:
        st.subheader("Rule-by-rule verdict")
        rows = {}
        for name in NAMES[:3]:
            for item in record["portfolios"][name].get("checks", []):
                row = rows.setdefault(item["rule"], {"Rule": item["rule"], "Limit": item["limit"]})
                label = "Pass" if item["pass"] else "Fail"
                measured = percent(item["value"]) if item["rule"] != "Annual rebalance schedule" else selected
                row[name] = f"{label} · {measured}"
        st.dataframe(pd.DataFrame(rows.values()).reindex(columns=["Rule", "Limit", *NAMES[:3]]).fillna(
            "No portfolio"
        ), hide_index=True)
        st.caption("Liquidity is modeled from approved ETF classifications. The issuer cap is applied to direct holdings. "
                   "These checks evaluate the rebalance target. Weights drift between scheduled reviews.")

    with stress:
        if locked:
            show_locked(result, locked)
        else:
            st.subheader("Default versus current scenario")
            base = reference["decisions"][index]
            comparison = []
            for label, item in [("Default", base), ("Current scenario", record)]:
                portfolio = item["portfolios"][NAMES[2]]
                comparison.append({
                    "Scenario": label, "Status": portfolio["status"], "Risk cap": percent(item["risk_cap"]),
                    "Estimated net": percent(portfolio.get("estimated_net")),
                    "Estimated volatility": percent(portfolio.get("estimated_volatility")),
                    "Maximum eligible net": percent(item["best_net_within_risk"]),
                    **{ticker: percent(value) for ticker, value in portfolio.get("weights", {}).items()},
                })
            st.dataframe(pd.DataFrame(comparison).fillna("—"), hide_index=True)
            st.caption("Change assumptions, the trailing window, costs, or constraints in the sidebar. "
                       "These exploratory scenarios are separate from the student's locked experiment.")
            st.download_button("Download scenario settings and result", json.dumps(result, indent=2, allow_nan=False),
                               "scenario-result.json", "application/json")

    with methodology:
        st.subheader("Quarterly pilot review")
        st.write("Monitor net returns, estimated and realized volatility, costs, liquidity, concentration, "
                 "and mandate compliance. Stop issuing new allocations if the optimizer cannot satisfy "
                 "the mandate. Conduct the annual simulated rebalance only after compliance review.")
        st.subheader("Investment mandate")
        st.write("Seven-year planning horizon with annual October reviews. Seek at least 5% nominal annual "
                 "estimated net return while minimizing estimated volatility. Universe VOO, SPY, BND, VB, BIL. "
                 "The annually rebalanced 60% SPY / 40% BND reference sets the volatility cap using the same "
                 "trailing covariance estimate. See the compliance tab for the approved trading rules.")
        st.subheader("S&P 500 overlap")
        st.write(f"VOO and SPY track the same index. Holding both duplicates large-cap and indirect issuer exposure. "
                 f"The risk model incorporates their shared covariance and the dashboard sums the two weights. "
                 f"Estimated correlation at this cutoff was {record['voo_spy_correlation']:.4f}. "
                 "Fund wrappers can differ in fees, liquidity and execution.")
        st.subheader("Point-in-time signal")
        st.write(f"SPY six-month price momentum was {percent(record['spy_signal'])} at {record['asof']}. "
                 "The signal uses SPY month-end closes through the prior month. A negative reading lowers both "
                 "S&P 500 funds’ annual return estimates by 2 percentage points. A nonnegative reading leaves "
                 "them unchanged. The penalty is a fixed classroom assumption.")
        st.caption("Snapshot source and revision limitations, exclusions and cost conventions are in the repository data card.")


def scenario_settings():
    with st.sidebar:
        st.header("Scenario inputs")
        st.caption("Mandate defaults are shown on first launch. Stress limits can be tightened.")
        with st.form("settings"):
            months = st.selectbox("Estimation window (months)", [36, 24, 12])
            costs = st.number_input("One-way trading cost (bps)", 0, 500, 10, step=5)
            equity = st.slider("S&P 500 annual return adjustment (percentage points)", -20.0, 10.0, 0.0, .5)
            shrink = st.slider("Covariance shrinkage (%)", 0, 50, 0, 5)
            reserve = st.slider("Treasury-bill floor (%)", 5, 100, 5, 5)
            cap = st.slider("Volatility cap (% of benchmark)", 0, 100, 100, 5)
            st.form_submit_button("Apply scenario", type="primary")
        settings = Settings(months, costs, reserve / 100, cap / 100, equity / 100, shrink / 100)
        st.caption("Education only. Approved real-capital allocation range 0% throughout the paper pilot.")
    return settings


st.title("Portfolio Committee")
st.caption("FIN 439 · Project 2 · Strategy evaluation for a hypothetical $100,000 account")
st.info(f"{PILOT_DECISION}. Simulated capital $100,000. Original BIL floor 5%. "
        "Annual rebalancing subject to compliance review. Reassess after 12 months before considering funding. "
        "The pilot does not authorize live trading.")


snapshot_available = (engine.DATA / "prices.csv").is_file() and all(
    (engine.DATA / "sources" / f"{ticker}.json").is_file() for ticker in engine.TICKERS
)
views = [SAVED, SYNTHETIC]
if snapshot_available:
    views.append(LOCAL)
view = st.radio("Dashboard view", views, horizontal=True)

try:
    if view == SAVED:
        st.caption("Published historical analysis · read-only saved results")
        result = json.loads((ROOT / "visible-output.json").read_text())
        locked = json.loads((ROOT / "locked-reserve-90-output.json").read_text())
        settings = Settings(**result["settings"])
    else:
        synthetic = view == SYNTHETIC
        if synthetic:
            st.warning("Synthetic demo data. All charts, estimates and scenario downloads in this view "
                       "use generated prices.")
        else:
            st.caption("Authorized local historical snapshot · interactive calculations")
        settings = scenario_settings()
        reference = scenario(Settings(), synthetic)
        result = scenario(settings, synthetic)
except (ValueError, OSError, KeyError) as exc:
    st.error(f"Analysis stopped. {exc}")
    st.stop()

if view == SAVED:
    show_saved_summary(result)
    show_results(result, settings, locked=locked)
else:
    show_results(result, settings, reference=reference, synthetic=synthetic)
