# Committee decision memo

**AI use.** I used ChatGPT and OpenAI Codex to develop, troubleshoot and verify the application. Codex also assisted with this memo.

**Ownership and purpose.** Elijah Riley owns the analysis and made the final committee decision. This project is for education and does not constitute investment advice.

## Committee ask

Approve a **12-month paper-trading pilot** under the original **5% minimum Treasury-bill allocation**. Start with a **$100,000 simulated portfolio** and a **0% real-capital allocation range throughout the pilot**. The simulated account follows the optimizer’s mandate-compliant weights. Review the account quarterly and rebalance annually, subject to compliance review. This approval covers paper trading only. Live trading requires a separate committee decision after reassessment at month 12.

## Evidence and rationale

| Strategy | Annualized net return | Realized annualized volatility |
| --- | ---: | ---: |
| Constrained minimum volatility | 5.98% | 1.91% |
| 60% SPY / 40% BND benchmark | 11.42% | 8.24% |

The evaluation covers **23 monthly holding returns and two annual rebalances**. The optimizer cleared the 5% estimated net return target and benchmark-relative risk cap at both dates. Its historical targets were **20% VOO / 80% BIL** in October 2024 and **5% VOO / 95% BIL** in October 2025. Future simulated weights depend on the eligible inputs at each rebalance. [Baseline output](../visible-output.json)

The optimized strategy achieved the 5% annualized net target in the observed sample and took considerably less realized risk than the benchmark. It also gave up substantial return relative to the benchmark. Two decisions provide limited evidence for a seven-year mandate, and the historical allocations depended heavily on BIL and the choice of estimation window. A paper pilot allows prospective observation before either full adoption or a funded allocation.

In the locked experiment, tightening the BIL minimum to **90%** made the mandate infeasible at the first rebalance. The highest estimated net return among grid allocations meeting the structural and risk limits was **4.30%**. The optimizer issued no allocation and remained stopped. This result demonstrates the stop rule and shows how sensitive feasibility can be to the reserve constraint. [Locked experiment output](../locked-reserve-90-output.json)

## Monitoring and stop conditions

Each quarter, review net returns, estimated and realized volatility, modeled trading costs, five-business-day liquidity, direct issuer and combined S&P 500 concentration, and mandate compliance. Review proposed weights before the annual simulated rebalance. **Stop issuing new allocations if the optimizer cannot satisfy the mandate.** At month 12, review the prospective evidence and decide whether to extend, stop, or separately consider a funded allocation. The pilot commits no real capital.
