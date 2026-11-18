"""Run after `python train.py` (the Dockerfile `test` stage and Jenkins do this)."""
import json
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app import app

CONFIG = json.loads(Path('config.json').read_text())
FEATURES = CONFIG['features']
client = TestClient(app)


def test_dataset_is_valid():
    df = pd.read_csv('dataset/train.csv')
    assert len(df) >= 100
    assert set(FEATURES + ['label']).issubset(df.columns)
    assert df['label'].nunique() == 2


def test_metrics_file_matches_data():
    metrics = json.loads(Path('artifacts/metrics.json').read_text())
    assert metrics['student_id'] == CONFIG['student_id']
    assert metrics['training_rows'] == len(pd.read_csv('dataset/train.csv'))
    assert len(metrics['model_version']) == 12
    assert metrics['git_sha']


def test_model_is_accurate_enough():
    metrics = json.loads(Path('artifacts/metrics.json').read_text())
    assert metrics['accuracy'] >= 0.70, metrics


def test_health_and_metrics_endpoints():
    assert client.get('/health').json() == {'status': 'ok'}
    body = client.get('/metrics').json()
    for key in ('student_id', 'accuracy', 'training_rows', 'model_version', 'git_sha'):
        assert key in body


def test_predict_endpoint():
    record = {f: 0.5 for f in FEATURES}
    r = client.post('/predict', json={'records': [record, {f: -2.0 for f in FEATURES}]})
    assert r.status_code == 200
    out = r.json()
    assert len(out['predictions']) == 2
    assert all(p in (0, 1) for p in out['predictions'])
    assert all(0.0 <= p <= 1.0 for p in out['probabilities'])


def test_predict_rejects_empty_batch():
    assert client.post('/predict', json={'records': []}).status_code == 422
