"""Profile and clean event telemetry through Polars lazy queries."""
import polars as pl
from src.common import ROOT, save_json, markdown

def validate():
    out=ROOT/'data/processed'; out.mkdir(exist_ok=True)
    users=pl.scan_parquet(ROOT/'data/raw/users/*.parquet')
    events=pl.scan_parquet(ROOT/'data/raw/events/*.parquet')
    duplicate_count=events.select(pl.len()-pl.col('event_id').n_unique()).collect().item()
    # Deduplicate before validating; keep earliest arrival deterministically.
    unique=events.sort(['event_id','ingested_at']).unique('event_id',keep='first',maintain_order=True)
    joined=unique.join(users.select('user_id','signup_at'),on='user_id',how='left')
    labelled=joined.with_columns(
        pl.when(pl.col('user_id').is_null()).then(pl.lit('missing_user'))
        .when(pl.col('signup_at').is_null()).then(pl.lit('orphan_user'))
        .when(pl.col('event_at')<pl.col('signup_at')).then(pl.lit('before_signup'))
        .when(pl.col('event_at')>=pl.col('signup_at')+pl.duration(days=30)).then(pl.lit('outside_followup'))
        .when(pl.col('ingested_at')<pl.col('event_at')).then(pl.lit('negative_ingestion_lag'))
        .otherwise(pl.lit('valid')).alias('quality_status'))
    labelled.sink_parquet(out/'events_labelled.parquet',compression='zstd')
    cached=pl.scan_parquet(out/'events_labelled.parquet')
    cached.filter(pl.col('quality_status')=='valid').drop('quality_status','signup_at').sink_parquet(out/'events_clean.parquet',compression='zstd')
    cached.filter(pl.col('quality_status')!='valid').sink_parquet(out/'events_quarantine.parquet',compression='zstd')
    quality=cached.group_by('quality_status').len().collect().sort('quality_status')
    delayed=cached.filter((pl.col('ingested_at')-pl.col('event_at')).dt.total_hours()>48).select(pl.len()).collect().item()
    tables=[]; nulls=[]
    for name in ['users','assignments','events','transactions','support','fraud','tracking_issues']:
        lf=pl.scan_parquet(ROOT/f'data/raw/{name}/*.parquet')
        schema=lf.collect_schema()
        rowcount=lf.select(pl.len()).collect().item()
        tables.append({'table':name,'rows':rowcount,'columns':len(schema)})
        nc=lf.select(pl.all().null_count()).collect().row(0,named=True)
        for col,dtype in schema.items():
            nulls.append({'table':name,'column':col,'dtype':str(dtype),'null_count':nc[col]})
    pl.DataFrame(tables).write_csv(out/'table_profile.csv')
    pl.DataFrame(nulls).write_csv(out/'column_profile.csv')
    quality.write_csv(out/'event_quality.csv')
    pl.DataFrame(tables).write_csv(ROOT/'data/dashboard/table_profile.csv')
    quality.write_csv(ROOT/'data/dashboard/event_quality.csv')
    summary={'duplicate_rows_removed':duplicate_count,'delayed_events_retained':delayed,'statuses':quality.to_dicts()}
    save_json('reports/quality_summary.json',summary)
    (ROOT/'reports/data_quality_report.md').write_text('# Data quality report\n\nSynthetic data; generated deliberately for analysis practice.\n\n'+markdown(pl.DataFrame(tables))+'\n\n## Event handling\n\n'+markdown(quality)+f'\n\nRemoved {duplicate_count:,} duplicate event rows. Retained {delayed:,} events arriving more than 48 hours late because the final ingestion watermark allows 72 hours. Missing users, unknown users and events before signup are quarantined.\n\nThe injection log is only used to audit detection; cleaning never reads the log. Corrupt additional records affect app-open telemetry; original lifecycle records and transaction truth are intact. Thus this dataset does not model missing business outcomes or differential instrumentation loss between arms.\n')
    # The labelled intermediate is reproducible and need not duplicate 6M events on disk.
    (out/'events_labelled.parquet').unlink()
    print(summary)

if __name__=='__main__': validate()
