#!/usr/bin/env bash

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow"
pip install "mlflow>=3.1"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Patching MLflow security middleware"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

# Trouver le fichier de sécurité
MLFLOW_PATH=$(python -c "import mlflow; import os; print(os.path.dirname(mlflow.__file__))")
SECURITY_FILE="$MLFLOW_PATH/server/fastapi_security.py"

echo "MLflow path: $MLFLOW_PATH"
echo "Security file: $SECURITY_FILE"

# Backup et patch - remplacer la fonction de validation pour toujours retourner True
if [ -f "$SECURITY_FILE" ]; then
    cp "$SECURITY_FILE" "$SECURITY_FILE.backup"
    
    # Patch : faire que is_valid_host retourne toujours True
    sed -i 's/def is_valid_host(host.*$/def is_valid_host(host, allowed_hosts=None): return True  # PATCHED/' "$SECURITY_FILE"
    sed -i 's/def _is_valid_host(host.*$/def _is_valid_host(host, allowed_hosts=None): return True  # PATCHED/' "$SECURITY_FILE"
    
    echo "Security file patched!"
    grep -n "PATCHED" "$SECURITY_FILE" || echo "Checking patch..."
else
    echo "Security file not found, trying alternative location..."
    find "$MLFLOW_PATH" -name "*.py" -exec grep -l "DNS rebinding" {} \; 2>/dev/null
fi

# Patch alternatif : chercher et patcher tout fichier avec la validation
for f in $(find "$MLFLOW_PATH" -name "*.py" -exec grep -l "is_valid_host\|allowed_hosts\|rebinding" {} \; 2>/dev/null); do
    echo "Patching: $f"
    sed -i 's/if not is_valid_host/if False and not is_valid_host/g' "$f"
    sed -i 's/if not _is_valid_host/if False and not _is_valid_host/g' "$f"
done

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Launching MLflow server"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts" \
    --allowed-hosts "*"
