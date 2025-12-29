Excellent progrès ! Le problème de host est résolu (Allowed hosts: *). Maintenant c'est un 404 Not Found - le --static-prefix ne fonctionne pas correctement avec MLflow 3.x.

Solution : Utiliser --root-path au lieu de --static-prefix
#!/usr/bin/env bash

export MLFLOW_PORT=8888

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

STATIC_PREFIX="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

export SCRIPT_NAME="$STATIC_PREFIX"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow >= 3.1"
pip install "mlflow>=3.1"
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Root path: $STATIC_PREFIX"
echo "Launching MLflow server"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts" \
    --allowed-hosts "*" \
    --root-path "$STATIC_PREFIX"
Alternative : Via uvicorn directement
#!/usr/bin/env bash

export MLFLOW_PORT=8888

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

ROOT_PATH="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

export MLFLOW_BACKEND_STORE_URI="sqlite:///$MLFLOW_HOME/mlflow.db"
export MLFLOW_DEFAULT_ARTIFACT_ROOT="$MLFLOW_HOME/mlartifacts"
export MLFLOW_ALLOWED_HOSTS="*"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow >= 3.1"
pip install "mlflow>=3.1" uvicorn
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Root path: $ROOT_PATH"
echo "Launching MLflow via uvicorn"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

uvicorn mlflow.server:app \
    --host 0.0.0.0 \
    --port 8888 \
    --root-path "$ROOT_PATH"
Alternative : Wrapper Python avec configuration
Créez mlflow_server.py :

import os
import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "pip", "install", "mlflow>=3.1"])

import uvicorn
from mlflow.server import app

mlflow_home = os.path.expanduser("~/.mlflow")
os.makedirs(f"{mlflow_home}/mlartifacts", exist_ok=True)

os.environ["MLFLOW_BACKEND_STORE_URI"] = f"sqlite:///{mlflow_home}/mlflow.db"
os.environ["MLFLOW_DEFAULT_ARTIFACT_ROOT"] = f"{mlflow_home}/mlartifacts"
os.environ["MLFLOW_ALLOWED_HOSTS"] = "*"

root_path = f"/{os.environ.get('DOMINO_PROJECT_OWNER')}/{os.environ.get('DOMINO_PROJECT_NAME')}/r/notebookSession/{os.environ.get('DOMINO_RUN_ID')}"

print(f"Starting MLflow with root_path: {root_path}")

uvicorn.run(
    app,
    host="0.0.0.0",
    port=8888,
    root_path=root_path
)
Puis app.sh :

#!/usr/bin/env bash
python mlflow_server.py
Essayez d'abord la première solution avec --root-path au lieu de --static-prefix !
