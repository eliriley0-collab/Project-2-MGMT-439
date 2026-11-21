"""Reproduce the committee analysis from the bundled market snapshot."""
from dataclasses import asdict, dataclass
from functools import lru_cache
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
TICKERS = ["VOO", "SPY", "BND", "VB", "BIL"]
BENCHMARK = np.array([0, .6, .4, 0, 0])
START = np.array([0, 0, 0, 0, 1])
# Universe metadata. Exchange trading within five business days is a model assumption.
LIQUID = np.ones(5)
RESERVE = START
DIRECT_ISSUERS = {}  # The confirmed universe contains only diversified ETFs.
TARGET = .05
INITIAL_VALUE = 100_000
PILOT_DECISION = "PILOT · 12-month paper trading · quarterly monitoring · 0% real capital"

FIRST_TRADE = pd.Timestamp("2024-10-31")
TOL = 1e-10
NAMES = ["Equal weight", "Inverse volatility", "Minimum volatility", "60/40 benchmark"]


@dataclass(frozen=True)
class Settings:
    months: int = 36
    costs_bps: float = 10
    reserve: float = .05
    risk_multiple: float = 1
    equity_shift: float = 0
    shrink: float = 0


def demo_data():
    """Original deterministic synthetic prices for a clean checkout without market data."""
    dates = pd.date_range("2021-09-30", "2026-09-30", freq="ME", name="Date")
    month = np.arange(len(dates))
    equity = 100 * np.exp(.009 * month + .05 * np.sin(month))
    prices = pd.DataFrame({
        "VOO": equity,
        "SPY": equity * (1 + .001 * np.sin(month / 4)),
        "BND": 100 * np.exp(.002 * month + .012 * np.sin(2 * month)),
        "VB": 100 * np.exp(.007 * month + .06 * np.sin(month + .5)),
        "BIL": 100 * np.exp(.003 * month + .0005 * np.sin(month)),
    }, index=dates)
    prices.attrs["synthetic_demo"] = True
    return prices, prices["SPY"]


def load_data(*, allow_demo=False):
    if allow_demo and not (DATA / "prices.csv").exists():
        return demo_data()
    prices = pd.read_csv(DATA / "prices.csv", index_col="Date", parse_dates=True)
    if list(prices.columns) != TICKERS or not prices.index.equals(
        pd.date_range(prices.index[0], prices.index[-1], freq="ME", name="Date")
    ) or not np.isfinite(prices).all().all() or (prices <= 0).any().any():
        raise ValueError("Price snapshot must contain complete positive aligned monthly data.")
    manifest = json.loads((DATA / "sources/provenance.json").read_text())
    if [item["ticker"] for item in manifest] != TICKERS:
        raise ValueError("Provenance manifest does not match the approved universe.")
    for item in manifest:
        ticker = item["ticker"]
        payload = (DATA / "sources" / f"{ticker}.json").read_bytes()
        if sha256(payload).hexdigest() != item["sha256"]:
            raise ValueError(f"Raw source checksum mismatch for {ticker}.")
        result = json.loads(payload)["chart"]["result"][0]
        dates = pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_convert(
            result["meta"]["exchangeTimezoneName"]
        ).tz_localize(None).normalize()
        quotes = pd.DataFrame({
            "adjusted": result["indicators"]["adjclose"][0]["adjclose"],
            "close": result["indicators"]["quote"][0]["close"],
        }, index=dates).dropna(subset=["adjusted"])
        monthly = quotes.resample("ME").last()
        if not monthly.index.equals(prices.index) or not np.allclose(
            monthly["adjusted"], prices[ticker], rtol=0, atol=1e-10
        ):
            raise ValueError(f"Monthly adjusted closes do not reconcile for {ticker}.")
        if ticker == "SPY":
            if result.get("events", {}).get("splits") or not np.isfinite(
                monthly["close"]
            ).all() or (monthly["close"] <= 0).any():
                raise ValueError("SPY signal requires complete positive closes with no splits.")
            signal_prices = monthly["close"]
    return prices, signal_prices


@lru_cache(maxsize=1)
def weight_grid():
    # Stars and bars enumerate every fully invested, long-only mix in 5-point steps.
    return np.array([
        np.diff((-1, *bars, 24)) - 1 for bars in combinations(range(24), 4)
    ]) / 20


def turnover(weights, previous):
    return .5 * np.abs(weights - previous).sum(axis=-1)


def annual_risk(weights, covariance):
    return np.sqrt(np.maximum(np.einsum("...i,ij,...j->...", weights, covariance, weights), 0))


def net_estimate(weights, previous, mean, rate):
    cost = turnover(weights, previous) * rate
    return (1 - cost) * (1 + weights @ mean) - 1


def estimates(returns, signal_prices, asof, settings):
    history = returns.loc[:asof].tail(settings.months)
    if len(history) != settings.months:
        raise ValueError("Insufficient trailing returns for the requested window.")
    covariance = history.cov().to_numpy() * 12
    shrink_target = np.diag(np.diag(covariance))
    shrink_target[:2, :2] = covariance[:2, :2]  # Preserve shared S&P 500 exposure.
    covariance = (1 - settings.shrink) * covariance + settings.shrink * shrink_target
    mean = history.mean().to_numpy() * 12
    closes = signal_prices.loc[:asof]
    signal = float(closes.iloc[-1] / closes.iloc[-7] - 1)
    mean[:2] += settings.equity_shift - (.02 if signal < 0 else 0)
    return mean, covariance, signal


def issuer_exposure(weights):
    return max((float(weights[positions].sum()) for positions in DIRECT_ISSUERS.values()), default=0)


def checks(weights, previous, mean, covariance, rate, risk_cap, reserve, scheduled):
    values = [
        ("Fully invested", weights.sum(), "equals 100%", abs(weights.sum() - 1) <= TOL),
        ("Long-only / no borrowing or shorts", weights.min(), "minimum weight ≥ 0%", weights.min() >= -TOL),
        ("Eligible instruments / no derivatives", 1., "100% approved ETFs", True),
        ("Cash or T-bill reserve", weights @ RESERVE, f"≥ {reserve:.1%}", weights @ RESERVE >= reserve - TOL),
        ("Five-business-day liquidity (modeled)", weights @ LIQUID, "≥ 95%", weights @ LIQUID >= .95 - TOL),
        ("Largest direct company issuer", issuer_exposure(weights), "≤ 10%", issuer_exposure(weights) <= .10 + TOL),
        ("Annual rebalance schedule", int(scheduled), "scheduled date", scheduled),
        ("Estimated annualized volatility", annual_risk(weights, covariance), f"≤ {risk_cap:.2%}",
         annual_risk(weights, covariance) <= risk_cap + TOL),
        ("Estimated annual net return target", net_estimate(weights, previous, mean, rate), "≥ 5%",
         net_estimate(weights, previous, mean, rate) >= TARGET - TOL),
    ]
    return [{"rule": rule, "value": float(value), "limit": limit, "pass": bool(passed)}
            for rule, value, limit, passed in values]


def optimize(previous, mean, covariance, rate, risk_cap, reserve):
    grid = weight_grid()
    risks = annual_risk(grid, covariance)
    net = net_estimate(grid, previous, mean, rate)
    valid = (grid @ RESERVE >= reserve - TOL) & (grid @ LIQUID >= .95 - TOL)
    for positions in DIRECT_ISSUERS.values():
        valid &= grid[:, positions].sum(axis=1) <= .10 + TOL
    admissible = valid & (risks <= risk_cap + TOL)
    feasible = np.flatnonzero(admissible & (net >= TARGET - TOL))
    best_net = float(net[admissible].max()) if admissible.any() else None
    if not feasible.size:
        return None, best_net
    # Primary objective is minimum risk. Break exact ties with lower turnover.
    order = np.lexsort((turnover(grid[feasible], previous), risks[feasible]))
    return grid[feasible[order[0]]], best_net


def evaluate(prices, signal_prices, settings=Settings()):
    if not (settings.months in (12, 24, 36) and 0 <= settings.costs_bps <= 500
            and 0.05 <= settings.reserve <= 1 and 0 <= settings.risk_multiple <= 1
            and abs(settings.equity_shift) <= .5 and 0 <= settings.shrink <= .5):
        raise ValueError("Scenario inputs are outside supported bounds.")
    returns = prices.pct_change(fill_method=None).iloc[1:]
    holdings = {name: START.copy() for name in NAMES}
    nav = dict.fromkeys(NAMES, float(INITIAL_VALUE))
    rate = settings.costs_bps / 10_000
    decisions, path = [], [{ "date": FIRST_TRADE.date().isoformat(), **nav }]
    first_failure = None
    for date in returns.index[returns.index >= FIRST_TRADE]:
        if date > FIRST_TRADE:
            for name, weights in holdings.items():
                if nav[name] is None:
                    continue
                growth = weights * (1 + returns.loc[date].to_numpy())
                nav[name] *= float(growth.sum())
                holdings[name] = growth / growth.sum()
            path.append({"date": date.date().isoformat(), **nav})
        if date.month != FIRST_TRADE.month:
            continue
        # The prior month is the information cutoff. Current close is the execution proxy.
        asof = prices.index[prices.index.get_loc(date) - 1]
        mean, covariance, signal = estimates(returns, signal_prices, asof, settings)
        benchmark_risk = float(annual_risk(BENCHMARK, covariance))
        risk_cap = benchmark_risk * settings.risk_multiple
        inverse = 1 / np.sqrt(np.diag(covariance))
        optimized, best_net = (None, None) if first_failure else optimize(
            holdings[NAMES[2]], mean, covariance, rate, risk_cap, settings.reserve
        )
        record = {
            "date": date.date().isoformat(), "asof": asof.date().isoformat(),
            "benchmark_risk": benchmark_risk, "risk_cap": risk_cap, "spy_signal": signal,
            "voo_spy_correlation": float(covariance[0, 1] / np.sqrt(covariance[0, 0] * covariance[1, 1])),
            "best_net_within_risk": best_net, "portfolios": {},
            "annualized_return_inputs": dict(zip(TICKERS, map(float, mean))),
            "annualized_covariance": covariance.tolist(),
        }
        equal = np.full(len(TICKERS), 1 / len(TICKERS))
        for name, weights in zip(NAMES, (equal, inverse / inverse.sum(), optimized, BENCHMARK)):
            if weights is None:
                status = "Stopped after prior failure" if first_failure else "Mandate infeasible"
                first_failure = first_failure or record["date"]
                record["portfolios"][name] = {"status": status, "first_failure": first_failure}
                nav[name] = None
                continue
            previous = holdings[name]
            traded = float(turnover(weights, previous))
            # The benchmark is an investable reference and pays the same modeled cost.
            audit = checks(weights, previous, mean, covariance, rate, risk_cap, settings.reserve,
                           date.month == FIRST_TRADE.month and date.is_month_end)
            status = "Pass" if all(rule["pass"] for rule in audit) else "Fail"
            if name == NAMES[2] and status != "Pass":
                raise RuntimeError("Optimizer produced a portfolio that failed independent rule checks.")
            record["portfolios"][name] = {
                "status": status, "weights": dict(zip(TICKERS, map(float, weights))),
                "prior_weights": dict(zip(TICKERS, map(float, previous))),
                "checks": audit, "turnover": traded, "cost_fraction": traded * rate,
                "cost_usd": nav[name] * traded * rate, "sp500_weight": float(weights[:2].sum()),
                "estimated_net": float(net_estimate(weights, previous, mean, rate)),
                "estimated_volatility": float(annual_risk(weights, covariance)),
            }
            nav[name] *= 1 - traded * rate
            holdings[name] = weights
            # Store post-trade NAV. Performance uses starting capital to capture entry costs.
            path[-1][name] = nav[name]
        decisions.append(record)
    synthetic = prices.attrs.get("synthetic_demo", False)
    snapshot = prices.to_csv().encode() if synthetic else (DATA / "prices.csv").read_bytes()
    result = {
        "settings": asdict(settings), "market_data_through": prices.index[-1].date().isoformat(),
        "snapshot_sha256": sha256(snapshot).hexdigest(),
        "committee_decision": PILOT_DECISION,
        "decisions": decisions, "path": path,
    }
    if synthetic:
        result["data_source"] = "Synthetic demo · workflow verification only"
    return result


def performance(result):
    path = pd.DataFrame(result["path"]).set_index("date")
    # Without a full optimized path, show the common completed comparison period.
    path = path.dropna(how="any")
    growth = path / INITIAL_VALUE
    if len(path) < 2:
        return pd.DataFrame(), growth
    monthly = path.pct_change(fill_method=None).iloc[1:]
    monthly.iloc[0] = growth.iloc[1] - 1  # Include initial implementation cost.
    peak = growth.cummax().clip(lower=1)
    return pd.DataFrame({
        "Cumulative net": growth.iloc[-1] - 1,
        "Annualized net": growth.iloc[-1] ** (12 / (len(path) - 1)) - 1,
        "Realized vol.": monthly.std() * np.sqrt(12),
        "Max drawdown": (growth / peak - 1).min(),
        "Tracking error": monthly.sub(monthly[NAMES[-1]], axis=0).std() * np.sqrt(12),
    }), growth
