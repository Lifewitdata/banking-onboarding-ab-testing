"""Interactive display of verified synthetic results. No pipeline runs at startup."""
from pathlib import Path
import json
import polars as pl
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
COLORS = {'control': '#475569', 'treatment': '#ef6470'}
LABELS = {'activated_7d':'First payment within 7 days', 'verified_7d':'Verification within 7 days',
          'funded_7d':'Funding within 7 days', 'support_7d':'Support contact within 7 days',
          'failure_7d':'Recoverable onboarding error within 7 days', 'fraud_30d':'Fraud flag within 30 days'}
st.set_page_config(page_title='Banking Onboarding Lab', page_icon='📊', layout='wide')

@st.cache_data
def csv(name):
    return pl.read_csv(ROOT/'data/dashboard'/f'{name}.csv',try_parse_dates=True)

@st.cache_data
def document(name):
    return json.loads((ROOT/'reports'/name).read_text())

def chart(fig, ytitle=None):
    fig.update_layout(template='plotly_white',font={'family':'Arial','size':13},
        margin={'l':20,'r':20,'t':30,'b':30},legend={'orientation':'h','y':1.13},
        hovermode='closest',yaxis_title=ytitle)
    st.plotly_chart(fig,width='stretch',config={'displaylogo':False})

def download(df,name):
    st.download_button('Download this table as CSV',df.write_csv().encode(),file_name=f'{name}.csv',mime='text/csv',key=f'download_{name}')

def table(df):
    st.dataframe(df,width='stretch',hide_index=True)

def overview(summary,counts):
    st.header('Did simpler onboarding improve activation?')
    st.write('Compare a simplified onboarding journey with the existing journey, using every assigned customer as the denominator.')
    primary=summary['primary']
    cols=st.columns(4)
    cols[0].metric('Assigned users',f"{counts['users']:,}")
    cols[1].metric('Control activation',f"{primary['control_rate']:.2%}")
    cols[2].metric('Treatment activation',f"{primary['treatment_rate']:.2%}")
    cols[3].metric('Absolute lift',f"{primary['difference']*100:+.2f} pp")
    st.caption(f"Primary 95% CI: {primary['ci_low']*100:.2f} to {primary['ci_high']*100:.2f} pp · Relative lift: {primary['relative_lift']:.2%}")
    if summary['decision']=='SIMULATED LAUNCH CRITERIA MET':
        st.success('The simulated launch criteria are met. This is a result of the configured simulation, not evidence of real-world product impact.')
    else:st.warning('The simulated launch criteria are not met. Review the primary outcome and guardrail uncertainty.')
    left,right=st.columns([2,1])
    with left:
        st.subheader('Activation by signup date')
        view=st.radio('Trend granularity',['Daily','Weekly'],horizontal=True,key='trend')
        daily=csv('daily_activation')
        if view=='Weekly':
            daily=daily.with_columns(pl.col('signup_date').dt.truncate('1w')).group_by('variant','signup_date').agg(
                pl.col('users').sum(),(pl.col('activation_rate')*pl.col('users')).sum().alias('activated_weighted')
            ).with_columns((pl.col('activated_weighted')/pl.col('users')).alias('activation_rate'))
        fig=go.Figure()
        for arm in COLORS:
            d=daily.filter(pl.col('variant')==arm).sort('signup_date')
            fig.add_trace(go.Scatter(x=d['signup_date'].to_list(),y=d['activation_rate'].to_list(),mode='lines+markers',name=arm.title(),line={'color':COLORS[arm]},hovertemplate='%{x}<br>Activation: %{y:.2%}<extra>%{fullData.name}</extra>'))
        fig.update_yaxes(tickformat='.0%');chart(fig,'Seven-day activation')
        st.caption('Weekly rates use user-count weighting. Trends are descriptive; there is no daily significance testing.')
    with right:
        st.subheader('Study scope')
        st.metric('Product events',f"{counts['events']:,}")
        st.metric('Transactions',f"{counts['transactions']:,}")
        st.write('84 days of enrolment · 30 days of follow-up per user · 50:50 randomisation at signup.')
        st.write('Data processing: **Polars + DuckDB SQL**. The app reads the compact, precomputed outputs of that analysis.')

def funnel():
    st.header('Customer journey')
    st.caption('Seven-day funnel; every step uses the original assignment denominator.')
    df=csv('funnel');fig=go.Figure()
    measure=st.radio('Funnel measure',['Conversion rate','User count'],horizontal=True,key='funnel_measure')
    field='overall_conversion' if measure=='Conversion rate' else 'users'
    for arm in COLORS:
        d=df.filter(pl.col('variant')==arm).sort('step_order')
        fig.add_trace(go.Bar(x=d['step'].to_list(),y=d[field].to_list(),name=arm.title(),marker_color=COLORS[arm]))
    fig.update_layout(barmode='group')
    if field=='overall_conversion':fig.update_yaxes(tickformat='.0%',range=[0,1.08])
    chart(fig,measure)
    with st.expander('Funnel counts and step conversion'):table(df);download(df,'funnel')
    st.subheader('Explore acquisition and device differences')
    dimension=st.selectbox('Segment dimension',['channel','device'],format_func=str.title,key='segment_dimension')
    seg=csv('segments').filter(pl.col('dimension')==dimension).sort('segment','variant')
    fig=go.Figure()
    for arm in COLORS:
        d=seg.filter(pl.col('variant')==arm)
        fig.add_trace(go.Bar(x=d['segment'].to_list(),y=d['activation_rate'].to_list(),name=arm.title(),marker_color=COLORS[arm],customdata=d['users'].to_list(),hovertemplate='%{x}<br>Activation: %{y:.2%}<br>Assigned: %{customdata:,}<extra>%{fullData.name}</extra>'))
    fig.update_yaxes(tickformat='.0%');fig.update_layout(barmode='group');chart(fig,'Seven-day activation')
    st.info('These are exploratory cuts, not significant subgroup findings. They do not change the overall experiment estimates or launch decision.')
    table(seg);download(seg,'segments')

def experiment(summary):
    st.header('Experiment evidence')
    result=csv('experiment_results')
    metric=st.selectbox('Outcome',result['metric'].to_list(),format_func=lambda m:LABELS[m],key='outcome')
    r=result.filter(pl.col('metric')==metric).row(0,named=True)
    cols=st.columns(3)
    cols[0].metric('Control rate',f"{r['control_rate']:.2%}")
    cols[1].metric('Treatment rate',f"{r['treatment_rate']:.2%}")
    cols[2].metric('Difference',f"{r['difference']*100:+.3f} pp")
    fig=go.Figure(go.Scatter(x=[r['difference']*100],y=[LABELS[metric]],mode='markers',marker={'size':14,'color':COLORS['treatment']},
        error_x={'type':'data','symmetric':False,'array':[(r['ci_high']-r['difference'])*100],'arrayminus':[(r['difference']-r['ci_low'])*100]},
        hovertemplate='Effect: %{x:.3f} pp<extra></extra>'))
    fig.add_vline(x=0,line_color='#94a3b8',line_dash='dash')
    fig.update_layout(height=240,xaxis_title='Treatment − control, percentage points (95% CI)');chart(fig)
    st.caption(f"95% CI: {r['ci_low']*100:.3f} to {r['ci_high']*100:.3f} pp · Two-sided p = {r['p_value']:.3g} · Control n = {r['control_n']:,} · Treatment n = {r['treatment_n']:,}")
    if metric in ['verified_7d','funded_7d']:
        st.caption(f"Secondary efficacy endpoint: Holm-adjusted p = {r['holm_p']:.3g}. The displayed 95% interval is unadjusted.")
    elif metric in ['support_7d','failure_7d','fraud_30d']:
        st.info('A lower rate is preferable for this harm metric. Use the simultaneous upper bound below for the guardrail decision, not this two-sided p-value.')
    st.subheader('Guardrails: uncertainty below the harm limit')
    guards=csv('guardrails').with_columns(
        pl.col('metric').replace_strict(LABELS).alias('outcome'),
        (pl.col('difference')*100).alias('difference_pp'),
        (pl.col('upper_bound')*100).alias('upper_bound_pp'),
        (pl.col('margin')*100).alias('allowed_increase_pp'))
    table(guards.select('outcome','difference_pp','upper_bound_pp','allowed_increase_pp','passes'))
    st.caption('One-sided bounds use Bonferroni alpha 0.05/3 for at least 95% family-wise coverage. Margins are illustrative. Fraud flags are not confirmed fraud losses.')
    st.subheader('Assignment and planning')
    cols=st.columns(3)
    cols[0].metric('Allocation check p-value',f"{summary['srm_p_value']:.4f}")
    cols[1].metric('Planned minimum per arm',f"{summary['planned_n_per_arm']:,}")
    cols[2].metric('Minimum worthwhile effect','0.5 pp')
    st.write('The primary lower confidence bound must exceed +0.5 pp; all guardrails must pass; allocation p must be at least 0.001. Data integrity checks must also pass.')
    with st.expander('Baseline balance and full results'):
        table(csv('baseline_balance'));table(result);download(result,'experiment_results')

def retention():
    st.header('Retention cohorts')
    st.write('Return means an app-open or successful payment. Week 1 covers days 7–13, week 2 days 14–20, and week 3 days 21–27 after assignment.')
    df=csv('retention')
    arm=st.selectbox('Variant',['control','treatment'],format_func=str.title,key='retention_variant')
    cohorts=sorted(str(v) for v in df['signup_week'].unique().to_list())
    chosen=st.multiselect('Signup weeks',cohorts,default=cohorts,key='cohorts')
    if not chosen:
        st.info('Select at least one signup week to show the cohort results.');return
    d=df.filter((pl.col('variant')==arm)&pl.col('signup_week').cast(pl.String).is_in(chosen))
    pivot=d.pivot(on='week',index='signup_week',values='return_rate').sort('signup_week')
    fig=go.Figure(go.Heatmap(z=pivot.select('1','2','3').to_numpy(),x=['Week 1','Week 2','Week 3'],y=[str(v) for v in pivot['signup_week']],
        colorscale='Blues',zmin=0,zmax=1,texttemplate='%{z:.1%}',colorbar={'tickformat':'.0%'},hovertemplate='Signup week: %{y}<br>%{x}<br>Return: %{z:.2%}<extra></extra>'))
    fig.update_layout(height=max(330,35*pivot.height),yaxis={'autorange':'reversed'});chart(fig)
    weighted=d.group_by('week').agg(pl.col('returning_users').sum(),pl.col('eligible_users').sum()).with_columns((pl.col('returning_users')/pl.col('eligible_users')).alias('weighted_return_rate')).sort('week')
    table(weighted);download(d,'selected_retention_cohorts')
    st.warning('Return rates reflect simplified synthetic app activity. They are not banking benchmarks. Filters affect this page only, not the experiment decision.')

def quality(counts):
    st.header('Data quality')
    q=document('quality_summary.json')
    rejected=sum(r['len'] for r in q['statuses'] if r['quality_status']!='valid')
    cols=st.columns(4)
    cols[0].metric('Raw events',f"{counts['events']:,}")
    cols[1].metric('Duplicates removed',f"{q['duplicate_rows_removed']:,}")
    cols[2].metric('Quarantined',f'{rejected:,}')
    cols[3].metric('Late events retained',f"{q['delayed_events_retained']:,}")
    table(csv('event_quality'))
    st.caption('Late events overlap the valid category and are not an additional excluded group. The snapshot allows 72 hours of ingestion delay.')
    st.subheader('Relational and time-order checks')
    checks=csv('sql_quality_checks');table(checks)
    if checks['failures'].sum()==0:st.success('All saved SQL integrity checks passed.')
    else:st.error('Some saved integrity checks failed; do not interpret the experiment until they are resolved.')
    st.subheader('Dataset inventory');table(csv('table_profile'))
    st.write('Corrupt records were deliberately injected into ancillary app-open telemetry. The cleaning logic did not use the injection log. Activation comes from successful transaction records, and no assigned users were removed because of bad ancillary events.')

def methods():
    st.header('Methodology and downloads')
    st.write('This app presents saved results from a reproducible synthetic analysis. It does not regenerate five million events on each page load or recompute experimental inference from segment filters.')
    selected=st.selectbox('Read a project document',['Experiment plan','Simulation assumptions','Data dictionary','Event tracking plan','Experiment readout'],key='document')
    paths={'Experiment plan':'docs/experiment_plan.md','Simulation assumptions':'docs/simulation_assumptions.md','Data dictionary':'docs/data_dictionary.md','Event tracking plan':'docs/event_tracking_plan.md','Experiment readout':'reports/experiment_readout.md'}
    text=(ROOT/paths[selected]).read_text()
    st.download_button('Download selected document',text,file_name=Path(paths[selected]).name,mime='text/markdown')
    st.markdown(text)

def main():
    st.title('Banking Onboarding Lab')
    st.caption('PRODUCT ANALYTICS · POLARS + SQL · RANDOMISED EXPERIMENT SIMULATION')
    st.warning('Synthetic portfolio study. No real Monzo customer data, affiliation or deployed banking experiment.')
    with st.sidebar:
        st.header('Explore the analysis')
        page=st.radio('Page',['Overview','Customer journey','Experiment','Retention','Data quality','Methodology'],label_visibility='collapsed',key='page')
        st.divider();st.caption('Saved analysis snapshot · synthetic users')
        st.caption('Filters are local to each page. The overall experiment uses the original assigned population.')
    try:
        summary=document('experiment_summary.json')
        counts=json.loads((ROOT/'data/manifest.json').read_text())['counts']
        if page=='Overview':overview(summary,counts)
        elif page=='Customer journey':funnel()
        elif page=='Experiment':experiment(summary)
        elif page=='Retention':retention()
        elif page=='Data quality':quality(counts)
        else:methods()
    except FileNotFoundError:
        st.error('A required analysis extract is missing. Include the data/dashboard, reports and docs folders when uploading the app.')
        st.caption('See README.md for the complete upload structure.')
        st.stop()

if __name__=='__main__':main()
