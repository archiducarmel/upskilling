Je vais analyser les spécificités de MLflow 3.1+ et le contexte Domino pour créer un script fonctionnel.

## Analyse des points clés :

1. **Root path** : MLflow utilise `--static-prefix` pour gérer les proxies
2. **Port** : Domino attend généralement le port 8888
3. **Stockage** : Backend store (métadonnées) + Artifact store (fichiers)
4. **Authentification** : MLflow 3.x supporte l'auth native avec `--app-name basic-auth`

---

## Solution 1 : Script de base (sans authentification)

```bash
#!/usr/bin/env bash

echo "[Exporting variables ...]"
export MLFLOW_PORT=8888

# Répertoire de travail persistant
MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

# Calcul du root path pour le proxy Domino
STATIC_PREFIX="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow >= 3.1"
pip install "mlflow>=3.1"
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Static Prefix: $STATIC_PREFIX"
echo "Backend Store: sqlite:///$MLFLOW_HOME/mlflow.db"
echo "Artifact Root: $MLFLOW_HOME/mlartifacts"
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

## Solution 2 : Script avec authentification (recommandé pour production)

```bash
#!/usr/bin/env bash

echo "[Exporting variables ...]"
export MLFLOW_PORT=8888

# Répertoire de travail persistant
MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

# Calcul du root path pour le proxy Domino
STATIC_PREFIX="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

# Configuration de l'authentification
AUTH_CONFIG_PATH="$MLFLOW_HOME/basic_auth.ini"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow >= 3.1"
pip install "mlflow>=3.1"
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

# Créer le fichier de configuration auth
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Creating authentication config"
cat > "$AUTH_CONFIG_PATH" << 'EOF'
[mlflow]
default_permission = READ
database_uri = sqlite:///basic_auth.db
admin_username = admin
admin_password = admin123
authorization_function = mlflow.server.auth:authenticate_request_basic_auth
EOF
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

export MLFLOW_AUTH_CONFIG_PATH="$AUTH_CONFIG_PATH"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Static Prefix: $STATIC_PREFIX"
echo "Backend Store: sqlite:///$MLFLOW_HOME/mlflow.db"
echo "Artifact Root: $MLFLOW_HOME/mlartifacts"
echo "Auth Config: $AUTH_CONFIG_PATH"
echo "Default credentials: admin / admin123"
echo "Launching MLflow server with authentication"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts" \
    --static-prefix "$STATIC_PREFIX" \
    --app-name basic-auth
```

---

## Solution 3 : Script robuste avec fallback (si `--static-prefix` ne fonctionne pas)

```bash
#!/usr/bin/env bash

echo "[Exporting variables ...]"
export MLFLOW_PORT=8888

# Répertoire de travail persistant
MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

# Calcul du root path pour le proxy Domino
STATIC_PREFIX="/$DOMINO_PROJECT_OWNER/$DOMINO_PROJECT_NAME/r/notebookSession/$DOMINO_RUN_ID"

# Variables d'environnement alternatives pour le root path
export SCRIPT_NAME="$STATIC_PREFIX"
export MLFLOW_STATIC_PREFIX="$STATIC_PREFIX"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Installing MLflow >= 3.1"
pip install "mlflow>=3.1"
echo "Installation finished"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

# Afficher les options disponibles pour diagnostic
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "MLflow version:"
mlflow --version
echo ""
echo "Available server options:"
mlflow server --help | grep -E "(static-prefix|root-path|base-url)" || echo "Checking options..."
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
    --static-prefix "$STATIC_PREFIX"
```

---

## Recommandation

Commencez par la **Solution 1** (sans auth) pour valider que ça fonctionne, puis passez à la **Solution 2** pour la production.

Si vous avez une page blanche comme avec Phoenix, essayez d'ajouter ces variables d'environnement :

```bash
export SCRIPT_NAME="$STATIC_PREFIX"
export MLFLOW_STATIC_PREFIX="$STATIC_PREFIX"
```

Tenez-moi au courant du résultat ! 🚀
