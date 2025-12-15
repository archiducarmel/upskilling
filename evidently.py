#!/usr/bin/env bash
set -euo pipefail

echo "=== Domino Evidently UI (SIP enabled) ==="

APP_HOST="0.0.0.0"
APP_PORT="8888"

BASE_PATH="${DOMINO_RUN_HOST_PATH:-}"
if [[ -z "${BASE_PATH}" ]]; then
  echo "ERROR: DOMINO_RUN_HOST_PATH is not set"
  exit 1
fi
# Normalisation: pas de trailing slash
BASE_PATH="${BASE_PATH%/}"
echo "Detected BASE_PATH=${BASE_PATH}"

WORKSPACE_DIR="${EVIDENTLY_WORKSPACE_DIR:-/mnt/evidently_workspace}"
mkdir -p "${WORKSPACE_DIR}"

python -m pip install -U pip >/dev/null
python -m pip install -U evidently uvicorn starlette httpx >/dev/null

INTERNAL_HOST="127.0.0.1"
INTERNAL_PORT="8889"

evidently ui --workspace "${WORKSPACE_DIR}" --host "${INTERNAL_HOST}" --port "${INTERNAL_PORT}" &
EVID_PID=$!

cat > /tmp/evidently_proxy.py << 'PY'
import os
import re
import httpx
from starlette.applications import Starlette
from starlette.responses import Response, RedirectResponse
from starlette.routing import Route
import uvicorn

APP_HOST = "0.0.0.0"
APP_PORT = 8888

BASE_PATH = os.environ["BASE_PATH"].rstrip("/")  # ex: /user/proj/r/notebookSession/xxxx
UPSTREAM = os.environ.get("UPSTREAM", "http://127.0.0.1:8889")

client = httpx.AsyncClient(follow_redirects=False, timeout=60.0)

def strip_base(path: str) -> str:
    if path == BASE_PATH:
        return "/"
    if path.startswith(BASE_PATH + "/"):
        return path[len(BASE_PATH):]
    return path

def rewrite_location(loc: str) -> str:
    # For redirects like "/projects", prefix BASE_PATH
    if loc.startswith("/") and not loc.startswith(BASE_PATH + "/") and loc != BASE_PATH:
        return BASE_PATH + loc
    return loc

def rewrite_html(html: str) -> str:
    # Prefix absolute root links with BASE_PATH: href="/x" -> href="{BASE_PATH}/x"
    # Covers href, src, action, and common JS fetch("/...") patterns.
    bp = BASE_PATH

    html = re.sub(r'(href|src|action)="/', rf'\1="{bp}/', html)
    html = re.sub(r"""(fetch\(["'])/""", rf"\1{bp}/", html)
    html = re.sub(r"""(axios\.(get|post|put|delete)\(["'])/""", rf"\1{bp}/", html)
    return html

async def proxy(request):
    upstream_path = strip_base(request.url.path)
    upstream_url = UPSTREAM + upstream_path
    if request.url.query:
        upstream_url += "?" + request.url.query

    headers = dict(request.headers)
    headers.pop("host", None)

    resp = await client.request(
        request.method,
        upstream_url,
        headers=headers,
        content=await request.body(),
    )

    # Redirects
    if resp.status_code in (301,302,303,307,308):
        return RedirectResponse(
            url=rewrite_location(resp.headers.get("location", "/")),
            status_code=resp.status_code
        )

    out_headers = dict(resp.headers)
    # remove hop-by-hop + encoding; also drop content-length because we might rewrite
    for k in ["content-encoding", "transfer-encoding", "connection", "content-length"]:
        out_headers.pop(k, None)

    content = resp.content
    ctype = resp.headers.get("content-type", "")

    # If HTML, rewrite to make it base-path aware under Domino
    if "text/html" in ctype.lower():
        try:
            text = resp.text
            text = rewrite_html(text)
            content = text.encode("utf-8")
            out_headers["content-type"] = "text/html; charset=utf-8"
        except Exception:
            # If rewrite fails, fallback to raw
            content = resp.content

    return Response(content=content, status_code=resp.status_code, headers=out_headers)

app = Starlette(routes=[Route("/{path:path}", proxy, methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"])])

if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="info")
PY

export BASE_PATH
export UPSTREAM="http://${INTERNAL_HOST}:${INTERNAL_PORT}"

python /tmp/evidently_proxy.py

kill "${EVID_PID}" || true
PY
