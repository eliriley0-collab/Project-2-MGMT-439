# Portfolio Committee · Purdue FIN 439 Project 2

**AI use.** I used ChatGPT and OpenAI Codex for requirements review, implementation, troubleshooting, verification and documentation.

**Ownership and purpose.** Elijah Riley owns the analysis and made the final committee decision. This project is for education and does not constitute investment advice.

## Committee decision

**PILOT** the original 5% Treasury-bill reserve strategy in a 12-month paper-trading pilot. Use a $100,000 simulated account, quarterly monitoring, annual rebalancing subject to compliance review, and a 0% real-capital allocation. Reassess after 12 months. The pilot does not authorize live trading. [Decision memo](docs/decision-memo.md)

## Run the app

Use Python 3.9–3.12 and open a terminal in this directory. On macOS or Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows PowerShell, use `py -3 -m venv .venv` and `.venv\Scripts\python.exe -m pip install -r requirements.txt`, then `.venv\Scripts\python.exe -m streamlit run app.py`. Open the local URL Streamlit prints. Installation uses PyPI. The app requires no credentials or live market calls. The dashboard opens in **Saved historical results**. Review the October 2024 and 2025 allocations, historical performance against the benchmark, and the locked 90% BIL result. This read-only view displays the published run and needs no vendor files.

Use **Dashboard view** to choose **Interactive synthetic demo** for scenario controls using generated prices. When the authorized snapshot is in the local paths listed in the [data card](docs/data-card.md), **Interactive local historical analysis** also appears. In either interactive view, apply settings in the sidebar and use **Stress comparison** to compare and download the scenario. The optimizer stops at the first infeasible rebalance.

## Verify the published historical calculations

After installing the requirements, run:

```sh
python verify_published.py
```

The command prints PASS or FAIL for historical allocations, annualized net returns and realized volatility, and the locked 90% BIL scenario. A failed check exits with a nonzero status. It reruns allocation rules from saved estimates and pretrade weights, recalculates performance from saved portfolio values, and checks that the locked scenario stopped. It needs no original market data or API credentials. Full historical reproduction starts from the original market-data snapshot and follows the instructions below.

## Reproduce the analysis

Run the same workflow with the distributable example:

```sh
python reproduce.py --demo
python verify.py
```

For exact historical replay, place an authorized copy of the original snapshot in the local paths listed in the [data card](docs/data-card.md). Restart the app after adding the authorized inputs. Use data acquired and shared under applicable permissions. The public project does not include the Yahoo price archive or automate its collection. The exact historical replay requires separately authorized access to the original vintage; the synthetic demo verifies the workflow.

```sh
python reproduce.py > reproduced-output.json
python verify.py
```

[Visible executed output](visible-output.json) contains the data fingerprint, inputs, each rebalance and estimate cutoff, results and the approved committee decision. Historical CLI scenarios `short-window`, `estimates`, `cost` and `stop` can be passed to `reproduce.py --scenario` as exploratory checks.

- [Decision memo](docs/decision-memo.md)
- [Validation and AI use](docs/validation-and-ai-use.md)
- [Data and signal card](docs/data-card.md)
- [Submission manifest](docs/manifest.md)
- [Video links and corrected transcripts](docs/manifest.md#videos-and-transcripts)
