L'option `--root-path` n'existe pas dans `mlflow server`. Il faut passer par **uvicorn directement**.

## Solution : Uvicorn avec root-path

```bash
#!/usr/bin/env bash

export MLFLOW_PORT=8888

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

ROOT_PATH="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

# Configuration via variables d'environnement
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
```

---

## Alternative : Script Python complet

Créez `mlflow_server.py` :

```python
import os
import sys
import subprocess

# Installation
subprocess.check_call([sys.executable, "-m", "pip", "install", "mlflow>=3.1", "uvicorn"])

# Configuration
mlflow_home = os.path.expanduser("~/.mlflow")
os.makedirs(f"{mlflow_home}/mlartifacts", exist_ok=True)

os.environ["MLFLOW_BACKEND_STORE_URI"] = f"sqlite:///{mlflow_home}/mlflow.db"
os.environ["MLFLOW_DEFAULT_ARTIFACT_ROOT"] = f"{mlflow_home}/mlartifacts"
os.environ["MLFLOW_ALLOWED_HOSTS"] = "*"

root_path = f"/{os.environ.get('DOMINO_PROJECT_OWNER')}/{os.environ.get('DOMINO_PROJECT_NAME')}/r/notebookSession/{os.environ.get('DOMINO_RUN_ID')}"

print(f"Root path: {root_path}")
print("Starting MLflow server...")

import uvicorn
from mlflow.server import app

uvicorn.run(
    app,
    host="0.0.0.0",
    port=8888,
    root_path=root_path
)
```

Puis `app.sh` :

```bash
#!/usr/bin/env bash
python mlflow_server.py
```

---

Essayez la première solution avec uvicorn en ligne de commande !
