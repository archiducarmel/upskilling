#!/usr/bin/env bash
set -euo pipefail

echo "=== Domino Evidently UI (SIP enabled) ==="

# Domino constraints
APP_HOST="0.0.0.0"
APP_PORT="8888"

BASE_PATH="${DOMINO_RUN_HOST_PATH}"
if [[ -z "${BASE_PATH}" ]]; then
  echo "ERROR: DOMINO_RUN_HOST_PATH is not set — SIP expected but missing"
  exit 1
fi

echo "Detected BASE_PATH=${BASE_PATH}"

# Workspace (persisted across runs if /mnt is mounted)
WORKSPACE_DIR="${EVIDENTLY_WORKSPACE_DIR:-/mnt/evidently_workspace}"
mkdir -p "${WORKSPACE_DIR}"

# Install deps
python -m pip install -U pip >/dev/null
python -m pip install -U evidently uvicorn starlette httpx >/dev/null

# Start Evidently on internal port
INTERNAL_PORT="8889"
evidently ui \
  --workspace "${WORKSPACE_DIR}" \
  --host 127.0.0.1 \
  --port "${INTERNAL_PORT}" &
EVID_PID=$!

# Reverse proxy (strip BASE_PATH)
cat > /tmp/evidently_proxy.py << 'PY'
import os, httpx
from starlette.applications import Starlette
from starlette.responses import Response, RedirectResponse
from starlette.routing import Route
import uvicorn

APP_HOST = "0.0.0.0"
APP_PORT = 8888
BASE_PATH = os.environ["BASE_PATH"].rstrip("/")
UPSTREAM = "http://127.0.0.1:8889"

client = httpx.AsyncClient(timeout=60.0)

def strip_base(path):
    if path == BASE_PATH:
        return "/"
    if path.startswith(BASE_PATH + "/"):
        return path[len(BASE_PATH):]
    return path

def rewrite_location(loc):
    if loc.startswith("/") and not loc.startswith(BASE_PATH):
        return BASE_PATH + loc
    return loc

async def proxy(request):
    upstream_path = strip_base(request.url.path)
    url = UPSTREAM + upstream_path
    if request.url.query:
        url += "?" + request.url.query

    headers = dict(request.headers)
    headers.pop("host", None)

    resp = await client.request(
        request.method, url, headers=headers, content=await request.body()
    )

    if resp.status_code in (301,302,303,307,308):
        return RedirectResponse(
            url=rewrite_location(resp.headers.get("location","/")),
            status_code=resp.status_code,
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={k:v for k,v in resp.headers.items()
                 if k.lower() not in ("content-encoding","transfer-encoding","connection")},
    )

app = Starlette(routes=[Route("/{path:path}", proxy, methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"])])

uvicorn.run(app, host=APP_HOST, port=APP_PORT)
PY

export BASE_PATH
python /tmp/evidently_proxy.py

# Cleanup
kill "${EVID_PID}" || true
