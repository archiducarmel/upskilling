Le problème de "could not load experiments" est souvent lié au **root path** du proxy. Le frontend MLflow fait des appels API vers `/api/2.0/mlflow/...` mais le proxy Domino s'attend à `/{owner}/{project}/r/notebookSession/{run_id}/api/2.0/mlflow/...`.

Vérifions ce qui se passe. Pouvez-vous me donner :

1. **Les logs du serveur MLflow** - Est-ce que vous voyez des requêtes API arriver ?

2. **L'erreur exacte dans la console du navigateur** (F12 → Console et Network) - Quel est le statut HTTP des appels vers `/api/2.0/mlflow/experiments/search` ?

En attendant, essayez cette version avec `--static-prefix` :

```bash
#!/usr/bin/env bash

MLFLOW_HOME="${HOME}/.mlflow"
mkdir -p "$MLFLOW_HOME/mlartifacts"

# Construire le root path Domino
ROOT_PATH="/${DOMINO_PROJECT_OWNER}/${DOMINO_PROJECT_NAME}/r/notebookSession/${DOMINO_RUN_ID}"

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "ROOT_PATH: $ROOT_PATH"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

pip install "mlflow>=3.5"

python << 'EOF'
import mlflow
import os
mlflow_home = os.path.expanduser("~/.mlflow")
mlflow.set_tracking_uri(f"sqlite:///{mlflow_home}/mlflow.db")
try:
    mlflow.create_experiment("Default")
except:
    pass
print("Database ready!")
EOF

echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'
echo "Launching MLflow"
echo '¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤'

mlflow server \
    --host 0.0.0.0 \
    --port 8888 \
    --backend-store-uri "sqlite:///$MLFLOW_HOME/mlflow.db" \
    --default-artifact-root "$MLFLOW_HOME/mlartifacts" \
    --static-prefix "$ROOT_PATH" \
    --disable-security-middleware
```

Si ça ne marche toujours pas, montrez-moi les logs serveur et les erreurs navigateur.
