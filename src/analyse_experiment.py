"""User-level intention-to-treat inference. Polars tables, NumPy/statistical scalars."""
import math
import numpy as np
import polars as pl
from scipy import stats
from statsmodels.stats.proportion import confint_proportions_2indep, proportions_ztest, proportion_effectsize
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.multitest import multipletests
from src.common import ROOT, config, save_json, markdown

def compare_binary(control_success,control_n,treatment_success,treatment_n,alpha=.05):
    pc=control_success/control_n; pt=treatment_success/treatment_n
    low,high=confint_proportions_2indep(treatment_success,treatment_n,control_success,control_n,method='newcomb',compare='diff',alpha=alpha)
    if control_success+treatment_success in (0,control_n+treatment_n): pvalue=1.0
    else: _,pvalue=proportions_ztest([treatment_success,control_success],[treatment_n,control_n])
    return {'control_n':int(control_n),'treatment_n':int(treatment_n),
            'control_success':int(control_success),'treatment_success':int(treatment_success),
            'control_rate':pc,'treatment_rate':pt,'difference':pt-pc,
            'relative_lift':(pt/pc-1) if pc else None,
            'ci_low':float(low),'ci_high':float(high),'p_value':float(pvalue)}

def analyse():
    cfg=config()['experiment']
    df=pl.read_parquet(ROOT/'data/processed/user_metrics.parquet')
    counts=df.group_by('variant').len().sort('variant')
    nc=counts.filter(pl.col('variant')=='control')['len'].item()
    nt=counts.filter(pl.col('variant')=='treatment')['len'].item()
    expected=np.array([1-cfg['allocation'],cfg['allocation']])*(nc+nt)
    srm=stats.chisquare([nc,nt],f_exp=expected)
    per_arm=math.ceil(NormalIndPower().solve_power(effect_size=abs(proportion_effectsize(cfg['baseline_activation']+cfg['minimum_detectable_effect'],cfg['baseline_activation'])),power=cfg['power'],alpha=cfg['alpha'],ratio=1,alternative='two-sided'))
    metrics=['activated_7d','verified_7d','funded_7d','support_7d','failure_7d','fraud_30d']
    rows=[]
    for metric in metrics:
        mature='mature_30d' if metric=='fraud_30d' else 'mature_7d'
        group=df.filter(pl.col(mature)).group_by('variant').agg(pl.len().alias('n'),pl.col(metric).sum().alias('success'))
        c=group.filter(pl.col('variant')=='control').row(0,named=True)
        t=group.filter(pl.col('variant')=='treatment').row(0,named=True)
        rows.append({'metric':metric,**compare_binary(c['success'],c['n'],t['success'],t['n'])})
    results=pl.DataFrame(rows)
    # Verification and funding are secondary efficacy endpoints; Holm adjusts their p values.
    secondary=results.filter(pl.col('metric').is_in(['verified_7d','funded_7d']))
    secondary=secondary.with_columns(pl.Series('holm_p',multipletests(secondary['p_value'].to_numpy(),method='holm')[1]))
    results=results.join(secondary.select('metric','holm_p'),on='metric',how='left')
    results.write_csv(ROOT/'data/dashboard/experiment_results.csv')
    # One-sided family-wise 95% upper bounds for three harm guardrails.
    guardrails=[]
    for metric,margin in [('support_7d',cfg['support_margin']),('failure_7d',cfg['failure_margin']),('fraud_30d',cfg['fraud_margin'])]:
        r=results.filter(pl.col('metric')==metric).row(0,named=True)
        bounds=compare_binary(r['control_success'],r['control_n'],r['treatment_success'],r['treatment_n'],alpha=2*cfg['alpha']/3)
        guardrails.append({'metric':metric,'difference':r['difference'],'upper_bound':bounds['ci_high'],'margin':margin,'passes':bounds['ci_high']<margin})
    guards=pl.DataFrame(guardrails)
    guards.write_csv(ROOT/'data/dashboard/guardrails.csv')
    # Standardised mean differences for baseline categorical indicators.
    balance=[]
    for col in ['channel','device','age_band']:
        for value in df[col].unique().sort():
            rates=[]
            for arm in ['control','treatment']:
                rates.append(df.filter(pl.col('variant')==arm).select((pl.col(col)==value).mean()).item())
            sd=math.sqrt(sum(p*(1-p) for p in rates)/2)
            balance.append({'dimension':col,'category':value,'control_share':rates[0],'treatment_share':rates[1],'standardised_difference':(rates[1]-rates[0])/sd if sd else 0})
    pl.DataFrame(balance).write_csv(ROOT/'data/dashboard/baseline_balance.csv')
    c=df.filter(pl.col('variant')=='control')['restricted_days_to_payment'].to_numpy()
    t=df.filter(pl.col('variant')=='treatment')['restricted_days_to_payment'].to_numpy()
    diff=float(t.mean()-c.mean()); se=math.sqrt(t.var(ddof=1)/len(t)+c.var(ddof=1)/len(c))
    restricted={'control_days':float(c.mean()),'treatment_days':float(t.mean()),'difference_days':diff,'ci_low':diff-1.96*se,'ci_high':diff+1.96*se}
    primary=results.filter(pl.col('metric')=='activated_7d').row(0,named=True)
    passes=bool(srm.pvalue>=cfg['srm_alpha'] and primary['ci_low']>cfg['practical_lift'] and guards['passes'].all())
    decision='SIMULATED LAUNCH CRITERIA MET' if passes else 'SIMULATED LAUNCH CRITERIA NOT MET'
    summary={'synthetic':True,'decision':decision,'srm_p_value':float(srm.pvalue),
             'planned_n_per_arm':per_arm,'observed_control_n':nc,'observed_treatment_n':nt,
             'primary':primary,'guardrails':guardrails,'restricted_time':restricted,
             'additional_activations_per_100000':primary['difference']*100000}
    save_json('reports/experiment_summary.json',summary)
    report=f'''# Experiment readout: digital banking onboarding

**SYNTHETIC PORTFOLIO STUDY — not a Monzo experiment or real customer evidence.**

## Decision

**{decision}.** Within the configured simulation, seven-day activation was {primary['control_rate']:.2%} in control and {primary['treatment_rate']:.2%} in treatment. The estimated effect was **{primary['difference']*100:.2f} percentage points** (95% Newcombe CI {primary['ci_low']*100:.2f} to {primary['ci_high']*100:.2f} pp), or {primary['relative_lift']:.2%} relative lift.

This corresponds to about {summary['additional_activations_per_100000']:,.0f} additional activations per 100,000 assigned users under these synthetic assumptions. It is not a revenue estimate, realised business impact, or forecast for Monzo.

## Design and integrity

- Randomisation unit: user; treatment assigned before onboarding; analysis retains all eligible assigned users.
- Population: {nc+nt:,} users ({nc:,} control; {nt:,} treatment). No post-treatment filtering.
- Enrolment: 84 days; 30-day follow-up per user; ingestion watermark allows an additional 72 hours.
- Planning assumptions: 45% baseline, 1 pp detectable improvement, two-sided alpha .05, 80% power. Required sample: {per_arm:,} per arm. The 250,000-user design exceeds this to support learning with large data, not because this many users are necessary for the primary test.
- Sample-ratio mismatch p={srm.pvalue:.5f}; alert threshold {cfg['srm_alpha']}. Baseline categorical balance is available in the dashboard extracts.
- Primary activation comes from successful payment transactions, not client event counts.

## Results

Rates and differences below are proportions; multiply differences by 100 for percentage points.

{markdown(results.select('metric','control_rate','treatment_rate','difference','ci_low','ci_high','p_value','holm_p'))}

Primary efficacy uses a pooled two-proportion z test and Newcombe confidence interval. Verification and funding use Holm-adjusted secondary p-values; their displayed intervals are unadjusted descriptive intervals. Guardrail decision-making uses the separate simultaneous upper bounds below, not their two-sided p-values.

## Guardrails

{markdown(guards)}

Three one-sided upper bounds use Bonferroni alpha .05/3, providing at least 95% family-wise coverage. Passing means the upper bound is below a predeclared acceptable increase: support and onboarding failure 0.5 pp; fraud flags 0.1 pp. These thresholds are illustrative assumptions, not approved bank risk limits. A nonsignificant difference alone does not establish safety.

## Time to first payment

Mean time without a first payment, restricted to seven days, was {restricted['control_days']:.3f} days in control and {restricted['treatment_days']:.3f} in treatment. Difference: {diff:.3f} days (large-sample 95% CI {restricted['ci_low']:.3f}, {restricted['ci_high']:.3f}). Non-activators contribute seven days; this avoids comparing only the selected users who activated. This is an exploratory endpoint.

## Product interpretation and next action

The simulated treatment changes verification completion, funding propensity and verification speed. Funnel movement is consistent with those programmed mechanisms. It does not independently discover that clearer instructions cause these outcomes in real banking customers.

For a real pilot, validate the instrumentation, agree risk margins with product and risk teams, and run a fixed-horizon randomised experiment. Continue monitoring confirmed fraud losses, support costs and longer-term customer value. Cohort return rates and channel/device cuts here are exploratory; no segment-specific rollout is justified by these cuts alone.

## Limits

- Synthetic mechanisms encode the treatment effect; this project demonstrates analysis and engineering, not product validation.
- Fraud flags are transaction-linked proxy alerts, not confirmed fraud or financial loss. More payments can produce more flags; the per-user measure captures total assigned-user exposure.
- Thirty days cannot establish long-term profitability, losses or lifetime value.
- Background app visits are simplified; weekly return rates should not be interpreted as realistic banking benchmarks.
- Injected corrupt records are ancillary telemetry. The study does not simulate unobserved business outcomes or differential missingness.
- No operational deployment, real-user experiment, Tableau workbook or GitHub publication has occurred.
'''
    (ROOT/'reports/experiment_readout.md').write_text(report)
    print(decision,primary,flush=True)

if __name__=='__main__':analyse()
