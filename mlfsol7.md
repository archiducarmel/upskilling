Progrès ! Le serveur démarre mais il y a une erreur d'initialisation. L'app MLflow n'est pas correctement configurée quand lancée via uvicorn directement.

## Solution : Script Python avec initialisation complète

Créez `mlflow_server.py` :

```python
import os
import sys
import subprocess

# Installation
subprocess.check_call([sys.executable, "-m", "pip", "install", "mlflow>=3.1", "uvicorn"])

# Configuration des chemins
mlflow_home = os.path.expanduser("~/.mlflow")
os.makedirs(f"{mlflow_home}/mlartifacts", exist_ok=True)

# Variables d'environnement AVANT import mlflow
os.environ["MLFLOW_BACKEND_STORE_URI"] = f"sqlite:///{mlflow_home}/mlflow.db"
os.environ["MLFLOW_DEFAULT_ARTIFACT_ROOT"] = f"{mlflow_home}/mlartifacts"
os.environ["MLFLOW_ARTIFACTS_DESTINATION"] = f"{mlflow_home}/mlartifacts"
os.environ["MLFLOW_ALLOWED_HOSTS"] = "*"

# Calculer le root path
root_path = f"/{os.environ.get('DOMINO_PROJECT_OWNER')}/{os.environ.get('DOMINO_PROJECT_NAME')}/r/notebookSession/{os.environ.get('DOMINO_RUN_ID')}"

print(f"Backend Store: sqlite:///{mlflow_home}/mlflow.db")
print(f"Artifact Root: {mlflow_home}/mlartifacts")
print(f"Root path: {root_path}")

# Initialiser MLflow avec la bonne configuration
from mlflow.server import app
from mlflow.server.handlers import initialize_backend_stores

# Initialiser les stores
initialize_backend_stores(
    backend_store_uri=f"sqlite:///{mlflow_home}/mlflow.db",
    default_artifact_root=f"{mlflow_home}/mlartifacts"
)

print("Backend stores initialized")
print("Starting MLflow server...")

import uvicorn
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

## Alternative : Combiner mlflow server avec proxy

Si l'approche uvicorn ne fonctionne pas, on peut lancer MLflow sur un port interne et faire un proxy :

```bash
#!/usr/bin/env bash

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

export MLFLOW_ALLOWED_HOSTS="*"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing dependencies"
pip install "mlflow>=3.1"
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

# Lancer MLflow normalement sur le port 8888
# Le static-prefix aide pour les assets, mais on accepte le 404 sur la racine
mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts" \
    --allowed-hosts "*"
```

Puis accédez directement à l'URL **sans le préfixe Domino** si possible, ou vérifiez si Domino a une option pour désactiver le proxy path.

---

## Alternative : Vérifier les logs d'erreur détaillés

Modifiez le script pour voir l'erreur exacte :

```bash
#!/usr/bin/env bash

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

export MLFLOW_BACKEND_STORE_URI="sqlite:///$MLFLOW_HOME/mlflow.db"
export MLFLOW_DEFAULT_ARTIFACT_ROOT="$MLFLOW_HOME/mlartifacts"
export MLFLOW_ALLOWED_HOSTS="*"

ROOT_PATH="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

pip install "mlflow>=3.1" uvicorn

echo "Root path: $ROOT_PATH"

# Ajouter --log-level debug pour voir les erreurs
uvicorn mlflow.server:app \
    --host 0.0.0.0 \
    --port 8888 \
    --root-path "$ROOT_PATH" \
    --log-level debug
```

Essayez d'abord le script Python avec `initialize_backend_stores` !
