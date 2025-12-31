#!/usr/bin/env bash

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

ROOT_PATH="/${DOMINO_PROJECT_OWNER}/${DOMINO_PROJECT_NAME}/r/notebookSession/${DOMINO_RUN_ID}"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "ROOT_PATH: $ROOT_PATH"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

pip install "mlflow>=3.5" "flask" "requests"

# Initialiser la base de données
python << 'EOF'
import mlflow, os
mlflow.set_tracking_uri(f"sqlite:///{os.path.expanduser('~/.mlflow')}/mlflow.db")
try: mlflow.create_experiment("Default")
except: pass
print("Database ready!")
EOF

# Créer le proxy Python
cat > /tmp/mlflow_proxy.py << 'PROXY'
#!/usr/bin/env python3
import os
import sys
from flask import Flask, request, Response
import requests

app = Flask(__name__)

ROOT_PATH = f"/{os.environ['DOMINO_PROJECT_OWNER']}/{os.environ['DOMINO_PROJECT_NAME']}/r/notebookSession/{os.environ['DOMINO_RUN_ID']}"
MLFLOW_URL = "http://127.0.0.1:5000"

print(f"Proxy starting - ROOT_PATH: {ROOT_PATH}", file=sys.stderr)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    # Strip ROOT_PATH prefix if present
    prefix = ROOT_PATH.lstrip('/')
    original_path = path
    if path.startswith(prefix):
        path = path[len(prefix):].lstrip('/')
    
    # Build target URL
    target_url = f"{MLFLOW_URL}/{path}"
    if request.query_string:
        target_url += f"?{request.query_string.decode()}"
    
    print(f"Proxy: {original_path} -> {path}", file=sys.stderr)
    
    # Forward request
    headers = {k: v for k, v in request.headers if k.lower() not in ['host', 'content-length']}
    
    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            allow_redirects=False,
            timeout=30
        )
        
        # Filter response headers
        excluded = ['content-encoding', 'transfer-encoding', 'connection', 'keep-alive']
        response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded]
        
        return Response(resp.content, resp.status_code, response_headers)
    except Exception as e:
        print(f"Proxy error: {e}", file=sys.stderr)
        return Response(f"Proxy error: {e}", 502)

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 8888, app, threaded=True, use_reloader=False)
PROXY

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Starting MLflow on port 5000 (internal)"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

# Lancer MLflow en arrière-plan sur port 5000
mlflow server \
    --host 127.0.0.1 \
    --port 5000 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts" \
    --disable-security-middleware &

MLFLOW_PID=$!

# Attendre que MLflow soit prêt
echo "Waiting for MLflow to start..."
sleep 5

for i in {1..30}; do
    if curl -s http://127.0.0.1:5000/ > /dev/null 2>&1; then
        echo "MLflow is ready!"
        break
    fi
    sleep 1
done

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Starting proxy on port 8888 (public)"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

# Lancer le proxy sur le port public
python /tmp/mlflow_proxy.py
