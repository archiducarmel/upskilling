#!/usr/bin/env bash

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

# Construire le root path Domino
ROOT_PATH="/${DOMINO_PROJECT_OWNER}/${DOMINO_PROJECT_NAME}/r/notebookSession/${DOMINO_RUN_ID}"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "ROOT_PATH: $ROOT_PATH"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

pip install "mlflow>=3.5"

python << 'EOF'
import mlflow
import os
mlflow_home = os.path.expanduser("~/.mlflow")
mlflow.set_tracking_uri(f"sqlite:///{mlflow_home}/mlflow.db")
try:
    mlflow.create_experiment("Default")
except:
    pass
print("Database ready!")
EOF

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Launching MLflow"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts" \
    --static-prefix "$ROOT_PATH" \
    --disable-security-middleware
