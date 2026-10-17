# Banking Onboarding Lab — Streamlit + Polars

**Live app: <https://app-uqpgve5fduneydt94nw42m.streamlit.app/>**

An interactive product analytics portfolio app based on **250,000 synthetic users, 5,901,194 events and 698,846 transactions**. No real Monzo customer data or affiliation.

The dashboard presents the completed analysis using compact saved extracts. It does not require the 164 MB dataset archive, a database server, API key, or HTML report to start.

## Live deployment

The dashboard runs on Streamlit Community Cloud at <https://app-uqpgve5fduneydt94nw42m.streamlit.app/>, deployed from `main` with Python 3.12 and no secrets. Pushing to `main` rebuilds it automatically; the first visit after a period of inactivity is a cold start and takes a few seconds.

`streamlit_app.py` and `requirements.txt` sit at the repository root, and the app reads `data/dashboard`, `reports` and `docs` at startup, so re-creating this deployment needs only three settings:

1. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
2. Create an app from this repository on the `main` branch with **Main file path** `streamlit_app.py`.
3. In advanced settings select **Python 3.12**, then deploy.

Streamlit Community Cloud hosts the running app; GitHub only stores the code. GitHub Pages cannot run a Python Streamlit app.

Tested against the pinned `streamlit==1.66.0`, `polars==2.0.0`, `plotly==7.1.0`: all six pages and their interactions pass Streamlit AppTest, and the deployed app serves 250,000 assigned users with 48.43% control against 52.31% treatment.

Official deployment guidance: [repository/entrypoint selection](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [file organisation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization), [dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

## Run locally

From the repository root:

```bash
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` on Windows PowerShell or `source .venv/bin/activate` on macOS/Linux, then:

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open the local URL printed by Streamlit. You do not need to run the data pipeline first.

## Dashboard sections

| Page | What you can explore |
| --- | --- |
| Overview | Activation KPIs, absolute lift, confidence interval, daily/weekly trends |
| Customer journey | Funnel rates/counts and descriptive device/channel cuts |
| Experiment | Primary and secondary outcomes, uncertainty, guardrails and allocation |
| Retention | Variant and signup-cohort filters, weighted return rates, CSV download |
| Data quality | Duplicates, quarantine, late records and SQL integrity checks |
| Methodology | Experiment plan, assumptions, dictionary and downloadable readout |

The overall decision is fixed to the original intention-to-treat analysis. Segment and cohort filters do not recompute or change its estimates. This avoids implying a significant subgroup result from exploratory cuts.

## Repository contents

```text
streamlit_app.py
requirements.txt
.streamlit/config.toml
data/dashboard/              # Small CSV extracts used by the app
data/manifest.json           # Dataset counts and provenance
data/samples/                # Small CSV examples
reports/                    # Summary JSON, markdown, charts and HTML readout
docs/                       # Analysis methods and dictionary
src/                        # Full generator and analytical pipeline
sql/                        # Reusable analytical queries
notebooks/                  # Three executed notebooks
config/simulation.yaml
requirements-analysis.txt   # Optional full-analysis dependencies
run_pipeline.py
tests_app/                  # Dashboard interaction checks
tests/                      # Full analytical tests; require generated data
```

`data/raw/` and `data/processed/` hold about 164 MB of partitioned Parquet and are excluded by `.gitignore`; `python run_pipeline.py --generate` recreates them. `reports/experiment_readout.html` is the self-contained visual report of that same analysis.

## Reproduce the full analysis (optional)

This is a local development task, not a deployment startup step:

```bash
python -m pip install -r requirements-analysis.txt
python run_pipeline.py --generate --notebooks
python -m pytest tests -q
```

The pipeline refreshes the dashboard extracts and reports. Commit updated small outputs if you want the hosted app to show a new analysis. Keep `data/raw/`, `data/processed/` and DuckDB files out of Git. The regenerated documentation writes to `ANALYSIS_GUIDE.md`, preserving this deployment README.

Test the app independently:

```bash
python -m pip install pytest
python -m pytest tests_app -q
```

## Polars usage and limitations

Project code uses Polars for DataFrames; Plotly receives lists/arrays directly. There are no direct Pandas imports or conversions in the app. Streamlit and statsmodels may use Pandas internally as a dependency.

Observed synthetic activation is 48.43% in control and 52.31% in treatment, a 3.88 pp difference. Treatment mechanisms are deliberately encoded in the simulation. This demonstrates analysis and engineering, not real customer impact or real large-scale experimentation experience. Fraud flags are proxies, and background retention behaviour is deliberately simplified.

The full pipeline guide is in `ANALYSIS_GUIDE.md`; its large-dataset instructions apply after regenerating data or using the original complete archive. The dashboard itself requires only `requirements.txt` and the included extracts.
