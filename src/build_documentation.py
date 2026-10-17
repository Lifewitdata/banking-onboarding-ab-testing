"""Create a current README, schema dictionary and self-contained HTML readout."""
import base64
import html
import json
import re
import sys
from importlib.metadata import version
import polars as pl
from src.common import ROOT,markdown,save_json

DESCRIPTIONS={
 'user_id':'Synthetic user key; joins users, assignment and activity.',
 'signup_at':'Signup timestamp, UTC.', 'channel':'Synthetic acquisition channel.',
 'device':'Primary synthetic signup device.', 'age_band':'Synthetic adult age band; no actual personal data.',
 'variant':'Randomised control/treatment assignment.', 'assigned_at':'Assignment time, before onboarding exposure.',
 'eligible':'True for every generated user; defines the ITT population.',
 'event_id':'Event identifier; raw data contain deliberate duplicate IDs.',
 'event_name':'Instrumented action; see event tracking plan.',
 'event_at':'Occurrence timestamp, UTC.', 'ingested_at':'Arrival timestamp, UTC; may be delayed.',
 'transaction_id':'Transaction key, referenced by fraud flags.', 'transaction_at':'Transaction timestamp, UTC.',
 'kind':'funding or payment.', 'status':'success or failed; only successful payments activate.',
 'amount_gbp':'Synthetic GBP amount; two decimal places.',
 'contact_id':'Unique support contact key.', 'contact_at':'Support contact timestamp, UTC.',
 'reason':'Synthetic contact reason.', 'resolution_hours':'Synthetic time to resolve contact in hours.',
 'flag_id':'Unique fraud flag key.', 'flag_at':'Flag timestamp, after linked payment.',
 'flag_type':'Synthetic alert category; not confirmed fraud.',
 'issue':'Injected tracking issue label; audit only, excluded from cleaning and outcome calculation.'}

def inline(s):
    s=html.escape(s)
    s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
    return re.sub(r'`([^`]+)`',r'<code>\1</code>',s)

def simple_markdown(md):
    result=[];table=False
    for line in md.splitlines():
        if line.startswith('|'):
            if set(line.replace('|','').replace(' ','').replace(':','')) <= {'-'}:continue
            if not table:result.append('<div class="table-wrap"><table>');table=True
            result.append('<tr>'+''.join('<td>'+inline(c.strip())+'</td>' for c in line.strip('|').split('|'))+'</tr>');continue
        if table:result.append('</table></div>');table=False
        if line.startswith('# '):result.append('<h1>'+inline(line[2:])+'</h1>')
        elif line.startswith('## '):result.append('<h2>'+inline(line[3:])+'</h2>')
        elif line.startswith('- '):result.append('<p class="bullet">• '+inline(line[2:])+'</p>')
        elif line.strip():result.append('<p>'+inline(line)+'</p>')
    if table:result.append('</table></div>')
    return '\n'.join(result)

def build():
    manifest=json.loads((ROOT/'data/manifest.json').read_text());counts=manifest['counts']
    summary=json.loads((ROOT/'reports/experiment_summary.json').read_text());p=summary['primary']
    profile=pl.read_csv(ROOT/'data/processed/column_profile.csv')
    profile=profile.with_columns(pl.col('column').replace_strict(DESCRIPTIONS,default='See event tracking and experiment plan.').alias('description'))
    dictionary='# Data dictionary\n\nAll timestamps are UTC, represented as timezone-naive Parquet datetimes. All data are synthetic.\n\n'
    for table in counts:
        dictionary+=f'## {table}\n\n'+markdown(profile.filter(pl.col('table')==table).select('column','dtype','null_count','description'))+'\n\n'
    dictionary+='## Derived analytical tables\n\n`user_metrics` is one row per assigned user. Seven-day binary outcomes are integer 0/1, fraud uses a 30-day window, and maturity flags determine eligibility for each observation horizon. `restricted_days_to_payment` is the smaller of first-payment delay and seven days, assigning seven days to non-payers. Lifecycle timestamps are nullable for users who never reach the stage.\n\nDashboard CSV grains: funnel = variant × step; experiment_results = metric; guardrails = metric; segments = dimension × segment × variant; retention = variant × signup week × return week; daily_activation = variant × signup date; baseline_balance = dimension × category.\n'
    (ROOT/'docs/data_dictionary.md').write_text(dictionary)
    readme=f'''# Digital Banking Onboarding & Activation Experiment

**A large synthetic product analytics project built with Polars, SQL and Python.**

This independent portfolio project is inspired by a product data science job description. It uses no Monzo customer data, has no Monzo affiliation, and does not represent a real deployed experiment.

## What is included

- {counts['users']:,} users and randomised assignments.
- {counts['events']:,} product event rows, {counts['transactions']:,} transactions, {counts['support']:,} support contacts and {counts['fraud']:,} fraud flags.
- Partitioned, compressed Parquet datasets; 100-row CSV previews; row-count/hash manifest.
- Polars data cleaning, DuckDB SQL models, experiment inference, seven charts, three executed notebooks and a self-contained HTML readout.
- Data dictionary, tracking plan, experimental assumptions, quality checks, tests, and Tableau-ready extracts with a dashboard build guide.

## Start here

1. Open `reports/experiment_readout.html` for the complete visual report.
2. Read `docs/experiment_plan.md` and `docs/simulation_assumptions.md` before interpreting results.
3. Explore the executed notebooks in order: quality/EDA, funnel/retention, experiment evaluation.
4. Use `data/samples/` for small CSV previews; full data are in `data/raw/` as Parquet.

## Observed synthetic results

Seven-day activation: **{p['control_rate']:.2%} control → {p['treatment_rate']:.2%} treatment**.
Absolute difference **{p['difference']*100:.2f} pp**, 95% CI **{p['ci_low']*100:.2f}–{p['ci_high']*100:.2f} pp**.

Decision: **{summary['decision']}**. The generator intentionally changes behaviour in treatment. These results demonstrate valid analysis of a simulated experiment; they do not establish a real business improvement.

## Installation

Tested with Python {sys.version.split()[0]}. Python 3.11+ is recommended. Use a virtual environment and install the pinned versions:

```bash
python -m venv .venv
```

Windows PowerShell: `.venv\\Scripts\\Activate.ps1`. macOS/Linux: `source .venv/bin/activate`.

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

“Built a synthetic banking onboarding experiment analysis using Polars, DuckDB SQL and Python across {counts['users']:,} users and {counts['events']:,} events; evaluated activation, funnel conversion and guardrails with intention-to-treat analysis and confidence intervals.”

Do not describe the simulated uplift as a delivered commercial result or claim real large-scale banking A/B testing experience.

## Technical references

- [Polars lazy sources and sinks](https://docs.pola.rs/user-guide/lazy/sources_sinks/)
- [DuckDB integration with Polars](https://duckdb.org/docs/stable/guides/python/polars)
- [Statsmodels independent-proportion intervals](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.confint_proportions_2indep.html)
- [SciPy chi-square goodness-of-fit test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.chisquare.html)
'''
    (ROOT/'ANALYSIS_GUIDE.md').write_text(readme)
    body=simple_markdown((ROOT/'reports/experiment_readout.md').read_text())
    figures=''
    for path in sorted((ROOT/'reports/figures').glob('*.png')):
        encoded=base64.b64encode(path.read_bytes()).decode()
        figures+=f'<figure><img alt="{html.escape(path.stem)}" src="data:image/png;base64,{encoded}"></figure>'
    css='''body{font:16px/1.65 system-ui,sans-serif;color:#213047;background:#f1f4f8;margin:0}main{max-width:1080px;margin:36px auto;padding:44px;background:white;border-radius:16px}h1{font-size:34px;line-height:1.2;letter-spacing:-1px}h2{margin-top:36px;color:#23324a;border-bottom:2px solid #e55d69;padding-bottom:8px}p{max-width:95ch}code{background:#eef2f6;padding:2px 5px;border-radius:4px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}td{padding:9px;border-bottom:1px solid #e3e9f0;text-align:left;white-space:nowrap}tr:first-child{background:#26354b;color:white;font-weight:600}tr:nth-child(even){background:#f5f7fa}img{width:100%;height:auto}figure{margin:24px 0}.badge{font-size:12px;letter-spacing:2px;color:#bc3546;font-weight:bold}.bullet{margin:6px 0}@media(max-width:700px){main{margin:0;padding:22px}h1{font-size:27px}}@media print{main{margin:0;padding:0}figure{break-inside:avoid}}'''
    page=f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Banking onboarding experiment — synthetic study</title><style>{css}</style></head><body><main><div class="badge">PRODUCT ANALYTICS / POLARS + SQL</div>{body}<h2>Visual analysis</h2>{figures}</main></body></html>'
    (ROOT/'reports/experiment_readout.html').write_text(page)
    save_json('reports/environment.json',{'python':sys.version,'packages':{n:version(n) for n in ['polars','duckdb','pyarrow','numpy','scipy','statsmodels','matplotlib','nbformat','nbclient','pytest']}})
    print('README, dictionary and self-contained HTML report created.')

if __name__=='__main__':build()
