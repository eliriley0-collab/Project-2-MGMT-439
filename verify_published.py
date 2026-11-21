"""Verify the historical calculations from the published JSON artifacts."""
import json
from pathlib import Path
import sys

import numpy as np

from engine import BENCHMARK, INITIAL_VALUE, NAMES, START, TARGET, TICKERS, annual_risk, optimize

ROOT = Path(__file__).resolve().parent
OPTIMIZED = NAMES[2]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def estimate_inputs(record):
    mean = np.array([record["annualized_return_inputs"][ticker] for ticker in TICKERS])
    covariance = np.array(record["annualized_covariance"])
    return mean, covariance


def check_allocations(baseline):
    settings = baseline["settings"]
    require(settings["reserve"] == .05, "Baseline reserve must be 5%.")
    records = baseline["decisions"]
    require([row["date"] for row in records] == ["2024-10-31", "2025-10-31"],
            "Unexpected baseline rebalance dates.")
    descriptions = []
    for record, expected_voo in zip(records, (.20, .05)):
        saved = record["portfolios"][OPTIMIZED]
        mean, covariance = estimate_inputs(record)
        cap = annual_risk(BENCHMARK, covariance) * settings["risk_multiple"]
        np.testing.assert_allclose(cap, record["risk_cap"], rtol=0, atol=1e-12)
        prior = np.array([saved["prior_weights"][ticker] for ticker in TICKERS])
        if expected_voo == .20:
            np.testing.assert_array_equal(prior, START)
        weights, _ = optimize(prior, mean, covariance, settings["costs_bps"] / 10_000,
                              cap, settings["reserve"])
        require(saved["status"] == "Pass", f'{record["date"]}: saved portfolio did not pass.')
        np.testing.assert_allclose(weights, [saved["weights"][ticker] for ticker in TICKERS],
                                   rtol=0, atol=1e-12)
        np.testing.assert_allclose(weights, [expected_voo, 0, 0, 0, 1 - expected_voo],
                                   rtol=0, atol=1e-12)
        inverse = 1 / np.sqrt(np.diag(covariance))
        for name, expected in zip((NAMES[0], NAMES[1], NAMES[3]),
                                  (np.full(len(TICKERS), 1 / len(TICKERS)), inverse / inverse.sum(), BENCHMARK)):
            published = record["portfolios"][name]["weights"]
            np.testing.assert_allclose([published[ticker] for ticker in TICKERS], expected,
                                       rtol=0, atol=1e-12, err_msg=f'{record["date"]} {name}')
        descriptions.append(f'{record["date"]} {weights[0]:.0%} VOO / {weights[-1]:.0%} BIL')
    return "; ".join(descriptions) + "; both baselines and benchmark weights matched"


def check_performance(baseline):
    path = baseline["path"]
    require(len(path) == 24 and path[0]["date"] == "2024-10-31"
            and path[-1]["date"] == "2026-09-30", "Unexpected historical performance period.")
    expected = [("10.70%", "8.33%"), ("4.75%", "1.05%"),
                ("5.98%", "1.91%"), ("11.42%", "8.24%")]
    descriptions = []
    for name, reported in zip(NAMES, expected):
        nav = np.array([row[name] for row in path])
        require(np.isfinite(nav).all() and (nav > 0).all(), f"{name}: invalid portfolio value.")
        monthly = nav[1:] / nav[:-1] - 1
        monthly[0] = nav[1] / INITIAL_VALUE - 1  # Count the initial trade cost.
        annualized = (nav[-1] / INITIAL_VALUE) ** (12 / len(monthly)) - 1
        volatility = monthly.std(ddof=1) * np.sqrt(12)
        actual = f"{annualized:.2%}", f"{volatility:.2%}"
        require(actual == reported, f"{name}: expected {reported}, got {actual}.")
        descriptions.append(f"{name}: {actual[0]} net, {actual[1]} volatility")
    return "; ".join(descriptions)


def check_locked(baseline, locked):
    require(locked["settings"] == {**baseline["settings"], "reserve": .90},
            "The reserve floor must be the only changed input.")
    require(locked["snapshot_sha256"] == baseline["snapshot_sha256"],
            "Baseline and locked data fingerprints differ.")
    records = locked["decisions"]
    require([row["date"] for row in records] == [row["date"] for row in baseline["decisions"]],
            "Locked and baseline rebalance schedules differ.")
    base = baseline["decisions"][0]
    first = records[0]
    mean, covariance = estimate_inputs(base)
    locked_mean, locked_covariance = estimate_inputs(first)
    np.testing.assert_array_equal(mean, locked_mean)
    np.testing.assert_array_equal(covariance, locked_covariance)
    cap = annual_risk(BENCHMARK, covariance) * locked["settings"]["risk_multiple"]
    np.testing.assert_allclose(cap, first["risk_cap"], rtol=0, atol=1e-12)
    weights, best = optimize(START, mean, covariance, locked["settings"]["costs_bps"] / 10_000,
                             cap, locked["settings"]["reserve"])
    require(weights is None and best is not None and best < TARGET,
            "Expected a return shortfall with no feasible optimized allocation.")
    np.testing.assert_allclose(best, first["best_net_within_risk"], rtol=0, atol=1e-12)
    require(f"{best:.2%}" == "4.30%", "Maximum eligible return differs from the published figure.")
    for record, status in zip(records, ("Mandate infeasible", "Stopped after prior failure")):
        portfolio = record["portfolios"][OPTIMIZED]
        require(portfolio["status"] == status and portfolio["first_failure"] == first["date"]
                and "weights" not in portfolio, f'{record["date"]}: unexpected locked stop state.')
    return f'{first["date"]} infeasible; maximum eligible net return {best:.6%}; next rebalance stopped'


def main():
    print("Published calculation check (saved estimates and portfolio values; no market-data replay)")
    try:
        baseline = json.loads((ROOT / "visible-output.json").read_text())
        locked = json.loads((ROOT / "locked-reserve-90-output.json").read_text())
    except (OSError, ValueError) as exc:
        print(f"FAIL | Load published outputs | {exc}")
        return 1

    failed = False
    for label, check, inputs in (
        ("Historical allocations", check_allocations, (baseline,)),
        ("Annualized return and realized volatility", check_performance, (baseline,)),
        ("Locked 90% BIL scenario", check_locked, (baseline, locked)),
    ):
        try:
            detail = check(*inputs)
        except (AssertionError, IndexError, KeyError, TypeError, ValueError) as exc:
            print(f"FAIL | {label} | {exc}")
            failed = True
        else:
            print(f"PASS | {label} | {detail}")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
