#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Domino App: MLflow Tracking Server
#
# Expected environment variables (set them in Domino Project/App env vars):
#   MLFLOW_BACKEND_STORE_URI        (required) e.g. postgresql+psycopg2://user:pass@host:5432/mlflow
#   MLFLOW_DEFAULT_ARTIFACT_ROOT    (required) e.g. s3://my-mlflow-artifacts/proj-x
#
# Optional (S3 / MinIO / enterprise object storage):
#   AWS_ACCESS_KEY_ID
#   AWS_SECRET_ACCESS_KEY
#   AWS_SESSION_TOKEN
#   AWS_DEFAULT_REGION
#   MLFLOW_S3_ENDPOINT_URL          e.g. https://minio.company.tld (or COS/S3 compatible endpoint)
#   AWS_CA_BUNDLE                  path to internal CA bundle if needed
#
# App runtime:
#   PORT                            default 8888 (Domino-friendly)
#   MLFLOW_WORKERS                  default: min(4, nproc)
#   MLFLOW_GUNICORN_OPTS            extra gunicorn flags (timeouts, etc.)
###############################################################################

echo "[app.sh] Starting MLflow on Domino..."

# --- Port: Domino proxy friendly ---
PORT="${PORT:-8888}"

# --- Hard requirements ---
: "${MLFLOW_BACKEND_STORE_URI:?Missing env var MLFLOW_BACKEND_STORE_URI}"
: "${MLFLOW_DEFAULT_ARTIFACT_ROOT:?Missing env var MLFLOW_DEFAULT_ARTIFACT_ROOT}"

# --- Ensure mlflow is available (in a bank you typically bake this into the Domino Environment image) ---
if ! command -v mlflow >/dev/null 2>&1; then
  echo "[app.sh] ERROR: 'mlflow' binary not found in PATH."
  echo "[app.sh] In an enterprise setup, install MLflow in the Domino Compute Environment image."
  echo "[app.sh] Example (Dockerfile): RUN pip install 'mlflow[extras]' psycopg2-binary boto3"
  exit 127
fi

# --- Basic dependency sanity checks (backend DB drivers / S3 SDK) ---
python - <<'PY'
import sys
missing=[]
for mod in ["mlflow"]:
    try: __import__(mod)
    except Exception: missing.append(mod)
# psycopg2 is needed for postgres backend-store-uri (common in enterprise)
try: __import__("psycopg2")
except Exception: pass
# boto3 needed for s3 artifact browsing / UI downloads
try: __import__("boto3")
except Exception: pass
if missing:
    print("[app.sh] Missing python modules:", missing, file=sys.stderr)
    sys.exit(1)
print("[app.sh] Python deps OK")
PY

# --- Compute a safe default worker count ---
NPROC="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)"
DEFAULT_WORKERS="$NPROC"
if [ "$DEFAULT_WORKERS" -gt 4 ]; then DEFAULT_WORKERS=4; fi
MLFLOW_WORKERS="${MLFLOW_WORKERS:-$DEFAULT_WORKERS}"

# --- Gunicorn defaults (safe for slow artifact listing / large UI requests) ---
# You can override via MLFLOW_GUNICORN_OPTS in Domino env vars.
# NOTE: keep logs to stdout/stderr for Domino log collection.
GUNICORN_OPTS_DEFAULT="--timeout 120 --graceful-timeout 30 --keep-alive 5 --access-logfile - --error-logfile -"
MLFLOW_GUNICORN_OPTS="${MLFLOW_GUNICORN_OPTS:-$GUNICORN_OPTS_DEFAULT}"

# --- Print non-sensitive config (never print secrets) ---
echo "[app.sh] PORT=$PORT"
echo "[app.sh] MLFLOW_WORKERS=$MLFLOW_WORKERS"
echo "[app.sh] Backend store: ${MLFLOW_BACKEND_STORE_URI%%:*}://***"
echo "[app.sh] Artifact root: $MLFLOW_DEFAULT_ARTIFACT_ROOT"
if [ -n "${MLFLOW_S3_ENDPOINT_URL:-}" ]; then
  echo "[app.sh] Using S3 endpoint: $MLFLOW_S3_ENDPOINT_URL"
fi

# --- Recommended: ensure Domino / corporate proxy doesn't buffer too aggressively (best-effort) ---
export PYTHONUNBUFFERED=1

# --- Start MLflow server ---
# We bind on 0.0.0.0 so Domino can route traffic into the container.
# We keep it stateless; metadata in DB, artifacts in S3-compatible storage.
exec mlflow server \
  --host 0.0.0.0 \
  --port "$PORT" \
  --workers "$MLFLOW_WORKERS" \
  --backend-store-uri "$MLFLOW_BACKEND_STORE_URI" \
  --default-artifact-root "$MLFLOW_DEFAULT_ARTIFACT_ROOT" \
  --gunicorn-opts "$MLFLOW_GUNICORN_OPTS"
