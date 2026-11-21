# Validation and AI use

**AI use.** OpenAI Codex assisted with implementation, calculations, validation scripts and drafting documentation.

**Ownership and purpose.** Elijah Riley owns the analysis and final committee decision. This project is for education and does not constitute investment advice.

## Evidence boundary

The [data card](data-card.md) records the data sources, timing rules, revisions, redistribution caveat and cost model. The [executed default output](../visible-output.json) contains the snapshot hash and both rebalance records. Market data ends September 2026. The evaluation uses two annual rebalances and 23 monthly holding returns. There is no independent additional holdout; the signal penalty was fixed for this implementation and both observed readings were positive.

The earlier Lab 20 prototype was preserved separately as prior development evidence. It used static historical estimates and a reserve and return check. This version uses lagged rolling estimates, strategy-specific drift and costs, date-specific benchmark risk, complete modeled constraint checks and an explicit failure path. The Lab 20 files are prior evidence for the student's Edition A/B comparison. The student determines their official edition boundary.

## Verification results

Executed November 21, 2026 with Python 3.9.6, NumPy 2.0.2, pandas 2.3.3 and Streamlit 1.50.0. All four [verification test groups](../verify.py) passed.

| Check | Observed result |
| --- | --- |
| Hand calculations | Full switch from BIL to the benchmark gives 100% one-way turnover. A 5.00% gross estimate with 1% implementation cost gives 3.95% net. A perfectly correlated illustrative covariance gives 16% benchmark risk and 20% risk when two identical 20%-volatility sleeves are split evenly. |
| Data and signal timing | All five raw files reconciled to monthly adjusted prices. Changing the final market observation changed realized wealth while both earlier decisions were identical. The synthetic negative signal reduced only the two S&P 500 return inputs by two percentage points. |
| Compliance and output | Reproduction matched the saved baseline in the tested environment. Both optimized allocations passed each modeled rule. First-month NAV matched the independent entry-cost and equal-weight return calculation. |
| Failure and interface | A zero-volatility-cap stress stopped the optimizer at its first rebalance. The dashboard showed an infeasibility error and omitted the optimized allocation. Streamlit AppTest exercised the default and changed sidebar state. |

### Exploratory stress runs

All figures below refer to the October 2024 rebalance. Run each with `python reproduce.py --scenario NAME`. These checks are independent of the student’s Locked Changed-Input Record.

| Scenario | Change from default | Estimated net | Estimated volatility | Optimized target |
| --- | --- | --- | --- | --- |
| default | 36 months, 10 bps, full benchmark cap | 5.23% | 3.64% | 20% VOO, 80% BIL |
| short-window | 24 rather than 36 months | 5.87% | 0.69% | 5% VOO, 95% BIL |
| estimates | Reduce S&P 500 annual return inputs by 3 points and shrink cross-sleeve covariance 25% | 5.10% | 5.23% | 25% VOO, 5% VB, 70% BIL |
| cost | 100 rather than 10 bps | 5.04% | 3.64% | 20% VOO, 80% BIL |
| stop | Zero rather than 100% of benchmark risk | Infeasible | — | No allocation issued |

### Clean setup

A new virtual environment was created by following the README. The first install attempt failed because the execution sandbox blocked PyPI DNS. Approved external package access resolved the failure. Dependency checking and all four verification groups passed in the new environment, including default rendering and the failure view in Streamlit AppTest. The sandbox also blocked binding to localhost. With approved localhost access, the headless Streamlit command started successfully on 127.0.0.1:8765.

### Final verification

After the decision and reviewer-data updates, all five test groups passed with the local historical snapshot. Dependency checks reported no broken requirements. A separate source-only copy omitted the vendor CSV and five raw files. The synthetic CLI run and Streamlit interface test passed in that copy using the installed pinned dependencies. The historical suite was skipped in the source-only copy as designed. A cold run from the published GitHub repository and reviewer access confirmation remain pending.

The baseline JSON now carries the approved decision; the recorded allocation and performance calculations are unchanged. The locked JSON remains the frozen execution artifact. Its committee status reflects the state at execution. The subsequent approved decision is recorded below and in the memo.

## Material AI uses and dispositions

| Date | Tool/model | Contribution and disposition |
| --- | --- | --- |
| 2026-11-21 | OpenAI Codex, GPT-6 family; exact build unavailable in the interface | Compared Lab 13, Lab 15, Lab 20 and the rubric. Accepted the student's approved benchmark-relative risk cap and documented the later 5% nominal target separately from the earlier Lab 13 goal. |
| 2026-11-21 | OpenAI Codex, GPT-6 family | Implemented the optimizer, lagged signal, cost convention and app. Checked the cost formula and overlap treatment with known-answer tests, and added a future-observation perturbation and explicit infeasibility test. Accepted the implementation for classroom review with short-window and vintage limitations. |
| 2026-11-21 | OpenAI Codex, GPT-6 family | Drafted the committee memo and manifest. Elijah later approved a paper pilot with a 0% real-capital allocation. The student should record the AI output they personally checked for Video 1. |

| 2026-11-21 | OpenAI Codex, GPT-6 family | Applied Elijah’s approved pilot decision, reviewed the provider’s terms, and implemented and verified a synthetic checkout path. Exact historical replay remains conditional on access to the authorized original snapshot. |

## Locked Changed-Input Record

Status: Original GitHub upload verified; experiment executed after verification.

Parameter being changed: Treasury-bill reserve floor (Settings.reserve)

Original value: 5% (0.05)

New value: 90% (0.90)

Settings held constant: 36-month estimation window, 10 bps one-way trading cost, 5% estimated annual net return target, and benchmark-relative volatility cap.

My Independent Prediction (AI Off)

A 90% T-Bill minimum leaves very little room for equities. I expect lower potential returns and I doubt the portfolio would hit its 5% target. I also expect there to be lower risk because T-Bills are generally much less volatile compared to stocks.

Expected Impact on Committee Recommendation

I believe the committee would reject the app. I feel that the 90% focus on T-Bills is too conservative and will likely miss the target return rate, despite the lower volatility.

### GitHub verification

The original upload commit contains the student's independent prediction and expected committee effect. GitHub displayed **November 21, 2026, 1:52 p.m. EST** (18:52 UTC, minute precision). [Verified upload commit](https://github.com/eliriley0-collab/Project-2-MGMT-439/commit/d1a3f6e605eeb80da6a82fd42e6c5bf0cc79786d)

### Actual experiment results · executed November 21, 2026, 19:06:40 UTC

The reserve floor increased from 5% to 90%. The saved settings and SHA-256 check confirmed that the other inputs and market snapshot matched the [baseline output](../visible-output.json). The [changed output](../locked-reserve-90-output.json) includes the commit reference, run timestamp and rebalance records.

| Rebalance | Baseline optimization | 90% reserve floor |
| --- | --- | --- |
| 2024-10-31 | Pass. 20% VOO, 80% BIL. Estimated net return 5.23%. Estimated volatility 3.64% vs. a 12.89% cap. Turnover 20.00%, modeled cost $20.00. | Mandate infeasible. Highest estimated net return among grid mixes meeting structural and risk limits was 4.30%, about 0.70 percentage points below target. No optimized allocation or trade was issued. |
| 2025-10-31 | Pass. 5% VOO, 95% BIL. Estimated net return 5.53%. Estimated volatility 0.68% vs. a 9.72% cap. Turnover 17.55%, modeled cost $18.91. | Process remained stopped after the October 2024 failure. No optimized allocation, risk estimate, turnover or cost was produced. |

**Direction and diagnosis.** At the first rebalance, the highest net return available within the structural and risk limits fell from 9.89% to 4.30%. The inability to reach 5% agrees with the prediction. The predicted decline in optimized volatility could not be evaluated because the changed run produced no compliant optimized portfolio. The first failure came from a return shortfall among allocations that met the structural and risk limits.

**Observed decision effect.** The 5% reserve setting produced eligible historical targets at both dates. The 90% setting triggered the process stop at the first date, so the changed scenario supplied no portfolio for committee authorization. Elijah subsequently approved a **12-month paper-trading pilot** under the original **5% BIL minimum**, with a **$100,000 simulated account**, quarterly monitoring, annual rebalancing subject to compliance review, and a **0% real-capital allocation range**. The committee will reassess after 12 months. The pilot grants no authority to trade live. [Approved decision memo](decision-memo.md)

To reproduce the changed calculation in the project directory, use the same virtual environment and run:

```sh
python -c 'from dataclasses import replace; from engine import Settings, evaluate, load_data; import json; print(json.dumps(evaluate(*load_data(), replace(Settings(), reserve=.90)), indent=2, allow_nan=False))'
```
