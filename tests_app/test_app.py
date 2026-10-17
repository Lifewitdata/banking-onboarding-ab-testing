"""Smoke tests across pages and interactions; no large dataset or socket required."""
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def app():
    return AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()

def test_overview_and_weekly_weighting(app):
    assert not app.exception
    assert app.metric[0].value=='250,000'
    app.radio(key='trend').set_value('Weekly').run()
    assert not app.exception
    assert app.metric[0].value=='250,000'

def test_funnel_controls(app):
    app.radio(key='page').set_value('Customer journey').run()
    assert not app.exception
    app.radio(key='funnel_measure').set_value('User count').run()
    app.selectbox(key='segment_dimension').set_value('device').run()
    assert not app.exception

def test_all_experiment_outcomes(app):
    app.radio(key='page').set_value('Experiment').run()
    for outcome in ['activated_7d','verified_7d','funded_7d','support_7d','failure_7d','fraud_30d']:
        app.selectbox(key='outcome').set_value(outcome).run()
        assert not app.exception

def test_retention_and_empty_selection(app):
    app.radio(key='page').set_value('Retention').run()
    assert not app.exception
    app.selectbox(key='retention_variant').set_value('treatment').run()
    first=app.multiselect(key='cohorts').options[0]
    app.multiselect(key='cohorts').set_value([first]).run()
    assert not app.exception
    app.multiselect(key='cohorts').set_value([]).run()
    assert not app.exception
    assert any('Select at least one' in x.value for x in app.info)

def test_quality(app):
    app.radio(key='page').set_value('Data quality').run()
    assert not app.exception
    assert app.metric[0].value=='5,901,194'
    assert any('All saved SQL' in x.value for x in app.success)

def test_methodology_documents(app):
    app.radio(key='page').set_value('Methodology').run()
    for name in ['Experiment plan','Simulation assumptions','Data dictionary','Event tracking plan','Experiment readout']:
        app.selectbox(key='document').set_value(name).run()
        assert not app.exception
