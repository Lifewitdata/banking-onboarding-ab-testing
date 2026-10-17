"""Generate large, reproducible synthetic data using NumPy and Polars only.

Random streams are seeded once. User batches bound memory use. Records are
artificial; the mechanisms are documented assumptions, not banking estimates.
"""
from datetime import datetime, timedelta
import argparse
import hashlib
import numpy as np
import polars as pl
from src.common import ROOT, config, save_json

DAY = 86400

def generate():
    cfg = config()
    rng = np.random.default_rng(cfg['seed'])
    n = cfg['n_users']
    start = int(datetime.fromisoformat(cfg['start_date']).timestamp())
    # Stored timestamps are naive UTC; input dates never depend on local timezone.
    start = int(np.datetime64(cfg['start_date'], 's').astype('int64'))
    raw = ROOT / 'data/raw'
    for folder in ['events','users','assignments','transactions','support','fraud','tracking_issues']:
        (raw / folder).mkdir(parents=True, exist_ok=True)
        for old in (raw / folder).glob('part-*.parquet'): old.unlink()
    counters = dict(event=0, transaction=0, contact=0, flag=0)
    totals = {k:0 for k in ['users','assignments','events','transactions','support','fraud','tracking_issues']}
    for batch, lo in enumerate(range(0,n,cfg['batch_size'])):
        size = min(cfg['batch_size'],n-lo)
        ids = np.arange(lo+1,lo+size+1,dtype=np.int64)
        signup = start + rng.integers(0,cfg['enrolment_days']*DAY,size)
        variant = rng.random(size) < cfg['experiment']['allocation']
        channel = rng.choice(['organic','paid_search','referral','social'],size,p=[.34,.28,.22,.16])
        device = rng.choice(['iOS','Android','Web'],size,p=[.43,.49,.08])
        age = rng.choice(['18–24','25–34','35–49','50+'],size,p=[.24,.38,.26,.12])
        motivation = rng.normal(0,1,size)
        channel_effect = np.select([channel=='referral',channel=='social'],[.05,-.06],0)
        android = device=='Android'
        verified = rng.random(size) < np.clip(.76 + channel_effect + .035*variant - .035*android + .055*motivation,.1,.96)
        verification_seconds = rng.lognormal(np.log(5*3600),1.2,size) * np.where(variant,.85,1)
        vtime = signup + np.minimum(verification_seconds,10*DAY).astype('int64') + 60
        funded = verified & (rng.random(size)<np.clip(.79+channel_effect+.02*variant+.04*motivation,.1,.98))
        ftime = vtime + np.minimum(rng.exponential(1.2*DAY,size),12*DAY).astype('int64') + 60
        payer = funded & (rng.random(size)<np.clip(.86+.03*motivation,.1,.98))
        ptime = ftime + np.minimum(rng.exponential(1.5*DAY,size),12*DAY).astype('int64') + 60
        payer &= ptime < signup+30*DAY
        funded &= ftime < signup+30*DAY
        failure = rng.random(size) < (.115 - .014*variant + .03*android)
        support = rng.random(size) < (.055 + .13*failure - .007*variant)
        failure_time = np.minimum(signup + rng.integers(90,7*DAY,size),vtime-40)
        support_time = signup + rng.integers(90,7*DAY,size)
        users = pl.DataFrame({'user_id':ids,'signup_at':signup,'channel':channel,'device':device,'age_band':age}).with_columns(pl.from_epoch('signup_at',time_unit='s'))
        assignments = pl.DataFrame({'user_id':ids,'variant':np.where(variant,'treatment','control'),'assigned_at':signup,'eligible':np.ones(size,dtype=bool)}).with_columns(pl.from_epoch('assigned_at',time_unit='s'))

        event_frames=[]
        def events(u,ts,name):
            count=len(u)
            if not count:return
            eid=np.arange(counters['event']+1,counters['event']+count+1,dtype=np.int64)
            counters['event']+=count
            lag=rng.integers(0,600,count)
            event_frames.append(pl.DataFrame({'event_id':eid,'user_id':u,'event_name':np.repeat(name,count) if isinstance(name,str) else name,'event_at':ts,'ingested_at':ts+lag}))

        events(ids,signup+1,'onboarding_started')
        events(ids,signup+30,'verification_attempted')
        events(ids[failure],vtime[failure]-30,'verification_attempted')
        events(ids[verified],vtime[verified],'verification_completed')
        events(ids[funded],ftime[funded],'account_funded')
        events(ids[failure],failure_time[failure],'onboarding_failed')
        # Background events can occur for non-activators, representing repeated visits.
        repeats=rng.poisson(cfg['background_events_per_user'],size)
        uid=np.repeat(ids,repeats)
        st=np.repeat(signup,repeats)
        offsets=rng.integers(60,30*DAY,len(uid))
        names=rng.choice(['app_open','help_view','onboarding_view','balance_view'],len(uid),p=[.55,.12,.23,.10])
        # Account-only screens require funding and occur afterwards.
        ft=np.repeat(ftime,repeats); fu=np.repeat(funded,repeats)
        names=np.where((names=='balance_view')&(~fu|(st+offsets<ft)),'onboarding_view',names)
        events(uid,st+offsets,names)

        tx_frames=[]
        def transactions(u,ts,kind,status,amount):
            count=len(u)
            txid=np.arange(counters['transaction']+1,counters['transaction']+count+1,dtype=np.int64)
            counters['transaction']+=count
            frame=pl.DataFrame({'transaction_id':txid,'user_id':u,'transaction_at':ts,'kind':np.repeat(kind,count),'status':np.repeat(status,count),'amount_gbp':amount})
            tx_frames.append(frame)
            events(u,ts,'payment_succeeded' if kind=='payment' and status=='success' else ('payment_failed' if kind=='payment' else 'funding_confirmed'))
            return txid
        balances=np.round(rng.uniform(150,2500,size),2)
        transactions(ids[funded],ftime[funded],'funding','success',balances[funded])
        pidx=np.flatnonzero(payer)
        pcounts=1+rng.poisson(3,len(pidx))
        idx=np.repeat(pidx,pcounts)
        order=np.concatenate([np.arange(c) for c in pcounts]) if len(pcounts) else np.array([],dtype=int)
        fractions=rng.random(len(idx))
        t=ptime[idx]+((signup[idx]+30*DAY-ptime[idx]-1)*fractions).astype('int64')
        t=np.where(order==0,ptime[idx],t)
        amounts=np.round(balances[idx]*rng.uniform(.2,.75,len(idx))/np.repeat(pcounts,pcounts),2)
        payment_ids=transactions(ids[idx],t,'payment','success',amounts)
        # Failed payment attempts do not count as activation or consume funds.
        failed_p=payer & (rng.random(size)<.12)
        transactions(ids[failed_p],ptime[failed_p]-15,'payment','failed',np.round(balances[failed_p]*.05,2))
        # Flags are transaction-linked proxies, not confirmed loss or actual fraud.
        marked=rng.random(len(idx)) < .0018
        ftimes=np.minimum(t[marked]+rng.integers(60,3*DAY,int(marked.sum())),signup[idx[marked]]+30*DAY-1)
        fraud=pl.DataFrame({'flag_id':np.arange(counters['flag']+1,counters['flag']+int(marked.sum())+1,dtype=np.int64),'transaction_id':payment_ids[marked],'user_id':ids[idx[marked]],'flag_at':ftimes,'flag_type':rng.choice(['velocity','unusual_device','amount_pattern'],int(marked.sum()))})
        counters['flag']+=int(marked.sum())
        contacts=pl.DataFrame({'contact_id':np.arange(counters['contact']+1,counters['contact']+int(support.sum())+1,dtype=np.int64),'user_id':ids[support],'contact_at':support_time[support],'reason':np.where(failure[support],'onboarding_error','verification_question'),'resolution_hours':np.round(rng.exponential(12,int(support.sum())),2)})
        counters['contact']+=int(support.sum())
        events(ids[support],support_time[support],'support_contacted')

        event_df=pl.concat(event_frames)
        background=event_df.filter(pl.col('event_name')=='app_open')
        issues=[]
        extra=[]
        counts={'duplicate':int(event_df.height*.0015),'missing_user':int(event_df.height*.0005),'orphan_user':int(event_df.height*.0002),'before_signup':int(event_df.height*.0002),'delayed_ingestion':int(event_df.height*.003)}
        for issue,count in counts.items():
            sample=background.sample(n=count,seed=cfg['seed']+batch+len(issues))
            if issue!='duplicate':
                new_ids=np.arange(counters['event']+1,counters['event']+count+1,dtype=np.int64)
                counters['event']+=count
                sample=sample.with_columns(pl.Series('event_id',new_ids))
            if issue=='missing_user':sample=sample.with_columns(pl.lit(None,dtype=pl.Int64).alias('user_id'))
            if issue=='orphan_user':sample=sample.with_columns((pl.col('user_id')+n).alias('user_id'))
            if issue=='before_signup':
                sample=sample.join(users.select('user_id',pl.col('signup_at').dt.epoch('s').alias('signup_epoch')),on='user_id').with_columns((pl.col('signup_epoch')-60).alias('event_at'),(pl.col('signup_epoch')-30).alias('ingested_at')).drop('signup_epoch')
            if issue=='delayed_ingestion':sample=sample.with_columns((pl.col('event_at')+3*DAY).alias('ingested_at'))
            extra.append(sample)
            issues.append(sample.select('event_id').with_columns(pl.lit(issue).alias('issue')))
        event_df=pl.concat([event_df,*extra]).with_columns(pl.from_epoch('event_at',time_unit='s'),pl.from_epoch('ingested_at',time_unit='s'))
        tx=pl.concat(tx_frames).with_columns(pl.from_epoch('transaction_at',time_unit='s'))
        contacts=contacts.with_columns(pl.from_epoch('contact_at',time_unit='s'))
        fraud=fraud.with_columns(pl.from_epoch('flag_at',time_unit='s'))
        frames={'users':users,'assignments':assignments,'events':event_df,'transactions':tx,'support':contacts,'fraud':fraud,'tracking_issues':pl.concat(issues)}
        for name,frame in frames.items():
            frame.write_parquet(raw/name/f'part-{batch:03d}.parquet',compression='zstd')
            totals[name]+=frame.height
            if batch==0:frame.head(100).write_csv(ROOT/'data/samples'/f'{name}_sample.csv')
        print(f'Batch {batch+1}: {lo+size:,} users; {totals["events"]:,} events',flush=True)
    manifest=[]
    for path in sorted(raw.rglob('*.parquet')):
        manifest.append({'file':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    save_json('data/manifest.json',{'synthetic':True,'seed':cfg['seed'],'counts':totals,'files':manifest})
    print(totals)

if __name__=='__main__': generate()
