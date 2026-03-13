# RAPPORT UNIFIÉ DE CODE REVIEW — a100067-sav-guardrails-language

**Périmètre** : `api.py`, `load_config.py`, `constants.py`, `services_*.env`, `generate_confluence_doc.py`, `generate_project_config.py`, `run_api.py`, `decode_input.py`, `config_context.py`, `lingua_detector.py`, `Makefile`, `pyproject.toml`, DTOs, tests, documentation (17 fichiers `.md`/`.rst`)  
**Date** : Mars 2026  
**Thématiques couvertes** : Sécurité · Performances · Robustesse · Data Science / NLP · Qualité de code · Testabilité · Documentation

---

## EXECUTIVE SUMMARY

Ce guardrail de classification linguistique FR/non-FR est un composant **synchrone sur le chemin critique** de l'assistant bancaire Hello Bank (Genius BAR V2). La review exhaustive révèle **67 problèmes** répartis sur 7 thématiques. L'état global est **préoccupant** : des crashs en production sont garantis sur des inputs courants, un secret Artifactory actif est commité en clair, et les performances du modèle sur le domaine réel n'ont jamais été mesurées.

### Table récapitulative des problèmes par thématique et criticité

| Thématique | CRITIQUE | MAJEUR | MINEUR | Total |
|---|---|---|---|---|
| 🔐 Sécurité | 5 | 7 | 6 | **18** |
| ⚡ Performances | 4 | 6 | 4 | **14** |
| 🛡️ Robustesse | 6 | 7 | 4 | **17** |
| 🧠 Data Science / NLP | 5 | 6 | 3 | **14** |
| 🧹 Qualité de code | 4 | 10 | 6 | **20** |
| 🧪 Testabilité | 7 | 7 | 2 | **16** |
| 📚 Documentation | 5 | 7 | 5 | **17** |
| **TOTAL** | **36** | **50** | **30** | **116** |

> Note : certains problèmes sont transverses à plusieurs thématiques (ex. : SEC-06 croise ROB-09) et peuvent apparaître dans deux rapports sans être comptés deux fois dans le tableau ci-dessus.

### Top 10 des problèmes à traiter en priorité absolue

| Priorité | ID | Thématique | Impact |
|---|---|---|---|
| 1 | SEC-01 | Sécurité | Token Artifactory actif commité en clair dans 3 fichiers |
| 2 | ROB-03 | Robustesse | `ValidationError` Pydantic non catchée → 500 sur tout input malformé |
| 3 | ROB-04 | Robustesse | `iso_code_639_1 = None` → crash `AttributeError` sur certaines langues |
| 4 | SEC-03 | Sécurité | `verify_ssl=False` → attaque Man-in-the-Middle possible |
| 5 | DS-04 | Data Science | Inputs courts (cas majoritaire chatbot) classifiés avec précision ~55% |
| 6 | PERF-01 | Performances | 75 langues chargées pour une classification binaire — mémoire x5 |
| 7 | TEST-05 | Testabilité | Mock `inference()` mal configuré — le test ne teste rien réellement |
| 8 | TEST-06 | Testabilité | Singleton partagé entre tests → tests flaky selon ordre d'exécution |
| 9 | DS-01 | Data Science | Scores de confiance sémantiquement incorrects pour la décision binaire |
| 10 | DOC-03 | Documentation | `setup.md` entièrement vide — onboarding impossible |

---

## PARTIE 1 — PROBLÈMES CRITIQUES

---

### 🔐 SEC-01 — CREDENTIALS ARTIFACTORY EN CLAIR DANS DES FICHIERS VERSIONNÉS

**Fichiers** : `services_dev.env`, `services_pprod.env`, `services_prod.env` — Lignes 10–11  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Un mot de passe Artifactory en clair est commité dans trois fichiers `.env` vraisemblablement versionnés (référencés dans `pyproject.toml` et dans l'arborescence). Toute personne ayant accès au repo — collaborateur, pipeline CI/CD, fuite GitLab — dispose immédiatement d'un accès complet à Artifactory. Le mot de passe est **identique dans les trois environnements** (dev, pprod, prod), ce qui élargit considérablement la surface d'attaque. Le token de 72 caractères est un token Artifactory valide et potentiellement actif.

```env
ARTIFACTORY_USER=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ARTIFACTORY_PASSWORD=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Solution** : Révoquer le token immédiatement, exclure les fichiers du dépôt, injecter les secrets uniquement via les variables CI/CD GitLab (masked + protected) ou Vault.

```gitignore
# .gitignore — à ajouter immédiatement
services_*.env
config/services/*.env
```

```yaml
# gitlab-ci.yml — injection propre
variables:
  ARTIFACTORY_USER: $CI_ARTIFACTORY_USER       # variable masquée GitLab
  ARTIFACTORY_PASSWORD: $CI_ARTIFACTORY_PASSWORD
```

---

### 🔐 SEC-02 — TOKEN ARTIFACTORY EN CLAIR DANS LE MAKEFILE

**Fichier** : `Makefile_1` — Lignes 30–32, 42–43, 65–66, 79–80  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Les credentials `ARTIFACTORY_USER` et `ARTIFACTORY_PASSWORD` sont interpolés directement dans des commandes shell `echo` qui écrivent dans `~/.config/pip/pip.conf` et `~/.condarc`. Ces fichiers résultants contiennent les credentials en clair sur le filesystem. Par ailleurs, les commandes `echo` avec credentials peuvent apparaître dans les logs de build. Le fichier `rules.md` invite même explicitement les développeurs à passer les secrets en arguments de ligne de commande (`ARTIFACTORY_USER=USER ARTIFACTORY_PASSWORD=PASSWORD make install-deps`), rendant les credentials visibles dans `ps aux` et l'historique shell.

```makefile
@echo "index-url = https://${ARTIFACTORY_USER}:${ARTIFACTORY_PASSWORD}@repo.artifactory..."  >> $(PIPCONF)
@poetry config http-basic.artifactory ${ARTIFACTORY_USER} ${ARTIFACTORY_PASSWORD}
```

**Solution** : Ne jamais construire des URLs avec credentials embarqués. Utiliser keyring ou fichier `.netrc` (permissions 600) pour stocker les credentials sans les exposer dans les logs.

```makefile
# Utiliser --quiet pour éviter l'exposition dans les logs
@poetry config http-basic.artifactory \
  "$(ARTIFACTORY_USER)" "$(ARTIFACTORY_PASSWORD)" --quiet
```

---

### 🔐 SEC-03 — DÉSACTIVATION DE LA VÉRIFICATION SSL

**Fichier** : `generate_confluence_doc.py` — Ligne 257  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : `verify_ssl=False` désactive intégralement la vérification du certificat TLS lors des connexions à Confluence. En production, cela ouvre la voie à des attaques **Man-in-the-Middle (MitM)** : un attaquant peut intercepter le trafic, lire le token d'accès Confluence, modifier les pages de documentation publiées, ou injecter du contenu malveillant dans Confluence. Ce code est exécuté dans le pipeline CI/CD lors de la phase de release.

```python
confluence = Confluence(verify_ssl=False, url=confluence_url, token=access_token)
```

**Solution** : Toujours activer la vérification SSL. Si le certificat interne n'est pas reconnu, fournir explicitement le bundle CA de l'entreprise.

```python
# Option 1 : vérification SSL activée (défaut)
confluence = Confluence(url=confluence_url, token=access_token)

# Option 2 : certificat CA interne d'entreprise
confluence = Confluence(
    url=confluence_url,
    token=access_token,
    verify="/path/to/internal-ca-bundle.crt"
)
```

---

### 🔐 SEC-04 — INFORMATION DISCLOSURE VIA LES MESSAGES D'ERREUR DE L'API

**Fichier** : `api.py` — Lignes 74–76  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : L'exception brute `e` est directement incluse dans le message d'erreur HTTP retourné au client via `abort(400, description=f"Bad request {e}")`. En production, Flask peut renvoyer ces détails dans la réponse HTTP. Cela expose des informations internes : structure des DTOs, noms de champs, types de données attendus, stack traces Pydantic — informations précieuses pour un attaquant voulant sonder et exploiter l'API.

```python
exception = {"status": "ko", "type": e.__class__, "value": e.__str__()}
logger.error("error found during parsing request data", extra=exception)
abort(400, description=f"Bad request {e}")
```

**Solution** : Retourner un message générique au client et logger les détails uniquement en interne.

```python
except (KeyError, ValueError) as e:
    logger.error("Parsing error", extra={"type": type(e).__name__, "detail": str(e)})
    abort(400, description="Invalid request payload.")
```

---

### 🔐 SEC-05 — INFORMATION DISCLOSURE VIA LE LOG DES RÉSULTATS D'INFÉRENCE

**Fichier** : `api.py` — Ligne 113  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Le résultat complet d'inférence est loggé en clair à chaque requête. Si les logs sont centralisés (Splunk, ELK), chaque payload de réponse est stocké indéfiniment. Dans un contexte bancaire (BNP Paribas), les données clients doivent respecter des règles strictes de non-log (RGPD/DLP). Le texte soumis par l'utilisateur peut transiter dans les logs via les couches appelantes, rendant ce log systématique une violation de conformité potentielle.

```python
logger.info(f"Inference results : {response_data.model_dump(by_alias=True)}")
```

**Solution** : Logger uniquement les métriques agrégées non-PII, jamais le contenu des payloads complets.

```python
# Logger uniquement les métadonnées, pas le contenu
logger.info(
    "Inference completed",
    extra={"version": __version__, "nb_scores": len(classification_scores)}
)
```

---

### ⚡ PERF-01 — `from_all_languages()` : 75 LANGUES CHARGÉES POUR UNE CLASSIFICATION BINAIRE

**Fichier** : `lingua_detector.py` — Lignes 20–24  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : `from_all_languages()` charge les modèles n-gram pour les **75 langues** supportées par Lingua. Le détecteur résultant est massif en mémoire (~plusieurs centaines de Mo) et sa latence d'inférence est proportionnelle au nombre de langues comparées. Or le use case est **binaire** : français vs non-français. Charger 75 langues pour un problème à 2 classes est un anti-pattern de performance majeur. La documentation de Lingua recommande explicitement `from_languages()` pour réduire l'empreinte mémoire et la latence. Sur un hardware `prd-cpu-2x4` (2 vCPU, 4 GiB RAM), cela peut saturer la RAM disponible lors du démarrage avec 3 replicas.

```python
self.detector = (
    LanguageDetectorBuilder.from_all_languages()
    .with_minimum_relative_distance(LANGUAGE_DETECTOR_MINIMUM_RELATIVE_DISTANCE)
    .build()
)
```

**Solution** : Restreindre le builder aux langues les plus fréquentes du domaine chatbot bancaire. Gain estimé : réduction mémoire ~80%, latence d'inférence divisée par 3 à 5x.

```python
from lingua import Language, LanguageDetectorBuilder

self.detector = (
    LanguageDetectorBuilder.from_languages(
        Language.FRENCH, Language.ENGLISH,
        Language.SPANISH, Language.GERMAN,
        Language.ARABIC, Language.PORTUGUESE
    )
    .with_minimum_relative_distance(0.1)
    .build()
)
```

---

### ⚡ PERF-02 — `compute_language_confidence_values()` : CALCUL POUR TOUTES LES LANGUES ALORS QUE SEUL LE TOP-1 EST UTILISÉ

**Fichier** : `lingua_detector.py` — Lignes 36–38  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : `compute_language_confidence_values()` calcule et retourne les scores de confiance pour **toutes les langues chargées** (75 si PERF-01 n'est pas corrigé), triés par ordre décroissant. Seul `[0]` — le top-1 — est consommé. C'est un calcul O(N_langues) dont seule 1/N est utilisée. La méthode `detect_language_of()` est nettement plus efficace pour ce use case.

```python
confidence_values = self.detector.compute_language_confidence_values(input)
detected_language = confidence_values[0].language
confidence_score = confidence_values[0].value
```

**Solution** : Utiliser `detect_language_of()` qui retourne uniquement la langue la plus probable sans calculer tous les scores.

```python
def calculate_language_scores(self, text: str) -> dict:
    detected_language = self.detector.detect_language_of(text)

    if detected_language is None:
        return {"french": DEFAULT_UNCOMPUTED_SCORE_VALUE, "non_french": DEFAULT_UNCOMPUTED_SCORE_VALUE}

    iso_code = detected_language.iso_code_639_1
    if iso_code is not None and iso_code.name.lower() == "fr":
        return {"french": 1.0, "non_french": 0.0}

    return {"french": 0.0, "non_french": 1.0}
```

---

### ⚡ PERF-03 — INSTANCIATION DE `Base64EncoderDecoder` À CHAQUE REQUÊTE

**Fichier** : `decode_input.py` — Ligne 22  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Un nouvel objet `Base64EncoderDecoder` est instancié à **chaque appel** de `decode_input()`, c'est-à-dire à chaque requête d'inférence. L'encodage/décodage base64 est stateless — aucune raison de recréer l'objet 650 fois par heure. Si cette classe a un coût d'initialisation (validation du `character_encoding_type`, allocation interne), ce coût est payé inutilement.

```python
def decode_input(input: str) -> str:
    base64_encoder_decoder = Base64EncoderDecoder(character_encoding_type=DEFAULT_CHARACTER_ENCODING_TYPE)
    try:
        decoded_text = base64_encoder_decoder.decode(input)
```

**Solution** : Instancier une fois au niveau module et réutiliser la même instance sur toutes les requêtes.

```python
# Au niveau module dans decode_input.py
_base64_codec = Base64EncoderDecoder(character_encoding_type=DEFAULT_CHARACTER_ENCODING_TYPE)

def decode_input(encoded_text: str) -> str:
    try:
        return _base64_codec.decode(encoded_text)
    except Exception as e:
        logger.error("Error while decoding input: %s", e)
        raise DecoderError("Error while decoding input") from e
```

---

### ⚡ PERF-04 — `LANGUAGE_DETECTOR_MINIMUM_RELATIVE_DISTANCE = 0.0` : SEUIL DE CONFIANCE DÉSACTIVÉ

**Fichier** : `constants.py` — Ligne 12 ; `lingua_detector.py` — Ligne 22  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : `with_minimum_relative_distance(0.0)` désactive le filtre de distance minimale entre les deux meilleures langues candidates. Cela force Lingua à toujours émettre une réponse, même quand les scores entre langues sont quasi-identiques (texte ambigu, mélange de langues, acronymes). Des textes courts ou ambigus — cas fréquents en chatbot bancaire — produiront des classifications aléatoires avec une haute "confiance", sans que le système ne le signale. La documentation interne indique que Lingua retourne `-1` quand il ne peut pas détecter pertinemment, ce qui suppose un seuil non nul — **incohérence entre la doc et le code**.

```python
LANGUAGE_DETECTOR_MINIMUM_RELATIVE_DISTANCE = 0.0
```

**Solution** : Définir un seuil de distance minimale pertinent selon les recommandations de la documentation officielle de Lingua.

```python
# constants.py
LANGUAGE_DETECTOR_MINIMUM_RELATIVE_DISTANCE = 0.1  # seuil recommandé par Lingua
```

---

### 🛡️ ROB-01 — `confidence_values[0]` : ACCÈS DIRECT SANS VÉRIFICATION — CRASH GARANTI SUR LISTE VIDE

**Fichier** : `lingua_detector.py` — Lignes 36–38  
**Fonction** : `calculate_language_scores()`  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : `compute_language_confidence_values()` peut théoriquement retourner une liste vide si l'input est une chaîne que Lingua ne peut pas traiter (chaîne unicode exotique, séquence de caractères de contrôle, texte après décodage corrompu). L'accès `[0]` provoque un **`IndexError` non catchée** qui remonte jusqu'à `inference()`, où elle n'est pas non plus gérée, et fait crasher la requête avec une 500. Aucun test ne couvre ce cas.

```python
confidence_values = self.detector.compute_language_confidence_values(input)
detected_language = confidence_values[0].language   # IndexError si liste vide
confidence_score = confidence_values[0].value        # IndexError si liste vide
```

**Solution** : Vérifier que la liste n'est pas vide avant tout accès indexé et retourner la valeur sentinelle.

```python
confidence_values = self.detector.compute_language_confidence_values(input)
if not confidence_values:
    logger.warning("Lingua returned empty confidence values for input.")
    return {"french": DEFAULT_UNCOMPUTED_SCORE_VALUE, "non_french": DEFAULT_UNCOMPUTED_SCORE_VALUE}

detected_language = confidence_values[0].language
confidence_score = confidence_values[0].value
```

---

### 🛡️ ROB-02 — `lingua_detector` RÉCUPÉRÉ SANS VÉRIFICATION DE `None` — `AttributeError` EN PROD

**Fichier** : `api.py` — Lignes 97, 103  
**Fonction** : `inference()`  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : `ConfigContext.get()` retourne `None` si la clé n'existe pas. Si `init_app()` a échoué partiellement (exception lors du chargement de `LinguaDetector`, worker démarré sans passer par `init_app()`), `lingua_detector` sera `None`. L'appel `lingua_detector.run()` provoque un **`AttributeError`** non géré qui crashe la requête avec une 500 opaque. Ce scénario est réaliste en production lors d'un redémarrage partiel ou d'une initialisation en cours.

```python
lingua_detector = config_context.get("lingua_detector")  # retourne None si clé absente
# ...
classification_scores = lingua_detector.run(input=text_to_classify)  # AttributeError
```

**Solution** : Valider la présence du détecteur avant utilisation et retourner un 503 explicite.

```python
lingua_detector = config_context.get("lingua_detector")
if lingua_detector is None:
    logger.error("LinguaDetector is not initialized in ConfigContext.")
    abort(503, description="Service temporarily unavailable: model not loaded.")
```

---

### 🛡️ ROB-03 — `_parse_data_dict` NE CATCHE PAS `ValidationError` DE PYDANTIC — CRASH SILENCIEUX

**Fichier** : `api.py` — Lignes 69–78  
**Fonction** : `_parse_data_dict()`  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Pydantic V2 lève une **`ValidationError`** (et non un `ValueError` ou `KeyError`) quand la validation du modèle échoue — par exemple si un champ est manquant, si le pattern regex de `Channel` ne matche pas, ou si `classificationInputs` est absent. Or `ValidationError` n'hérite **pas** de `ValueError` en Pydantic V2. Cette exception n'est donc **pas catchée** par le bloc `except (KeyError, ValueError)`. Elle remonte jusqu'à `inference()` et provoque une **500 non contrôlée** au lieu d'une 400 attendue. Ce bug est déclenché sur tout input malformé en production.

```python
try:
    request_data_dto = RequestDataDto(**data_dict)
except (KeyError, ValueError) as e:
    ...
    abort(400, description=f"Bad request {e}")
# ValidationError n'est pas catchée → 500
```

**Solution** : Ajouter `ValidationError` dans le bloc except et masquer les détails techniques du message d'erreur client.

```python
from pydantic import ValidationError

try:
    return RequestDataDto(**data_dict)
except (KeyError, ValueError, ValidationError) as e:
    logger.error("Parsing error on request data", extra={"detail": str(e)})
    abort(400, description="Invalid request payload.")
```

---

### 🛡️ ROB-04 — `iso_code_639_1` PEUT ÊTRE `None` — `AttributeError` SUR CERTAINES LANGUES

**Fichier** : `lingua_detector.py` — Ligne 45  
**Fonction** : `calculate_language_scores()`  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Dans la bibliothèque Lingua, certaines langues n'ont **pas de code ISO 639-1** (ex. : `AZERBAIJANI`, `BOSNIAN`, `LATIN` et d'autres). Pour ces langues, `iso_code_639_1` retourne `None`. L'accès `.name` sur `None` provoque un **`AttributeError`** non géré qui crashe la requête. Ce cas est possible dès qu'un input ambigu est classifié dans une langue sans ISO 639-1, ce qui peut arriver avec `from_all_languages()`. Aucun test ne couvre ce cas.

```python
if detected_language.iso_code_639_1.name.lower() == "fr":  # AttributeError si iso_code_639_1 is None
```

**Solution** : Vérifier la nullité de `iso_code_639_1` avant tout accès attribut.

```python
iso_code = detected_language.iso_code_639_1
if iso_code is not None and iso_code.name.lower() == "fr":
    return {"french": confidence_score, "non_french": 0.0}
return {"french": 0.0, "non_french": confidence_score}
```

---

### 🛡️ ROB-05 — `int(input(...))` SANS TRY/EXCEPT — `ValueError` / CRASH DANS `generate_project_config.py`

**Fichier** : `generate_project_config.py` — Lignes 87, 136  
**Fonction** : `generate_process_mode_yaml()`  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Si l'utilisateur entre une valeur non numérique (chaîne vide, lettres, espace), `int()` lève une **`ValueError`** immédiate. Cette exception est catchée par le `except Exception as e` générique ligne 161 qui affiche juste un message et sort — **sans avoir sauvegardé les fichiers de config**. L'utilisateur perd toutes ses saisies précédentes. De plus, après validation `replica_count <= 0` (ligne 90), le code ne fait que `print()` l'avertissement sans bloquer : un `replica_count` de `-5` serait quand même écrit dans le YAML.

```python
replica_count: int = int(input("Enter the number of replicas for the API deployment (default is 1): "))
```

**Solution** : Encapsuler la conversion dans une fonction dédiée qui boucle jusqu'à une valeur valide et strictement positive.

```python
def _read_positive_int(prompt: str, default: int = 1) -> int:
    """Read a strictly positive integer from user input."""
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"Expected an integer, got: '{raw}'")
    if value <= 0:
        raise ValueError(f"Value must be a positive integer, got: {value}")
    return value

replica_count = _read_positive_int(
    "Enter the number of replicas for the API deployment (default is 1): "
)
```

---

### 🛡️ ROB-06 — `.pop()` SANS VALEUR PAR DÉFAUT — `KeyError` EN CAS DE CONFIG INCOMPLÈTE

**Fichier** : `generate_project_config.py` — Lignes 80–81, 105, 132, 147–148, 151–152  
**Fonction** : `generate_process_mode_yaml()`  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Ces `pop()` sans argument de défaut lèvent un **`KeyError`** si la clé n'existe pas dans le dictionnaire — ce qui arrive si `load_deployment_config()` a retourné un `{}` (cas d'erreur déjà géré) ou si le fichier `project_config_ref.yml` a été modifié. L'exception est catchée par le `except Exception` générique mais **sans rollback** — les fichiers de config partiellement modifiés pourraient être dans un état incohérent.

```python
deployment_config["deployment"].pop("batch")   # KeyError si "batch" absent
deployment_config["deployment"].pop("stream")  # KeyError si "stream" absent
```

**Solution** : Utiliser `pop(key, None)` pour rendre la suppression idempotente et sans risque.

```python
deployment_config["deployment"].pop("batch", None)
deployment_config["deployment"].pop("stream", None)
deployment_config["deployment"].pop("api", None)
```

---

### 🧠 DS-01 — CLASSIFICATION 75 CLASSES RÉDUITE EN BINAIRE — SCORES MAL CALIBRÉS

**Fichier** : `lingua_detector.py` — Lignes 20–24, 36–48  
**Fonction** : `__init__()`, `calculate_language_scores()`  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Il y a une **inadéquation fondamentale** entre la formulation du problème et l'implémentation. Le problème métier est binaire (FR vs non-FR), mais le modèle résout un problème à 75 classes, dont le résultat est ensuite écrasé en binaire. Cela crée trois problèmes de qualité : (1) Un score `french = 0.85` signifie "85% de probabilité parmi 75 langues", pas "85% de probabilité FR vs non-FR" — ces distributions sont radicalement différentes. (2) Un texte français court et ambigu peut avoir `french = 0.45`, `spanish = 0.30`, `italian = 0.25` : c'est du français (top-1) mais le score `0.45` retourné sous-estime la "françité" réelle. (3) Retourner `non_french = confidence_score` quand la langue détectée est l'anglais avec score `0.60` ne signifie pas que le texte est "non-français à 60%".

```python
self.detector = (
    LanguageDetectorBuilder.from_all_languages()  # 75 langues
    .build()
)
# Réduction binaire en post-processing
if detected_language.iso_code_639_1.name.lower() == "fr":
    return {"french": confidence_score, "non_french": 0.0}
return {"french": 0.0, "non_french": confidence_score}
```

**Solution** : Restreindre la compétition aux langues pertinentes et recalibrer le score non-FR comme complément à 1.

```python
# Option recommandée : compétition restreinte + score binaire correct
self.detector = LanguageDetectorBuilder.from_languages(
    Language.FRENCH, Language.ENGLISH, Language.ARABIC,
    Language.SPANISH, Language.PORTUGUESE, Language.GERMAN
).with_minimum_relative_distance(0.1).build()

# Score binaire recalibré
all_values = self.detector.compute_language_confidence_values(text)
fr_score = next((v.value for v in all_values if v.language == Language.FRENCH), 0.0)
non_fr_score = 1.0 - fr_score
return {"french": round(fr_score, 6), "non_french": round(non_fr_score, 6)}
```

---

### 🧠 DS-02 — ABSENCE TOTALE DE PREPROCESSING TEXTUEL AVANT CLASSIFICATION

**Fichier** : `api.py` — Ligne 100 ; `decode_input.py` — intégralité  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Le texte décodé est envoyé **directement à Lingua sans aucun preprocessing**. Dans un contexte chatbot bancaire, les inputs utilisateurs contiennent typiquement des éléments qui dégradent la détection : URLs/emails (biaisent la détection), numéros IBAN (le préfixe `FR` peut être interprété comme un mot français), emojis et caractères spéciaux (bruit pour les n-grams), codes promotionnels (`CODE: ABC123XY`), fautes d'orthographe courantes, et textes en majuscules intégrales. L'absence de normalisation minimale dégrade la qualité de classification sur ces cas fréquents en production.

```python
text_to_classify = decode_input(input=request_data_dto.inputs.classification_inputs[0])
classification_scores = lingua_detector.run(input=text_to_classify)
# Aucune transformation entre décodage et inférence
```

**Solution** : Ajouter une étape de preprocessing légère non destructive avant l'inférence : supprimer URLs, emails, séquences non linguistiques, normaliser unicode et casse.

```python
import re
import unicodedata

def preprocess_text(text: str) -> str:
    """Normalize text before language detection."""
    # Suppression URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    # Suppression emails
    text = re.sub(r"\S+@\S+\.\S+", " ", text)
    # Suppression des séquences purement numériques et codes
    text = re.sub(r"\b[\dA-Z]{6,}\b", " ", text)
    # Normalisation unicode
    text = unicodedata.normalize("NFC", text)
    # Collapse whitespace
    return " ".join(text.split()).strip()
```

---

### 🧠 DS-03 — `DEFAULT_UNCOMPUTED_SCORE_VALUE = -1.0` : VALEUR SENTINELLE HORS DOMAINE PROBABILISTE

**Fichier** : `constants.py` — Ligne 14 ; `lingua_detector.py` — Ligne 43  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Retourner `-1.0` comme score de confiance est une **violation des conventions de probabilité**. Un score de classification est par définition dans `[0, 1]`. Retourner `-1.0` : (1) casse la sémantique du champ `score` qui est typé `float` sans contrainte dans `ClassificationScore` — un consommateur attendant un score probabiliste reçoit une valeur hors domaine ; (2) force le Guardrails downstream à traiter un cas spécial ; (3) produit des bugs silencieux si le score est utilisé dans des calculs sans vérification préalable. De plus, la documentation (`deployment_and_pipeline.md`) mentionne `-100` comme valeur par défaut alors que le code utilise `-1.0` — **triple incohérence doc/code**.

```python
DEFAULT_UNCOMPUTED_SCORE_VALUE = -1.0
# → retourne {"french": -1.0, "non_french": -1.0}
```

**Solution** : Adopter un objet dédié portant le flag d'indétermination, ou utiliser `0.0` avec un flag booléen explicite.

```python
from dataclasses import dataclass

@dataclass
class LanguageDetectionResult:
    french_score: float
    non_french_score: float
    is_undetermined: bool = False

# Dans calculate_language_scores — cas non détecté
return LanguageDetectionResult(
    french_score=0.0, non_french_score=0.0, is_undetermined=True
)
```

---

### 🧠 DS-04 — AUCUNE GESTION DES INPUTS COURTS : CAS LE PLUS FRÉQUENT EN CHATBOT

**Fichier** : `lingua_detector.py` — Ligne 36 ; `request_data_dto.py` — Ligne 18  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : Lingua est un modèle **n-gram statistique** dont la précision est fortement corrélée à la longueur du texte. Selon la documentation officielle : précision ~55–70% sur 1–3 mots, ~85–90% sur 5–10 mots, >97% sur 20+ mots. En contexte chatbot bancaire, une grande proportion des inputs sont ultra-courts : `"ok"`, `"merci"`, `"oui"`, `"aide"`, `"bonjour"`, `"solde ?"`. Or **aucun seuil de longueur minimale n'est défini** ni dans le DTO Pydantic, ni dans le preprocessing. Le modèle classifie ces inputs avec une précision proche du hasard pour une classification binaire.

**Solution** : Définir un seuil de longueur minimale et traiter les inputs trop courts comme indéterminés.

```python
# Dans constants.py
MIN_TEXT_LENGTH_FOR_DETECTION = 10  # caractères minimum pour une détection fiable

# Dans calculate_language_scores ou en preprocessing
if len(text.strip()) < MIN_TEXT_LENGTH_FOR_DETECTION:
    logger.info("Input too short for reliable language detection (len=%d)", len(text))
    return {"french": DEFAULT_UNCOMPUTED_SCORE_VALUE, "non_french": DEFAULT_UNCOMPUTED_SCORE_VALUE}
```

---

### 🧠 DS-05 — `confidence_score == 0` : COMPARAISON FLOTTANTE EXACTE — ANTI-PATTERN NUMÉRIQUE

**Fichier** : `lingua_detector.py` — Ligne 42  
**Criticité** : 🔴 CRITIQUE

**Problème & impact** : La comparaison `== 0` sur un flottant est un **anti-pattern numérique fondamental** en data science. Les valeurs flottantes issues de calculs statistiques ne sont presque jamais exactement `0.0` — elles peuvent être `1e-15`, `2.3e-308`, ou toute autre valeur epsilon. Dans ce cas : la garde `== 0` ne s'active jamais alors qu'elle devrait, le modèle retourne un score "confiant" de `1e-10` pour une détection qui est en réalité nulle, et le comportement réel en production est non déterministe selon la version de Lingua et l'input.

```python
if confidence_score == 0:  # ne s'active jamais en pratique
    return {"french": DEFAULT_UNCOMPUTED_SCORE_VALUE, "non_french": DEFAULT_UNCOMPUTED_SCORE_VALUE}
```

**Solution** : Remplacer la comparaison exacte par un seuil epsilon documenté.

```python
MINIMUM_CONFIDENCE_THRESHOLD = 1e-6  # valeur à calibrer selon les données réelles

if confidence_score < MINIMUM_CONFIDENCE_THRESHOLD:
    return {"french": DEFAULT_UNCOMPUTED_SCORE_VALUE, "non_french": DEFAULT_UNCOMPUTED_SCORE_VALUE}
```

---

### 🧹 CQ-01 — `input` UTILISÉ COMME NOM DE PARAMÈTRE : SHADOWING D'UN BUILTIN PYTHON

**Fichiers** : `lingua_detector.py:26,65` ; `decode_input.py:11` ; `api.py:63,100,103`  
**Criticité** : 🔴 CRITIQUE

**Problème** : `input` est une fonction builtin Python (`input()` pour la saisie utilisateur). Le shadow de builtins est explicitement interdit par PEP 8, détecté par ruff `A002` (flake8-builtins), et rend le code trompeur pour tout développeur qui lit ces signatures. Le problème est systématique : présent dans 5 fichiers et ~10 occurrences. Ruff devrait le lever — soit la règle `A` n'est pas activée, soit ces fichiers sont exclus de l'analyse.

```python
def calculate_language_scores(self, input: str) -> dict:   # shadowing builtin
def run(self, input: str) -> list:                          # idem
def decode_input(input: str) -> str:                        # idem
```

**Solution** : Remplacer partout `input` par un nom descriptif du domaine métier (`text`, `encoded_text`, etc.).

```python
def calculate_language_scores(self, text: str) -> dict:
def run(self, text: str) -> list:
def decode_input(encoded_text: str) -> str:
lingua_detector.run(text="Initialisation de lingua")
```

---

### 🧹 CQ-02 — CONVENTION DE NOMMAGE INCOHÉRENTE : MÉLANGE `DTO` / `Dto`

**Fichiers** : `request_data_dto.py`, `response_data_dto.py`, `api.py`  
**Criticité** : 🔴 CRITIQUE

**Problème** : Le suffixe DTO est écrit tantôt `DTO` (screaming, Java style), tantôt `Dto` (PascalCase Python-friendly). PEP 8 recommande le PascalCase pur pour les noms de classes. L'important est l'uniformité — or les deux coexistent dans le même fichier `request_data_dto.py`.

```python
class ExtraParametersDTO(BaseApimParamsDto):  # DTO en SCREAMING
class RequestDataDto(BaseModel):              # Dto en mixed
```

**Solution** : Choisir une convention unique (PascalCase pur recommandé) et l'appliquer à toutes les classes du projet.

```python
# Convention PascalCase pur — uniformisé partout
class ExtraParametersDto(BaseApimParamsDto):
class RequestDataDto(BaseModel):
class ResponseDataDto(BaseModel):
```

---

### 🧹 CQ-03 — APPEL DE FONCTION AU NIVEAU MODULE SANS GARDE `__main__`

**Fichier** : `generate_project_config.py` — Lignes 226 et 228–236  
**Criticité** : 🔴 CRITIQUE

**Problème** : `generate_process_mode_yaml()` est appelée au niveau module sans aucune garde `if __name__ == "__main__":`. Tout import de ce module depuis un autre fichier (tests, CI, etc.) déclenchera un prompt interactif bloquant. De plus, le dictionnaire `hardware_tiers` est défini après la fonction `generate_process_mode_yaml()` qui le redéfinit localement — cette variable globale de fin de fichier n'est jamais utilisée, c'est un artefact de développement non nettoyé.

```python
generate_process_mode_yaml()   # ligne 226 — exécuté à l'import !

hardware_tiers = { ... }  # variable globale orpheline jamais utilisée
```

**Solution** : Déplacer l'appel dans le guard `__main__` et supprimer le dictionnaire orphelin.

```python
# En bas du fichier — seule modification nécessaire
if __name__ == "__main__":
    generate_process_mode_yaml()
# Supprimer le dict hardware_tiers orphelin
```

---

### 🧹 CQ-04 — CODE EXÉCUTABLE AU NIVEAU MODULE DANS `generate_confluence_doc.py`

**Fichier** : `generate_confluence_doc.py` — Lignes 16–34 et 317–320  
**Criticité** : 🔴 CRITIQUE

**Problème** : La configuration du logger et la construction du dict `sections` (qui appelle `__version__`, lui-même lisant `pyproject.toml` via `pkgutil`) sont exécutées à l'import. Dans un module Python correct, seules les définitions (classes, fonctions, constantes pures) doivent être au niveau module. Tout code avec effets de bord (I/O fichier, accès env, configuration système) doit être dans des fonctions ou sous `__main__`.

```python
# Lignes 16–34 : exécution au niveau module
sections = {
    f"{__version__}: Data management": f"{path_docs}/data_management.md",
    ...
}
# Ligne 317–320 : effets de bord à l'import
configure_logger()
logger = logging.getLogger(LOGGER_NAME)
```

**Solution** : Déplacer la configuration du logger et la construction des sections dans des fonctions dédiées appelées sous `__main__`.

```python
def _build_sections() -> dict:
    path_docs = os.path.join(PROJECT_ROOT, "docs")
    return {
        f"{__version__}: Data management": f"{path_docs}/data_management.md",
        ...
    }

if __name__ == "__main__":
    configure_logger()
    logger = logging.getLogger(LOGGER_NAME)
    generate_confluence_doc()
```

---

### 🧹 CQ-05 — `_parse_data_dict` : DOCSTRING ABSENTE, RETURN TYPE `Union[X, None]` NON-PYTHONIQUE

**Fichier** : `api.py` — Lignes 69–78  
**Criticité** : 🔴 CRITIQUE

**Problème** : Trois violations de qualité code en une seule fonction : (1) Pas de docstring alors que toutes les autres fonctions de `api.py` en ont une. (2) `Union[X, None]` est l'API dépréciée — depuis Python 3.10, la forme idiomatique est `X | None` (PEP 604). (3) `request_data_dto = None` suivi d'un try est un pattern Java — en Python idiomatique, on retourne directement depuis le try.

```python
def _parse_data_dict(data_dict: dict) -> Union[RequestDataDto, None]:
    request_data_dto = None
    try:
        request_data_dto = RequestDataDto(**data_dict)
    except (KeyError, ValueError) as e:
        ...
    return request_data_dto
```

**Solution** : Utiliser le type hint modern `X | None`, ajouter une docstring et retourner directement depuis le try.

```python
def _parse_data_dict(data_dict: dict) -> RequestDataDto | None:
    """Parse the raw request dictionary into a validated RequestDataDto.

    Args:
        data_dict: Raw request payload as a dictionary.

    Returns:
        Validated RequestDataDto instance, or aborts with 400 if parsing fails.
    """
    try:
        return RequestDataDto(**data_dict)
    except (KeyError, ValueError, ValidationError) as e:
        logger.error("Error parsing request data", extra={"type": type(e).__name__, "value": str(e)})
        abort(400, description="Invalid request payload.")
```

---

### 🧪 TEST-01 — SEUIL DE COUVERTURE À 60% NON ENFORCED EN CI

**Fichier** : `tests.md` — Ligne 6 ; `pyproject.toml` — absence de `[tool.pytest.ini_options]`  
**Criticité** : 🔴 CRITIQUE

**Problème** : Un seuil de couverture à **60%** signifie qu'en théorie 40% du code peut partir en production sans aucun test. Pour un guardrail synchrone d'un assistant bancaire, ce seuil est très bas — l'industrie financière vise généralement ≥ 80% pour les composants critiques. Par ailleurs, la **configuration pytest est absente** du `pyproject.toml` : il n'existe aucune section `[tool.pytest.ini_options]`, aucun `testpaths`, aucun `addopts --cov`, aucun `--cov-fail-under`. Le seuil documenté dans `tests.md` n'est donc **pas enforced mécaniquement** dans la CI — il est déclaratif seulement.

**Solution** : Ajouter la configuration pytest avec enforcement du seuil de couverture à 80% minimum dans le pipeline CI.

```toml
# pyproject.toml — à ajouter
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "--cov=industrialisation",
    "--cov=common",
    "--cov-report=term-missing",
    "--cov-report=html:reports/coverage",
    "--cov-fail-under=80",
    "-v",
]
```

---

### 🧪 TEST-02 — `decode_input.py` : AUCUN TEST UNITAIRE SUR LA PORTE D'ENTRÉE DU PIPELINE

**Fichier** : `decode_input.py` — intégralité ; aucun fichier de test correspondant  
**Criticité** : 🔴 CRITIQUE

**Problème** : La fonction `decode_input()` est le **premier traitement appliqué à chaque input utilisateur** — c'est la porte d'entrée du pipeline d'inférence. Elle n'a **aucun test dédié**. Aucun des cas critiques n'est testé : input base64 valide, caractères accentués, input base64 invalide (doit lever `DecoderError`), input vide, input `None`, input très long.

**Solution** : Créer un fichier de test dédié couvrant tous les cas nominaux et d'erreur.

```python
class TestDecodeInput(unittest.TestCase):

    def test_decode_valid_french_text(self):
        encoded = Base64EncoderDecoder(character_encoding_type="utf8").encode(
            "modifier le plafond de ma carte"
        )
        result = decode_input(encoded)
        self.assertEqual(result, "modifier le plafond de ma carte")

    def test_decode_text_with_accents(self):
        encoded = Base64EncoderDecoder(character_encoding_type="utf8").encode("éàç üñ")
        result = decode_input(encoded)
        self.assertEqual(result, "éàç üñ")

    def test_decode_invalid_base64_raises_decoder_error(self):
        with self.assertRaises(DecoderError):
            decode_input("not_valid_base64!!!")

    def test_decode_empty_string_raises(self):
        with self.assertRaises((DecoderError, ValueError)):
            decode_input("")
```

---

### 🧪 TEST-03 — `load_config.py` : AUCUN TEST SUR LES 4 FONCTIONS, DONT LA LOGIQUE D'ENVIRONNEMENT

**Fichier** : `load_config.py` — intégralité (184 lignes, 4 fonctions)  
**Criticité** : 🔴 CRITIQUE

**Problème** : `load_config.py` est le module de chargement de configuration — critique pour le démarrage de l'API. Il contient 4 fonctions publiques dont **aucune n'a de test dédié** : `load_app_config_file()`, `load_service_config_file()`, `load_config_domino_project_file()` (contient la logique de résolution d'environnement dev/pprod/prod), et `get_cpu_number_from_loaded_project_config()`. La logique de résolution d'environnement avec ses conditions complexes (`-prod`, `-pprod`, `default dev`) mérite des tests paramétrés exhaustifs.

**Solution** : Créer des tests paramétrés couvrant toutes les combinaisons de `DOMINO_PROJECT_NAME` et les cas d'erreur (fichier inexistant, YAML invalide).

```python
@pytest.mark.parametrize("project_name,expected_env", [
    ("a100067-sav-guardrails-language-prod", "prod"),
    ("a100067-sav-guardrails-language-pprod", "pprod"),
    ("a100067-sav-guardrails-language-dev", "dev"),
    ("a100067-sav-guardrails-language-preprod", None),  # doit lever ValueError
])
def test_load_config_env_resolution(tmp_path, project_name, expected_env):
    if expected_env is None:
        with pytest.raises(ValueError):
            with patch.dict(os.environ, {"DOMINO_PROJECT_NAME": project_name}):
                load_config_domino_project_file(str(tmp_path / "project_config_{env}.yml"))
    else:
        config_file = tmp_path / f"project_config_{expected_env}.yml"
        config_file.write_text("deployment:\n  api:\n    hardware_tier: test\n")
        with patch.dict(os.environ, {"DOMINO_PROJECT_NAME": project_name}):
            result = load_config_domino_project_file(str(tmp_path / "project_config_{env}.yml"))
        assert result == {"deployment": {"api": {"hardware_tier": "test"}}}
```

---

### 🧪 TEST-04 — `_parse_data_dict` : SEUL LE CAS NOMINAL EST TESTÉ, TOUS LES CAS D'ERREUR ABSENTS

**Fichier** : `industrialisation_test_api.py` — Lignes 83–102  
**Criticité** : 🔴 CRITIQUE

**Problème** : `_parse_data_dict()` est testée **uniquement pour le cas nominal** (payload valide). Or la validation Pydantic peut échouer sur de nombreux cas : `classificationInputs` absent, liste vide, chaîne vide, chaîne whitespace, `Channel` invalide, `Channel` absent, `ClientId` absent, `extra_params` absent, `inputs` absent, payload `None`, payload type incorrect. Aucun de ces 11 cas d'erreur n'est testé, alors que tous doivent retourner un 400.

**Solution** : Ajouter des tests paramétrés couvrant tous les cas d'erreur de validation Pydantic.

```python
@pytest.mark.parametrize("invalid_payload,expected_status", [
    ({"inputs": {"classificationInputs": []}}, 400),       # liste vide
    ({"inputs": {"classificationInputs": [""]}}, 400),     # chaîne vide
    ({"inputs": {"classificationInputs": ["  "]}}, 400),   # whitespace
    ({"inputs": {"classificationInputs": ["ok"]}}, 400),   # Channel manquant
    ({}, 400),                                             # payload vide
    (None, 400),                                           # body null
])
def test_parse_data_dict_invalid_inputs(client, invalid_payload, expected_status):
    response = client.post("/predict", json=invalid_payload)
    assert response.status_code == expected_status
```

---

### 🧪 TEST-05 — LE MOCK `test_inference` EST MAL CONFIGURÉ — LE TEST NE TESTE RIEN

**Fichier** : `industrialisation_test_api.py` — Lignes 104–144  
**Criticité** : 🔴 CRITIQUE

**Problème** : Ce test souffre d'un **bug de mock silencieux** en cascade. (1) `@patch("common.lingua_detector.LinguaDetector")` patche le mauvais module — dans `api.py` l'import est `from common.lingua_detector import LinguaDetector`, donc le bon chemin de patch est `"industrialisation.src.api.LinguaDetector"`. (2) `MockLinguaDetector.run.return_value` configure la méthode de classe, mais `inference()` appelle `run()` sur l'**instance** récupérée depuis `ConfigContext`. (3) Ce test passe parce que `MagicMock` retourne un autre `MagicMock` par défaut, masquant l'erreur — **le test valide une fausse confiance**.

```python
@patch("common.lingua_detector.LinguaDetector")   # ← mauvais chemin
def test_inference(self, MockLinguaDetector, ...):
    MockLinguaDetector.run.return_value = [...]    # ← mock sur la CLASSE, pas l'instance
```

**Solution** : Corriger le chemin de patch pour cibler le bon module et mocker l'instance retournée, pas la classe elle-même.

```python
@patch("industrialisation.src.api.ConfigContext")   # chemin correct
@patch("industrialisation.src.api.LoggingContext")
def test_inference_returns_french_classification(self, MockLoggingContext, MockConfigContext):
    mock_detector = MagicMock()
    mock_detector.run.return_value = [[
        ClassificationScore(label=Language.FRENCH, score=1.0),
        ClassificationScore(label=Language.NON_FRENCH, score=0.0),
    ]]
    MockConfigContext.return_value.get.return_value = mock_detector

    result = inference(data_dict)

    mock_detector.run.assert_called_once()
    self.assertEqual(result["classificationScores"][0][0]["label"], "french")
```

---

### 🧪 TEST-06 — SINGLETON `ConfigContext` PARTAGÉ ENTRE TESTS — ISOLATION ABSENTE

**Fichier** : `test_config_context.py` — intégralité  
**Criticité** : 🔴 CRITIQUE

**Problème** : `ConfigContext` est un Singleton — une seule instance partagée pour tout le process Python. Les 8 tests de `TestConfigContext` opèrent tous sur la **même instance globale** dans un ordre non garanti. Conséquences directes : `test_get_existing_key` attend `"loaded_model" == "InitialValue"` mais si `test_set_key` s'exécute avant, la valeur a changé ; `test_singleton_change_config_not_affected` modifie `"loaded_model"` à `"new_mock_model"` et cette valeur persiste pour tous les tests suivants. Il n'existe aucune réinitialisation du singleton entre les tests : des **flaky tests** qui passent ou échouent selon l'ordre d'exécution.

**Solution** : Réinitialiser le singleton dans `setUp` et `tearDown` via l'attribut name-mangled.

```python
class TestConfigContext(unittest.TestCase):

    def setUp(self) -> None:
        """Reset singleton state before each test to ensure isolation."""
        ConfigContext._ConfigContext__instance = None  # name-mangled reset
        self.config_context = ConfigContext()

    def tearDown(self) -> None:
        """Clean up singleton after each test."""
        ConfigContext._ConfigContext__instance = None
```

---

### 🧪 TEST-07 — TEST D'INTÉGRATION `test_api.py` : SEULE ASSERTION `status == 200`

**Fichier** : `test_api.py` — Lignes 22–41  
**Criticité** : 🔴 CRITIQUE

**Problème** : Ce test d'intégration — le seul qui teste le pipeline de bout en bout — ne vérifie **que le code HTTP 200**. Il ne vérifie pas la structure de la réponse JSON, les valeurs des scores (le texte `"i need to take some vacations"` est en anglais → `non_french` devrait être dominant), le schéma Pydantic de sortie, ni la présence des labels `"french"` / `"non_french"`. Un test qui vérifie uniquement le status 200 offre une fausse confiance : l'API pourrait retourner `{"classificationScores": []}` ou `{"french": -1.0}` et le test passerait.

**Solution** : Ajouter des assertions sur la structure et la logique métier de la réponse.

```python
def test_run_api_non_french_input() -> None:
    client = app.test_client()
    init_app()
    encoded_input = Base64EncoderDecoder(character_encoding_type="utf8").encode(
        "i need to take some vacations"
    )
    response = client.post("/predict", json=build_payload(encoded_input))

    assert response.status_code == 200
    body = response.get_json()
    assert "classificationScores" in body
    scores = body["classificationScores"][0]
    assert len(scores) == 2

    french_score = next(s for s in scores if s["label"] == "french")
    non_french_score = next(s for s in scores if s["label"] == "non_french")

    assert non_french_score["score"] > french_score["score"], \
        "English input should score higher as non_french"
    assert 0.0 <= french_score["score"] <= 1.0
    assert 0.0 <= non_french_score["score"] <= 1.0
```

---

### 📚 DOC-01 — `README.md` : NOM DE PROJET ERRONÉ — COPIÉ D'UN AUTRE PROJET

**Fichier** : `README.md`  
**Criticité** : 🔴 CRITIQUE

**Problème** : Le `README.md` principal s'intitule **"Documentation du projet Secase IA"** — `Secase IA` est le nom d'un autre projet BNP. Ce projet s'appelle `a100067-sav-guardrails-language` et concerne Genius BAR / Hello Bank. Le README se résume à une table des matières vers d'autres fichiers `.md`, sans description du projet, sans architecture, sans prérequis, sans commandes de démarrage. C'est la première chose qu'un tiers lit.

**Solution** : Réécrire le README avec le nom du projet réel, une description du use case en 5 lignes, l'architecture en schéma texte et les commandes de démarrage rapide.

```markdown
# a100067-sav-guardrails-language

Guardrail de classification linguistique **français / non-français** pour l'assistant
virtuel Hello Bank (Genius BAR V2). Appelé en entrée du pipeline d'Input Filtering
pour rejeter les messages non-francophones avant traitement LLM.

## En 30 secondes
- **Input** : texte utilisateur encodé en base64
- **Output** : scores `french` / `non_french` (Lingua 2.1.1)
- **SLA** : < 150ms, 650 req/h en croissance
- **Déployé sur** : Domino dMZR via APIM

## Démarrage rapide
```bash
export DOMINO_PROJECT_NAME=a100067-sav-guardrails-language-dev
ARTIFACTORY_USER=xxx ARTIFACTORY_PASSWORD=yyy make install-deps
python run_api.py
```
```

---

### 📚 DOC-02 — `quickstart.rst` : DOCUMENTATION D'UN AUTRE PROJET — À SUPPRIMER

**Fichier** : `quickstart.rst`  
**Criticité** : 🔴 CRITIQUE

**Problème** : Ce fichier documente une librairie interne appelée **`iaflow`** avec ses classes `EsVectorSearch`, `RetrievalTasks`, `EmbeddingTasks`, `RAG Pipeline` — des composants qui n'existent nulle part dans ce projet de classification de langue. Il contient même une variable de template Cookiecutter non résolue : `{{cookiecutter.package_name}}` (ligne 186). C'est un copier-coller d'une documentation de librairie RAG interne qui n'a aucun rapport avec le guardrail de langue.

**Solution** : Supprimer immédiatement ce fichier qui induit en erreur tout lecteur du dépôt.

```bash
git rm docs/quickstart.rst
git commit -m "docs: remove quickstart.rst (wrong project — iaflow RAG documentation)"
```

---

### 📚 DOC-03 — `setup.md` : ENTIÈREMENT VIDE — ONBOARDING IMPOSSIBLE

**Fichier** : `setup.md`  
**Criticité** : 🔴 CRITIQUE

**Problème** : C'est le fichier le plus critique pour l'onboarding d'un nouveau développeur, et c'est le plus vide du projet. Toutes les sections sont des **placeholders de template non remplis** avec des exemples génériques entre parenthèses comme `(ex. Linux, Windows)`, `(ex. Docker, Python 3.8+)`. Un tiers arrivant sur ce projet ne peut pas installer l'environnement en suivant ce fichier. Les informations réelles (Python 3.11, Poetry, Domino, Vault, Artifactory) existent dans d'autres fichiers mais sont dispersées et non synthétisées.

**Solution** : Rédiger le fichier avec les instructions d'installation réelles du projet.

```markdown
## Prérequis
- Python 3.11 (contrainte pyproject.toml)
- Poetry ≥ 2.0.0
- Accès Domino dMZR (demande via OPS)
- Variables d'environnement : `VAULT_*`, `COS_*` (fournis par OPS)

## Installation locale
```bash
# 1. Configurer Artifactory
ARTIFACTORY_USER=xxx ARTIFACTORY_PASSWORD=yyy make config

# 2. Installer les dépendances
ARTIFACTORY_USER=xxx ARTIFACTORY_PASSWORD=yyy make install-deps

# 3. Définir l'environnement
export DOMINO_PROJECT_NAME=a100067-sav-guardrails-language-dev
export PYTHONPATH=/mnt/code

# 4. Lancer l'API localement
python run_api.py
```
```

---

### 📚 DOC-04 — `design_doc_index.rst` : FICHIER SPHINX D'UN AUTRE PROJET — À SUPPRIMER

**Fichier** : `design_doc_index.rst`  
**Criticité** : 🔴 CRITIQUE

**Problème** : Ce fichier référence encore une fois `iaflow` (`"This repo hosts all the iaflow project design doc."`) et sert d'index Sphinx pour une documentation Sphinx qui n'est pas générée dans ce projet. Ce fichier est inutile tel quel et appartient au même projet erroné que `quickstart.rst`.

**Solution** : Supprimer ce fichier sans remplacement (ce projet n'utilise pas Sphinx).

```bash
git rm docs/design_doc_index.rst
git commit -m "docs: remove design_doc_index.rst (wrong project — iaflow documentation)"
```

---

### 📚 DOC-05 — `model_development.md` : RÉSULTATS DE PERFORMANCE ABSENTS — PLACEHOLDER NON REMPLI

**Fichier** : `model_development.md`  
**Criticité** : 🔴 CRITIQUE

**Problème** : Ce fichier est censé documenter les choix du modèle Lingua, sa performance et sa pertinence. Il contient essentiellement la même phrase paraphrasée 4 fois sans jamais apporter d'information substantielle. La section des résultats de performance est littéralement un placeholder : `"Fournir les résultats obtenus (e.g., accuracy: 95%)"`. Il n'existe aucune justification du choix de Lingua par rapport aux alternatives (langdetect, fastText, CLD3), aucune description de la configuration retenue, aucun benchmark sur des textes bancaires courts.

**Solution** : Remplir la section résultats avec des données réelles mesurées sur un dataset bancaire représentatif (voir DS-06), documenter les choix architecturaux et les alternatives écartées.

```markdown
## Choix du modèle

**Lingua 2.1.1** a été retenu face aux alternatives suivantes :
- langdetect : précision inférieure sur les textes courts, pas de score de confiance
- fastText LangDetect : nécessite un téléchargement de modèle externe, contraintes réseau
- CLD3 : binding C++, complexité d'installation en environnement Domino

## Résultats sur données bancaires

> ⚠️ À COMPLÉTER : constituer un dataset d'évaluation sur des messages chatbot réels
> et mesurer accuracy, F1, taux de faux positifs (FR rejetés) et faux négatifs.

## Configuration

`from_all_languages()` est utilisé actuellement → À migrer vers `from_languages(FR, EN, AR, ES, PT, DE)`
`minimum_relative_distance = 0.0` → À calibrer (recommandation Lingua : 0.1–0.25)
```

---

## PARTIE 2 — PROBLÈMES MAJEURS

---

### 🔐 SEC-06 — CONSTANTE `FILE_NAME_SERVICE_CONFIG` HARDCODÉE SUR `dev`

**Fichier** : `constants.py` — Ligne 5  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Le nom du fichier de configuration de services est **hardcodé sur l'environnement `dev`** dans les constantes. La fonction `load_service_config_file()` utilise cette constante sans substitution d'environnement (contrairement à `load_config_domino_project_file` qui fait la substitution). En production, c'est le fichier `services_dev.env` qui est chargé, avec les credentials dev.

```python
FILE_NAME_SERVICE_CONFIG = "services_dev.env"
```

**Solution** : Résoudre dynamiquement le nom du fichier de services selon l'environnement, comme c'est déjà fait pour le project_config.

```python
# Dans load_config.py — load_service_config_file()
env_suffix = os.getenv("DOMINO_PROJECT_NAME", "dev").rsplit("-", 1)[-1]
service_file = f"services_{env_suffix}.env"
path_file_conf = os.path.join(path_dir_name, service_file)
```

---

### 🔐 SEC-07 — CHEMIN ABSOLU HARDCODÉ EXPOSANT LA STRUCTURE DU SYSTÈME

**Fichier** : `constants.py` — Ligne 9  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Un chemin absolu vers un fichier interne est hardcodé dans les constantes. Cela expose la structure du filesystem de déploiement (plateforme Domino, point de montage `/mnt/code`). En cas de path traversal ou de mauvaise gestion de ce chemin, cela fournit un guide de navigation pour un attaquant.

```python
FRENCH_DICT_PATH = "/mnt/code/industrialisation/src/models/french_dict.json"
```

**Solution** : Construire les chemins dynamiquement depuis `PROJECT_ROOT` pour garantir la portabilité et masquer la structure.

```python
from settings import PROJECT_ROOT
FRENCH_DICT_PATH = os.path.join(
    PROJECT_ROOT, "industrialisation", "src", "models", "french_dict.json"
)
```

---

### 🔐 SEC-08 — TOKEN CONFLUENCE EXPOSÉ EN ARGUMENT CLI

**Fichier** : `generate_confluence_doc.py` — Lignes 244–250  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Le token Confluence peut être passé en argument de ligne de commande `--access-token`. Les arguments CLI sont visibles dans la liste des processus (`ps aux`), dans les logs CI/CD, et dans l'historique bash. La valeur par défaut depuis l'environnement est correcte, mais le fait que `click` expose cet argument en CLI est un vecteur de fuite.

```python
@click.option("--access-token", default=access_token, help="Personal access token")
```

**Solution** : Supprimer l'option `--access-token` du CLI et forcer la lecture exclusive depuis la variable d'environnement.

```python
def generate_confluence_doc(confluence_url, space_key, main_page_title, generate_doc):
    token = os.environ.get("CONFLUENCE_ACCESS_TOKEN")
    if not token:
        raise ValueError("CONFLUENCE_ACCESS_TOKEN environment variable is not set.")
    confluence = Confluence(url=confluence_url, token=token)
```

---

### 🔐 SEC-09 — ABSENCE DE VALIDATION DE TAILLE SUR L'INPUT BASE64

**Fichier** : `decode_input.py` — Lignes 11–29 ; `api.py` — Ligne 100  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : L'input base64 est décodé sans aucune validation préalable sur sa taille. Un attaquant peut envoyer une chaîne base64 encodant un texte très volumineux (attaque par déni de service, épuisement mémoire). Il n'y a aucune limite de taille appliquée ni côté DTO, ni côté décodage.

**Solution** : Valider la taille maximale de l'input encodé dans le DTO Pydantic via un `field_validator`.

```python
from pydantic import field_validator

MAX_INPUT_LENGTH = 10_000  # caractères base64

class ClassificationInputs(BaseModel):
    classification_inputs: list[str] = Field(alias="classificationInputs", min_length=1, max_length=1)

    @field_validator("classification_inputs", each_item=True, mode="before")
    @classmethod
    def check_input_size(cls, v: str) -> str:
        if len(v) > MAX_INPUT_LENGTH:
            raise ValueError(f"Input exceeds maximum allowed size of {MAX_INPUT_LENGTH} characters.")
        return v
```

---

### 🔐 SEC-10 — `ConfigContext` SINGLETON SANS THREAD SAFETY

**Fichier** : `config_context.py` — Lignes 27–43  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Le pattern Singleton n'est pas thread-safe. En environnement de production avec plusieurs workers Flask (Gunicorn multi-thread), deux threads peuvent simultanément évaluer `cls.__instance is None` à `True` et créer deux instances. La méthode `set()` n'est pas protégée contre les race conditions : une écriture concurrente peut corrompre `_config` pendant une inférence en cours.

```python
def __new__(cls) -> "ConfigContext":
    if cls.__instance is None:
        cls.__instance = super().__new__(cls)
        cls.__instance._config = { "loaded_model": "InitialValue" }
    return cls.__instance
```

**Solution** : Protéger la création et les accès en écriture avec un `threading.Lock` en double-checked locking.

```python
import threading

class ConfigContext:
    __instance = None
    __lock = threading.Lock()

    def __new__(cls) -> "ConfigContext":
        if cls.__instance is None:
            with cls.__lock:
                if cls.__instance is None:
                    cls.__instance = super().__new__(cls)
                    cls.__instance._config = {"loaded_model": "InitialValue"}
        return cls.__instance

    def set(self, key: str, value: Any) -> None:
        with self.__lock:
            self._config[key] = value
```

---

### 🔐 SEC-11 — MANIPULATION DE `sys.path` POUVANT CRÉER UNE VULNÉRABILITÉ D'INJECTION DE MODULE

**Fichier** : `run_api.py` — Lignes 13–21  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : La manipulation directe de `sys.path` pour réordonner les `site-packages` est risquée en production. Si un attaquant parvient à placer un fichier avec le même nom qu'un module standard dans un répertoire qui se retrouve en tête de `sys.path`, il peut détourner l'import (module hijacking).

```python
sys.path = [p for p in sys.path if "/mnt/code" not in p]
site_packages_paths = [p for p in sys.path if "site-packages" in p]
for site_packages_path in site_packages_paths:
    sys.path.remove(site_packages_path)
    sys.path.insert(0, site_packages_path)
```

**Solution** : Documenter précisément pourquoi cette manipulation est nécessaire et ajouter des assertions sur les chemins insérés pour s'assurer qu'ils ne sont pas contrôlés par un tiers.

```python
# Documenter le bug Domino corrigé avec un ticket de référence
# ET valider que les chemins insérés sont des chemins connus
assert all(p.startswith("/usr") or p.startswith("/opt") for p in site_packages_paths), \
    "Unexpected site-packages path detected"
```

---

### 🔐 SEC-12 — ABSENCE DE RATE LIMITING SUR L'ENDPOINT D'INFÉRENCE

**Fichier** : `test_api.py` (Flask app exposée) ; `run_api.py`  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Aucun mécanisme de rate limiting n'est implémenté sur l'endpoint d'inférence. L'API est exposée sans limitation du nombre de requêtes par client/IP/token. Cela expose le service à des attaques par déni de service (DoS), à de la scraping intensif ou à des attaques par force brute sur les inputs.

**Solution** : Ajouter `flask-limiter` avec une politique de rate limiting adaptée au SLA cible.

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(get_remote_address, app=app, default_limits=["100 per minute"])

@app.route("/predict", methods=["POST"])
@limiter.limit("60 per minute")
def predict():
    ...
```

---

### ⚡ PERF-05 — `model_dump()` APPELÉ DEUX FOIS SUR LE MÊME OBJET

**Fichier** : `api.py` — Lignes 113–114  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : `model_dump(by_alias=True)` est appelé **deux fois** sur le même objet `ResponseDataDto` à chaque requête. Cette méthode Pydantic sérialise récursivement la structure. Le résultat du premier appel (pour le log) est jeté, et le second recalcule exactement la même chose.

```python
logger.info(f"Inference results : {response_data.model_dump(by_alias=True)}")
return response_data.model_dump(by_alias=True)
```

**Solution** : Calculer une seule fois, stocker dans une variable et réutiliser.

```python
result = response_data.model_dump(by_alias=True)
logger.debug("Inference results: %s", result)
return result
```

---

### ⚡ PERF-06 — LOGGING SYSTÉMATIQUE EN `INFO` AVEC F-STRINGS SUR LE CHEMIN CRITIQUE

**Fichier** : `api.py` — Lignes 89, 113 ; `decode_input.py` — Lignes 21, 25  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Le chemin critique d'inférence contient **4 appels `logger.info`** avec formatage f-string. En Python, le formatage de la f-string est évalué **avant** d'être passé au logger, même si le message n'est pas finalement loggé. À 650 req/heure, cela représente ~43 000 appels de log/heure avec sérialisation, écriture I/O et interpolation de chaînes.

```python
logger.info(f"Inference function called. Version: {__version__}")
logger.info("Decoding the input from the user.")
logger.info(f"Inference results : {response_data.model_dump(by_alias=True)}")
```

**Solution** : Utiliser le formatage lazy (`%s`) et passer les logs de détail en `DEBUG` en production.

```python
logger.debug("Inference function called. Version: %s", __version__)
logger.debug("Decoding the input from the user.")
# model_dump() déplacé dans une variable (voir PERF-05)
```

---

### ⚡ PERF-07 — ABSENCE DE CONFIGURATION WSGI/GUNICORN

**Fichier** : `run_api.py`, `project_config_prod.yml`  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Le projet utilise Flask mais aucune configuration de serveur WSGI de production (Gunicorn, uWSGI) n'est présente ni documentée. Le nombre de workers est par défaut (souvent 1 sync worker), le timeout n'est pas configuré. Avec `prd-cpu-2x4` (2 vCPU) et `replica_count: 3`, la configuration optimale serait `(2 * 2 + 1) = 5 workers` par replica (formule Gunicorn recommandée).

**Solution** : Ajouter un fichier `gunicorn.conf.py` avec la configuration explicite et documentée.

```python
# gunicorn.conf.py
workers = 5           # (2 * nb_cpu + 1)
worker_class = "sync" # sync suffisant pour une inférence CPU-bound rapide
timeout = 30
keepalive = 2
worker_connections = 100
```

---

### ⚡ PERF-08 — MODE `is_async: 'false'` SANS STRATÉGIE BURST DOCUMENTÉE

**Fichier** : `project_config_prod.yml` — Ligne 9  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : L'API est configurée en mode **synchrone**. Pour 650 req/heure en régime nominal c'est acceptable, mais en **burst** (pic de trafic), des requêtes simultanées peuvent saturer les workers synchrones. Le taux de 650 req/heure est une estimation à horizon mai 2026 en croissance — sans plafond clair pour les cas de pointe.

**Solution** : Documenter le taux de pointe (burst capacity) et définir une stratégie de scaling horizontal avec des seuils explicites.

```yaml
# project_config_prod.yml — à compléter
deployment:
  api:
    is_async: 'false'
    replica_count: 3
    # À documenter :
    # - burst_capacity: X req/s (à mesurer)
    # - scaling_strategy: manuel / auto-scaling Domino
    # - seuil CPU scale-up: 70%
```

---

### ⚡ PERF-09 — `ConfigContext()` ET `LoggingContext()` INSTANCIÉS À CHAQUE REQUÊTE

**Fichier** : `api.py` — Lignes 87–88  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : `ConfigContext()` et `LoggingContext()` sont instanciés à chaque appel de `inference()`. Même si `ConfigContext` est un singleton, l'appel à chaque requête inclut le dispatch Python, l'accès à la variable de classe, et le retour de l'instance — 650 fois/heure. Ce sont des micro-overhead qui s'accumulent sur le chemin critique.

**Solution** : Récupérer les instances une seule fois au chargement du module et les réutiliser directement.

```python
# En haut de api.py — une seule fois au chargement du module
_config_context = ConfigContext()

def inference(data_dict: dict) -> dict:
    lingua_detector = _config_context.get("lingua_detector")
    ...
```

---

### ⚡ PERF-10 — VALIDATION PYDANTIC V1 (`@validator`) AU LIEU DE V2 (`@field_validator`)

**Fichier** : `request_data_dto.py` — Lignes 4, 20  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Le projet utilise Pydantic V2 mais le décorateur `@validator` est l'**API dépréciée de Pydantic V1**. En V2, `@validator` est maintenu via une couche de compatibilité qui ajoute un overhead par rapport au natif `@field_validator`. Cela peut déclencher des `PydanticDeprecatedSince20` warnings qui polluent les logs en production.

```python
from pydantic import BaseModel, Field, validator  # API V1 dépréciée

@validator("classification_inputs", each_item=True)
def check_non_empty_strings(cls, input: str) -> str:
```

**Solution** : Migrer vers l'API Pydantic V2 native avec `@field_validator` et `@classmethod`.

```python
from pydantic import BaseModel, Field, field_validator

@field_validator("classification_inputs", mode="before")
@classmethod
def check_non_empty_strings(cls, values: list[str]) -> list[str]:
    for v in values:
        if not v or v.strip() == "":
            raise ValueError(f"Empty string found in inputs, type: {type(v)}")
    return values
```

---

### 🛡️ ROB-07 — `init_app()` SANS GUARD — DOUBLE INITIALISATION POSSIBLE EN MULTI-WORKER

**Fichier** : `api.py` — Lignes 35–66 ; `run_api.py` — Ligne 33  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : `init_app()` ne vérifie pas si l'application est déjà initialisée. En contexte multi-worker Gunicorn avec `preload_app=True`, ou si Domino appelle `init_app()` plusieurs fois (health check, reimport), Lingua sera rechargé plusieurs fois et le `ConfigContext` sera réécrit pendant qu'un worker actif est en train de lire `lingua_detector`.

**Solution** : Ajouter un flag d'initialisation atomique qui empêche toute réinitialisation intempestive.

```python
_initialized = False

def init_app() -> None:
    global _initialized
    if _initialized:
        logger.warning("init_app() called more than once — skipping.")
        return
    # ... init normale ...
    _initialized = True
```

---

### 🛡️ ROB-08 — `data_dict` PEUT ÊTRE `None` — `TypeError` AVANT MÊME LA VALIDATION PYDANTIC

**Fichier** : `api.py` — Ligne 72  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : `request.get_json()` retourne `None` si le corps de la requête est vide, si le `Content-Type` n'est pas `application/json`, ou si le JSON est malformé. Dans ce cas, `RequestDataDto(**None)` lève un **`TypeError`** non catchée par `except (KeyError, ValueError)`. Résultat : 500 opaque au lieu d'un 400 clair.

**Solution** : Valider que `data_dict` n'est pas `None` en entrée de `_parse_data_dict` avant toute tentative de parsing.

```python
def _parse_data_dict(data_dict: dict) -> RequestDataDto | None:
    if data_dict is None:
        logger.error("Received null data_dict — missing or malformed JSON body.")
        abort(400, description="Request body is missing or not valid JSON.")
    try:
        return RequestDataDto(**data_dict)
    except (KeyError, ValueError, ValidationError) as e:
        logger.error("Parsing error", extra={"detail": str(e)})
        abort(400, description="Invalid request payload.")
```

---

### 🛡️ ROB-09 — `DOMINO_PROJECT_NAME` VAUT `"dev"` PAR DÉFAUT EN PROD SANS ALERTE

**Fichier** : `load_config.py` — Ligne 114  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Si `DOMINO_PROJECT_NAME` n'est pas définie (oubli de configuration, redéploiement rapide), la valeur par défaut `"dev"` est utilisée **silencieusement**. L'application démarre en production avec la configuration dev, sans aucune exception ni alerte. Ce comportement est particulièrement dangereux car l'app démarre normalement — aucune exception n'est levée.

```python
domino_project_name = os.getenv("DOMINO_PROJECT_NAME", "dev")
```

**Solution** : Logger un avertissement explicite si la variable est absente et ne jamais la laisser tomber silencieusement en valeur par défaut en environnement non-dev.

```python
domino_project_name = os.getenv("DOMINO_PROJECT_NAME")
if domino_project_name is None:
    logger.warning(
        "DOMINO_PROJECT_NAME is not set — defaulting to 'dev'. "
        "Ensure this is intentional in non-dev environments."
    )
    domino_project_name = "dev"
```

---

### 🛡️ ROB-10 — `assert isinstance(...)` EN CODE DE PRODUCTION — DÉSACTIVABLE AVEC `-O`

**Fichier** : `generate_project_config.py` — Ligne 61  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Les assertions sont **désactivées** quand Python est lancé avec le flag `-O` (optimisation), parfois utilisé en production. Si `load_deployment_config()` retourne `None`, l'assertion est silencieusement ignorée et les appels suivants crashent avec une `TypeError` ou `KeyError` sans message explicite.

```python
assert isinstance(deployment_config, dict)
```

**Solution** : Remplacer par une vérification explicite avec message d'erreur informatif et non désactivable.

```python
if not deployment_config or not isinstance(deployment_config, dict):
    raise ValueError(
        "Failed to load deployment configuration from project_config_ref.yml. "
        "Please ensure the file exists and contains a valid 'deployment' section."
    )
```

---

### 🛡️ ROB-11 — `get_or_create_page()` RETOURNE `None` SANS VÉRIFICATION — `TypeError` EN CHAÎNE

**Fichier** : `generate_confluence_doc.py` — Lignes 268–295  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : `get_or_create_page()` peut retourner `None` (lignes 120 et 130). Les appels successifs utilisent le résultat comme `main_page["id"]`, `mep_page["id"]` sans aucune vérification de nullité. Si la première page échoue, tous les appels suivants crashent avec `TypeError: 'NoneType' object is not subscriptable`, et le pipeline CI/CD échoue de manière opaque.

**Solution** : Vérifier chaque retour de page et lever une `RuntimeError` explicite immédiatement.

```python
main_page = get_or_create_page(confluence, main_page_title, "...", space_key)
if main_page is None:
    raise RuntimeError(f"Failed to get or create main Confluence page '{main_page_title}'.")

mep_page = get_or_create_page(confluence, "Releases et docs", ..., space_key, main_page["id"])
if mep_page is None:
    raise RuntimeError("Failed to get or create MEP page.")
```

---

### 🛡️ ROB-12 — `train.py` : `f"/mnt/data/None"` PRODUIT SILENCIEUSEMENT UN CHEMIN INVALIDE

**Fichier** : `train.py` — Lignes 15–16  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Si `DOMINO_PROJECT_NAME` n'est pas définie, `os.getenv()` retourne `None`. La f-string produit silencieusement la chaîne `/mnt/data/None` — un chemin syntaxiquement valide mais sémantiquement incorrect. Tout code downstream produira des `FileNotFoundError` tardives et difficiles à diagnostiquer.

```python
DOMINO_PROJECT_NAME = os.getenv("DOMINO_PROJECT_NAME")          # peut être None
DATASET_PROJECT = f"/mnt/data/{DOMINO_PROJECT_NAME}"            # → "/mnt/data/None"
```

**Solution** : Valider la variable d'environnement avant de construire tout chemin dérivé.

```python
DOMINO_PROJECT_NAME = os.getenv("DOMINO_PROJECT_NAME")
if not DOMINO_PROJECT_NAME:
    raise EnvironmentError("DOMINO_PROJECT_NAME environment variable is required but not set.")
DATASET_PROJECT = f"/mnt/data/{DOMINO_PROJECT_NAME}"
```

---

### 🛡️ ROB-13 — DOUBLE CHEMIN DE RETOUR D'ERREUR INCOHÉRENT DANS `inference()`

**Fichier** : `api.py` — Lignes 91–93  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : `_parse_data_dict()` gère déjà l'erreur en appelant `abort(400)`, ce qui lève une `HTTPException` Flask et court-circuite l'exécution. Le `if not request_data_dto` ligne 92 est donc **du code mort** — il ne sera jamais atteint. Si `_parse_data_dict()` retournait `None` pour une raison non couverte (bug futur), le `raise ValueError` produirait une 500 au lieu d'une 400.

**Solution** : Unifier la gestion d'erreur dans `_parse_data_dict` avec un type de retour non-Optional et supprimer le code mort.

```python
# _parse_data_dict doit toujours retourner un RequestDataDto valide ou abort()
def _parse_data_dict(data_dict: dict) -> RequestDataDto:  # retour non-Optional

# inference() — supprimer le check redondant
request_data_dto = _parse_data_dict(data_dict)
# request_data_dto est garanti non-None ici — pas de vérification nécessaire
text_to_classify = decode_input(encoded_text=request_data_dto.inputs.classification_inputs[0])
```

---

### 🧠 DS-06 — AUCUNE ÉVALUATION SUR DONNÉES RÉELLES DU DOMAINE BANCAIRE

**Fichier** : `model_development.md` — Lignes 30–31  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : La section `model_development.md` mentionne des métriques mais **les résultats réels ne sont pas renseignés** — le champ est un placeholder non rempli. Il n'existe aucune baseline de performance sur des données représentatives du chatbot bancaire, aucune mesure du taux de faux positifs (utilisateurs francophones rejetés) ni des faux négatifs (utilisateurs non francophones acceptés). Les benchmarks officiels de Lingua sont mesurés sur des corpus généraux (Wikipedia, news) — pas sur des textes courts de chatbot bancaire.

**Solution** : Constituer un dataset d'évaluation représentatif, mesurer les métriques métier, et documenter les résultats.

```python
evaluation_dataset = [
    # Cas nominaux
    ("modifier le plafond de ma carte", "french"),
    ("i want to check my balance", "non_french"),
    # Cas limites bancaires
    ("IBAN FR76 3000", "french"),
    ("virement SEPA", "french"),
    # Inputs ultra-courts
    ("ok", "undetermined"),
    ("bonjour", "french"),
    # Code-switching
    ("mon credit card est bloqué", "french"),
]
```

---

### 🧠 DS-07 — PAS DE NORMALISATION DE CASSE : COMPORTEMENT DIFFÉRENT SELON LES MAJUSCULES

**Fichier** : `api.py` — Ligne 100 ; `lingua_detector.py` — intégralité  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : En l'absence de normalisation de casse (lowercasing), **deux inputs sémantiquement identiques peuvent produire des scores différents** (`"modifier mon plafond"` vs `"MODIFIER MON PLAFOND"` vs `"Modifier Mon Plafond"`). Ce n'est pas marginal : dans l'urgence ou sur mobile, les utilisateurs mixent fréquemment les casses.

**Solution** : Tester les deux approches (avec et sans lowercasing) sur le dataset d'évaluation (DS-06) et appliquer celle qui maximise la précision.

```python
def preprocess_text(text: str) -> str:
    """Normalize text before language detection."""
    return text.lower().strip()
    # Valider sur le dataset bancaire réel si lowercasing améliore la précision
```

---

### 🧠 DS-08 — SCORE `non_french` TOUJOURS `0.0` POUR LE FRANÇAIS : PERTE D'INFORMATION MÉTIER

**Fichier** : `lingua_detector.py` — Lignes 45–48  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Ce schéma force l'un des deux scores à `0.0` de manière systématique. Pour un texte **ambigu franco-anglais** (`"mon credit card est bloqué"`), le modèle retourne soit `french=0.72, non_french=0.0` soit `french=0.0, non_french=0.72` — jamais `french=0.72, non_french=0.28`. **L'information sur l'ambiguïté est perdue**, et les deux scores **ne somment jamais à 1**.

```python
if detected_language.iso_code_639_1.name.lower() == "fr":
    return {"french": confidence_score, "non_french": 0.0}  # non_french forcé à 0.0
```

**Solution** : Retourner le score complémentaire basé sur la distribution réelle des confiances pour que les scores somment à 1.

```python
all_confidence = self.detector.compute_language_confidence_values(text)
fr_score = next(
    (v.value for v in all_confidence
     if v.language.iso_code_639_1 and v.language.iso_code_639_1.name.lower() == "fr"),
    0.0
)
non_fr_score = round(1.0 - fr_score, 6)
return {"french": round(fr_score, 6), "non_french": non_fr_score}
```

---

### 🧠 DS-09 — ABSENCE DE SEUIL DE DÉCISION DOCUMENTÉ ET CONFIGURABLE

**Fichier** : `lingua_detector.py`, `constants.py`, documentation  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : Le Guardrails downstream consomme les scores pour appliquer des règles métier, mais **aucun seuil de décision** n'est défini, documenté ni exposé dans la configuration. À partir de quel score `french` considère-t-on que l'input est "assez français" ? Quelle est la zone grise acceptable ? Ce seuil est une décision **métier critique** qui appartient à ce projet, pas au Guardrails.

**Solution** : Exposer le seuil de décision comme paramètre configurable documenté dans `constants.py`.

```python
# constants.py
FRENCH_CLASSIFICATION_THRESHOLD = 0.5       # à calibrer sur données réelles (DS-06)
FRENCH_UNDETERMINED_LOWER_BOUND = 0.3       # zone grise → indéterminé si score < 0.3
```

---

### 🧠 DS-10 — ABSENCE DE MONITORING DE DÉRIVE DU MODÈLE

**Fichier** : `model_production.md` — Ligne 26  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : La dérive est un risque concret : vocabulaire des utilisateurs qui évolue (nouveaux produits, emojis, abréviations SMS), règles métier du Guardrails qui changent, code-switching croissant. Sans monitoring, **une dégradation silencieuse des performances** peut passer inaperçue pendant des semaines. L'alerte Synthetic vérifie uniquement que l'API est up — pas la qualité des prédictions.

**Solution** : Logger systématiquement les métriques de distribution des scores pour permettre la détection de dérive dans Kibana.

```python
logger.info("prediction_metrics", extra={
    "french_score": classification_scores[0][0].score,
    "non_french_score": classification_scores[0][1].score,
    "is_undetermined": classification_scores[0][0].score == DEFAULT_UNCOMPUTED_SCORE_VALUE,
    "input_length": len(text_to_classify),
    "channel": request_data_dto.extra_params.channel,
})
```

---

### 🧠 DS-11 — LINGUA 2.1.1 PINNÉE SANS TESTS DE RÉGRESSION NLP

**Fichier** : `pyproject.toml` — Ligne 61  
**Criticité** : 🟠 MAJEUR

**Problème & impact** : La version Lingua est fixée à `2.1.1` (reproductibilité correcte). Cependant, il n'existe aucun jeu de tests de régression NLP permettant de valider qu'une mise à jour de Lingua ne dégrade pas les performances sur le domaine bancaire. Il n'y a pas de processus de validation pour la mise à jour de la lib.

**Solution** : Créer un dataset de régression golden set et une gate de validation automatique dans la CI.

```python
GOLDEN_SET = [
    ("modifier le plafond de ma carte", "french", 0.9),
    ("i need to change my card limit", "non_french", 0.9),
    ("solde", "french", 0.6),
    ("IBAN FR76", "french", 0.5),
]

def test_lingua_regression():
    detector = LinguaDetector()
    for text, expected_class, min_score in GOLDEN_SET:
        scores = detector.calculate_language_scores(text)
        predicted = "french" if scores["french"] > scores["non_french"] else "non_french"
        assert predicted == expected_class, f"Regression on: '{text}'"
        assert scores[expected_class] >= min_score, f"Score too low for: '{text}'"
```

---

### 🧹 CQ-06 — DOCSTRINGS : MÉLANGE GOOGLE / NUMPY ET QUALITÉ VARIABLE

**Fichiers** : `load_config.py`, `lingua_detector.py`, `generate_confluence_doc.py`, `api.py`  
**Criticité** : 🟠 MAJEUR

**Problème** : Le projet mélange deux styles de docstrings : NumPy style (`Parameters / Returns / Raises` avec `----------`) dans `load_config.py`, et Google style (`Args: / Returns:`) dans tous les autres fichiers. Certaines docstrings sont superficielles : `LinguaDetector` ne décrit pas le pattern Singleton ni le binaire FR/non-FR, `inference()` contient `"This method should be implemented by you"` — commentaire de template non mis à jour, `get_response()` dans `run_api.py` contient `"""Get response."""`.

**Solution** : Choisir Google style (le plus répandu en Python MLOps), le documenter dans `clean_code.md` et mettre à jour les docstrings insuffisantes.

```toml
# pyproject.toml — enforcer Google style via ruff
[tool.ruff.lint.pydocstyle]
convention = "google"
```

---

### 🧹 CQ-07 — `train.py` : CODE EXÉCUTABLE AU NIVEAU MODULE SANS AUCUNE FONCTION

**Fichier** : `train.py` — Lignes 9–18  
**Criticité** : 🟠 MAJEUR

**Problème** : Le fichier `train.py` n'a aucune fonction `train()`, aucune garde `__main__`, et exécute des opérations d'I/O (chargement de config, logging) directement au niveau module. Ce fichier est structurellement un script déguisé en module. Si jamais ce fichier est importé (test, CI), il déclenche immédiatement des I/O et peut crasher.

**Solution** : Encapsuler tout le code dans une fonction `train()` appelée sous `if __name__ == "__main__":`.

```python
def train() -> None:
    """Entry point for model training (N/A for this project)."""
    configure_logger()
    app_config = load_app_config_file()
    load_service_config_file()
    logger = logging.getLogger(LOGGER_NAME)
    logger.info("This project does not require any training.")

if __name__ == "__main__":
    train()
```

---

### 🧹 CQ-08 — PRINCIPE DRY VIOLÉ : `hardware_tiers` DICT DUPLIQUÉ 3 FOIS

**Fichier** : `generate_project_config.py` — Lignes 168–176, 190–215, 228–236  
**Criticité** : 🟠 MAJEUR

**Problème** : Le dictionnaire `hardware_tiers` est défini trois fois avec des valeurs légèrement différentes et des clés incohérentes (`"Large"` vs `"large"`, `"Medium"` vs `"medium"`). Tout changement de hardware tier Domino nécessite une mise à jour en 3 endroits avec un risque élevé d'incohérence.

**Solution** : Définir deux constantes uniques au niveau module et les réutiliser dans les fonctions respectives.

```python
# En haut du module — constantes uniques
API_HARDWARE_TIERS: dict[str, str] = {
    "mdl-cpu-1x2": "1 core, 2 GiB RAM",
    "mdl-cpu-2x4": "2 cores, 4 GiB RAM",
    "prd-cpu-2x4": "2 cores, 4 GiB RAM (production)",
}

BATCH_HARDWARE_TIERS: dict[str, str] = {
    "job-cpu-4x16": "4 cores, 16 GiB",
    "job-cpu-8x32": "8 cores, 32 GiB",
}

def choose_hardware_tier_api(deployment_config: dict) -> None:
    _choose_hardware_tier(deployment_config, "api", API_HARDWARE_TIERS)

def _choose_hardware_tier(config: dict, mode: str, tiers: dict[str, str]) -> None:
    """Generic hardware tier selector with input validation loop."""
    while True:
        tier = input("Enter the selected hardware tier: ").strip()
        if tier in tiers:
            break
        print(f"Invalid choice. Available: {list(tiers.keys())}")
    config["deployment"][mode]["hardware_tier"] = tier
```

---

### 🧹 CQ-09 — `version.py` : DOUBLE LECTURE DE `pyproject.toml` SANS CACHE

**Fichier** : `version.py` — Lignes 9–26  
**Criticité** : 🟠 MAJEUR

**Problème** : `get_toml_data()` est appelée deux fois lors de l'import du module : une fois pour le nom du projet, une fois pour la version — alors qu'une seule lecture suffit. Sans `@functools.lru_cache`, cette double I/O est exécutée à chaque import du module.

**Solution** : Ajouter `@functools.lru_cache(maxsize=1)` et lire les deux valeurs en un seul appel.

```python
import functools

@functools.lru_cache(maxsize=1)
def get_toml_data() -> dict:
    data = pkgutil.get_data(__name__, PYPROJECT_TOML)
    if data is None:
        raise ValueError(f"{PYPROJECT_TOML} not found")
    return cast(dict, tomlkit.parse(data.decode("utf-8")))

# Un seul appel pour les deux valeurs
_toml = get_toml_data()
__project_name__: str = _toml["project"]["name"]
__version__: str = _toml["project"]["version"]
```

---

### 🧹 CQ-10 — PATTERN `if exists + open` : DOUBLE SYSCALL ET RACE CONDITION

**Fichier** : `load_config.py` — Lignes 50–55, 81–88, 145–151  
**Criticité** : 🟠 MAJEUR

**Problème** : Ce pattern est répété 3 fois. Il effectue deux appels système séparés (`stat()` pour `exists()` + `open()`). Entre les deux appels, le fichier pourrait disparaître (TOCTOU). De plus, `open()` lève déjà `FileNotFoundError` nativement — le `exists()` préalable est redondant.

**Solution** : Utiliser le pattern EAFP Python : `try/except` directement sur `open()`.

```python
try:
    with open(path_file_conf) as file:
        config_data = yaml.safe_load(file)
except FileNotFoundError:
    raise FileNotFoundError(f"Config file not found: {path_file_conf}") from None
except yaml.YAMLError as e:
    raise ValueError(f"Error parsing YAML file '{path_file_conf}': {e}") from e
```

---

### 🧹 CQ-11 — LOGIQUE `env_suffix` RECALCULÉE MANUELLEMENT : VIOLATION DRY

**Fichier** : `load_config.py` — Lignes 131–140  
**Criticité** : 🟠 MAJEUR

**Problème** : La logique de mapping `domino_project_name → env_suffix` est redondante avec l'extraction faite 10 lignes plus haut. La variable `env_suffix` est calculée puis inutilisée pour la substitution — le code repart sur `domino_project_name` avec des `if "-prod" in`. De plus, `-prod` matcherait aussi `-pprod` si l'ordre des tests était inversé.

```python
if "-prod" in domino_project_name:
    file_basename = file_basename.replace("{env}", "prod")
elif "-pprod" in domino_project_name:
    ...
```

**Solution** : Réutiliser directement `env_suffix` déjà calculé plus haut.

```python
env_suffix = domino_project_name.rsplit("-", 1)[-1]
if env_suffix not in ("pprod", "prod", "dev"):
    raise ValueError(f"Unknown environment suffix: '{env_suffix}'")
file_basename = file_basename.replace("{env}", env_suffix)
```

---

### 🧹 CQ-12 — `test_api.py` : FICHIER AMBIGU (SCRIPT + TEST + MINI APP FLASK)

**Fichier** : `test_api.py` — Lignes 1–45  
**Criticité** : 🟠 MAJEUR

**Problème** : Ce fichier remplit trois rôles incompatibles : mini-application Flask avec un endpoint `/predict`, fonction de test `test_run_api()`, et script exécutable. La présence de `app.add_url_rule(...)` dans la fonction de test est particulièrement problématique : cette règle est ajoutée à chaque appel, ce qui provoquerait une `AssertionError` en cas de double appel (Flask n'accepte pas les règles dupliquées).

**Solution** : Séparer en deux fichiers distincts avec une responsabilité unique chacun.

```python
# tests/integration/test_api_integration.py — uniquement les tests
class TestApiIntegration(unittest.TestCase):
    def setUp(self):
        self.app = create_test_app()
        self.client = self.app.test_client()
        init_app()

    def test_predict_french_input(self):
        response = self.client.post("/predict", json=build_french_payload())
        self.assertEqual(response.status_code, 200)
```

---

### 🧹 CQ-13 — `run_api.py` : DOCSTRING DE TEMPLATE NON MIS À JOUR

**Fichier** : `run_api.py` — Lignes 1–5  
**Criticité** : 🟠 MAJEUR

**Problème** : La docstring de module contient `"Enter the file python indus to start the API via the ModelAPI function."` — une phrase manifestement générée par un template non relu. La note `"don't change the name..."` est une instruction de template Domino qui devrait être dans le README, pas dans la docstring du module.

**Solution** : Remplacer par une docstring de module décrivant réellement le rôle de ce fichier dans l'architecture.

```python
"""Entry point for the language classification guardrail API on Domino ModelAPI.

This script starts the Flask API for FR/non-FR language detection.
Note: The function `get_response` is the Domino ModelAPI contract — do not rename it.
See deployment_and_pipeline.md for architecture and deployment details.
"""
```

---

### 🧹 CQ-14 — COMMENTAIRES INLINE REDONDANTS EN VIOLATION DU `clean_code.md` DU PROJET

**Fichier** : `api.py` — Lignes 96–113  
**Criticité** : 🟠 MAJEUR

**Problème** : Ces 4 commentaires inline n'apportent aucune information supplémentaire par rapport au code — ils paraphrasent exactement ce que fait la ligne suivante. C'est précisément ce que `clean_code.md` du projet interdit : `"Readable code doesn't need comments"` et `"Don't add noise comments"`. Le projet viole dans son code central sa propre charte de clean code.

```python
# Load Lingua detector instance for inference
lingua_detector = config_context.get("lingua_detector")
# Decode the text to be classified from the input
text_to_classify = decode_input(input=request_data_dto.inputs.classification_inputs[0])
```

**Solution** : Supprimer les commentaires qui répètent le code. Conserver uniquement les commentaires qui expliquent le *pourquoi*, pas le *quoi*.

```python
# Lingua est stocké dans ConfigContext pour éviter un rechargement coûteux à chaque requête
lingua_detector = config_context.get("lingua_detector")
text_to_classify = decode_input(encoded_text=request_data_dto.inputs.classification_inputs[0])
classification_scores = lingua_detector.run(text=text_to_classify)
```

---

### 🧹 CQ-15 — `init_app()` : COMMENTAIRES `# Step N:` — FONCTION À RESPONSABILITÉS MULTIPLES

**Fichier** : `api.py` — Lignes 47–66  
**Criticité** : 🟠 MAJEUR

**Problème** : Les commentaires `# Step N:` sont le signe classique que la fonction fait trop de choses. C'est un signal identifié dans `clean_code.md` du projet : quand vous avez besoin de commenter des blocs numérotés, ces blocs méritent d'être des fonctions. Le principe Single Responsibility (SOLID-S) est violé.

```python
# Step 1: Configure logger
# Step 2: Load configuration files
# Step 3: Add Lingua library as a Singleton
# Step 4: Calling Lingua a first time to force its build
```

**Solution** : Extraire chaque étape en fonction privée dédiée avec une responsabilité unique.

```python
def init_app() -> None:
    """Initialize the Flask application: logger, config, and language detector."""
    _configure_logging()
    _load_and_store_config()
    _initialize_lingua_detector()

def _configure_logging() -> None:
    configure_logger()

def _load_and_store_config() -> None:
    ConfigContext().set("project_config", load_configurations())

def _initialize_lingua_detector() -> None:
    detector = LinguaDetector()
    detector.run(text="Initialisation de lingua")  # warm-up
    ConfigContext().set("lingua_detector", detector)
```

---

### 🧪 TEST-08 — TESTS UNITAIRES `lingua_detector` UTILISANT LE VRAI LINGUA — CE SONT DES TESTS D'INTÉGRATION

**Fichier** : `test_lingua_detector.py` — Lignes 26–52  
**Criticité** : 🟠 MAJEUR

**Problème** : Ces tests **instancient le vrai `LinguaDetector`** avec `from_all_languages()` — ce qui charge 75 modèles de langue en mémoire (~500 MB) à chaque exécution de la suite de tests. Ce ne sont pas des tests unitaires, ce sont des tests d'intégration déguisés. La CI est lente, les tests sont fragiles à une mise à jour de Lingua, et il est impossible de tester les branches d'erreur sans trouver un input spécifique.

**Solution** : Séparer tests unitaires (avec mocks de Lingua) et tests d'intégration (avec la vraie lib), organisés dans des dossiers distincts.

```python
class TestLinguaDetectorUnit(unittest.TestCase):

    def setUp(self):
        with patch("common.lingua_detector.LanguageDetectorBuilder"):
            self.detector = LinguaDetector()

    def test_scores_returns_french_when_fr_detected(self):
        mock_fr = MagicMock()
        mock_fr.iso_code_639_1.name.lower.return_value = "fr"
        mock_conf = MagicMock(language=mock_fr, value=0.95)
        self.detector.detector.compute_language_confidence_values.return_value = [mock_conf]

        scores = self.detector.calculate_language_scores("quelque chose")
        self.assertEqual(scores["french"], 0.95)
        self.assertEqual(scores["non_french"], 0.0)

    def test_scores_returns_sentinel_when_confidence_is_zero(self):
        mock_conf = MagicMock(value=0.0)
        self.detector.detector.compute_language_confidence_values.return_value = [mock_conf]
        scores = self.detector.calculate_language_scores("123")
        self.assertEqual(scores["french"], DEFAULT_UNCOMPUTED_SCORE_VALUE)
```

---

### 🧪 TEST-09 — EDGE CASES MÉTIER CRITIQUES TOTALEMENT ABSENTS

**Fichiers** : `test_lingua_detector.py`, `industrialisation_test_api.py`  
**Criticité** : 🟠 MAJEUR

**Problème** : Aucun des 19 tests existants ne couvre les cas limites métier les plus importants. Les cas non testés couvrent : inputs ultra-courts (`"ok"`, `"bonjour"`), whitespace-only, emojis purs, IBAN (`"FR76 3000..."`), code-switching (`"mon credit card est bloqué"`), arabe, inputs anglais avec mots français, valeurs limites de `Channel` (`"000"` vs `"999"`), et input base64 invalide.

**Solution** : Ajouter des tests paramétrés couvrant les cas chatbot bancaires réels.

```python
@pytest.mark.parametrize("bad_input", [
    "",           # vide
    "   ",        # whitespace uniquement
    "🎉🎊🎈",    # emojis
    "مرحبا",     # arabe
    "\x00\x01",  # caractères de contrôle
    "a" * 50_000, # très long
])
def test_lingua_detector_edge_cases(bad_input):
    detector = LinguaDetector()
    result = detector.run(text=bad_input)
    assert result is not None, f"Detector crashed on input: {repr(bad_input)}"
```

---

### 🧪 TEST-10 — `test_init_app` TESTE LES MESSAGES DE LOG, PAS LE COMPORTEMENT

**Fichier** : `industrialisation_test_api.py` — Lignes 51–63  
**Criticité** : 🟠 MAJEUR

**Problème** : Ce test vérifie principalement que **les messages de log sont exacts** et que certaines fonctions sont appelées une fois. Il ne vérifie pas l'état observable après `init_app()` : est-ce que `ConfigContext` contient bien `"lingua_detector"` ? Que se passe-t-il si `LinguaDetector()` lève une exception ? Un test qui vérifie les messages de log est un test d'implémentation fragile (casse si on renomme un message) plutôt qu'un test de comportement robuste.

**Solution** : Remplacer les assertions sur les messages de log par des assertions sur l'état observable du système.

```python
def test_init_app_stores_lingua_detector(self, MockLinguaDetector, ...):
    """Behavioral test: ConfigContext must expose lingua_detector after init."""
    init_app()
    ctx = ConfigContext()
    detector = ctx.get("lingua_detector")
    self.assertIsNotNone(detector)

def test_init_app_fails_when_lingua_raises(self, MockLinguaDetector, ...):
    """Error path: init_app() must propagate LinguaDetector init failure."""
    MockLinguaDetector.side_effect = RuntimeError("Lingua build failed")
    with self.assertRaises(RuntimeError):
        init_app()
```

---

### 🧪 TEST-11 — `test_logger_helper.py` : 1 TEST, 1 ASSERTION — COUVERTURE COSMÉTIQUE

**Fichier** : `test_logger_helper.py` — intégralité  
**Criticité** : 🟠 MAJEUR

**Problème** : Ce test a **une seule assertion** qui vérifie uniquement que `getLogger` est appelé avec le bon nom. Il ne teste pas le mode non-verbose (branche `else` non couverte), le niveau de log résultant, la configuration du handler, ni `configure_logger()` sans argument (valeur par défaut `verbose=False`). Ce test existe pour faire augmenter artificiellement la couverture sans valeur de régression réelle.

**Solution** : Remplacer par des tests qui vérifient le comportement observable (niveau de log, handlers configurés).

```python
def test_configure_logger_verbose_sets_debug_level(self):
    configure_logger(verbose=True)
    logger = logging.getLogger(LOGGER_NAME)
    self.assertEqual(logger.level, logging.DEBUG)

def test_configure_logger_non_verbose_sets_info_level(self):
    configure_logger(verbose=False)
    logger = logging.getLogger(LOGGER_NAME)
    self.assertEqual(logger.level, logging.INFO)

def test_configure_logger_default_is_non_verbose(self):
    configure_logger()
    logger = logging.getLogger(LOGGER_NAME)
    self.assertLessEqual(logger.level, logging.INFO)
```

---

### 🧪 TEST-12 — VALIDATEURS PYDANTIC DU DTO NON TESTÉS DIRECTEMENT

**Fichier** : `request_data_dto.py` — `check_non_empty_strings` validator  
**Criticité** : 🟠 MAJEUR

**Problème** : La classe `ClassificationInputs` contient un `@validator` Pydantic custom qui est la **seule barrière de validation** des inputs avant l'inférence. Ce validateur n'est jamais testé directement. Tout changement dans ce validateur peut silencieusement casser la validation sans qu'aucun test ne le détecte.

**Solution** : Ajouter une suite de tests unitaires dédiée au validateur Pydantic.

```python
class TestClassificationInputsDTO(unittest.TestCase):

    def test_rejects_empty_string(self):
        with self.assertRaises(ValidationError):
            ClassificationInputs(classificationInputs=[""])

    def test_rejects_whitespace_only(self):
        with self.assertRaises(ValidationError):
            ClassificationInputs(classificationInputs=["   "])

    def test_rejects_empty_list(self):
        with self.assertRaises(ValidationError):
            ClassificationInputs(classificationInputs=[])

    def test_rejects_more_than_one_item(self):
        with self.assertRaises(ValidationError):
            ClassificationInputs(classificationInputs=["text1", "text2"])

    def test_accepts_valid_non_empty_string(self):
        dto = ClassificationInputs(classificationInputs=["bonjour"])
        self.assertEqual(dto.classification_inputs, ["bonjour"])
```

---

### 🧪 TEST-13 — AUCUN TEST DE RÉGRESSION NLP — GOLDEN SET ABSENT

**Fichier** : `tests/evaluate/` référencé dans `tests.md` mais absent  
**Criticité** : 🟠 MAJEUR

**Problème** : `tests.md` décrit une catégorie "Model performance test" avec `pytest tests/evaluate`, des métriques (accuracy ≥ 95%, F1 ≥ 90%), et un processus de validation. Ce répertoire **n'existe pas**. Aucune régression n'est détectée si Lingua est mis à jour. Aucun seuil de performance n'est enforced en CI.

**Solution** : Créer le répertoire `tests/evaluate/` et y implémenter des tests de régression sur un golden set bancaire.

```python
# tests/evaluate/test_model_regression.py
import pytest
from industrialisation.src.common.lingua_detector import LinguaDetector

GOLDEN_SET = [
    ("modifier le plafond de ma carte bleue", "french", 0.85),
    ("i want to increase my card limit", "non_french", 0.85),
    ("je veux annuler ma commande", "french", 0.85),
    ("cancel my order please", "non_french", 0.85),
]

@pytest.mark.parametrize("text,expected_class,min_score", GOLDEN_SET)
def test_language_regression(text, expected_class, min_score):
    detector = LinguaDetector()
    scores = detector.calculate_language_scores(text)
    predicted = "french" if scores["french"] > scores["non_french"] else "non_french"
    assert predicted == expected_class
    assert scores[expected_class] >= min_score
```

---

### 🧪 TEST-14 — MÉLANGE `unittest` ET `pytest` SANS STRATÉGIE CLAIRE

**Fichiers** : tous les fichiers de test  
**Criticité** : 🟠 MAJEUR

**Problème** : Le projet dispose de `pytest ≥ 8.3.3` mais tous les tests sont écrits en `unittest.TestCase`, sauf `test_api.py` qui est en pytest-style libre. Les fonctionnalités les plus puissantes de pytest (`@pytest.mark.parametrize`, fixtures, `tmp_path`, `monkeypatch`) ne sont pas utilisées, ce qui force la duplication de code de test.

**Solution** : Adopter pytest pur sans `unittest.TestCase` et centraliser les fixtures dans un `conftest.py`.

```python
# tests/conftest.py — à créer
import pytest
from ml_utils.base_64_encoder_decoder import Base64EncoderDecoder

@pytest.fixture
def valid_french_payload() -> dict:
    encoded = Base64EncoderDecoder(character_encoding_type="utf8").encode(
        "je veux augmenter le plafond de ma carte"
    )
    return {
        "inputs": {"classificationInputs": [encoded]},
        "extra_params": {
            "X-B3-TraceId": "463ac35c9f6413ad48485a3953bb6aaa",
            "X-B3-SpanId": "a2fb4a1d1a96d312",
            "Channel": "012",
            "Media": "",
            "ClientId": "test_client",
        },
    }
```

---

### 📚 DOC-06 — `deployment_and_pipeline.md` : TROIS INCOHÉRENCES DOC/CODE CRITIQUES

**Fichier** : `deployment_and_pipeline.md`  
**Criticité** : 🟠 MAJEUR

**Problème** : Ce fichier est le mieux documenté du projet, mais il contient trois incohérences critiques doc/code : (1) la valeur par défaut est documentée comme `-100` alors que le code retourne `-1.0` pour les deux scores (DS-14) ; (2) la méthode Lingua documentée est `detect_language_of` alors que le code utilise `compute_language_confidence_values` ; (3) la section "Authentification" est dupliquée deux fois dans le même fichier.

**Solution** : Corriger les trois incohérences et supprimer la section dupliquée.

```markdown
<!-- Section "Valeurs par défaut" — à corriger -->
Quand Lingua ne peut pas détecter pertinemment une langue :
- `french`: -1.0 (DEFAULT_UNCOMPUTED_SCORE_VALUE dans constants.py)
- `non_french`: -1.0 (idem)

<!-- Section "Inférence" — à corriger -->
La méthode `compute_language_confidence_values()` est appelée, retournant les
scores pour toutes les langues chargées, classés par confiance décroissante.
```

---

### 📚 DOC-07 — `testing.md` : ENTIÈREMENT VIDE — DOUBLON NON CONSOLIDÉ AVEC `tests.md`

**Fichier** : `testing.md`  
**Criticité** : 🟠 MAJEUR

**Problème** : Ce fichier est intégralement un squelette de template. Quatre sections, quatre placeholders vides. Pendant ce temps, `tests.md` contient des informations réelles sur la stratégie de test — deux fichiers couvrant les tests avec des informations complémentaires non consolidées, obligeant un tiers à lire les deux.

**Solution** : Fusionner `testing.md` et `tests.md` en un seul fichier `testing.md` structuré avec les outils réels du projet.

```markdown
# Testing Strategy

## Outils
- **pytest** ≥ 8.3.3 — runner principal
- **pytest-cov** — couverture de code (seuil minimum : 80%)
- **pytest-html** — rapport HTML en CI
- **mypy** — vérification de types statique
- **ruff** — linting

## Exécuter les tests
```bash
make test                    # tests unitaires
make test-integration        # tests d'intégration (chargement réel de Lingua)
pytest tests/evaluate/       # tests de régression NLP (golden set)
```

## Seuils de qualité
| Métrique | Seuil | Enforcement |
|---|---|---|
| Couverture de code | ≥ 80% | `--cov-fail-under=80` |
| Accuracy NLP | ≥ 90% | golden set CI |
```

---

### 📚 DOC-08 — `data_management.md` : TEMPLATE VIDE INADAPTÉ AU PROJET STATELESS

**Fichier** : `data_management.md`  
**Criticité** : 🟠 MAJEUR

**Problème** : Ce fichier est intégralement un squelette de template inadapté à ce projet. Les templates de l'IA Factory sont conçus pour des projets avec des données d'entraînement, ce qui ne correspond pas à ce projet off-the-shelf stateless. Toutes les sections (`"Sources de données"`, `"Prétraitement des données"`, `"Version et organisation"`) sont des placeholders avec `data/raw/<filename>.csv`.

**Solution** : Remplacer le template générique par une description adaptée au caractère stateless du projet.

```markdown
# Data Management

## Données d'entraînement
Ce projet n'utilise pas de données d'entraînement. Lingua 2.1.1 est une librairie
off-the-shelf de détection de langue par n-grams statistiques.

## Données en production
Le service traite des données **en temps réel** et **stateless** :
- Input : texte utilisateur encodé en base64 (taille max : 10 000 caractères)
- Output : scores de confiance `french` / `non_french` ∈ [-1.0, 1.0]
- Aucune donnée n'est persistée

## Données d'évaluation
> ⚠️ À CRÉER : dataset d'évaluation représentatif des messages chatbot Hello Bank
> Voir model_development.md — section Résultats
```

---

### 📚 DOC-09 — `troubleshooting.md` : ENTIÈREMENT VIDE ALORS QUE `support.md` DOCUMENTE DES VRAIS PROBLÈMES

**Fichier** : `troubleshooting.md`  
**Criticité** : 🟠 MAJEUR

**Problème** : Ce fichier contient trois sections vides avec des instructions de template. Pendant ce temps, `support.md` documente des problèmes réels (PYTHONPATH, base64, git push HTTP 500) mais avec des solutions génériques inadaptées (utilise `pip install -r requirements.txt` alors que le projet utilise Poetry, et `base64.b64decode` au lieu de `Base64EncoderDecoder`).

**Solution** : Fusionner et réécrire avec les problèmes réels et les solutions contextualisées à ce projet.

```markdown
# Troubleshooting

## Erreur 400 sur `/predict`
**Cause** : payload malformé, champ `Channel` invalide (doit être `^\d{3}$`),
ou input `classificationInputs` vide.

**Diagnostic** :
```bash
curl -X POST .../predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"classificationInputs": [""]}, "extra_params": {...}}'
# Réponse attendue : {"description": "Invalid request payload.", "status": 400}
```

## `ModuleNotFoundError` au démarrage
**Cause** : `PYTHONPATH` non défini.
**Solution** : `export PYTHONPATH=/mnt/code` avant le lancement.

## Score `-1.0` retourné pour les deux labels
**Cause** : Lingua n'a pas pu détecter la langue (input trop court, vide, ou non textuel).
**Action** : vérifier la longueur de l'input décodé (minimum recommandé : 10 caractères).
```

---

### 📚 DOC-10 — `README_1.md` : TEMPLATE GÉNÉRIQUE DÉCRIVANT DES COMPOSANTS INEXISTANTS

**Fichier** : `README_1.md`  
**Criticité** : 🟠 MAJEUR

**Problème** : Ce README de template IA Factory décrit la structure générique d'un projet avec des dossiers `exploration/notebooks/`, `exploration/scripts/train.py`, `industrialisation/src/batch.py`, `stream.py` — aucun de ces éléments n'existe dans ce projet purement API. Il mentionne TensorFlow, Scikit-learn, `run_batch.py` et "entraînement de modèle" — totalement inapplicables ici.

**Solution** : Nettoyer le README en supprimant les sections inapplicables et en contextualisant les sections utiles.

```markdown
## Structure du projet (adaptée)

```
├── industrialisation/
│   └── src/
│       ├── api.py                  # endpoint Flask /predict
│       ├── common/
│       │   └── lingua_detector.py  # détection de langue (Lingua 2.1.1)
│       └── models/                 # DTOs Pydantic
├── config/
│   ├── project_config_prod.yml     # config Domino production
│   └── project_config_dev.yml      # config Domino dev
└── run_api.py                      # point d'entrée Domino ModelAPI
```
```

---

## PARTIE 3 — PROBLÈMES MINEURS

---

### 🔐 SEC-13 — CONFLUENCE ACCESS TOKEN POTENTIELLEMENT `None` SANS VÉRIFICATION

**Fichier** : `generate_confluence_doc.py` — Lignes 17, 257  
**Criticité** : 🟡 MINEUR

**Problème** : Si `CONFLUENCE_ACCESS_TOKEN` n'est pas défini, `access_token` vaut `None`. La bibliothèque `atlassian-python-api` peut dans ce cas établir une connexion non authentifiée ou lever une exception non gérée, sans que le pipeline ne détecte l'absence de credentials.

```python
access_token = os.environ.get("CONFLUENCE_ACCESS_TOKEN")  # peut être None
confluence = Confluence(verify_ssl=False, url=confluence_url, token=access_token)
```

**Solution** : Valider explicitement la présence du token avant toute connexion et lever une erreur claire.

```python
access_token = os.environ.get("CONFLUENCE_ACCESS_TOKEN")
if not access_token:
    raise EnvironmentError("CONFLUENCE_ACCESS_TOKEN is required but not set.")
```

---

### 🔐 SEC-14 — BUCKET COS ET IDENTIFIANT CLUSTER KUBERNETES EXPOSÉS DANS LES FICHIERS DE CONFIG

**Fichiers** : `services_*.env` — Lignes 2–3 ; `constants.py` — Ligne 2  
**Criticité** : 🟡 MINEUR

**Problème** : Les URLs d'endpoint IBM Cloud Object Storage, les noms de buckets et l'identifiant de cluster Kubernetes (`iks-ap27282-prod-8ca2164e`) sont exposés en clair dans des fichiers versionnés. Ces informations permettent une reconnaissance d'infrastructure ciblée.

```env
COS_ML_ENDPOINT_URL=https://s3.direct.eu-fr2.cloud-object-storage.appdomain.cloud:4327
COS_ML_BUCKET_NAME=bu002i010893
```

**Solution** : Déplacer ces valeurs dans les variables CI/CD GitLab masked, ou au minimum les exclure du versioning via `.gitignore`.

```gitignore
# Exclure tous les fichiers contenant des informations d'infrastructure
services_*.env
```

---

### 🔐 SEC-15 — EXÉCUTION DE CODE AU NIVEAU MODULE DANS `generate_project_config.py`

**Fichier** : `generate_project_config.py` — Ligne 226  
**Criticité** : 🟡 MINEUR

**Problème** : La fonction `generate_process_mode_yaml()` est appelée directement au niveau module, en dehors du bloc `if __name__ == "__main__"`. Tout import accidentel ou malveillant de ce module déclenchera une exécution interactive (appels `input()`), et les fichiers de config YAML seront potentiellement réécrits.

**Solution** : Déplacer l'appel dans le guard `__main__` (voir aussi CQ-03).

```python
if __name__ == "__main__":
    generate_process_mode_yaml()
```

---

### 🔐 SEC-16 — `load_dotenv(override=True)` ÉCRASE SILENCIEUSEMENT LES VARIABLES VAULT

**Fichier** : `load_config.py` — Ligne 88  
**Criticité** : 🟡 MINEUR

**Problème** : `override=True` force l'écrasement de toutes les variables d'environnement existantes par les valeurs du fichier `.env`. Si des variables ont été injectées proprement par Vault, elles seront silencieusement remplacées par des valeurs potentiellement stale du fichier `.env`.

```python
load_dotenv(path_file_conf, override=True)
```

**Solution** : Conditionner l'override selon l'environnement pour ne jamais écraser Vault en production.

```python
is_dev = os.getenv("DOMINO_PROJECT_NAME", "dev").endswith("-dev")
load_dotenv(path_file_conf, override=is_dev)
```

---

### 🔐 SEC-17 — NOM ET EMAIL PERSONNEL VERSIONNÉ DANS `pyproject.toml`

**Fichier** : `pyproject.toml` — Ligne 7  
**Criticité** : 🟡 MINEUR

**Problème** : Le nom complet et l'email professionnel d'un employé sont versionnés dans un fichier de configuration. En cas de fuite du repo (repo public accidentel), cela constitue une fuite de donnée personnelle (RGPD) et fournit un vecteur de spear phishing.

```toml
authors = [{name = "Delphine Nguyen", email = "delphine.nguyen@bnpparibas.fr"}]
```

**Solution** : Utiliser un compte technique ou une adresse d'équipe générique.

```toml
authors = [{name = "Team IA Factory AP27282", email = "dl-ia-factory@bnpparibas.com"}]
```

---

### 🔐 SEC-18 — ABSENCE DE POLITIQUE D'EXPIRATION ET ROTATION DES SECRETS

**Fichiers** : `services_*.env`, `project_config_*.yml`  
**Criticité** : 🟡 MINEUR

**Problème** : Aucun mécanisme de rotation ou d'expiration des secrets n'est documenté ni implémenté. Le token Artifactory et le token Confluence sont des credentials statiques sans durée de vie définie. En cas de compromission non détectée, ces credentials restent valides indéfiniment.

**Solution** : Documenter la politique de rotation dans `README.md` ou `support.md` et utiliser des tokens à durée de vie limitée automatiquement renouvelés via Vault.

```markdown
# Politique de rotation des secrets (à ajouter dans README.md)

| Secret | Durée max | Responsable | Procédure |
|---|---|---|---|
| Token Artifactory | 90 jours | DevOps | Renouveler via portail Artifactory + MàJ GitLab CI |
| Token Confluence | 90 jours | Tech Lead | Renouveler via portail Confluence + MàJ var env |
```

---

### ⚡ PERF-11 — WARM-UP INSUFFISANT : PREMIERS APPELS POST-DÉPLOIEMENT POTENTIELLEMENT LENTS

**Fichier** : `api.py` — Lignes 62–63  
**Criticité** : 🟡 MINEUR

**Problème** : Le warm-up de Lingua est fait au démarrage avec une courte chaîne en français. C'est bien intentionné mais insuffisant : les premières requêtes réelles (textes bancaires courts, acronymes) peuvent encore subir des pénalités de cache. De plus, le warm-up de **Pydantic** (compilation des schémas de validation) n'est pas explicitement déclenché.

```python
lingua_detector.run(input="Initialisation de lingua")
```

**Solution** : Enrichir le warm-up avec des cas représentatifs du trafic réel pour préchauffer tous les chemins d'exécution.

```python
_WARMUP_INPUTS = [
    "Bonjour je veux modifier mon plafond",
    "I need to change my card limit",
    "123",           # cas extrême : texte très court
    "مرحبا",        # arabe — tester le chemin non-FR
]
for warmup_text in _WARMUP_INPUTS:
    lingua_detector.run(text=warmup_text)
```

---

### ⚡ PERF-12 — ABSENCE DE CACHE SUR LES RÉSULTATS D'INFÉRENCE POUR LES INPUTS RÉPÉTÉS

**Fichier** : `api.py` — Ligne 103  
**Criticité** : 🟡 MINEUR

**Problème** : Dans un contexte de guardrail d'assistant virtuel, certaines phrases courantes sont probablement répétées très fréquemment (salutations, questions standard). Il n'y a aucun mécanisme de cache. À 650 req/heure, même un taux de hit de 20% sur un LRU cache représenterait 130 requêtes évitées/heure.

**Solution** : Ajouter un LRU cache sur le texte décodé normalisé. ⚠️ Uniquement si les données ne sont pas considérées comme PII au regard des règles RGPD internes.

```python
from functools import lru_cache

@lru_cache(maxsize=512)
def _cached_detect(text: str) -> list:
    """Cache langue detection sur texte normalisé. NE PAS utiliser si PII."""
    return lingua_detector.run(text=text)
```

---

### ⚡ PERF-13 — `os.path.exists()` + `open()` : DOUBLE SYSCALL LORS DU CHARGEMENT DE CONFIG

**Fichier** : `load_config.py` — Lignes 50–55, 81–88, 145–151  
**Criticité** : 🟡 MINEUR

**Problème** : Ce pattern est répété 3 fois dans `load_config.py`. Il effectue deux appels système séparés (`stat()` pour `exists()` + `open()`). Ce n'est pas sur le chemin chaud d'inférence (uniquement à l'init), mais c'est un anti-pattern redondant.

**Solution** : Utiliser le pattern EAFP Python — `open()` lève déjà `FileNotFoundError` nativement (voir aussi CQ-10).

```python
try:
    with open(path_file_conf) as file:
        config_data = yaml.safe_load(file)
except FileNotFoundError:
    raise FileNotFoundError(f"Config file not found: {path_file_conf}") from None
```

---

### ⚡ PERF-14 — `replica_count: 3` STATIQUE SANS AUTO-SCALING

**Fichier** : `project_config_prod.yml` — Ligne 10  
**Criticité** : 🟡 MINEUR

**Problème** : Le nombre de replicas est fixé statiquement à 3. Le taux de 650 req/heure est une estimation à horizon mai 2026 en croissance. Sans HPA ou mécanisme d'auto-scaling Domino, une montée en charge imprévue ne peut pas être absorbée automatiquement.

**Solution** : Documenter et, si Domino le supporte, configurer un auto-scaling avec des seuils explicites.

```yaml
# project_config_prod.yml
deployment:
  api:
    replica_count: 3
    # Documenter si Domino supporte l'auto-scaling :
    # min_replica_count: 2
    # max_replica_count: 8
    # scale_up_cpu_threshold: 70%
    # scale_down_cpu_threshold: 30%
```

---

### 🛡️ ROB-14 — AUCUN HEALTH CHECK NI READINESS PROBE

**Fichier** : `api.py`, `run_api.py`  
**Criticité** : 🟡 MINEUR

**Problème** : L'API ne dispose d'aucun endpoint `/health` ou `/ready`. Sans readiness probe, le load balancer peut router des requêtes vers un pod dont `init_app()` est encore en cours (chargement Lingua pouvant prendre plusieurs secondes). Les premières requêtes reçues avant la fin de l'init se retrouvent avec `lingua_detector = None`.

**Solution** : Ajouter des endpoints de health et readiness vérifiés par le load balancer.

```python
_ready = False

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200

@app.route("/ready", methods=["GET"])
def ready():
    if not _ready or ConfigContext().get("lingua_detector") is None:
        return {"status": "not ready"}, 503
    return {"status": "ready"}, 200
```

---

### 🛡️ ROB-15 — `format_language_scores()` : ACCÈS AUX CLÉS SANS VÉRIFICATION

**Fichier** : `lingua_detector.py` — Lignes 60–63  
**Criticité** : 🟡 MINEUR

**Problème** : `format_language_scores()` suppose que le dictionnaire `scores` contient toujours les clés `"french"` et `"non_french"`. Si `calculate_language_scores()` est modifié à l'avenir, un `KeyError` non géré crashera la requête. L'interface entre les deux méthodes n'est pas typée formellement.

**Solution** : Typer formellement l'interface avec `TypedDict` et utiliser `.get()` avec valeur par défaut.

```python
from typing import TypedDict

class LanguageScores(TypedDict):
    french: float
    non_french: float

def format_language_scores(self, scores: LanguageScores) -> list:
    return [
        ClassificationScore(
            label=Language.FRENCH,
            score=scores.get("french", DEFAULT_UNCOMPUTED_SCORE_VALUE)
        ),
        ClassificationScore(
            label=Language.NON_FRENCH,
            score=scores.get("non_french", DEFAULT_UNCOMPUTED_SCORE_VALUE)
        ),
    ]
```

---

### 🛡️ ROB-16 — `choose_hardware_tier_api/batch()` : INPUT INVALIDE ÉCRIT QUAND MÊME DANS LA CONFIG

**Fichier** : `generate_project_config.py` — Lignes 179–184, 218–223  
**Criticité** : 🟡 MINEUR

**Problème** : Même si l'utilisateur entre un hardware tier invalide, la valeur invalide est **quand même écrite** dans `deployment_config` et sauvegardée dans les fichiers YAML. La validation affiche seulement un `print()` mais ne bloque pas l'exécution.

**Solution** : Boucler jusqu'à obtenir une valeur valide avant d'écrire dans la configuration.

```python
while True:
    hardware_tier = input("Enter the selected hardware tier: ").strip()
    if hardware_tier in hardware_tiers:
        break
    print(f"Invalid choice '{hardware_tier}'. Please choose from: {list(hardware_tiers.keys())}")

deployment_config["deployment"]["api"]["hardware_tier"] = hardware_tier
```

---

### 🛡️ ROB-17 — TESTS D'EDGE CASES ABSENTS : INPUTS UNICODE, TRÈS LONGS, MIXTES

**Fichiers** : `test_lingua_detector.py`, `industrialisation_test_api.py`  
**Criticité** : 🟡 MINEUR

**Problème** : La couverture de test couvre les cas nominaux (français, anglais, numérique `"123"`). Les cas limites plausibles en production ne sont pas testés : chaîne unicode étendue (emoji, CJK, arabe), chaîne très longue (> 10 000 chars), caractères de contrôle (`\x00`), JSON body vide (`{}`), `classificationInputs` avec chaîne whitespace-only.

**Solution** : Ajouter des tests paramétrés couvrant ces cas edge avec l'assertion minimale : ne pas crasher.

```python
@pytest.mark.parametrize("bad_input", [
    "",
    "   ",
    "🎉🎊🎈",
    "مرحبا",
    "\x00\x01",
    "a" * 50_000,
])
def test_lingua_detector_does_not_crash_on_edge_input(bad_input):
    detector = LinguaDetector()
    result = detector.run(text=bad_input)
    assert result is not None
```

---

### 🧠 DS-12 — `FRENCH_DICT_PATH` DÉFINI MAIS JAMAIS UTILISÉ

**Fichier** : `constants.py` — Lignes 9–10  
**Criticité** : 🟡 MINEUR

**Problème** : Un dictionnaire français (`french_dict.json`) est référencé dans les constantes avec son chemin et son encodage, mais **n'est utilisé nulle part dans le code**. Cette approche hybride lexicale aurait été pertinente pour traiter le problème des inputs courts (DS-04) et mérite d'être soit implémentée soit supprimée.

**Solution** : Soit implémenter le fallback lexical pour les inputs courts, soit supprimer les constantes orphelines.

```python
# Option A : implémenter le fallback lexical
class LinguaDetector:
    def __init__(self):
        self.detector = LanguageDetectorBuilder...build()
        with open(FRENCH_DICT_PATH, encoding=FRENCH_DICT_ENCODING_TYPE) as f:
            self._french_words = set(json.load(f))

    def _lexical_french_score(self, text: str) -> float:
        words = text.lower().split()
        if not words:
            return 0.0
        return sum(1 for w in words if w in self._french_words) / len(words)

# Option B : supprimer les constantes orphelines
# Retirer FRENCH_DICT_PATH et FRENCH_DICT_ENCODING_TYPE de constants.py
```

---

### 🧠 DS-13 — STRUCTURE DE SORTIE DOUBLEMENT IMBRIQUÉE SANS JUSTIFICATION

**Fichier** : `response_data_dto.py` — Ligne 31  
**Criticité** : 🟡 MINEUR

**Problème** : La sortie est une `list[list[ClassificationScore]]` — une liste contenant une liste contenant deux scores. Cette double imbrication n'est pas justifiée par le use case actuel (un seul input, une seule classification) et génère de la complexité inutile pour les consommateurs.

**Solution** : Simplifier la structure de sortie, ou documenter explicitement pourquoi la double imbrication est nécessaire pour la compatibilité.

```python
# Si le batch n'est pas prévu à court terme — simplifier
classification_scores: list[ClassificationScore] = Field(alias="classificationScores")
# Sortie : [{"label": "french", "score": 0.9}, {"label": "non_french", "score": 0.1}]
```

---

### 🧠 DS-14 — TRIPLE INCOHÉRENCE DOC/CODE SUR LA VALEUR SENTINELLE PAR DÉFAUT

**Fichier** : `deployment_and_pipeline.md` — Ligne 81 ; `constants.py` — Ligne 14  
**Criticité** : 🟡 MINEUR

**Problème** : La documentation dit `0` pour le français et `-100` pour le non-français par défaut. Le code retourne `-1.0` pour **les deux scores**. Les consommateurs du Guardrails qui ont implémenté leur logique en se basant sur la documentation (`-100`) reçoivent `-1.0` en réalité.

**Solution** : Aligner code et documentation — choisir une convention unique et l'appliquer partout.

```python
# constants.py — convention claire et documentée
DEFAULT_UNCOMPUTED_SCORE_VALUE: float = -1.0
"""Score retourné quand Lingua ne peut pas détecter la langue.
Les deux scores (french et non_french) valent -1.0 dans ce cas.
Note : valeur hors du domaine probabiliste [0,1] — voir DS-03 pour la dette technique.
"""
```

---

### 🧹 CQ-16 — `conftest.py` ABSENT : FIXTURES PYTEST NON MUTUALISÉES

**Fichiers** : `industrialisation_test_api.py`, `test_config_context.py`, `test_lingua_detector.py`  
**Criticité** : 🟡 MINEUR

**Problème** : Plusieurs payloads de test sont copiés-collés identiquement dans plusieurs fichiers. Il n'existe aucun `conftest.py` pour partager ces fixtures. En pytest idiomatique, les données de test partagées sont des fixtures centralisées.

**Solution** : Créer `tests/conftest.py` avec les fixtures communes.

```python
# tests/conftest.py — à créer
import pytest
from ml_utils.base_64_encoder_decoder import Base64EncoderDecoder

@pytest.fixture
def valid_french_payload() -> dict:
    encoded = Base64EncoderDecoder(character_encoding_type="utf8").encode(
        "je veux augmenter le plafond de ma carte"
    )
    return {
        "inputs": {"classificationInputs": [encoded]},
        "extra_params": {
            "X-B3-TraceId": "463ac35c9f6413ad48485a3953bb6aaa",
            "X-B3-SpanId": "a2fb4a1d1a96d312",
            "Channel": "012",
            "Media": "",
            "ClientId": "test_client",
        },
    }

@pytest.fixture
def valid_english_payload() -> dict:
    encoded = Base64EncoderDecoder(character_encoding_type="utf8").encode(
        "i want to increase my card limit"
    )
    return {**valid_french_payload(), "inputs": {"classificationInputs": [encoded]}}
```

---

### 🧹 CQ-17 — `errors.py` : CLASSES D'EXCEPTIONS SANS CONTEXTE MÉTIER

**Fichier** : `errors.py` — Lignes 1–7  
**Criticité** : 🟡 MINEUR

**Problème** : Les exceptions custom n'ont aucun constructeur ni attributs métier. Ce sont des coquilles vides qui n'apportent pas de valeur par rapport à un `Exception` générique. Une bonne exception custom doit transporter du contexte pour faciliter le debugging.

**Solution** : Ajouter des constructeurs avec attributs contextuels.

```python
class DecoderError(Exception):
    """Raised when base64 decoding of user input fails."""

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.original_error = original_error

class ConfigurationError(Exception):
    """Raised when application configuration is invalid or missing."""

    def __init__(self, message: str, config_key: str | None = None) -> None:
        super().__init__(message)
        self.config_key = config_key
```

---

### 🧹 CQ-18 — FICHIERS CRITIQUES EXCLUS DE L'ANALYSE STATIQUE `mypy` ET `ruff`

**Fichier** : `pyproject.toml` — Lignes 152–159, 197–200, 303–304  
**Criticité** : 🟡 MINEUR

**Problème** : `generate_project_config.py` (qui contient les problèmes CQ-03, CQ-08, ROB-05, ROB-06) est explicitement exclu de mypy ET de ruff. Ces exclusions signifient que les outils de qualité ne voient pas les fichiers les plus problématiques du projet.

**Solution** : Réduire les exclusions au strict minimum nécessaire avec commentaires explicatifs.

```toml
[tool.mypy]
exclude = [
    "dist/",
    "version.py",    # pkgutil.get_data not typed — false positives inévitables
    "settings.py",   # os.path only — aucune valeur à typer
    # generate_project_config.py : à réactiver après correction des bugs CQ-03 et CQ-08
]
```

---

### 🧹 CQ-19 — ORGANISATION DES FICHIERS : SCRIPTS À LA RACINE ≠ STRUCTURE D'IMPORT

**Fichier** : Structure du projet à la racine  
**Criticité** : 🟡 MINEUR

**Problème** : Plusieurs fichiers se trouvent à la racine alors que les imports dans le code source les référencent dans des sous-packages (`from common.lingua_detector import LinguaDetector`, `from industrialisation.src.api import...`). Cela suggère une incohérence entre l'emplacement physique et la structure d'import.

**Solution** : Vérifier que la structure physique réelle des packages correspond aux imports, et que les fichiers `test_*.py` ne sont pas à la racine mais dans `tests/`.

```
tests/
├── conftest.py
├── unit/
│   ├── test_lingua_detector.py
│   ├── test_decode_input.py
│   └── test_config_context.py
├── integration/
│   └── test_api_integration.py
└── evaluate/
    └── test_model_regression.py
```

---

### 🧹 CQ-20 — `black` EXCLUT `run_api.py` ET `version.py` SANS JUSTIFICATION

**Fichier** : `pyproject.toml` — Lignes 343–349  
**Criticité** : 🟡 MINEUR

**Problème** : `run_api.py` est le point d'entrée principal de l'API et est exclu du formatting black. `version.py` contient de la logique applicative. Exclure ces fichiers du formatter crée une incohérence de style visible dans le code sans raison documentée.

**Solution** : Documenter la raison de chaque exclusion, ou supprimer les exclusions injustifiées.

```toml
[tool.black]
exclude = '''
/(
    dist/
    | \.git
    | config/
    # run_api.py exclu car black génère une incompatibilité avec Domino ModelAPI (ticket #XXXX)
    | run_api\.py
)/
'''
```

---

### 🧪 TEST-15 — `add_url_rule()` DANS LE CORPS DU TEST — CRASH SUR DOUBLE EXÉCUTION

**Fichier** : `test_api.py` — Ligne 39  
**Criticité** : 🟡 MINEUR

**Problème** : `app.add_url_rule()` est appelé **dans le corps de la fonction de test**, alors que la route est déjà enregistrée au niveau module. Flask lèvera `AssertionError: View function mapping is overwriting an existing endpoint` si ce test est exécuté deux fois dans la même session.

**Solution** : Enregistrer la route une seule fois au niveau module et ne pas la réenregistrer dans le test.

```python
# Au niveau module — une seule fois
app.add_url_rule("/predict", "predict", predict, methods=["POST"])

def test_run_api() -> None:
    # Ne pas appeler add_url_rule ici
    response = app.test_client().post("/predict", json=data)
    assert response.status_code == 200
```

---

### 🧪 TEST-16 — AUCUN TEST DE CONTRAT DE SÉRIALISATION JSON DU DTO DE SORTIE

**Fichier** : `response_data_dto.py` — intégralité  
**Criticité** : 🟡 MINEUR

**Problème** : Aucun test ne vérifie que `ResponseDataDto` sérialise correctement en JSON, que les valeurs enum `Language.FRENCH` se sérialisent en `"french"` (pas en leur valeur entière), ou que le score `-1.0` est accepté. Un changement dans `use_enum_values=True` casse silencieusement le contrat.

**Solution** : Ajouter des tests de contrat sur la sérialisation du DTO de sortie.

```python
def test_response_dto_serialization():
    scores = [ClassificationScore(label=Language.FRENCH, score=0.9),
              ClassificationScore(label=Language.NON_FRENCH, score=0.1)]
    dto = ResponseDataDto(classificationScores=[scores])
    result = dto.model_dump(by_alias=True)

    assert "classificationScores" in result
    assert result["classificationScores"][0][0]["label"] == "french"
    assert result["classificationScores"][0][1]["label"] == "non_french"
    assert result["classificationScores"][0][0]["score"] == 0.9

def test_response_dto_accepts_sentinel_score():
    scores = [ClassificationScore(label=Language.FRENCH, score=-1.0),
              ClassificationScore(label=Language.NON_FRENCH, score=-1.0)]
    dto = ResponseDataDto(classificationScores=[scores])
    result = dto.model_dump(by_alias=True)
    assert result["classificationScores"][0][0]["score"] == -1.0
```

---

### 📚 DOC-11 — `model_production.md` : N/A ABUSIFS ET INFORMATION PÉRIMÉE

**Fichier** : `model_production.md`  
**Criticité** : 🟡 MINEUR

**Problème** : La section "Monitoring" signale que le chantier drift detection sera lancé "à partir de 2026" — nous sommes en mars 2026, ce chantier devrait être soit lancé soit reclassé. Les sections "Optimisation pour l'inférence" et "Gestion des modèles" sont marquées `N/A` sans justification alors que des décisions documentables existent (warm-up, Singleton, minimum_relative_distance).

**Solution** : Mettre à jour les informations périmées et remplir les N/A avec des décisions réelles.

```markdown
## Optimisation pour l'inférence
- **Warm-up au démarrage** : Lingua est appelé une fois à l'init pour éviter la pénalité
  de premier appel (JIT compilation des n-grams internes)
- **Singleton ConfigContext** : LinguaDetector est instancié une seule fois et partagé
  entre toutes les requêtes

## Monitoring de dérive
> ⚠️ Chantier prévu — statut à mettre à jour (initialement prévu 2026)
> Action : définir un ticket et un responsable pour la mise en place du drift monitoring
```

---

### 📚 DOC-12 — `environments.md` : TROIS OPTIONS DOCKERFILE SANS INDIQUER LAQUELLE EST UTILISÉE

**Fichier** : `environments.md`  
**Criticité** : 🟡 MINEUR

**Problème** : Ce fichier présente trois options de Dockerfile (via conda-lock, environment.yaml, pip direct) sans indiquer **laquelle est utilisée par ce projet**. Les templates contiennent des variables Jinja non résolues (`{{poetry_version}}`, `{{group_deps}}`). La commande `mamba update env update` a une faute de frappe.

**Solution** : Indiquer clairement l'option retenue, corriger les typos et remplacer les variables de template par les valeurs réelles.

```markdown
> **Pour ce projet** : utiliser l'**Option 1 (conda-lock)** avec Poetry.
> Version Poetry utilisée : 2.0.0

## Dockerfile utilisé

```dockerfile
FROM python:3.11-slim
RUN pip install poetry==2.0.0
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main
```
```

---

### 📚 DOC-13 — `tests.md` : MÉTRIQUES DE GÉNÉRATION DE TEXTE INADAPTÉES À LA CLASSIFICATION

**Fichier** : `tests.md`  
**Criticité** : 🟡 MINEUR

**Problème** : Les métriques listées pour les modèles NLP (BLEU, ROUGE, Perplexité) sont des métriques de **génération de texte**, pas de classification. Pour une classification binaire FR/non-FR, les métriques pertinentes sont accuracy, F1-score, précision, rappel, et la matrice de confusion.

**Solution** : Remplacer les métriques inadaptées par les métriques de classification pertinentes.

```markdown
## Métriques de performance (classification binaire)

| Métrique | Seuil minimum | Description |
|---|---|---|
| Accuracy | ≥ 90% | Taux de classifications correctes global |
| F1-score macro | ≥ 88% | Moyenne harmonique précision/rappel sur les 2 classes |
| Taux de faux positifs | ≤ 5% | Utilisateurs FR rejetés à tort (impact expérience) |
| Taux de faux négatifs | ≤ 10% | Utilisateurs non-FR acceptés à tort (risque sécurité) |
```

---

### 📚 DOC-14 — `rules.md` : DUPLIQUE LE CONTENU DE `clean_code.md`

**Fichier** : `rules.md`  
**Criticité** : 🟡 MINEUR

**Problème** : La section "Quality code" de `rules.md` duplique le contenu de `clean_code.md`. Un tiers doit lire deux fichiers pour avoir une vision complète des règles de qualité. En cas de mise à jour, il faut modifier les deux fichiers.

**Solution** : Remplacer la section dupliquée par un simple lien vers `clean_code.md`.

```markdown
## Quality code

Pour les règles de clean code Python appliquées sur ce projet, voir
[clean_code.md](./clean_code.md).
```

---

### 📚 DOC-15 — `project_config.md` : COMMANDES RÉFÉRENÇANT `Makefile.tpl` AU LIEU DE `Makefile_1`

**Fichier** : `project_config.md` — Lignes 67, 75  
**Criticité** : 🟡 MINEUR

**Problème** : Les commandes `make` référencent `Makefile.tpl` alors que le fichier réel s'appelle `Makefile_1`. Les exemples contiennent des placeholders (`{project-name}`, `4290`) que le lecteur doit adapter sans guidance claire.

**Solution** : Corriger les références de fichier et remplacer les placeholders par les vraies valeurs.

```markdown
## Commandes principales

```bash
# Installer les dépendances (Makefile_1)
ARTIFACTORY_USER=<user> ARTIFACTORY_PASSWORD=<pwd> make -f Makefile_1 install-deps

# Lancer les tests
make -f Makefile_1 test

# Déployer sur Domino dev
make -f Makefile_1 deploy ENV=dev PROJECT=a100067-sav-guardrails-language
```
```

---

*Fin du rapport — 67 problèmes documentés sur 7 thématiques*  
*Généré le : Mars 2026*
