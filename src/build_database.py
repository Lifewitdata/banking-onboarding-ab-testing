"""Create local DuckDB views; source data remain in Parquet."""
import duckdb
from src.common import ROOT, config

def connect(read_only=False):
    con=duckdb.connect(str(ROOT/'data/processed/banking.duckdb'),read_only=read_only)
    con.execute("SET threads=4")
    return con

def build():
    con=connect()
    for name in ['users','assignments','events','transactions','support','fraud','tracking_issues']:
        path=str(ROOT/f'data/raw/{name}/*.parquet').replace("'","''")
        con.execute(f"CREATE OR REPLACE VIEW raw_{name} AS SELECT * FROM read_parquet('{path}')")
    path=str(ROOT/'data/processed/events_clean.parquet').replace("'","''")
    con.execute(f"CREATE OR REPLACE VIEW events AS SELECT * FROM read_parquet('{path}')")
    cfg=config()
    con.execute('CREATE OR REPLACE TABLE observation AS SELECT CAST(? AS TIMESTAMP) + (? + ?) * INTERVAL 1 DAY AS event_cutoff', [cfg['start_date'],cfg['enrolment_days'],cfg['followup_days']])
    con.execute((ROOT/'sql/01_staging.sql').read_text())
    con.close()
    print('DuckDB views created. Re-run after relocating the project.')

if __name__=='__main__':build()
