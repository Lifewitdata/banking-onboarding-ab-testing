> **Repository note:** this guide describes the full analysis pipeline. `README.md` covers the Streamlit dashboard and its deployment. Raw and processed Parquet datasets are not committed; run the pipeline with `--generate` to recreate them locally. The self-contained HTML report in `reports/experiment_readout.html` is included.

# Digital Banking Onboarding & Activation Experiment

**A large synthetic product analytics project built with Polars, SQL and Python.**

This independent portfolio project is inspired by a product data science job description. It uses no Monzo customer data, has no Monzo affiliation, and does not represent a real deployed experiment.

## What is included

- 250,000 users and randomised assignments.
- 5,901,194 product event rows, 698,846 transactions, 16,517 support contacts and 982 fraud flags.
- Partitioned, compressed Parquet datasets; 100-row CSV previews; row-count/hash manifest.
- Polars data cleaning, DuckDB SQL models, experiment inference, seven charts, three executed notebooks and a self-contained HTML readout.
- Data dictionary, tracking plan, experimental assumptions, quality checks, tests, and Tableau-ready extracts with a dashboard build guide.

## Start here

1. Open `reports/experiment_readout.html` for the complete visual report.
2. Read `docs/experiment_plan.md` and `docs/simulation_assumptions.md` before interpreting results.
3. Explore the executed notebooks in order: quality/EDA, funnel/retention, experiment evaluation.
4. Use `data/samples/` for small CSV previews; full data are in `data/raw/` as Parquet.

## Observed synthetic results

Seven-day activation: **48.43% control → 52.31% treatment**.
Absolute difference **3.88 pp**, 95% CI **3.48–4.27 pp**.

Decision: **SIMULATED LAUNCH CRITERIA MET**. The generator intentionally changes behaviour in treatment. These results demonstrate valid analysis of a simulated experiment; they do not establish a real business improvement.

## Installation

Tested with Python 3.12.14. Python 3.11+ is recommended. Use a virtual environment and install the pinned versions:

```bash
python -m venv .venv
```

Windows PowerShell: `.venv\Scripts\Activate.ps1`. macOS/Linux: `source .venv/bin/activate`.

```bash
python -m pip install -r requirements.txt
```

Run commands from the project directory. An internet connection is required to install dependencies; the dataset and analysis themselves do not require external APIs or accounts.

## Reproduce

Rebuild analytical outputs from supplied raw data:

```bash
python run_pipeline.py
python -m pytest -q
```

Regenerate all datasets and execute all notebooks:

```bash
python run_pipeline.py --generate --notebooks
```

The notebook runner executes actual cells through in-process IPython and captures tables, text and images without requiring network sockets. No system-wide Jupyter changes are required. Executed notebooks are already included and can also be opened normally in Jupyter or VS Code. Raw generation replaces this project's `data/raw/*/part-*.parquet` partitions; keep a copy before changing assumptions.

For a smaller learning run, change `n_users` to 25000 in `config/simulation.yaml`, then regenerate. Sample size changes may cause guardrail uncertainty; the code reports the decision rather than forcing it to pass.

DuckDB stores local absolute view paths, so its cache is excluded from the download and Git. `python -m src.build_database` followed by `python -m src.build_metrics` recreates it after moving the project. The normal pipeline already does this.

## Step-by-step pipeline

| Stage | Entry point | Purpose |
| --- | --- | --- |
| Generate | `python -m src.generate_data` | Batch synthetic users, events and transaction-linked outcomes |
| Validate | `python -m src.validate_data` | Polars lazy scans, event deduplication and quarantine |
| Database | `python -m src.build_database` | DuckDB views over Parquet |
| Metrics | `python -m src.build_metrics` | Integrity checks, user outcomes, funnels, cohorts and segments |
| Statistics | `python -m src.analyse_experiment` | Power, SRM, effect intervals, harm guardrails and decision |
| Charts | `python -m src.create_charts` | Seven static charts using NumPy arrays from Polars |
| Documentation | `python -m src.build_documentation` | Current dictionary, README and HTML readout |
| Notebooks | `python -m src.build_notebooks` | Build and execute all three notebooks |

## Skills and library choices

Polars is the only DataFrame library used directly by project code and notebooks. It handles generation tables, lazy scans, cleaning, joins, aggregation, exports and validation. DuckDB preserves the SQL component and returns results with `.pl()`. NumPy provides random sampling and numerical arrays; SciPy/statsmodels perform inference; Matplotlib plots arrays.

No project code imports Pandas or calls `.to_pandas()`. Statsmodels may install/import Pandas internally as a dependency; this project does not use Pandas DataFrames. Seaborn is omitted to keep the plotting path direct and clear.

## Resource use and packaging

Designed for a local laptop with roughly 4–8 GB of available RAM and at least 2 GB free disk for environment and outputs; actual usage depends on versions and thread settings. These are planning suggestions, not measured minimums. Generation batches users; event cleaning uses lazy scans but sorting/deduplication can still require memory. Raw and cleaned Parquet datasets are deliberately kept out of source control by `.gitignore`; regenerate them with `--generate`.

Commit source, executed notebooks, reports including the HTML readout, dashboard aggregates, sample CSVs and documentation. Keep large raw/processed data out of Git because the generator reproduces them. See `README.md` for the dashboard deployment steps.

## Portfolio wording

After you have reproduced and understood the analysis, a truthful project description is:

“Built a synthetic banking onboarding experiment analysis using Polars, DuckDB SQL and Python across 250,000 users and 5,901,194 events; evaluated activation, funnel conversion and guardrails with intention-to-treat analysis and confidence intervals.”

Do not describe the simulated uplift as a delivered commercial result or claim real large-scale banking A/B testing experience.

## Technical references

- [Polars lazy sources and sinks](https://docs.pola.rs/user-guide/lazy/sources_sinks/)
- [DuckDB integration with Polars](https://duckdb.org/docs/stable/guides/python/polars)
- [Statsmodels independent-proportion intervals](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.confint_proportions_2indep.html)
- [SciPy chi-square goodness-of-fit test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.chisquare.html)
