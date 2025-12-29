#!/usr/bin/env bash

echo "[Exporting variables ...]"
export PHOENIX_PORT=8888
export PHOENIX_DEFAULT_RETENTION_POLICY_DAYS=10
export PHOENIX_DEFAULT_ADMIN_INITIAL_PASSWORD="admin"
export PHOENIX_ENABLE_AUTH="true"
export PHOENIX_SECRET="BCEFIT_2DAI5_IAFACTORY_monitoringtool_PROOFOFCONCEPT"
export PHOENIX_USE_SECRET_COOKIES="true"

# Root path pour le proxy Domino
ROOT_PATH="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

echo "Installing Arize Phoenix"
pip install arize-phoenix uvicorn
echo "Installation finished"

echo "Launching Arize server with root_path: $ROOT_PATH"

# Trouver le bon module ASGI de Phoenix
python -c "from phoenix.server.app import create_app; print('Module found')"

# Lancer avec uvicorn
uvicorn phoenix.server.app:create_app --factory --host 0.0.0.0 --port 8888 --root-path "$ROOT_PATH"
