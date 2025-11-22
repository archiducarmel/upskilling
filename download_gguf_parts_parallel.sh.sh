#!/usr/bin/env bash
# Télécharge des fichiers .partXXX avec curl en parallèle (max 5 jobs)
# puis reconstitue le fichier final avec cat.
#
# Usage :
#   bash download_gguf_parts_parallel.sh BASE_URL START_INDEX END_INDEX
#
# Exemple :
#   bash download_gguf_parts_parallel.sh \
#     "https://github.com/archiducarmel/upskilling/releases/download/data/Qwen3-8B-Q8_0.gguf.part" \
#     1 16

set -euo pipefail

### --- 1. Lecture et contrôle des arguments ---------------------------------

if [ "$#" -ne 3 ]; then
  echo "Usage : $0 BASE_URL START_INDEX END_INDEX" >&2
  echo "Exemple :" >&2
  echo "  $0 \"https://.../Qwen3-8B-Q8_0.gguf.part\" 1 16" >&2
  exit 1
fi

BASE_URL="$1"      # URL SANS le numéro de part, mais AVEC '.part'
START_INDEX="$2"   # ex : 1
END_INDEX="$3"     # ex : 16

# Nombre de chiffres du padding : part001 → 3
PAD_WIDTH=3

# Max de téléchargements en parallèle
MAX_JOBS=5

### --- 2. Déduction du nom racine & création du dossier ----------------------

# Exemple : Qwen3-8B-Q8_0.gguf.part → Qwen3-8B-Q8_0.gguf
FILE_WITH_PART="$(basename "$BASE_URL")"
ROOT_NAME="${FILE_WITH_PART%.part}"

OUT_DIR="$ROOT_NAME"

echo "Nom racine du fichier : $ROOT_NAME"
echo "Dossier de destination : $OUT_DIR"
echo "Téléchargements parallèles : max ${MAX_JOBS} en même temps"
echo

mkdir -p "$OUT_DIR"

### --- 3. Téléchargement des parts en parallèle (pool limité) ----------------

# Boucle numérique en bash, évite la dépendance à `seq`
for ((i=START_INDEX; i<=END_INDEX; i++)); do
  INDEX_PADDED="$(printf "%0${PAD_WIDTH}d" "$i")"     # 1 → 001, 2 → 002...
  PART_URL="${BASE_URL}${INDEX_PADDED}"
  PART_FILE="${OUT_DIR}/${ROOT_NAME}.part${INDEX_PADDED}"

  echo ">>> Préparation du téléchargement : $PART_URL"
  echo "    → $PART_FILE"

  # Si déjà présent : on ne relance pas le téléchargement
  if [ -f "$PART_FILE" ]; then
    echo "    [SKIP] $PART_FILE existe déjà."
    echo
    continue
  fi

  # 🔒 Limiter le nombre de téléchargements en parallèle
  # Tant qu'il y a déjà MAX_JOBS jobs en cours, on attend.
  while :; do
    # `jobs -p` renvoie les PID des jobs en arrière-plan lancés par ce script
    running_jobs=$(jobs -p | wc -l | tr -d ' ')
    if [ "$running_jobs" -lt "$MAX_JOBS" ]; then
      break
    fi
    sleep 1
  done

  echo "    [DL] Lancement en arrière-plan..."
  # Téléchargement en tâche de fond
  (
    # Sous-shell pour ne pas polluer le shell principal
    if ! curl -fL --retry 3 -o "$PART_FILE" "$PART_URL"; then
      echo "    [ERREUR] Échec du téléchargement de $PART_URL" >&2
      exit 1
    fi
  ) &

  echo
done

# On attend la fin de TOUS les téléchargements
wait

echo
echo "✔ Tous les téléchargements sont terminés."

### --- 4. Reconstitution du fichier final avec cat ---------------------------

FINAL_FILE="${OUT_DIR}/${ROOT_NAME}"

echo ">>> Assemblage des parts dans : $FINAL_FILE"

cat "${OUT_DIR}/${ROOT_NAME}.part"* > "$FINAL_FILE"

echo "✔ Fichier final reconstruit : $FINAL_FILE"
echo "Tu peux maintenant l'utiliser (par ex. avec ollama / llama.cpp, etc.)."

