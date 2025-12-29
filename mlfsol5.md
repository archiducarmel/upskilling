Parfait ! Je vois le problème maintenant. Le Host header rejeté est :

```
run-6952932aa2ba4b3ffc84a3e.domino-compute-8ca2164e.svc.cluster.local:8765
```

C'est le hostname **interne Kubernetes** de Domino. Il faut l'ajouter explicitement !

## Solution : Ajouter les hostnames Kubernetes internes

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

# Ajouter les hostnames Kubernetes internes avec wildcard
ALLOWED_HOSTS="localhost,127.0.0.1,0.0.0.0,.svc.cluster.local,.domino-compute-8ca2164e.svc.cluster.local,datalab.cloud.echonet,datalab.cloud.net,.datalab.cloud.echonet,.datalab.cloud.net"

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

## Alternative : Pattern plus générique avec wildcard

Si MLflow supporte les wildcards avec `*` :

```bash
ALLOWED_HOSTS="*"
```

Ou :

```bash
ALLOWED_HOSTS="localhost,127.0.0.1,0.0.0.0,*.svc.cluster.local,*.datalab.cloud.echonet,*.datalab.cloud.net"
```

---

## Si ça ne fonctionne toujours pas : Patcher le middleware

Créez `mlflow_patch.py` :

```python
import os
import sys
import subprocess

subprocess.check_call([sys.executable, "-m", "pip", "install", "mlflow>=3.1"])

# Patcher le module de sécurité AVANT le démarrage
from mlflow.server import fastapi_security

# Sauvegarder la fonction originale
original_validate = fastapi_security.validate_host

# Nouvelle fonction qui accepte tout
def patched_validate(*args, **kwargs):
    return True

# Remplacer
fastapi_security.validate_host = patched_validate

# Aussi essayer de patcher la liste des hosts
if hasattr(fastapi_security, '_allowed_hosts'):
    fastapi_security._allowed_hosts = None
if hasattr(fastapi_security, 'ALLOWED_HOSTS'):
    fastapi_security.ALLOWED_HOSTS = None

print("Security middleware patched!")

# Lancer le serveur
mlflow_home = os.path.expanduser("~/.mlflow")
os.makedirs(f"{mlflow_home}/mlartifacts", exist_ok=True)

static_prefix = f"/{os.environ.get('DOMINO_PROJECT_OWNER')}/{os.environ.get('DOMINO_PROJECT_NAME')}/r/notebookSession/{os.environ.get('DOMINO_RUN_ID')}"

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
python mlflow_patch.py
```

---

Essayez d'abord la première solution avec `.svc.cluster.local` dans les allowed hosts !
