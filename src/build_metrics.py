"""Execute reusable SQL and export Polars DataFrames without Pandas conversion."""
from src.common import ROOT, markdown
from src.build_database import connect

def build():
    con=connect()
    checks=con.execute((ROOT/'sql/02_quality_checks.sql').read_text()).pl()
    checks.write_csv(ROOT/'data/processed/sql_quality_checks.csv')
    checks.write_csv(ROOT/'data/dashboard/sql_quality_checks.csv')
    assert checks['failures'].sum()==0, checks
    con.execute((ROOT/'sql/04_user_experiment_metrics.sql').read_text())
    con.sql('SELECT * FROM user_metrics').pl().write_parquet(ROOT/'data/processed/user_metrics.parquet',compression='zstd')
    for name,file in [('funnel','03_onboarding_funnel.sql'),('retention','05_retention_cohorts.sql'),('segments','06_segment_analysis.sql')]:
        con.execute((ROOT/'sql'/file).read_text()).pl().write_csv(ROOT/f'data/dashboard/{name}.csv')
    con.sql("SELECT variant,date_trunc('day',assigned_at)::DATE AS signup_date,count(*) AS users,avg(activated_7d) AS activation_rate FROM user_metrics WHERE mature_7d GROUP BY ALL ORDER BY signup_date,variant").pl().write_csv(ROOT/'data/dashboard/daily_activation.csv')
    with (ROOT/'reports/data_quality_report.md').open('a') as f:f.write('\n## Relational and temporal checks\n\n'+markdown(checks)+'\n')
    con.close()
    print('SQL checks passed; user metrics and dashboard extracts exported.')

if __name__=='__main__':build()
