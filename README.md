# MIDTERM-SP23-BAI-039 — automated ML retraining pipeline

GitHub push → Jenkins (`MIDTERM-SP23-BAI-039`) → `train.py` + pytest → Docker image → redeploy on AWS EC2 → email.

- `config.json` / `dataset/train.csv` – roll-specific config and generated training data
- `Dockerfile` – multi-stage: `test` (train + pytest) and `runtime` (FastAPI on :8000)
- `Jenkinsfile` – pipeline; `scripts/send_email.py` – post-build mail
- API: `GET /metrics`, `GET /health`, `POST /predict`
test
test2

_Pipeline: trigger verified 2026-11-23._
