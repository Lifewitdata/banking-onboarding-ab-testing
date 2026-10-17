"""Shared paths, configuration and compact Polars output helpers."""
from pathlib import Path
import json
import polars as pl
import yaml

ROOT = Path(__file__).resolve().parents[1]

def config():
    return yaml.safe_load((ROOT / 'config/simulation.yaml').read_text())

def save_json(path, value):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + '\n')

def markdown(df: pl.DataFrame) -> str:
    def fmt(x):
        if x is None: return '—'
        if isinstance(x, float): return f'{x:,.5f}'
        return str(x)
    return '\n'.join(['| ' + ' | '.join(df.columns) + ' |',
                      '| ' + ' | '.join(['---'] * len(df.columns)) + ' |'] +
                     ['| ' + ' | '.join(fmt(v) for v in r) + ' |' for r in df.iter_rows()])
