"""Validate full generated data, including independent SQL/Polars reconciliation."""
import json
import polars as pl
from src.common import ROOT
from src.build_database import connect

def test_all_relational_checks_pass():
    checks=pl.read_csv(ROOT/'data/processed/sql_quality_checks.csv')
    assert checks['failures'].sum()==0

def test_all_assigned_users_retained():
    raw=pl.scan_parquet(ROOT/'data/raw/assignments/*.parquet').select(pl.len()).collect().item()
    metrics=pl.read_parquet(ROOT/'data/processed/user_metrics.parquet')
    assert metrics.height==raw==metrics['user_id'].n_unique()

def test_independent_polars_primary_metric_matches_sql():
    assignments=pl.scan_parquet(ROOT/'data/raw/assignments/*.parquet')
    paid=pl.scan_parquet(ROOT/'data/raw/transactions/*.parquet').filter((pl.col('kind')=='payment')&(pl.col('status')=='success'))
    counts=assignments.join(paid,on='user_id',how='left').group_by('user_id').agg(
        ((pl.col('transaction_at')>=pl.col('assigned_at'))&(pl.col('transaction_at')<pl.col('assigned_at')+pl.duration(days=7))).any().fill_null(False).cast(pl.Int32).alias('polars_activation')).collect()
    joined=pl.read_parquet(ROOT/'data/processed/user_metrics.parquet').join(counts,on='user_id')
    assert joined.filter(pl.col('activated_7d')!=pl.col('polars_activation')).is_empty()

def test_funnel_is_monotone():
    df=pl.read_csv(ROOT/'data/dashboard/funnel.csv')
    for arm in ['control','treatment']:
        x=df.filter(pl.col('variant')==arm).sort('step_order')['users'].to_list()
        assert x==sorted(x,reverse=True)

def test_injected_errors_reconciled_without_using_log_to_clean():
    log=pl.scan_parquet(ROOT/'data/raw/tracking_issues/*.parquet').group_by('issue').len().collect()
    expected=dict(log.iter_rows())
    summary=json.loads((ROOT/'reports/quality_summary.json').read_text())
    actual={r['quality_status']:r['len'] for r in summary['statuses']}
    assert summary['duplicate_rows_removed']==expected['duplicate']
    assert summary['delayed_events_retained']==expected['delayed_ingestion']
    for k in ['missing_user','orphan_user','before_signup']:assert actual[k]==expected[k]

def test_clean_events_unique_and_known():
    lf=pl.scan_parquet(ROOT/'data/processed/events_clean.parquet')
    assert lf.select(pl.len()-pl.col('event_id').n_unique()).collect().item()==0
    assert lf.select(pl.col('user_id').null_count()).collect().item()==0

def test_funded_balances_cover_successful_payments():
    # The simulation is a simple funded wallet, not a bank accounting ledger.
    tx=pl.scan_parquet(ROOT/'data/raw/transactions/*.parquet').filter(pl.col('status')=='success')
    balance=tx.group_by('user_id').agg(pl.when(pl.col('kind')=='funding').then(pl.col('amount_gbp')).otherwise(-pl.col('amount_gbp')).sum().alias('balance')).collect()
    assert balance['balance'].min()>=0
