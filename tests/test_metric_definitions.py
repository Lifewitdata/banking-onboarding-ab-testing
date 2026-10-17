"""Test boundary cases against the actual production metric SQL."""
import duckdb
import numpy as np
import pytest
from scipy.stats import binomtest
from src.common import ROOT
from src.analyse_experiment import compare_binary

@pytest.fixture
def boundary_metrics():
    con=duckdb.connect()
    con.execute('''CREATE TABLE lifecycle AS
      SELECT i AS user_id, TIMESTAMP '2026-01-01' AS assigned_at,
        NULL::TIMESTAMP AS verified_at,NULL::TIMESTAMP AS funded_at,
        CASE i WHEN 1 THEN TIMESTAMP '2026-01-07 23:59:59'
               WHEN 2 THEN TIMESTAMP '2026-01-08'
               WHEN 4 THEN TIMESTAMP '2026-01-02' ELSE NULL END AS first_payment_at,
        NULL::TIMESTAMP AS first_contact_at,NULL::TIMESTAMP AS failure_at,
        CASE WHEN i=4 THEN TIMESTAMP '2026-01-31' ELSE NULL END AS first_flag_at
      FROM range(1,5) t(i)''')
    con.execute((ROOT/'sql/04_user_experiment_metrics.sql').read_text())
    yield con
    con.close()

def test_seven_day_boundary_and_no_payment(boundary_metrics):
    assert boundary_metrics.sql('SELECT activated_7d FROM user_metrics ORDER BY user_id').fetchall()==[(1,),(0,),(0,),(1,)]

def test_restricted_time_keeps_non_activators(boundary_metrics):
    rows=boundary_metrics.sql('SELECT restricted_days_to_payment FROM user_metrics ORDER BY user_id').fetchall()
    assert rows[1:]==[(7.0,),(7.0,),(1.0,)]

def test_thirty_day_boundary(boundary_metrics):
    assert boundary_metrics.sql('SELECT sum(fraud_30d) FROM user_metrics').fetchone()[0]==0

def test_interval_contains_known_difference_and_direction():
    result=compare_binary(450,1000,500,1000)
    assert np.isclose(result['difference'],.05)
    assert result['ci_low'] < .05 < result['ci_high']
    reverse=compare_binary(500,1000,450,1000)
    assert np.isclose(result['ci_low'],-reverse['ci_high'])

def test_identical_arms():
    result=compare_binary(450,1000,450,1000)
    assert result['p_value']==pytest.approx(1)
    assert result['ci_low']<0<result['ci_high']
