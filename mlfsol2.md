C'est une protection de sécurité de MLflow contre les attaques DNS rebinding. Il faut autoriser le hostname du proxy Domino.

## Solution : Ajouter `--allowed-hosts`

```bash
#!/usr/bin/env bash

echo "[Exporting variables ...]"
export MLFLOW_PORT=8888

# Répertoire de travail persistant
MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

# Calcul du root path pour le proxy Domino
STATIC_PREFIX="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

# Variables d'environnement pour le root path
export SCRIPT_NAME="$STATIC_PREFIX"
export MLFLOW_STATIC_PREFIX="$STATIC_PREFIX"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow >= 3.1"
pip install "mlflow>=3.1"
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "MLflow version:"
mlflow --version
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Static Prefix: $STATIC_PREFIX"
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

## Alternative si `--allowed-hosts` n'existe pas dans votre version

```bash
#!/usr/bin/env bash

echo "[Exporting variables ...]"
export MLFLOW_PORT=8888

# Répertoire de travail persistant
MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

# Calcul du root path pour le proxy Domino
STATIC_PREFIX="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

# Autoriser tous les hosts via variable d'environnement
export MLFLOW_ALLOWED_HOSTS="all"
# Alternative : spécifier les domaines explicitement
# export MLFLOW_ALLOWED_HOSTS="datalab.cloud.echonet,datalab.cloud.net,localhost"

export SCRIPT_NAME="$STATIC_PREFIX"
export MLFLOW_STATIC_PREFIX="$STATIC_PREFIX"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow >= 3.1"
pip install "mlflow>=3.1"
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Static Prefix: $STATIC_PREFIX"
echo "Allowed Hosts: $MLFLOW_ALLOWED_HOSTS"
echo "Launching MLflow server"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts" \
    --static-prefix "$STATIC_PREFIX"
```

---

## Diagnostic si ça ne fonctionne toujours pas

Ajoutez ce bloc pour voir les options disponibles :

```bash
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Checking available host options:"
mlflow server --help | grep -i host
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
```

Essayez d'abord avec `--allowed-hosts "all"` et dites-moi le résultat ! 🚀
