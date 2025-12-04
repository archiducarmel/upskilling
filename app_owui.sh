#!/bin/bash

# ===========================================
# Open WebUI - Domino Data Lab App Publishing
# ===========================================

# Installation de open-webui
pip install open-webui --break-system-packages

# --- Configuration des variables d'environnement ---

# Répertoire de données persistant (utilise le stockage Domino)
export DATA_DIR="${DOMINO_WORKING_DIR}/open-webui-data"
mkdir -p "$DATA_DIR"

# Clé secrète pour les sessions (obligatoire si auth activée)
# Génère une clé aléatoire si non définie
export WEBUI_SECRET_KEY="${WEBUI_SECRET_KEY:-$(openssl rand -hex 32)}"

# Désactiver l'authentification pour un accès simplifié (optionnel)
# Mettre "True" pour activer l'authentification
export WEBUI_AUTH="${WEBUI_AUTH:-False}"

# --- Configuration des backends LLM ---

# Option 1: Ollama (si vous avez un serveur Ollama)
# export OLLAMA_BASE_URL="http://your-ollama-server:11434"

# Option 2: OpenAI API (décommenter et configurer)
# export OPENAI_API_KEY="your-openai-api-key"
# export OPENAI_API_BASE_URL="https://api.openai.com/v1"

# Option 3: Azure OpenAI (décommenter et configurer)
# export OPENAI_API_KEY="your-azure-api-key"
# export OPENAI_API_BASE_URL="https://your-resource.openai.azure.com/openai/deployments/your-deployment"

# Option 4: Anthropic Claude (via OpenAI-compatible endpoint)
# export OPENAI_API_KEY="your-anthropic-api-key"
# export OPENAI_API_BASE_URL="https://api.anthropic.com/v1"

# Option 5: Autres providers compatibles OpenAI (Groq, Together, etc.)
# export OPENAI_API_KEY="your-api-key"
# export OPENAI_API_BASE_URL="https://api.groq.com/openai/v1"

# --- Paramètres additionnels ---

# Activer le mode debug (optionnel)
export ENV="${ENV:-prod}"

# Désactiver la télémétrie (optionnel)
export SCARF_NO_ANALYTICS="true"
export DO_NOT_TRACK="true"

# Taille max des uploads (en bytes, défaut: 100MB)
export MAX_UPLOAD_SIZE="${MAX_UPLOAD_SIZE:-104857600}"

# --- Lancement de Open WebUI ---
# Note: Pour pip install, on utilise --port et non la variable PORT
# Domino expose généralement sur le port 8888

echo "=========================================="
echo "Starting Open WebUI on port 8888..."
echo "Data directory: $DATA_DIR"
echo "Authentication: $WEBUI_AUTH"
echo "=========================================="

open-webui serve --host 0.0.0.0 --port 8888
