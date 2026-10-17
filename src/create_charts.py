"""Publication-style static charts; Matplotlib consumes NumPy arrays from Polars."""
import json
import numpy as np
import polars as pl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from src.common import ROOT

COLORS={'control':'#43536A','treatment':'#E55D69'}
def style():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.titlepad':14,'figure.facecolor':'#FFFFFF','axes.facecolor':'#FFFFFF','savefig.facecolor':'#FFFFFF'})

def save(fig,name):
    fig.text(.02,.01,'SYNTHETIC DATA • Portfolio analysis • Not Monzo customer results',fontsize=8,color='#64748B')
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(ROOT/f'reports/figures/{name}.png',dpi=160);plt.close(fig)

def charts():
    style()
    df=pl.read_parquet(ROOT/'data/processed/user_metrics.parquet')
    funnel=pl.read_csv(ROOT/'data/dashboard/funnel.csv')
    fig,ax=plt.subplots(figsize=(9,5))
    for arm in ['control','treatment']:
        d=funnel.filter(pl.col('variant')==arm).sort('step_order')
        ax.plot(d['step'].to_list(),d['overall_conversion'].to_numpy(),marker='o',lw=3,color=COLORS[arm],label=arm.title())
        for x,y in zip(d['step'],d['overall_conversion']):ax.annotate(f'{y:.1%}',(x,y),xytext=(0,10 if arm=='treatment' else -17),textcoords='offset points',ha='center',fontsize=9)
    ax.set(title='Seven-day onboarding funnel',ylabel='Share of all assigned users',ylim=(.3,1.12));ax.yaxis.set_major_formatter(PercentFormatter(1));ax.legend();save(fig,'01_funnel')

    result=pl.read_csv(ROOT/'data/dashboard/experiment_results.csv')
    d=result.head(3)
    fig,ax=plt.subplots(figsize=(9,4))
    y=np.arange(d.height);x=d['difference'].to_numpy()*100
    ax.errorbar(x,y,xerr=np.vstack([x-d['ci_low'].to_numpy()*100,d['ci_high'].to_numpy()*100-x]),fmt='o',color=COLORS['treatment'],capsize=5,ms=8)
    ax.axvline(0,color='#CBD5E1');ax.set_yticks(y,['Activation','Verification','Funding']);ax.invert_yaxis()
    ax.set(title='Estimated treatment effect',xlabel='Treatment − control (percentage points); 95% CI')
    save(fig,'02_experiment_effects')

    daily=pl.read_csv(ROOT/'data/dashboard/daily_activation.csv',try_parse_dates=True)
    fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True)
    for arm in ['control','treatment']:
        d=daily.filter(pl.col('variant')==arm).sort('signup_date')
        axes[0].plot(d['signup_date'].to_numpy(),d['users'].to_numpy(),color=COLORS[arm],alpha=.8,label=arm.title())
        axes[1].plot(d['signup_date'].to_numpy(),d['activation_rate'].rolling_mean(7).to_numpy(),color=COLORS[arm],label=arm.title())
    axes[0].set(title='Enrolment and activation over time',ylabel='Assigned users / day');axes[0].legend()
    axes[1].set(ylabel='7-day rolling mean activation',xlabel='Signup date');axes[1].yaxis.set_major_formatter(PercentFormatter(1));save(fig,'03_daily_trends')

    retention=pl.read_csv(ROOT/'data/dashboard/retention.csv')
    fig,axes=plt.subplots(1,2,figsize=(10,6),sharey=True)
    for ax,arm in zip(axes,['control','treatment']):
        d=retention.filter(pl.col('variant')==arm).pivot(on='week',index='signup_week',values='return_rate').sort('signup_week')
        arr=d.select('1','2','3').to_numpy()
        im=ax.imshow(arr,vmin=.7,vmax=1,cmap='Blues',aspect='auto')
        ax.set_xticks([0,1,2],['Week 1','Week 2','Week 3']);ax.set_yticks(range(d.height),d['signup_week'].to_list());ax.set_title(arm.title())
        for i in range(d.height):
            for j in range(3):ax.text(j,i,f'{arr[i,j]:.0%}',ha='center',va='center',fontsize=8,color='white' if arr[i,j]>.88 else '#172B4D')
    fig.suptitle('Weekly return among all assigned users',fontweight='bold');save(fig,'04_retention_cohorts')

    segments=pl.read_csv(ROOT/'data/dashboard/segments.csv')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,dimension in zip(axes,['channel','device']):
        cats=sorted(segments.filter(pl.col('dimension')==dimension)['segment'].unique().to_list())
        for j,arm in enumerate(['control','treatment']):
            d=segments.filter((pl.col('dimension')==dimension)&(pl.col('variant')==arm)).sort('segment')
            ax.bar(np.arange(len(cats))+(j-.5)*.35,d['activation_rate'].to_numpy(),width=.35,label=arm.title(),color=COLORS[arm])
        ax.set_xticks(np.arange(len(cats)),cats,rotation=20);ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set(title=dimension.title(),ylim=(0,.7));ax.legend(fontsize=8)
    fig.suptitle('Exploratory activation cuts — no subgroup significance claims',fontweight='bold');save(fig,'05_segments')

    fig,ax=plt.subplots(figsize=(9,5))
    for arm in ['control','treatment']:
        d=df.filter(pl.col('variant')==arm)
        hours=(d['first_payment_at']-d['assigned_at']).dt.total_seconds().to_numpy()/3600
        grid=np.arange(0,169,6)
        rate=np.array([np.sum(np.isfinite(hours)&(hours<g))/len(hours) for g in grid])
        ax.plot(grid/24,rate,color=COLORS[arm],lw=2.5,label=arm.title())
    ax.set(title='Cumulative first-payment conversion',xlabel='Days since assignment',ylabel='Share of all assigned users');ax.yaxis.set_major_formatter(PercentFormatter(1));ax.legend();save(fig,'06_time_to_activation')

    tx=pl.scan_parquet(ROOT/'data/raw/transactions/*.parquet').filter((pl.col('kind')=='payment')&(pl.col('status')=='success')).select('amount_gbp').collect()
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    axes[0].hist(tx['amount_gbp'].to_numpy(),bins=60,color='#43536A');axes[0].set(title='Successful payment amounts',xlabel='GBP',ylabel='Transactions');axes[0].set_yscale('log')
    hours=df.filter(pl.col('verified_at').is_not_null()).select(((pl.col('verified_at')-pl.col('assigned_at')).dt.total_seconds()/3600).alias('hours'))['hours'].to_numpy()
    axes[1].hist(hours,bins=60,color='#E55D69');axes[1].set(title='Time to completed verification',xlabel='Hours (completers only)',ylabel='Users');axes[1].set_yscale('log');save(fig,'07_distributions')
    print('Seven chart files created.')

if __name__=='__main__':charts()
