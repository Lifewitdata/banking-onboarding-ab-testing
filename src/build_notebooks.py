"""Build explanatory notebooks and execute them with the current interpreter."""
import json
import os
from pathlib import Path
import sys
import tempfile
import nbformat as nbf
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output
from src.common import ROOT

SETUP='''from pathlib import Path
import sys, json
import numpy as np
import polars as pl
from IPython.display import display, Markdown, Image
ROOT = Path.cwd() if (Path.cwd() / "config/simulation.yaml").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT))
from src.common import config
pl.Config.set_tbl_rows(16)
pl.Config.set_tbl_cols(14)
print("Polars:", pl.__version__)
'''

def md(text):return nbf.v4.new_markdown_cell(text)
def code(text):return nbf.v4.new_code_cell(text)

def quality_notebook():
    return [md('''# 01 · Data quality and exploratory analysis

**Synthetic banking dataset. No Monzo customer data or real experiment.**

Question: are the records trustworthy enough to compare activation between randomised groups? We inspect the unit of observation before aggregation, keep denominator-changing decisions explicit, and use Polars throughout. Run `python run_pipeline.py` first if the derived outputs are absent.'''),code(SETUP),
    md('## 1. Dataset inventory and reproducibility\nRead the manifest and profile. Event rows are not users; transaction rows are not activated users.'),
    code('''manifest=json.loads((ROOT/'data/manifest.json').read_text())
display(pl.read_csv(ROOT/'data/processed/table_profile.csv'))
print('Synthetic:',manifest['synthetic'],'Seed:',manifest['seed'])
print('Raw bytes:',sum(x['bytes'] for x in manifest['files']))'''),
    md('## 2. Schema and missing fields\nA null user ID in telemetry is a quality problem. A null first-payment timestamp in the derived population is a valid non-activation outcome.'),
    code('''profile=pl.read_csv(ROOT/'data/processed/column_profile.csv')
display(profile)
display(profile.filter(pl.col('null_count')>0))
users=pl.scan_parquet(ROOT/'data/raw/users/*.parquet')
assignments=pl.scan_parquet(ROOT/'data/raw/assignments/*.parquet')
events=pl.scan_parquet(ROOT/'data/raw/events/*.parquet')
tx=pl.scan_parquet(ROOT/'data/raw/transactions/*.parquet')'''),
    md('## 3. Key uniqueness and table grain'),
    code('''for name,lf,key in [('users',users,'user_id'),('assignments',assignments,'user_id'),('transactions',tx,'transaction_id'),('raw events',events,'event_id')]:
    print(name,lf.select(pl.len().alias('rows'),pl.col(key).n_unique().alias('distinct_keys')).collect().to_dicts())'''),
    md('## 4. Event taxonomy\nDo not sum `account_funded` and `funding_confirmed` to count funded customers. Both describe the same funding moment.'),
    code("display(events.group_by('event_name').len().sort('len',descending=True).collect())"),
    md('## 5. Duplicate, invalid and delayed records\nCleaning deduplicates event IDs and quarantines invalid references/times. Late arrivals remain usable at the final snapshot.'),
    code('''quality=json.loads((ROOT/'reports/quality_summary.json').read_text())
display(pl.read_csv(ROOT/'data/processed/event_quality.csv'))
print('Duplicate rows removed:',quality['duplicate_rows_removed'])
print('Late events retained:',quality['delayed_events_retained'])
clean=pl.scan_parquet(ROOT/'data/processed/events_clean.parquet')
display(events.select(((pl.col('ingested_at')-pl.col('event_at')).dt.total_seconds()/3600).quantile(.99).alias('p99_ingestion_hours')).collect())'''),
    md('## 6. Independent injection audit\nThis log was not used by the cleaning logic. It allows us to check that known issues were caught.'),
    code("display(pl.scan_parquet(ROOT/'data/raw/tracking_issues/*.parquet').group_by('issue').len().sort('issue').collect())"),
    md('## 7. Acquisition mix'),
    code("display(users.group_by('channel').len().with_columns((pl.col('len')/pl.col('len').sum()).alias('share')).sort('len',descending=True).collect())"),
    md('## 8. Device and synthetic age distribution\nThese categories are invented and do not describe Monzo customers.'),
    code("display(users.group_by('device').len().collect()); display(users.group_by('age_band').len().sort('age_band').collect())"),
    md('## 9. Enrolment coverage and group sizes'),
    code('''display(users.select(pl.col('signup_at').min().alias('first_signup'),pl.col('signup_at').max().alias('last_signup')).collect())
display(assignments.group_by('variant').len().collect())
display(Image(filename=str(ROOT/'reports/figures/03_daily_trends.png')))'''),
    md('## 10. Baseline balance\nInspect standardised differences rather than hunting for baseline p-values. Assignment is independent of the observed profile in the generator.'),
    code("balance=pl.read_csv(ROOT/'data/dashboard/baseline_balance.csv'); display(balance); print('Largest absolute SMD:',balance['standardised_difference'].abs().max())"),
    md('## 11. Transactions: status, type and amount\nFailed attempts must not contribute to activation or payment value.'),
    code('''display(tx.group_by('kind','status').agg(pl.len().alias('transactions'),pl.col('amount_gbp').sum().alias('total_gbp'),pl.col('amount_gbp').median().alias('median_gbp'),pl.col('amount_gbp').quantile(.99).alias('p99_gbp')).sort('kind','status').collect())
display(Image(filename=str(ROOT/'reports/figures/07_distributions.png')))'''),
    md('## 12. Heavy users and verification retries\nAn event-heavy user must not get more weight in the experiment than a quiet user.'),
    code('''per_user=clean.group_by('user_id').len()
display(per_user.select(pl.col('len').min().alias('min_events'),pl.col('len').median().alias('median_events'),pl.col('len').quantile(.99).alias('p99_events'),pl.col('len').max().alias('max_events')).collect())
attempts=clean.filter(pl.col('event_name')=='verification_attempted').group_by('user_id').len()
display(attempts.group_by('len').agg(pl.len().alias('users')).sort('len').collect())'''),
    md('## 13. Support and fraud proxies'),
    code('''display(pl.scan_parquet(ROOT/'data/raw/support/*.parquet').group_by('reason').agg(pl.len().alias('contacts'),pl.col('resolution_hours').median().alias('median_resolution_hours')).collect())
display(pl.scan_parquet(ROOT/'data/raw/fraud/*.parquet').group_by('flag_type').len().collect())'''),
    md('## 14. Relational and temporal integrity'),
    code("checks=pl.read_csv(ROOT/'data/processed/sql_quality_checks.csv'); display(checks); assert checks['failures'].sum()==0"),
    md('''## Interpretation

The raw event table is intentionally imperfect. Cleaning preserves all assigned users and trustworthy transaction outcomes. We do not drop customers because they have bad ancillary telemetry. Amount distributions and app-return rates reflect generator choices; they are not banking benchmarks. The next notebook uses a single row per assigned user to avoid fan-out bias.''')]

def funnel_notebook():
    return [md('''# 02 · Onboarding funnel and retention

**Synthetic study.** Which stage loses customers, how quickly do they progress, and how do descriptive return patterns vary?'''),code(SETUP),
    code('''from src.build_database import connect,build
from src.build_metrics import build as build_metrics
if not (ROOT/'data/processed/banking.duckdb').exists():
    build();build_metrics()
con=connect(read_only=True)
metrics=pl.read_parquet(ROOT/'data/processed/user_metrics.parquet')
display(metrics.select('user_id','variant','verified_7d','funded_7d','activated_7d').head())'''),
    md('## 1. Define the common seven-day denominator\nAll assigned users with full follow-up remain in the denominator, even if they never verify or fund.'),
    code("display(metrics.group_by('variant').agg(pl.len().alias('assigned'),pl.col('mature_7d').sum().alias('eligible_7d'),pl.col('mature_30d').sum().alias('eligible_30d')))"),
    md('## 2. SQL funnel with window functions\nThe previous-step conversion uses `LAG`; overall conversion uses the first step. Read the source SQL before running it.'),
    code("query=(ROOT/'sql/03_onboarding_funnel.sql').read_text(); print(query); funnel=con.execute(query).pl(); display(funnel)"),
    code("display(Image(filename=str(ROOT/'reports/figures/01_funnel.png')))"),
    md('## 3. Absolute drop-off counts\nA large drop-off stage is a place to investigate. It does not prove the cause or guarantee that optimising it improves business value.'),
    code("display(funnel.with_columns((pl.col('users').shift(1).over('variant')-pl.col('users')).alias('lost_from_previous_step')))") ,
    md('## 4. Time between stages\nThese medians are conditional on reaching each stage and are descriptive. They are not causal comparisons between equivalent populations.'),
    code('''display(metrics.group_by('variant').agg(
    ((pl.col('verified_at')-pl.col('assigned_at')).dt.total_seconds()/3600).median().alias('median_hours_to_verification_completers'),
    ((pl.col('funded_at')-pl.col('verified_at')).dt.total_seconds()/3600).median().alias('median_hours_verification_to_funding'),
    ((pl.col('first_payment_at')-pl.col('funded_at')).dt.total_seconds()/3600).median().alias('median_hours_funding_to_payment')))'''),
    md('## 5. Cumulative activation with all assigned users\nThis plot keeps non-activators in the denominator. It is preferable to comparing only the average time among users who activated.'),
    code("display(Image(filename=str(ROOT/'reports/figures/06_time_to_activation.png')))"),
    md('## 6. Channel and device cuts\nThese are exploratory estimates, not a formal treatment-interaction test.'),
    code("segments=con.execute((ROOT/'sql/06_segment_analysis.sql').read_text()).pl(); display(segments); display(Image(filename=str(ROOT/'reports/figures/05_segments.png')))") ,
    md('## 7. Funnel by acquisition channel\nThis deeper cut can identify where to ask product questions; it does not explain why a channel differs.'),
    code('''display(con.sql("""SELECT channel,variant,count(*) AS assigned,
 avg(verified_7d) AS verification_rate,avg(funded_7d) AS funding_rate,
 avg(activated_7d) AS activation_rate
 FROM user_metrics WHERE mature_7d GROUP BY ALL ORDER BY channel,variant""").pl())'''),
    md('## 8. Weekly return definition\nWeek 1 is days 7–13, week 2 days 14–20, and week 3 days 21–27 since assignment. Return means an app-open or successful payment. Every denominator has enough observation time.'),
    code("retention=con.execute((ROOT/'sql/05_retention_cohorts.sql').read_text()).pl(); display(retention.head(18))"),
    code("display(Image(filename=str(ROOT/'reports/figures/04_retention_cohorts.png')))"),
    md('## 9. Weighted cohort aggregation\nUse sums of returning and eligible users; averaging cohort percentages can overweight small cohorts.'),
    code("display(retention.group_by('variant','week').agg(pl.col('returning_users').sum(),pl.col('eligible_users').sum()).with_columns((pl.col('returning_users')/pl.col('eligible_users')).alias('weighted_return_rate')).sort('variant','week'))"),
    md('## 10. Event count versus customer count\nActivity is useful context, but the experimental unit remains the user.'),
    code('''display(con.sql("""SELECT p.variant,count(*) AS payment_transactions,
 count(DISTINCT t.user_id) AS unique_payers
 FROM raw_transactions t JOIN population p USING(user_id)
 WHERE t.kind='payment' AND t.status='success'
 GROUP BY p.variant""").pl())
con.close()'''),
    md('''## Interpretation

Use the overall experiment to evaluate the treatment. Use funnel stages to understand where programmed changes appear, and segment cuts to propose further questions. Background app activity is deliberately simplified and may generate high return rates. Do not interpret these as retention benchmarks or claim a statistically established segment-specific benefit.''')]

def experiment_notebook():
    return [md('''# 03 · A/B experiment evaluation

**Synthetic fixed-horizon experiment.** We evaluate the predeclared primary outcome, effect size and harm thresholds. Read `docs/experiment_plan.md` before interpreting outputs.'''),code(SETUP),
    code('''from scipy import stats
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize
from src.analyse_experiment import compare_binary
cfg=config()['experiment']
df=pl.read_parquet(ROOT/'data/processed/user_metrics.parquet')
summary=json.loads((ROOT/'reports/experiment_summary.json').read_text())'''),
    md('## 1. Sample-size planning\nBaseline 45%, 1 pp absolute MDE, 80% power and two-sided alpha .05. This is a planning approximation for independent users.'),
    code('''effect=abs(proportion_effectsize(cfg['baseline_activation']+cfg['minimum_detectable_effect'],cfg['baseline_activation']))
n=NormalIndPower().solve_power(effect_size=effect,power=cfg['power'],alpha=cfg['alpha'],ratio=1)
print('Required users per arm:',int(np.ceil(n)))
print('Observed assignment sizes:',df.group_by('variant').len().to_dicts())'''),
    md('## 2. Sample-ratio mismatch\nA failed allocation check would block interpreting the primary result until investigated. The threshold is .001, set before analysis.'),
    code('''counts=df.group_by('variant').len().sort('variant')
observed=counts['len'].to_numpy()
expected=np.array([1-cfg['allocation'],cfg['allocation']])*observed.sum()
stat,p=stats.chisquare(observed,f_exp=expected)
display(counts); print('SRM statistic:',stat,'p:',p,'passes:',p>=cfg['srm_alpha'])'''),
    md('## 3. Independent user-level aggregation\nCount each customer once. Failed payments and payments outside seven days do not count.'),
    code("arm=df.filter(pl.col('mature_7d')).group_by('variant').agg(pl.len().alias('n'),pl.col('activated_7d').sum().alias('activated')); display(arm)"),
    md('## 4. Primary effect, interval and test\nThe Newcombe interval estimates treatment minus control. The z test evaluates equal proportions. Relative lift and percentage-point lift are different quantities.'),
    code('''c=arm.filter(pl.col('variant')=='control').row(0,named=True)
t=arm.filter(pl.col('variant')=='treatment').row(0,named=True)
primary=compare_binary(c['activated'],c['n'],t['activated'],t['n'])
display(pl.DataFrame([primary]))
print(f"Absolute lift: {primary['difference']*100:.3f} pp")
print(f"Relative lift: {primary['relative_lift']:.2%}")
print(f"95% CI: [{primary['ci_low']*100:.3f}, {primary['ci_high']*100:.3f}] pp")'''),
    md('## 5. Secondary efficacy outcomes\nVerification and funding are secondary. Holm correction is applied across those two p-values; their displayed 95% intervals remain descriptive, unadjusted intervals.'),
    code("results=pl.read_csv(ROOT/'data/dashboard/experiment_results.csv'); display(results); display(Image(filename=str(ROOT/'reports/figures/02_experiment_effects.png')))") ,
    md('## 6. Guardrail non-inferiority logic\nFor each harm metric, the simultaneous upper bound must be below its predeclared margin. A nonsignificant harm test does not imply safety.'),
    code("guards=pl.read_csv(ROOT/'data/dashboard/guardrails.csv'); display(guards); print('All guardrails pass:',guards['passes'].all())"),
    md('## 7. Rare outcomes and financial meaning\nFraud flags are alerts, not confirmed fraud, chargebacks or loss. We report per-assigned-user exposure. Higher transaction volume can increase flag counts even without a change in per-transaction flag probability.'),
    code("display(results.filter(pl.col('metric')=='fraud_30d').select('control_n','control_success','treatment_n','treatment_success','difference','ci_low','ci_high'))"),
    md('## 8. Restricted time to activation\nEvery user contributes min(time to first payment, seven days); non-activators contribute seven days. With complete seven-day follow-up this estimates restricted mean time without first payment. It avoids selection on post-treatment activation.'),
    code('''display(df.group_by('variant').agg(pl.col('restricted_days_to_payment').mean().alias('mean_restricted_days'),pl.col('restricted_days_to_payment').std().alias('sd')))
display(pl.DataFrame([summary['restricted_time']]))'''),
    md('## 9. Practical effect and simulated decision'),
    code('''print(summary['decision'])
print('Primary CI lower bound clears 0.5 pp:',primary['ci_low']>cfg['practical_lift'])
print('Additional activations per 100,000 under simulation assumptions:',round(primary['difference']*100000))
print('This is not a revenue forecast or actual business result.')'''),
    md('## 10. Sensitivity to the acceptable fraud increase\nThis is a transparent scenario analysis, not a way to change the predeclared pass/fail decision after looking at results.'),
    code('''upper=guards.filter(pl.col('metric')=='fraud_30d')['upper_bound'].item()
display(pl.DataFrame({'hypothetical_margin_pp':[.025,.05,.10,.20]}).with_columns((pl.col('hypothetical_margin_pp')/100>upper).alias('would_pass_given_current_upper_bound')))
print('Predeclared margin remains 0.10 pp.')'''),
    md('## 11. What we can and cannot conclude'),
    code("display(Markdown((ROOT/'reports/experiment_readout.md').read_text()))"),
    md('''## Interview discussion

- Why is assignment the denominator instead of users who completed onboarding?
- Why does a payment exactly seven days after assignment fall outside the window?
- Why does statistical significance not establish commercial value?
- Why do guardrails need acceptable harm thresholds and uncertainty bounds?
- Why do synthetic results not replace real large-scale experimentation experience?
- What would change with partial follow-up, cross-device identity errors, delayed losses or dependent users?''')]

def build():
    names=[('01_data_quality_and_eda',quality_notebook()),('02_funnel_and_retention',funnel_notebook()),('03_ab_test_evaluation',experiment_notebook())]
    # In-process IPython executes the actual cells and captures rich outputs.
    # It requires no TCP socket, kernel daemon, browser or network connection.
    shell=InteractiveShell.instance()
    os.chdir(ROOT)
    for name,cells in names:
        shell.reset(new_session=True)
        nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]},'execution_method':'IPython in-process; actual cells executed with captured outputs'})
        count=0
        for cell in nb.cells:
            if cell.cell_type!='code':continue
            count+=1
            with capture_output(stdout=True,stderr=True,display=True) as captured:
                result=shell.run_cell(cell.source,store_history=True)
            if result.error_before_exec or result.error_in_exec:
                raise RuntimeError(f'{name} cell {count} failed: {result.error_before_exec or result.error_in_exec}')
            cell.execution_count=count
            outputs=[]
            if captured.stdout:outputs.append(nbf.v4.new_output('stream',name='stdout',text=captured.stdout))
            if captured.stderr:outputs.append(nbf.v4.new_output('stream',name='stderr',text=captured.stderr))
            for output in captured.outputs:
                outputs.append(nbf.v4.new_output('display_data',data=output.data,metadata=output.metadata))
            cell.outputs=outputs
        path=ROOT/'notebooks'/f'{name}.ipynb'
        nbf.validate(nb)
        nbf.write(nb,path)
        print('Executed:',path.name,flush=True)

if __name__=='__main__':build()
