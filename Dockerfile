# ---- base: dependencies + code + data ----
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py train.py config.json ./
COPY dataset ./dataset

# ---- test: retrain, then run the test-suite (Jenkins builds this target first) ----
FROM base AS test
ARG GIT_COMMIT=local
ENV GIT_COMMIT=${GIT_COMMIT}
RUN pip install pytest httpx
COPY tests ./tests
RUN python train.py && python -m pytest -q tests

# ---- runtime: retrain on the latest data baked into the image, serve on 8000 ----
FROM base AS runtime
ARG GIT_COMMIT=local
ENV GIT_COMMIT=${GIT_COMMIT}
RUN python train.py
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
