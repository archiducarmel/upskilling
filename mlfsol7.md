D'accord, prenons du recul et analysons TOUT.

## Récapitulatif des tentatives et échecs :

| Tentative | Résultat |
|-----------|----------|
| `--static-prefix` + `--allowed-hosts "*"` | DNS rebinding malgré "Allowed hosts: *" dans les logs |
| `--allowed-hosts` avec domaines explicites | Même erreur |
| uvicorn + `--root-path` | Erreur WSGI/ASGI incompatible |
| gunicorn + `SCRIPT_NAME` | "Bad Request - path doesn't start with SCRIPT_NAME" |
| gunicorn sans `SCRIPT_NAME` | Retour DNS rebinding |

## Analyse du problème réel :

Le header Host reçu par MLflow est :
```
run-xxx.domino-compute-8ca2164e.svc.cluster.local:8765
```

**Le problème** : MLflow affiche "Allowed hosts: *" mais **le middleware rejette quand même**. Cela suggère que :
1. Le wildcard `*` ne fonctionne pas comme prévu dans MLflow 3.x
2. Ou le middleware est appliqué AVANT que l'option soit lue

## Solution : Patcher le middleware AVANT le chargement

Créez `mlflow_server.py` :

```python
import os
import sys
import subprocess

# Installation
subprocess.check_call([sys.executable, "-m", "pip", "install", "mlflow>=3.1", "gunicorn"])

# ============================================
# PATCH DU MIDDLEWARE DE SÉCURITÉ
# Doit être fait AVANT d'importer mlflow.server
# ============================================

# Patch 1: Désactiver la vérification dans fastapi_security
try:
    import mlflow.server.fastapi_security as security_module
    
    # Remplacer la fonction de validation
    original_validate = getattr(security_module, 'validate_host', None)
    if original_validate:
        security_module.validate_host = lambda *args, **kwargs: True
    
    # Désactiver le middleware
    if hasattr(security_module, 'SecurityMiddleware'):
        class DummyMiddleware:
            def __init__(self, app, **kwargs):
                self.app = app
            async def __call__(self, scope, receive, send):
                await self.app(scope, receive, send)
        security_module.SecurityMiddleware = DummyMiddleware
    
    print("[PATCH] fastapi_security patched successfully")
except Exception as e:
    print(f"[PATCH] fastapi_security patch failed: {e}")

# Patch 2: Désactiver dans handlers si présent
try:
    import mlflow.server.handlers as handlers_module
    
    if hasattr(handlers_module, '_is_valid_host'):
        handlers_module._is_valid_host = lambda *args, **kwargs: True
    if hasattr(handlers_module, 'is_valid_host'):
        handlers_module.is_valid_host = lambda *args, **kwargs: True
    
    print("[PATCH] handlers patched successfully")
except Exception as e:
    print(f"[PATCH] handlers patch failed: {e}")

# Patch 3: Variable d'environnement pour forcer
os.environ["MLFLOW_ALLOWED_HOSTS"] = "*"
os.environ["MLFLOW_DISABLE_HOST_CHECK"] = "true"

# ============================================
# CONFIGURATION MLFLOW
# ============================================

mlflow_home = os.path.expanduser("~/.mlflow")
os.makedirs(f"{mlflow_home}/mlartifacts", exist_ok=True)

os.environ["MLFLOW_BACKEND_STORE_URI"] = f"sqlite:///{mlflow_home}/mlflow.db"
os.environ["MLFLOW_DEFAULT_ARTIFACT_ROOT"] = f"{mlflow_home}/mlartifacts"

print(f"Backend Store: sqlite:///{mlflow_home}/mlflow.db")
print(f"Artifact Root: {mlflow_home}/mlartifacts")
print("Starting MLflow server...")

# ============================================
# LANCEMENT VIA GUNICORN
# ============================================

os.system('gunicorn --bind 0.0.0.0:8888 --workers 2 --timeout 120 mlflow.server:app')
```

Puis `app.sh` :

```bash
#!/usr/bin/env bash
python mlflow_server.py
```

---

## Alternative : Patch plus agressif au niveau WSGI

Créez `mlflow_server.py` :

```python
import os
import sys
import subprocess

subprocess.check_call([sys.executable, "-m", "pip", "install", "mlflow>=3.1", "gunicorn", "werkzeug"])

# Configuration
mlflow_home = os.path.expanduser("~/.mlflow")
os.makedirs(f"{mlflow_home}/mlartifacts", exist_ok=True)

os.environ["MLFLOW_BACKEND_STORE_URI"] = f"sqlite:///{mlflow_home}/mlflow.db"
os.environ["MLFLOW_DEFAULT_ARTIFACT_ROOT"] = f"{mlflow_home}/mlartifacts"
os.environ["MLFLOW_ALLOWED_HOSTS"] = "*"

# Import et patch
from mlflow.server import app as mlflow_app

# Créer un wrapper WSGI qui bypasse la vérification du host
class HostBypassMiddleware:
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        # Forcer le host à localhost pour bypasser la vérification
        environ['HTTP_HOST'] = 'localhost:8888'
        environ['SERVER_NAME'] = 'localhost'
        environ['SERVER_PORT'] = '8888'
        return self.app(environ, start_response)

# Wrapper l'app
wrapped_app = HostBypassMiddleware(mlflow_app)

print("Starting MLflow with host bypass middleware...")

# Exporter pour gunicorn
app = wrapped_app
```

Créez aussi `gunicorn_config.py` :

```python
bind = "0.0.0.0:8888"
workers = 2
timeout = 120
```

Puis `app.sh` :

```bash
#!/usr/bin/env bash

pip install "mlflow>=3.1" gunicorn

python -c "
import os
import sys

mlflow_home = os.path.expanduser('~/.mlflow')
os.makedirs(f'{mlflow_home}/mlartifacts', exist_ok=True)

os.environ['MLFLOW_BACKEND_STORE_URI'] = f'sqlite:///{mlflow_home}/mlflow.db'
os.environ['MLFLOW_DEFAULT_ARTIFACT_ROOT'] = f'{mlflow_home}/mlartifacts'
os.environ['MLFLOW_ALLOWED_HOSTS'] = '*'

from mlflow.server import app as mlflow_app

class HostBypassMiddleware:
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        environ['HTTP_HOST'] = 'localhost:8888'
        environ['SERVER_NAME'] = 'localhost'
        environ['SERVER_PORT'] = '8888'
        return self.app(environ, start_response)

import mlflow.server
mlflow.server.app = HostBypassMiddleware(mlflow_app)
print('Middleware applied')
"

gunicorn --bind 0.0.0.0:8888 --workers 2 mlflow.server:app
```

---

## Solution de secours : MLflow 2.x

Si rien ne fonctionne, MLflow 2.x n'a pas ce middleware strict :

```bash
#!/usr/bin/env bash

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow 2.x (sans middleware strict)"
pip install "mlflow>=2.0,<3.0"
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts"
```

---

Essayez d'abord l'**Alternative avec HostBypassMiddleware**, sinon passez à **MLflow 2.x** !
