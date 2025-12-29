Le middleware semble ignorer l'option. Essayons plusieurs approches :

## Solution 1 : Variable d'environnement pour désactiver la vérification

```bash
#!/usr/bin/env bash

echo "[Exporting variables ...]"
export MLFLOW_PORT=8888

# Répertoire de travail persistant
MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

# Calcul du root path pour le proxy Domino
STATIC_PREFIX="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

export SCRIPT_NAME="$STATIC_PREFIX"
export MLFLOW_STATIC_PREFIX="$STATIC_PREFIX"

# Désactiver la vérification des hosts
export MLFLOW_ALLOWED_HOSTS="all"
export MLFLOW_DISABLE_HOST_CHECK="true"
export MLFLOW_HOST_HEADER_CHECK_ENABLED="false"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow >= 3.1"
pip install "mlflow>=3.1"
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Launching MLflow server"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts" \
    --static-prefix "$STATIC_PREFIX" \
    --allowed-hosts "all"
```

---

## Solution 2 : Spécifier explicitement les domaines Domino

```bash
#!/usr/bin/env bash

export MLFLOW_PORT=8888

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

STATIC_PREFIX="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

export SCRIPT_NAME="$STATIC_PREFIX"
export MLFLOW_STATIC_PREFIX="$STATIC_PREFIX"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow >= 3.1"
pip install "mlflow>=3.1"
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

# Liste explicite des domaines autorisés
ALLOWED_HOSTS="localhost,127.0.0.1,0.0.0.0,datalab.cloud.echonet,datalab.cloud.net,.datalab.cloud.echonet,.datalab.cloud.net"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Allowed hosts: $ALLOWED_HOSTS"
echo "Launching MLflow server"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts" \
    --static-prefix "$STATIC_PREFIX" \
    --allowed-hosts "$ALLOWED_HOSTS"
```

---

## Solution 3 : Wrapper Python pour patcher le middleware (si les autres échouent)

Créez `mlflow_server.py` dans votre projet :

```python
import os
import sys

# Installer MLflow
import subprocess
subprocess.check_call([sys.executable, "-m", "pip", "install", "mlflow>=3.1"])

# Patcher le middleware de sécurité AVANT d'importer mlflow
import mlflow.server.auth

# Monkey patch pour désactiver la vérification des hosts
original_check = None
try:
    from mlflow.server.handlers import _is_valid_host
    original_check = _is_valid_host
    mlflow.server.handlers._is_valid_host = lambda *args, **kwargs: True
except:
    pass

try:
    from mlflow.server import app as mlflow_app
    # Chercher et désactiver le middleware
    for attr in dir(mlflow_app):
        if 'host' in attr.lower() or 'security' in attr.lower():
            print(f"Found: {attr}")
except:
    pass

# Lancer le serveur
from mlflow.server import app
import mlflow.server.handlers

# Forcer l'acceptation de tous les hosts
if hasattr(mlflow.server.handlers, 'ALLOWED_HOSTS'):
    mlflow.server.handlers.ALLOWED_HOSTS = None

if hasattr(mlflow.server.handlers, '_allowed_hosts'):
    mlflow.server.handlers._allowed_hosts = None

# Configuration
mlflow_home = os.path.expanduser("~/.mlflow")
os.makedirs(f"{mlflow_home}/mlartifacts", exist_ok=True)

static_prefix = f"/{os.environ.get('DOMINO_PROJECT_OWNER')}/{os.environ.get('DOMINO_PROJECT_NAME')}/r/notebookSession/{os.environ.get('DOMINO_RUN_ID')}"

print(f"Starting MLflow with static_prefix: {static_prefix}")

# Lancer via CLI pour garder toutes les options
os.system(f'''mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///{mlflow_home}/mlflow.db" \
    --default-artifact-root "{mlflow_home}/mlartifacts" \
    --static-prefix "{static_prefix}" \
    --allowed-hosts "all"
''')
```

Puis `app.sh` :

```bash
#!/usr/bin/env bash
python mlflow_server.py
```

---

## Solution 4 : Utiliser gunicorn directement avec l'app WSGI

```bash
#!/usr/bin/env bash

export MLFLOW_PORT=8888

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

STATIC_PREFIX="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

export SCRIPT_NAME="$STATIC_PREFIX"
export MLFLOW_STATIC_PREFIX="$STATIC_PREFIX"
export MLFLOW_BACKEND_STORE_URI="sqlite:///$MLFLOW_HOME/mlflow.db"
export MLFLOW_DEFAULT_ARTIFACT_ROOT="$MLFLOW_HOME/mlartifacts"

# Désactiver toute vérification
export MLFLOW_ALLOWED_HOSTS="all"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow >= 3.1 and gunicorn"
pip install "mlflow>=3.1" gunicorn
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Launching MLflow via gunicorn"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

gunicorn \
    --bind 0.0.0.0:8888 \
    --workers 2 \
    --forwarded-allow-ips="*" \
    "mlflow.server:app"
```

---

## Solution 5 : Downgrade vers MLflow 2.x (dernier recours)

Si rien ne fonctionne, MLflow 2.x n'avait pas cette vérification stricte :

```bash
#!/usr/bin/env bash

export MLFLOW_PORT=8888

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

STATIC_PREFIX="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow 2.x"
pip install "mlflow>=2.0,<3.0"
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts" \
    --static-prefix "$STATIC_PREFIX"
```

---

Essayez d'abord la **Solution 2** (domaines explicites), puis la **Solution 4** (gunicorn). Dites-moi le résultat !
