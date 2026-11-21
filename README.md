# Portfolio Committee · Purdue FIN 439 Project 2

**AI use.** OpenAI Codex assisted with requirements review, implementation, test development, and documentation.

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

On Windows PowerShell, use `py -3 -m venv .venv` and `.venv\Scripts\python.exe -m pip install -r requirements.txt`, then `.venv\Scripts\python.exe -m streamlit run app.py`. Open the local URL Streamlit prints. Installation uses PyPI. The app requires no credentials or live market calls. A clean checkout without licensed historical inputs uses an original, clearly labeled synthetic demonstration. The saved historical outputs and memo are the evidence for the decision.

Use **Rebalance date** to inspect either historical decision, **Mandate compliance** for each rule, and **Scenario inputs** to stress estimates, trailing windows, transaction costs, and constraints. Apply the scenario in the sidebar. **Stress comparison** shows the default and active inputs' results and supports a JSON download. The optimized strategy stops at the first infeasible rebalance.

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

[Visible executed output](visible-output.json) contains the data fingerprint, inputs, each rebalance and estimate cutoff, results and the pending committee decision. Historical CLI scenarios `short-window`, `estimates`, `cost` and `stop` can be passed to `reproduce.py --scenario` as exploratory checks.

- [Decision memo](docs/decision-memo.md)
- [Validation and AI use](docs/validation-and-ai-use.md)
- [Data and signal card](docs/data-card.md)
- [Submission manifest](docs/manifest.md)
