L'app Phoenix nécessite des paramètres spécifiques. Essayons d'autres approches :

## Solution 1 : Variable d'environnement PHOENIX_HOST_ROOT_PATH

```bash
#!/usr/bin/env bash

export PHOENIX_PORT=8888
export PHOENIX_DEFAULT_RETENTION_POLICY_DAYS=10
export PHOENIX_DEFAULT_ADMIN_INITIAL_PASSWORD="admin"
export PHOENIX_ENABLE_AUTH="true"
export PHOENIX_SECRET="BCEFIT_2DAI5_IAFACTORY_monitoringtool_PROOFOFCONCEPT"
export PHOENIX_USE_SECRET_COOKIES="true"

# Essayer différentes variables d'environnement pour le root path
export PHOENIX_HOST_ROOT_PATH="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"
export PHOENIX_BASE_URL="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

pip install arize-phoenix

phoenix serve
```

## Solution 2 : Trouver le bon point d'entrée

Ajoutez ce script de diagnostic pour identifier le module correct :

```bash
#!/usr/bin/env bash

export PHOENIX_PORT=8888
export PHOENIX_DEFAULT_ADMIN_INITIAL_PASSWORD="admin"
export PHOENIX_ENABLE_AUTH="true"
export PHOENIX_SECRET="BCEFIT_2DAI5_IAFACTORY_monitoringtool_PROOFOFCONCEPT"

pip install arize-phoenix

# Diagnostic : trouver le bon module
python << 'EOF'
import phoenix
import inspect
import os

# Afficher la version
print(f"Phoenix version: {phoenix.__version__}")

# Chercher les modules disponibles
print("\n--- Modules disponibles ---")
for name in dir(phoenix):
    if not name.startswith('_'):
        print(f"  {name}")

# Chercher le point d'entrée ASGI
try:
    from phoenix.server import app as server_app
    print(f"\n--- phoenix.server.app contents ---")
    for name in dir(server_app):
        if not name.startswith('_'):
            obj = getattr(server_app, name)
            print(f"  {name}: {type(obj)}")
except Exception as e:
    print(f"Error: {e}")

# Vérifier les variables d'environnement supportées
print("\n--- Environment variables ---")
for key in sorted(os.environ.keys()):
    if 'PHOENIX' in key:
        print(f"  {key}={os.environ[key]}")
EOF

phoenix serve
```

## Solution 3 : Wrapper avec middleware ASGI

Créez un fichier `phoenix_wrapper.py` :

```python
import os
import subprocess
import sys

# Installer les dépendances
subprocess.check_call([sys.executable, "-m", "pip", "install", "arize-phoenix", "asgiref"])

from phoenix.server.main import main
import uvicorn

# Patch pour ajouter le root_path
original_run = uvicorn.run

def patched_run(app, **kwargs):
    root_path = f"/{os.environ.get('DOMINO_PROJECT_OWNER')}/{os.environ.get('DOMINO_PROJECT_NAME')}/r/notebookSession/{os.environ.get('DOMINO_RUN_ID')}"
    kwargs['root_path'] = root_path
    print(f"Starting with root_path: {root_path}")
    return original_run(app, **kwargs)

uvicorn.run = patched_run

# Lancer Phoenix
if __name__ == "__main__":
    sys.argv = ["phoenix", "serve"]
    main()
```

Puis `app.sh` :

```bash
#!/usr/bin/env bash

export PHOENIX_PORT=8888
export PHOENIX_DEFAULT_ADMIN_INITIAL_PASSWORD="admin"
export PHOENIX_ENABLE_AUTH="true"
export PHOENIX_SECRET="BCEFIT_2DAI5_IAFACTORY_monitoringtool_PROOFOFCONCEPT"

python phoenix_wrapper.py
```

## Solution 4 : Reverse proxy avec un simple script Python

Créez `proxy_app.py` :

```python
import os
import subprocess
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request

# Installer Phoenix
subprocess.check_call(["pip", "install", "arize-phoenix"])

# Lancer Phoenix en arrière-plan sur un port interne
def start_phoenix():
    os.environ["PHOENIX_PORT"] = "8889"  # Port interne
    subprocess.run(["phoenix", "serve"])

phoenix_thread = threading.Thread(target=start_phoenix, daemon=True)
phoenix_thread.start()
time.sleep(10)  # Attendre que Phoenix démarre

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Rediriger vers Phoenix interne
        target_url = f"http://localhost:8889{self.path}"
        try:
            with urllib.request.urlopen(target_url) as response:
                self.send_response(response.status)
                for header, value in response.getheaders():
                    self.send_header(header, value)
                self.end_headers()
                self.wfile.write(response.read())
        except Exception as e:
            self.send_error(502, str(e))
    
    do_POST = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8888), ProxyHandler)
    print("Proxy running on port 8888")
    server.serve_forever()
```

Essayez d'abord la **Solution 1** avec les variables d'environnement, puis la **Solution 2** pour le diagnostic. Pouvez-vous exécuter le diagnostic et me partager la sortie ?
