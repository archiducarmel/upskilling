L'erreur est claire maintenant ! MLflow utilise **Flask (WSGI)** mais uvicorn est un serveur **ASGI**. Il faut utiliser **gunicorn** à la place.

## Solution : Utiliser gunicorn avec root-path

```bash
#!/usr/bin/env bash

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

ROOT_PATH="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

export MLFLOW_BACKEND_STORE_URI="sqlite:///$MLFLOW_HOME/mlflow.db"
export MLFLOW_DEFAULT_ARTIFACT_ROOT="$MLFLOW_HOME/mlartifacts"
export MLFLOW_ALLOWED_HOSTS="*"
export SCRIPT_NAME="$ROOT_PATH"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing dependencies"
pip install "mlflow>=3.1" gunicorn
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Root path: $ROOT_PATH"
echo "Launching MLflow via gunicorn"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

gunicorn \
    --bind 0.0.0.0:8888 \
    --workers 2 \
    --env SCRIPT_NAME="$ROOT_PATH" \
    mlflow.server:app
```

---

## Alternative : Script Python avec gunicorn

Créez `mlflow_server.py` :

```python
import os
import sys
import subprocess

# Installation
subprocess.check_call([sys.executable, "-m", "pip", "install", "mlflow>=3.1", "gunicorn"])

# Configuration
mlflow_home = os.path.expanduser("~/.mlflow")
os.makedirs(f"{mlflow_home}/mlartifacts", exist_ok=True)

root_path = f"/{os.environ.get('DOMINO_PROJECT_OWNER')}/{os.environ.get('DOMINO_PROJECT_NAME')}/r/notebookSession/{os.environ.get('DOMINO_RUN_ID')}"

os.environ["MLFLOW_BACKEND_STORE_URI"] = f"sqlite:///{mlflow_home}/mlflow.db"
os.environ["MLFLOW_DEFAULT_ARTIFACT_ROOT"] = f"{mlflow_home}/mlartifacts"
os.environ["MLFLOW_ALLOWED_HOSTS"] = "*"
os.environ["SCRIPT_NAME"] = root_path

print(f"Root path: {root_path}")
print("Starting MLflow server via gunicorn...")

# Lancer gunicorn
os.system(f'gunicorn --bind 0.0.0.0:8888 --workers 2 --env SCRIPT_NAME="{root_path}" mlflow.server:app')
```

Puis `app.sh` :

```bash
#!/usr/bin/env bash
python mlflow_server.py
```

---

Essayez la première solution avec gunicorn directement !
