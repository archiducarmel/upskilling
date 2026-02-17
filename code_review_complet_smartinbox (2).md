# Rapport de Code Review -- SmartInbox Outlook

**Projet :** SmartInbox Outlook -- Suggestion de reponses email par IA pour conseillers bancaires
**Date :** 17 fevrier 2026
**Nombre de problemes identifies :** 56
**Fichiers analyses :** ~50 fichiers sources, configuration, documentation et tests

---

## Executive Summary

Ce rapport consolide l'analyse approfondie du code source du projet SmartInbox Outlook, un service de suggestion de reponses email base sur un pipeline embedding/reranking (BGE-M3 + BGE-Reranker-v2-M3) deploye sur Domino pour des conseillers bancaires.

L'audit revele **56 problemes** repartis en **17 critiques**, **21 majeurs** et **18 mineurs**, couvrant six axes : securite, robustesse, performance, data science, qualite de code et documentation.

### Risques prioritaires

**1. Securite -- Risque de compromission totale du service**

La deserialisation pickle non securisee (SEC-01) constitue une vulnerabilite RCE (Remote Code Execution) qui, combinee avec des credentials hardcodees en clair (SEC-04), permet une chaine d'attaque menant a l'exfiltration de cles API, de credentials Vault et de donnees clients bancaires. La fuite de contenus email dans les exceptions (SEC-10) constitue par ailleurs une violation RGPD.

**2. Robustesse -- Crash systematique sur requetes hors domaine**

Les scores cosine dans [-1, 1] injectes dans des contraintes Pydantic [0, 1] provoquent un `ValidationError` sur toute requete hors domaine (ROB-01). Les doublons dans les modeles par defaut (ROB-12), la metrique d'observabilite toujours egale a 2 (ROB-05), et le `response.json()` non protege (ROB-08) degradent la fiabilite du service.

**3. Performance -- Latence et scalabilite insuffisantes**

La matrice d'embeddings est reconstruite a chaque requete (PERF-01), les sessions HTTP ne sont pas reutilisees (PERF-06), et le deploiement est limite a un seul replica synchrone (PERF-16) plafonnant le throughput a ~2 req/s. Le retry est configure a une seule tentative sans backoff (PERF-07).

**4. Data Science -- Pipeline de suggestion non valide**

Aucun framework d'evaluation n'existe (DS-19) : les hyperparametres (threshold=0.1, top_k=15) sont des choix arbitraires jamais valides. Le texte email est envoye tel quel au modele d'embedding sans nettoyage (DS-03), avec un decodage Latin-1 au lieu d'UTF-8 (DS-04). Le seuil de similarite a 0.1 sur cosine brut est non interpretable (DS-10).

**5. Qualite de code et documentation**

Le singleton mutable `ConfigContext` (CQ-06), trois mecanismes de configuration coexistants (CQ-14), et un `__init__.py` avec side-effects et bug logique (CQ-13) temoignent d'un refactoring inacheve a partir d'un template de projet. La documentation est majoritairement constituee de templates vierges ou de residus d'un autre projet (iaflow/CR-AUTO).

### Recommandations de priorisation

| Priorite | Actions | Effort estime |
|----------|---------|---------------|
| P0 -- Immediat | Remplacer pickle par JSON (SEC-01), supprimer credentials hardcodees (SEC-04), corriger crash Pydantic (ROB-01), supprimer fuite RGPD (SEC-10) | 2-3 jours |
| P1 -- Sprint en cours | Corriger doublons (ROB-12), proteger response.json() (ROB-08), activer scale_score (DS-10), decoder en UTF-8 (DS-04), valider API key non-None (SEC-05) | 3-5 jours |
| P2 -- Sprint suivant | Cacher matrice embeddings (PERF-01), connection pooling (PERF-06), retry avec backoff (PERF-07), nettoyage email (DS-03), augmenter replicas (PERF-16) | 1-2 semaines |
| P3 -- Backlog | Evaluation framework (DS-19), unifier configuration (CQ-14), nettoyer documentation, supprimer code mort | 2-4 semaines |

---

## Table recapitulative

| ID | ID Original | Severite | Thematique | Titre | Fichier(s) principal(aux) |
|----|-------------|----------|------------|-------|---------------------------|
| P-01 | SEC-01 | CRITIQUE | Securite | Deserialisation pickle non securisee -- RCE | `io_utils.py` L57 |
| P-02 | SEC-04 | CRITIQUE | Securite | Credentials hardcodees en clair `usr/usr` | `main.py` L9-11 |
| P-03 | ROB-01 | CRITIQUE | Robustesse | Scores cosine [-1,1] vs contraintes Pydantic [0,1] -- crash | `suggestion_engine.py` L184, `selected_candidate.py` L15 |
| P-04 | ROB-05 | CRITIQUE | Robustesse | `len(ranked_results)` compte les cles du dict -- metrique toujours a 2 | `suggestion_engine.py` L212 |
| P-05 | ROB-12 | CRITIQUE | Robustesse | `_extend_with_default_models` injecte des doublons | `suggestion_engine.py` L120-130 |
| P-06 | DS-03 | CRITIQUE | Data Science | Aucun nettoyage du texte email -- bruit HTML, signatures | `email_suggestion_request.py` L97-115 |
| P-07 | DS-10 | CRITIQUE | Data Science | `scale_score=False` -- seuil 0.1 non interpretable | `suggestion_engine.py` L184-190 |
| P-08 | DS-19 | CRITIQUE | Data Science | Aucun framework d'evaluation -- pertinence non mesurable | `model_development.md`, `data_management.md` |
| P-09 | PERF-01 | CRITIQUE | Performance | Matrice d'embeddings reconstruite a chaque requete | `question_store.py` L336 |
| P-10 | PERF-06 | CRITIQUE | Performance | Session HTTP creee/detruite a chaque appel LLM | `llm_service.py` L69, `session_manager.py` L70-89 |
| P-11 | PERF-16 | CRITIQUE | Performance | `replica_count: 1` -- aucune HA, throughput plafonne | `project_config_prod.yml` L1-10 |
| P-12 | CQ-06 | CRITIQUE | Qualite de code | Singleton `ConfigContext` mutable -- Service Locator anti-pattern | `config_context.py` |
| P-13 | CQ-13 | CRITIQUE | Qualite de code | `__init__.py` execute du code avec side-effects + bug logique | `__init__.py` |
| P-14 | DOC-01 | CRITIQUE | Documentation | `quickstart.rst` decrit le projet iaflow -- hors sujet | `quickstart.rst` |
| P-15 | DOC-02 | CRITIQUE | Documentation | `design_doc_index.rst` est un residu iaflow vide | `design_doc_index.rst` |
| P-16 | DOC-05 | CRITIQUE | Documentation | `data_management.md` est un template vierge | `data_management.md` |
| P-17 | DOC-06 | CRITIQUE | Documentation | `model_development.md` est un template vierge | `model_development.md` |
| P-18 | SEC-03 | MAJEUR | Securite | f-strings dans les appels de logging (14 occurrences) | 8 fichiers |
| P-19 | SEC-05 | MAJEUR | Securite | Cle API LLMaaS peut etre `None` -- auth desactivee | `llm_settings.py` L61-65 |
| P-20 | SEC-10 | MAJEUR | Securite | `Base64DecodingError` stocke le contenu email (RGPD) | `validation_exception.py` L19-39 |
| P-21 | DS-04 | MAJEUR | Data Science | Decodage Base64 en Latin-1 au lieu d'UTF-8 | `email_suggestion_request.py` L63 |
| P-22 | DS-05 | MAJEUR | Data Science | Concatenation `"{objet} {corps}"` sans structuration semantique | `email_suggestion_request.py` L115 |
| P-23 | DS-08 | MAJEUR | Data Science | `email_sequence_index` non exploite -- pas d'adaptation 1er contact vs relance | `email_suggestion_request.py` L26 |
| P-24 | ROB-02 | MAJEUR | Robustesse | `IndexError` sur reponse reranker avec index hors bornes | `llm_reranker.py` L153-154 |
| P-25 | ROB-08 | MAJEUR | Robustesse | `response.json()` non protege -- crash si non-JSON | `llm_service.py` L73-80 |
| P-26 | ROB-22 | MAJEUR | Robustesse | `_l2_normalise` modifie la matrice in-place -- bug dormant | `question_store.py` L368-371 |
| P-27 | PERF-02 | MAJEUR | Performance | Normalisation L2 recalculee sur tous les documents a chaque requete | `question_store.py` L361-371 |
| P-28 | PERF-07 | MAJEUR | Performance | `total_retry: 1` = zero retry -- premier timeout = echec definitif | `app_config.yml` L6-10 |
| P-29 | PERF-10 | MAJEUR | Performance | `TokenAuth()` et URL reconstruits a chaque appel LLM | `llm_settings.py` L83-93 |
| P-30 | CQ-02 | MAJEUR | Qualite de code | Typo persistante `emdedding` -- 7 occurrences | `wide_event.py` L55-57, `llm_embedder.py` L73-76 |
| P-31 | CQ-14 | MAJEUR | Qualite de code | Trois mecanismes de chargement de configuration coexistent | `load_config.py`, `load_configuration.py`, `settings.py` |
| P-32 | CQ-15 | MAJEUR | Qualite de code | `request_llm_embedding.py` et `request_llm_reranker.py` -- code duplique inutilise | `request_llm_embedding.py`, `request_llm_reranker.py` |
| P-33 | DOC-07 | MAJEUR | Documentation | `logging.md` affiche des noms de modeles OpenAI au lieu de BGE | `logging.md` L180-185 |
| P-34 | DOC-08 | MAJEUR | Documentation | `logging.md` propage la typo `emdedding` du code | `logging.md` L143-148 |
| P-35 | DOC-09 | MAJEUR | Documentation | `troubleshooting.md` reference des variables d'env inexistantes | `troubleshooting.md` L83-93 |
| P-36 | DOC-10 | MAJEUR | Documentation | Seuil de couverture incoherent : 80% vs 60% | `testing.md` L29, `README.md` L200 |
| P-37 | DOC-12 | MAJEUR | Documentation | `wide_event.py` emet "Summarization" -- repris dans la doc | `wide_event.py` L202, `deployment_and_pipeline.md` |
| P-38 | DOC-25 | MAJEUR | Documentation | Pas de documentation de la construction de la knowledge base | `build_question_store.py`, `build_response_model_store.py` |
| P-39 | DS-07 | MINEUR | Data Science | Metadonnees metier disponibles mais non exploitees | `extra_parameters.py` L10-12 |
| P-40 | DS-09 | MINEUR | Data Science | Aucune detection de langue | `suggestion_engine.py` |
| P-41 | DS-18 | MINEUR | Data Science | Aucun signal de confiance global dans la reponse API | `email_suggestion_result.py` |
| P-42 | DS-20 | MINEUR | Data Science | `train.py` est un boilerplate Iris/XGBoost -- code mort | `train.py` |
| P-43 | ROB-23 | MINEUR | Robustesse | `_expit()` -- overflow numpy silencieux sur valeurs extremes | `question_store.py` L36-45 |
| P-44 | PERF-12 | MINEUR | Performance | Fallback threshold envoie TOUS les resultats au reranker | `suggestion_engine.py` L190-195 |
| P-45 | PERF-14 | MINEUR | Performance | Aucun cache d'embedding pour les requetes repetees | `suggestion_engine.py` L181 |
| P-46 | PERF-20 | MINEUR | Performance | `float64` par defaut pour les embeddings -- double memoire | `question_store.py` L336 |
| P-47 | CQ-01 | MINEUR | Qualite de code | Membres d'enum incoherents -- mix UPPER_CASE / lower_case | `enums.py` |
| P-48 | CQ-03 | MINEUR | Qualite de code | Descriptions de Fields inversees dans `LLMSettings` | `llm_settings.py` L35-38 |
| P-49 | CQ-04 | MINEUR | Qualite de code | Nommage variable `question` pour une liste de documents | `candidate_factory.py` L98-99 |
| P-50 | CQ-05 | MINEUR | Qualite de code | Incoherence `_logger` vs `logger` | Tout le projet |
| P-51 | CQ-07 | MINEUR | Qualite de code | `abort(400)` dans le decorateur `@wide_event` -- melange de responsabilites | `utils_wide_event.py` L86-94 |
| P-52 | CQ-11 | MINEUR | Qualite de code | `self.storage.keys()` au lieu de `self.storage` | `question_store.py` L206, 214, 230 |
| P-53 | CQ-12 | MINEUR | Qualite de code | Pattern `isinstance` en cascade sans branche par defaut | `error_handler.py` L81-88 |
| P-54 | CQ-24 | MINEUR | Qualite de code | `project.description = "Template IA project"` | `pyproject.toml` L4 |
| P-55 | DOC-13 | MINEUR | Documentation | `llm_settings.py` docstring dit "summarization" | `llm_settings.py` L29 |
| P-56 | DOC-21 | MINEUR | Documentation | Section "Support" vide dans `troubleshooting.md` | `troubleshooting.md` L184-187 |

### Synthese par severite et thematique

| Thematique | Critique | Majeur | Mineur | Total |
|------------|----------|--------|--------|-------|
| Securite | 2 | 3 | 0 | 5 |
| Robustesse | 3 | 3 | 1 | 7 |
| Data Science | 3 | 3 | 4 | 10 |
| Performance | 3 | 3 | 3 | 9 |
| Qualite de code | 2 | 3 | 8 | 13 |
| Documentation | 4 | 6 | 2 | 12 |
| **Total** | **17** | **21** | **18** | **56** |

---
---

# PARTIE 1 -- PROBLEMES CRITIQUES

---

## 1.1 Securite -- Critiques

---

### P-01 (SEC-01) -- CRITIQUE : Deserialisation pickle non securisee -- execution de code arbitraire (Remote Code Execution)

**Fichier :** `io_utils.py` -- fonction `load_pickle_file` -- ligne 57

**Code incrimine :**

```python
def load_pickle_file(pickle_path: Path) -> Any:
    try:
        with pickle_path.open("rb") as file:
            return pickle.load(file)  # <-- ARBITRARY CODE EXECUTION
    except (pickle.UnpicklingError, EOFError) as pickle_error:
        raise ValueError(f"Failed to deserialize pickle file: {pickle_path}") from pickle_error
```

**Aussi concerne :**
- `question_store.py` L168 : `data = load_pickle_file(pickle_path)` dans `InMemoryQuestionStore.load_from_disk()`
- `response_model_store.py` L61 : `data = load_pickle_file(pickle_path)` dans `ResponseModelStore.load_from_disk()`
- `suggestion_factory.py` L51-55 : appels indirects lors du `build_suggestion_engine()`

**Probleme :** `pickle.load()` execute du code Python arbitraire embarque dans le fichier pickle. Un attaquant qui parvient a remplacer un fichier `.pickle` dans `industrialisation/knowledge_base/` (via une compromission de la CI/CD, un acces au volume Domino, ...) obtient une **execution de code a distance (RCE)** avec les privileges du service API. Une vulnerabilite recente dans Llama stack de META : https://www.lemondeinformatique.fr/actualites/lire-une-faille-critique-empoisonne-llama-de-meta-95889.html

**Impact :** Compromission totale du serveur : exfiltration de la cle API LLMaaS, pivot reseau vers le vault, acces aux credentials DHV2, acces aux donnees clients.

**Solution :** Remplacer pickle par un format sur. Les stores ne contiennent que des dictionnaires et des listes de floats -- aucun besoin de serialisation d'objets arbitraires :

```python
# io_utils.py -- remplacement sur
import json
import hashlib
from pathlib import Path

def load_store_file(store_path: Path, expected_sha256: str | None = None) -> dict:
    """Load a JSON store file with optional integrity check."""
    raw = store_path.read_bytes()

    return json.loads(raw)
```

Si le format pickle doit etre conserve (performance/compatibilite), utiliser `RestrictedUnpickler` :

CODE REPRIS DE CE MODULE : https://github.com/ershov/restrictedpickle

```python
import pickle
import io

class SafeUnpickler(pickle.Unpickler):
    """Restrict unpickling to safe built-in types only."""
    SAFE_CLASSES = {
        ("builtins", "dict"),
        ("builtins", "list"),
        ("builtins", "set"),
        ("builtins", "str"),
        ("builtins", "int"),
        ("builtins", "float"),
        ("builtins", "bool"),
        ("builtins", "tuple"),
        ("builtins", "bytes"),
    }

    def find_class(self, module: str, name: str) -> type:
        if (module, name) not in self.SAFE_CLASSES:
            raise pickle.UnpicklingError(
                f"Forbidden class: {module}.{name}"
            )
        return super().find_class(module, name)

def safe_load_pickle(path: Path) -> dict:
    with path.open("rb") as f:
        return SafeUnpickler(f).load()
```

---

### P-02 (SEC-04) -- CRITIQUE : Credentials hardcodees en clair dans le code source d'exploration

**Fichier :** `main.py` -- lignes 9-11

**Code incrimine :**

```python
# Dummy credentials (in production, use hashed passwords and secure storage)
USER_CREDENTIALS = {
    os.environ.get("APP_USERNAME", "usr"): os.environ.get("APP_PASSWORD", "usr"),
}
```

```python
# ligne 29 -- comparaison en clair
if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
    st.session_state.authenticated = True
```

**Probleme :** Deux vulnerabilites cumulees :

1. **Credentials par defaut `usr/usr`** : si les variables d'environnement `APP_USERNAME` et `APP_PASSWORD` ne sont pas definies (oubli de configuration), l'application demarre avec des credentials triviales. Le commentaire lui-meme reconnait le probleme (« in production, use hashed passwords ») mais aucune mitigation n'a ete implementee.
2. **Comparaison de mots de passe en clair** : `USER_CREDENTIALS[username] == password` effectue une comparaison string standard, vulnerable aux timing attacks et stockant le mot de passe en memoire en clair.

**Impact :** Acces non autorise a l'interface d'upload de fichiers, qui permet l'ecriture de fichiers arbitraires sur le volume Domino (cf. SEC-02). Chaine d'attaque : credentials par defaut -> upload malveillant -> compromission.

**Classification OWASP :** A07:2021 -- Identification and Authentication Failures

**Solution :** Exiger les variables d'environnement (fail-fast) et utiliser le hachage :

```python
import os
import hashlib
import hmac

_username = os.environ.get("APP_USERNAME")
_password_hash = os.environ.get("APP_PASSWORD_HASH")

if not _username or not _password_hash:
    raise RuntimeError(
        "APP_USERNAME and APP_PASSWORD_HASH must be set. "
        "Generate hash: python -c \"import hashlib; "
        "print(hashlib.sha256(b'<password>').hexdigest())\""
    )

def verify_credentials(username: str, password: str) -> bool:
    """Verify credentials with constant-time comparison."""
    if username != _username:
        return False
    candidate = hashlib.sha256(password.encode()).hexdigest()
    return hmac.compare_digest(candidate, _password_hash)
```

---

## 1.2 Robustesse -- Critiques

---

### P-03 (ROB-01) -- CRITIQUE : Scores cosine dans [-1, 1] injectes dans des contraintes Pydantic [0, 1] -- crash `ValidationError`

**Fichier :** `suggestion_engine.py` -- ligne 184

**Code incrimine :**

```python
similar_questions = self.question_store.search_similar(
    top_k=self.settings.similarity_top_k * 2,
    query_embeddings=embedding_result["embedding"],
    # scale_score NON passe --> defaut = False
)
```

**Fichier :** `question_store.py` -- `search_similar` -- ligne 289

```python
doc_fields["score"] = score   # <-- score cosine brut dans [-1, 1]
```

**Fichier :** `candidate_factory.py` -- `documents_to_selection_candidate` -- lignes 56-61

```python
activation_data = [
    ActivationData(
        reference_question_id=int(question.id),
        version_question=question.get_metadata("version_question"),
        similarity_score=question.score,   # <-- score cosine brut injecte
    )
    for question in documents
]
```

**Fichier :** `selected_candidate.py` -- lignes 15-20

```python
similarity_score: float = Field(
    ge=0.0,       # <-- CRASH si score < 0.0
    le=1.0,       # <-- CRASH si score > 1.0
    serialization_alias="similarityScore",
)
```

**Probleme :** Le pipeline utilise la similarite cosine **non mise a l'echelle** (`scale_score=False` par defaut). La similarite cosine retourne des valeurs dans l'intervalle **[-1, 1]**. Or :

Le filtre `question.score >= self.settings.threshold` (seuil 0.1) empeche les negatifs d'atteindre ce point **sauf dans le fallback** ligne 194-195 :

```python
if not filtered_questions:
    filtered_questions = similar_questions  # <-- INCLUT les scores negatifs
```

**Impact :** Crash systematique de l'API sur toute requete hors domaine.

**Solution :** Clamper les scores ou activer `scale_score=True` :

```python
# Option 1 : Clamper les scores apres calcul (simple, defensif)
similarity_score=max(0.0, min(1.0, question.score))

# Option 2 : Activer le scaling dans search_similar (coherent)
similar_questions = self.question_store.search_similar(
    top_k=self.settings.similarity_top_k * 2,
    query_embeddings=embedding_result["embedding"],
    scale_score=True,   # <-- cosine --> (score + 1) / 2  --> [0, 1]
)
```

---

### P-04 (ROB-05) -- CRITIQUE : `len(ranked_results)` compte les cles du dict, pas les documents -- metrique toujours a 2

**Fichier :** `suggestion_engine.py` -- lignes 208-215

**Code incrimine :**

```python
enrich_event(
    **{
        "similar_questions": len(similar_questions),
        "filtered_questions": len(filtered_questions),
        "unranked_response_models": len(documents_to_rank),
        "ranked_response_models": len(ranked_results),  # <-- BUG
    }
)
```

**Probleme :** `ranked_results` est un `dict` retourne par `rerank_documents` :

```python
{"documents": [...], "meta": {...}}
```

`len(ranked_results)` retourne **toujours 2** (le nombre de cles du dict), pas le nombre de documents reranked. La metrique `ranked_response_models` dans le WideEvent est donc **systematiquement fausse** depuis le premier jour.

**Impact :** Metrique d'observabilite corrompue. Impossible de detecter les anomalies de reranking (ex : le LLMaaS retourne 0 resultats --> la metrique affiche quand meme 2).

**Solution :**

```python
"ranked_response_models": len(ranked_results["documents"]),
```

---

### P-05 (ROB-12) -- CRITIQUE : `_extend_with_default_models` injecte des doublons -- meme ID reranked + default

**Fichier :** `suggestion_engine.py` -- `_extend_with_default_models` -- lignes 120-130

**Code incrimine :**

```python
default_ids = self.settings.default_model_ids   # ["1", "2"]

final_documents = ranked_documents[:4]
if len(final_documents) <= 3:
    final_documents.extend(
        [Document(id=idx, score=0.0) for idx in self.settings.default_model_ids]
    )
else:
    final_documents.append(
        Document(id=self.settings.default_model_ids[0], score=0.0)
    )
```

**Probleme :** Les IDs par defaut (`"1"`, `"2"`) sont toujours ajoutes, **meme si l'un d'eux est deja dans `ranked_documents`**. Si le response model ID `"1"` a ete reranked avec un score de 0.85, il apparaitra deux fois dans la liste finale :
- Une fois avec `score=0.85` (resultat du reranker)
- Une fois avec `score=0.0` (ajoute comme defaut)

**Impact :** Doublons dans la reponse API. Le client Outlook affiche le meme modele de reponse deux fois au conseiller.

**Solution :** Verifier la presence avant d'ajouter :

```python
existing_ids = {doc.id for doc in final_documents}

for default_id in self.settings.default_model_ids:
    if default_id not in existing_ids:
        final_documents.append(Document(id=default_id, score=0.0))
        existing_ids.add(default_id)
        if len(final_documents) >= 5:
            break
```

---

## 1.3 Data Science -- Critiques

---

### P-06 (DS-03) -- CRITIQUE : Aucun nettoyage du texte email -- bruit HTML, signatures, chaines de reponse

**Fichier :** `email_suggestion_request.py` -- propriete `content` -- lignes 97-115

**Code incrimine :**

```python
@property
def content(self) -> str:
    if not self.email_object or self.email_object.strip() == "":
        return self.email_content
    if not self.email_content or self.email_content.strip() == "":
        return self.email_object
    return f"{self.email_object} {self.email_content}"
```

**Fichier :** `suggestion_engine.py` -- ligne 181

```python
embedding_result = self.embedder.embed_text(text=query.strip())
```

**Probleme :** Le contenu de l'email est envoye **tel quel** au modele d'embedding, apres un simple `strip()`. Aucun nettoyage n'est effectue. Dans un contexte bancaire Outlook, le contenu brut contient typiquement :

1. **Balises HTML** : `<div>`, `<br>`, `<span style="...">`, `&nbsp;`, tables HTML de signatures
2. **Signatures email** : nom du conseiller, coordonnees, mentions legales, logos en base64
3. **Chaines de reponse** : historique complet des echanges precedents (`>`, `De: ...`, `Envoye: ...`)
4. **Disclaimers legaux** : mentions de confidentialite (souvent en anglais), 5-10 lignes standard
5. **Caracteres de controle** : `\r\n`, `\t`, BOM Unicode
6. **Citations Outlook** : `-----Message d'origine-----` suivi de l'historique complet

BGE-M3 a une fenetre de contexte de **8192 tokens**. Un email bancaire avec historique de reponse peut facilement atteindre 3000-5000 tokens de bruit (signatures + chaine) contre 100-500 tokens de signal (le message du client). Le modele d'embedding doit donc extraire le signal pertinent d'un texte compose a **80-90% de bruit**.

**Solution :** Implementer un pipeline de nettoyage avant l'embedding (suppression HTML, extraction du dernier message, suppression des signatures).

---

### P-07 (DS-10) -- CRITIQUE : `scale_score=False` --> scores cosine bruts dans [-1, 1] --> seuil 0.1 non interpretable

**Fichier :** `suggestion_engine.py` -- lignes 184-190

**Code incrimine :**

```python
similar_questions = self.question_store.search_similar(
    top_k=self.settings.similarity_top_k * 2,
    query_embeddings=embedding_result["embedding"],
    # scale_score pas passe --> defaut False
)

filtered_questions = [q for q in similar_questions if q.score >= self.settings.threshold]
#                                                     ^^^^^^^^^^ threshold = 0.1
```

**Probleme :** Le seuil `threshold=0.1` s'applique sur des scores cosine bruts dans l'intervalle `[-1, 1]`. Ce seuil est **non interpretable** et probablement **mal calibre** :

- Cosine `0.1` signifie que les vecteurs forment un angle de ~84 degres -- c'est une similarite **tres faible**, quasiment orthogonale
- Les embeddings BGE-M3 tendent a produire des scores cosine concentres dans `[0.3, 0.9]` pour des textes dans la meme langue et le meme domaine (https://medium.com/%40abhilasha4042/the-art-and-science-of-vector-retrieval-a-deep-dive-into-embedding-model-evaluation-3255d346bcf7)
- Un seuil de `0.1` ne filtre quasiment rien -- seuls les textes dans des langues differentes ou completement hors domaine passent sous ce seuil

**Solution :** Calibrer le seuil sur des donnees reelles. Si `scale_score=True` est active (scores dans `[0, 1]`), un seuil de `0.55-0.65` est plus approprie pour BGE-M3 :

```yaml
suggestion:
  threshold: 0.6        # apres scale_score=True --> [0, 1]
  # 0.6 dans l'echelle [0,1] = cosine 0.2 = angle ~78 degres
  # Plus selectif que 0.1 sur cosine brut
```

---

### P-08 (DS-19) -- CRITIQUE : Aucun framework d'evaluation -- impossible de mesurer la pertinence

**Fichier :** `model_development.md` -- **entierement vide** (template non rempli)
**Fichier :** `data_management.md` -- **entierement vide** (template non rempli)

**Probleme :** Le projet n'a **aucun** framework d'evaluation de la pertinence des suggestions :

1. **Pas de dataset d'evaluation** : aucun jeu de test avec des paires (email, modele_de_reponse_attendu)
2. **Pas de metriques definies** : aucun recall@k, NDCG, MRR, ou precision@k n'est calcule
3. **Pas de baseline** : impossible de comparer BGE-M3 a un modele alternatif ou a un BM25
4. **Pas d'A/B testing** : aucune infrastructure pour comparer deux configurations en production
5. **Pas de feedback loop** : le systeme ne collecte pas le choix du conseiller (quel modele a ete selectionne)
6. **Documentation DS vide** : `model_development.md` et `data_management.md` sont des templates non remplis

Sans evaluation, tous les hyperparametres (threshold=0.1, similarity_top_k=15, reranker_top_k=5, default_model_ids) sont des **choix arbitraires** qui n'ont jamais ete valides empiriquement.

**Impact :** Impossible de savoir si le systeme fonctionne. Impossible de mesurer l'impact d'un changement de modele, d'un ajustement de seuil, ou d'un nettoyage du texte. Impossible de regresser.

**Solution :** Mettre en place un framework d'evaluation minimal :

```python
# 1. Creer un dataset d'evaluation
# eval_dataset.csv : email_content, expected_response_model_ids (gold labels)

# 2. Implementer les metriques standard
from sklearn.metrics import ndcg_score

def evaluate_pipeline(engine, eval_data):
    metrics = {"recall@1": 0, "recall@3": 0, "recall@5": 0, "mrr": 0}
```

---

## 1.4 Performance -- Critiques

---

### P-09 (PERF-01) -- CRITIQUE : Matrice d'embeddings reconstruite integralement a chaque requete

**Fichier :** `question_store.py` -- `_stack_document_embeddings` -- ligne 336

**Code incrimine :**

```python
def _stack_document_embeddings(self, documents: list[Document]) -> np.ndarray:
    try:
        matrix = np.array([doc.embedding for doc in documents])
    except ValueError as err:
        ...
    return matrix
```

**Appele par :** `_compute_query_embedding_similarity_scores` L441-442, elle-meme appelee par `search_similar` L281-283 -- **a chaque requete**.

**Probleme :** A chaque requete, la methode :

1. Itere **tous** les documents pour extraire les embeddings (list comprehension Python -- lent)
2. Cree un `np.ndarray` de shape `(N, 1024)` a partir de listes Python (copie memoire complete)

Allocation la plus couteuse du pipeline CPU.

**Solution :** Pre-calculer et cacher la matrice au chargement, puis la maintenir lors des insertions/suppressions.

---

### P-10 (PERF-06) -- CRITIQUE : Session HTTP creee et detruite a chaque appel LLM -- aucun connection pooling

**Fichier :** `llm_service.py` -- `call_llm` -- ligne 69

**Code incrimine :**

```python
def call_llm(self, data: dict[str, Any]) -> dict[str, Any]:
    with HttpSessionManager(
        token=self._llm_settings.llm_token,   # <-- property: cree un TokenAuth()
        retry_strategy=self._retry_strategy
    ) as session:
        response = session.post(self._llm_settings.llm_url, data=data)
    return response.json()
```

**Fichier :** `session_manager.py` -- `__enter__` / `__exit__` -- lignes 70-89

```python
def __enter__(self) -> HttpSessionManager:
    session = Session()          # <-- Nouvelle session TCP a chaque appel
    session.auth = self._token
    self.session = session
    return self

def __exit__(self, ...):
    if self.session:
        self.session.close()     # <-- Fermeture de la connexion TCP
```

**Probleme :** Chaque requete de suggestion effectue **2 appels LLM** (embedding + reranking). Chaque appel LLM cree une nouvelle `requests.Session`.

Soit **~20-100 ms de overhead reseau** par appel LLM, gaspilles 2x par requete.

**Impact :** 40-200 ms de latence reseau pure ajoutes par requete, non-lies au temps de calcul LLMaaS. Sous charge, le nombre de connexions TCP simultanees explose.

**Solution :** Creer une session persistante au niveau du `LLMService`, avec connection pooling :

CODE REPRIS D'ICI : https://medium.com/%40tusharbosamiya/python-requests-with-retry-building-reliable-http-requests-2150e8ccf8f1

```python
class LLMService:
    def __init__(self, llm_settings: LLMSettings, retry_strategy: RetryStrategy):
        self._llm_settings = llm_settings
        self._retry_strategy = retry_strategy
        self._url = llm_settings.llm_url        # calcule une seule fois

        # Session persistante avec connection pool
        self._session = Session()
        self._session.auth = TokenAuth(llm_settings.api_key)  # cree une seule fois

        # Configurer le pool de connexions
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        adapter = HTTPAdapter(
            pool_connections=5,       # connexions dans le pool
            pool_maxsize=10,          # taille max du pool
            max_retries=Retry(
                total=retry_strategy.total_retry,
                backoff_factor=retry_strategy.backoff_factor,
            ),
        )
        self._session.mount("https://", adapter)

    def call_llm(self, data: dict[str, Any]) -> dict[str, Any]:
        response = self._session.post(
            self._url,
            json=data,
            timeout=self._retry_strategy.timeout,
        )
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._session.close()
```

---

### P-11 (PERF-16) -- CRITIQUE : `replica_count: 1` -- aucune haute disponibilite, aucun scaling

**Fichier :** `project_config_prod.yml` -- lignes 1-10

**Code incrimine :**

```yaml
deployment:
  api:
    type: modelapi
    hardware_tier: hprd-cpu-4x6
    name_base_environment: iafactory_cpu_python_3.11
    external_volume_mount_ids: null
    script_file: run_api.py
    function: get_response
    is_async: 'false'        # <-- Synchrone
    replica_count: 1         # <-- UN SEUL replica
```

**Probleme :** Le deploiement de production ne comporte qu'**un seul replica** (instance) de l'API. Combine avec `is_async: false` (Flask synchrone), les implications sont :

1. **Aucune haute disponibilite** : si le replica crash, redemarre, ou est en deploiement --> **indisponibilite totale du service**
2. **Throughput plafonne** : un processus Flask synchrone ne traite qu'une requete a la fois. Avec ~500 ms par requete, le maximum theorique est **~2 req/s**
3. **Aucun scaling horizontal** : pas de possibilite d'absorber un pic de charge
4. **Single point of failure** : une requete qui trigger un OOM ou un hang bloque tout le service

La configuration hardware `hprd-cpu-4x6` suggere 4 cores / 6 Go RAM, mais un seul processus Python n'utilise qu'**un seul core** (GIL).

**Impact :** Indisponibilite en cas de crash ; throughput maximum ~2 req/s ; 3 cores sur 4 inutilises ; aucune tolerance aux pannes.

**Solution :** Augmenter les replicas et configurer un multi-worker :

```yaml
deployment:
  api:
    type: modelapi
    hardware_tier: hprd-cpu-4x6
    script_file: run_api.py
    function: get_response
    is_async: 'false'
    replica_count: 2              # Minimum 2 pour la HA
```

Avec un script Gunicorn interne pour exploiter les 4 cores :

```python
# gunicorn.conf.py
workers = 4                       # 1 par core
worker_class = "gthread"          # threads pour I/O
threads = 2
timeout = 30
graceful_timeout = 10
```

Throughput estime avec 2 replicas x 4 workers x 2 threads : **~32 req/s** (vs 2 req/s actuellement).

---

## 1.5 Qualite de code -- Critiques

---

### P-12 (CQ-06) -- CRITIQUE : Singleton `ConfigContext` mutable -- anti-pattern Service Locator non type

**Fichier :** `config_context.py`

**Code incrimine :**

```python
class ConfigContext:
    __instance = None
    _config: dict

    def get(self, key: str) -> Any:     # <-- retourne Any, aucun typage
        return self._config.get(key)

    def set(self, key: str, value: Any) -> None:   # <-- accepte Any
        self._config[key] = value
```

**Fichier :** `api.py` -- lignes 69-73

```python
config_context = ConfigContext()
suggestion_engine: SuggestionEngine = config_context.get("suggestion")
# Le type SuggestionEngine est caste MANUELLEMENT -- config_context.get retourne Any
```

**Problemes :**

1. **Service Locator anti-pattern** : les dependances sont recuperees par cle string (`"suggestion"`, `"settings"`) au lieu d'etre injectees. Le type de retour est `Any` -- aucune verification statique. Une faute de frappe dans la cle (`"suggestin"`) retourne `None` silencieusement.

2. **Singleton mutable** : le dictionnaire `_config` est partage globalement et mutable. N'importe quel code peut ecrire n'importe quoi dans le contexte.

3. **Testabilite degradee** : les tests doivent manipuler un singleton global au lieu de recevoir des dependances injectees.

4. **Commentaire template** : `"loaded_model": "InitialValue"` et `# Add more initial configurations here.` sont des vestiges du template de projet.

**Solution :** Remplacer par de l'injection de dependances ou au minimum typer le contexte :

```python
# Option 1 (simple) : Dataclass typee
@dataclass
class AppContext:
    settings: Settings
    suggestion_engine: SuggestionEngine

# Option 2 (meilleur) : Injection de dependances
def inference(data_dict: dict, engine: SuggestionEngine) -> dict:
    request = validate_api_input(data_dict)
    return engine.run_suggestion(request).model_dump(by_alias=True)
```

---

### P-13 (CQ-13) -- CRITIQUE : Fichier `__init__.py` racine execute du code avec side-effects a l'import

**Fichier :** `__init__.py`

**Code incrimine :**

```python
import importlib.metadata
import os

from version import __project_name__

try:
    importlib.metadata.PackageNotFoundError(__project_name__)
    os.environ["ENV_INDUS"] = "True"
except importlib.metadata.PackageNotFoundError:
    os.environ["ENV_INDUS"] = "False"
```

**Problemes :**

1. **Side-effects a l'import** : modifier `os.environ` dans un `__init__.py` est un anti-pattern. Toute importation (y compris dans les tests) modifie l'environnement global du processus.

2. **Bug logique** : `PackageNotFoundError(__project_name__)` **instancie** l'exception sans la lever. Le bloc `try` ne levera **jamais** `PackageNotFoundError` -- le code passe toujours dans le `try` et set `ENV_INDUS = "True"`. Le `except` est du code mort.

Le code correct serait :

```python
try:
    importlib.metadata.version(__project_name__)  # <-- version(), pas le constructeur
    os.environ["ENV_INDUS"] = "True"
except importlib.metadata.PackageNotFoundError:
    os.environ["ENV_INDUS"] = "False"
```

3. **`ENV_INDUS`** : cette variable d'environnement n'est utilisee nulle part dans le code industrialisation. C'est un vestige du template.

**Impact :** `ENV_INDUS` est toujours `"True"` a cause du bug logique -- si du code en depend, il est toujours en mode industrialisation.

**Solution :** Supprimer ce `__init__.py` ou deplacer la logique dans une fonction explicite.

---

## 1.6 Documentation -- Critiques

---

### P-14 (DOC-01) -- CRITIQUE : `quickstart.rst` decrit integralement le projet « iaflow » -- aucun rapport avec SmartInbox

**Fichier :** `quickstart.rst` -- lignes 1-252 (integralite)

**Code incrimine :**

```rst
Quickstart
==========
.. code-block::  Python
    iaflow/
    |-- iaflow/
    |   |-- __init__.py
    |   |-- common/
    |   |-- embedding/
    |   |-- retrieval/
    |   |-- prompt/
    |   |-- process/
```

```rst
Install the iaflow library using pip:
.. code-block:: bash
    pip install iaflow
```

```rst
Creer les API avec Iaflow est simple, Utilisez les decorateurs endpoints and lifespan events.
.. code-block:: python
    from iaflow.core import endpoint
    @endpoint
    def hello() -> str:
        return "hello"
```

**Probleme :** L'integralite du fichier (252 lignes) decrit un **autre projet** -- la bibliotheque `iaflow`. Un nouveau MLE qui lit ce fichier sera **activement induit en erreur** sur l'architecture, le framework et les classes du projet.

**Solution :** Supprimer ce fichier. Si un quickstart est necessaire, en creer un nouveau base sur le code reel.

---

### P-15 (DOC-02) -- CRITIQUE : `design_doc_index.rst` est un residu iaflow vide

**Fichier :** `design_doc_index.rst` -- lignes 1-10

**Code incrimine :**

```rst
.. _design_doc:

Design doc
==========
This repo hosts all the iaflow project design doc.

.. toctree::
  :glob:
  *
```

**Probleme :** Le fichier ne contient qu'une reference au projet « iaflow » et un `toctree` glob qui ne resout aucun document. Aucun contenu, aucune valeur. Bruit documentaire. Un MLE qui tombe sur ce fichier perd du temps a chercher les design docs references.

**Solution :** Supprimer le fichier.

---

### P-16 (DOC-05) -- CRITIQUE : `data_management.md` est un template vierge -- aucune donnee projet

**Fichier :** `data_management.md` -- lignes 9-46

**Code incrimine :**

```markdown
### Sources de Donnees
Decrivez d'ou proviennent vos donnees, leur format et comment elles sont collectees.

- **Brutes** : Donnees non traitees
- **Traitees** : Donnees apres nettoyage et transformation
- **Externes** : Donnees provenant de sources externes

## Pretraitement des donnees
Expliquez les etapes de nettoyage et de pretraitement des donnees : normalisation, encodage, etc.

## Version et organisation des donnees
Si applicable, expliquez comment les versions de donnees sont gerees,
```

**Probleme :** Le fichier entier est un **template vierge** (46 lignes d'instructions au redacteur, 0 ligne de contenu reel). Aucune information sur les donnees SmartInbox : modeles de reponse (MdR), questions clients, fichiers pickle `client_questions.pickle` et `response_models.pickle`, processus de mise a jour de la knowledge base. Un nouveau MLE n'a **aucune visibilite** sur les donnees manipulees par le projet. Il ne peut pas comprendre comment construire ou mettre a jour la knowledge base.

**Solution :** Remplir avec le contenu reel :

```markdown
# Gestion des donnees -- SmartInbox

## Sources de donnees

| Source | Format | Description |
|--------|--------|-------------|
| Questions clients | CSV -> pickle | Questions-types associees a des MdR |
| Modeles de reponse | CSV -> pickle | Templates de reponse email par ID |

## Fichiers de la knowledge base

- `knowledge_base/client_questions.pickle` : store vectoriel
- `knowledge_base/response_models.pickle` : dict `{id: texte}`

## Construction
python build_question_store.py
python build_response_model_store.py
```

---

### P-17 (DOC-06) -- CRITIQUE : `model_development.md` est un template vierge -- aucun choix de modele documente

**Fichier :** `model_development.md` -- lignes 27-45

**Code incrimine :**

```markdown
### Modele 1 : [Nom du Modele]

- **Description** : Breve description de ce que fait ce modele.
- **Raison du Choix** : Explication pourquoi ce modele a ete choisi
- **Performances du Modele** :
  - **Metriques de Performance** : Decrire les metriques utilisees pour evaluer le modele
  - **Resultats** : Fournir les resultats obtenus (e.g., accuracy: 95%).
- **Besoins Fonctionnels** :
  - **Fonctionnalites Requises** : Decrire les fonctionnalites que le modele doit fournir
```

**Probleme :** Template vierge avec des placeholders (`[Nom du Modele]`, `accuracy: 95%`). Aucune mention de BGE-M3, BGE-Reranker-v2-M3, du choix de la similarite cosine, du seuil `0.1`, ni de la strategie embed --> search --> rerank.

**Solution :** Remplir avec les choix reels :

```markdown
### Modele 1 : BGE-M3 (embedding)
- **Description** : Modele multilingual state-of-the-art (embeddings denses)
- **Raison du choix** : Support multilingual, performances MTEB
- **Configuration** : similarite cosine, `similarity_top_k: 15`
- **Seuil** : 0.1 (decrire comment c'est obtenu ...)

### Modele 2 : BGE-Reranker-v2-M3 (reranking)
- **Description** : Cross-encoder multilingual
- **Configuration** : `reranker_top_k: 5`
```

---
---

# PARTIE 2 -- PROBLEMES MAJEURS

---

## 2.1 Securite -- Majeurs

---

### P-18 (SEC-03) -- MAJEUR : f-strings dans les appels de logging (14 occurrences dans 8 fichiers)

**Fichiers concernes :**

**Code incrimine :**

```python
# api.py -- ligne 68
logger.info(f"Suggestion endpoint called. Version: {__version__}")

# llm_service.py -- ligne 31
logger.info(f"{type(self).__name__} initialized with %s", llm_settings.api_endpoint)

# llm_service.py -- ligne 72
logger.info(f"Sending request to the endpoint '{endpoint}' of the LLMaaS.")

# suggestion_engine.py -- ligne 188
logger.info(f"Retrieved {len(similar_questions)} candidate questions from the vector store.")

# suggestion_engine.py -- ligne 192
logger.info(f"Step 3: Filtered down to {len(filtered_questions)} questions (threshold = {self.settings.threshold}).")

# validation.py -- ligne 62
logger.info(f"Schema of the input received: {input_schema}")

# load_config.py -- ligne 52, 78, 91, 106, 109, 144, 157, 172, 175, 184, 189
logger.info(f"Loading configuration file from {path_file_conf}")
```

**Probleme :** L'utilisation de f-strings au lieu du lazy formatting (`%s`) dans les appels de logging pose deux problemes de securite :

**Evaluation prematuree** : la f-string est evaluee meme si le niveau de log est desactive, ce qui peut provoquer des effets de bord ou des exceptions dans des contextes inattendus.

**Solution :** Remplacer systematiquement les f-strings par le lazy formatting natif du module `logging` :

```python
# AVANT (vulnerable)
logger.info(f"Schema of the input received: {input_schema}")
logger.info(f"Sending request to the endpoint '{endpoint}' of the LLMaaS.")

# APRES (sur)
logger.info("Schema of the input received: %s", input_schema)
logger.info("Sending request to endpoint '%s' of LLMaaS.", endpoint)
```

---

### P-19 (SEC-05) -- MAJEUR : La cle API LLMaaS peut etre None -- authentification silencieusement desactivee

**Fichier :** `llm_settings.py` -- lignes 61-65

**Code incrimine :**

```python
@model_validator(mode="before")
@classmethod
def _fill_api_settings(cls, value: dict[str, Any]) -> dict[str, Any]:
    if value.get("api_uri") == "" or value.get("api_uri") is None:
        value["api_uri"] = getenv("LLMAAS_PROD_ENDPOINT")  # <-- peut retourner None

    if value.get("api_key") == "" or value.get("api_key") is None:
        value["api_key"] = getenv("LLMAAS_API_KEY")  # <-- peut retourner None

    return value
```

**Fichier :** `token_auth.py` -- ligne 54

```python
request.headers["Authorization"] = f"Bearer {self.token}"
# Si self.token est None --> "Bearer None" envoye au serveur
```

**Probleme :** Si la variable d'environnement `LLMAAS_API_KEY` n'est pas definie, `getenv()` retourne `None`. Ce `None` est stocke dans `api_key`, transmis au `TokenAuth`, et injecte dans le header HTTP sous la forme `Authorization: Bearer None`.

**Solution :** Valider que les champs critiques ne sont pas `None` apres le remplissage :

```python
@model_validator(mode="before")
@classmethod
def _fill_api_settings(cls, value: dict[str, Any]) -> dict[str, Any]:
    if not value.get("api_uri"):
        value["api_uri"] = getenv("LLMAAS_PROD_ENDPOINT")
    if not value.get("api_key"):
        value["api_key"] = getenv("LLMAAS_API_KEY")

    if not value.get("api_uri"):
        raise ValueError(
            "api_uri is required: set it in app_config.yml "
            "or via LLMAAS_PROD_ENDPOINT"
        )
    if not value.get("api_key"):
        raise ValueError(
            "api_key is required: set it in app_config.yml "
            "or via LLMAAS_API_KEY (provisioned by Vault)"
        )
    return value
```

---

### P-20 (SEC-10) -- MAJEUR : `Base64DecodingError` stocke le contenu brut de l'email (RGPD)

**Fichier :** `validation_exception.py` -- lignes 19-39

**Code incrimine :**

```python
class Base64DecodingError(ValidationError):
    def __init__(self, field_name: str, original_value: str, message: str | None = None) -> None:
        if message is None:
            message = (
                f"Failed to decode Base-64 value for field '{field_name}'. "
                "The provided string is not valid Base-64 or uses an unsupported encoding."
            )
        super().__init__(message)
        self.field_name = field_name
        self.original_value = original_value  # <-- CONTENU EMAIL BRUT STOCKE
```

**Fichier :** `email_suggestion_request.py` -- ligne 65

```python
raise Base64DecodingError(field_name=info.field_name, original_value=value) from exc
#                                                       ^^^^^^^^^^^^^^^^^^^^^^
#                                     Le contenu Base64 de l'email est passe tel quel
```

**Probleme :** Quand le decodage Base64 echoue, le **contenu brut de l'email** (sujet ou corps) est stocke dans l'attribut `original_value` de l'exception. Cette exception est ensuite stockee dans les logs (via `event.set_error(error)` dans `wide_event.py` qui stocke `str(error)` dans les logs) et potentiellement dans les reponses HTTP.

**Impact :** Fuite de donnees personnelles -- contenu d'emails de clients bancaires -- dans les logs Kibana, les reponses HTTP -> Violation RGPD.

**Solution :** Ne jamais stocker le contenu original dans l'exception :

```python
class Base64DecodingError(ValidationError):
    def __init__(self, field_name: str, message: str | None = None) -> None:
        if message is None:
            message = (
                f"Failed to decode Base-64 value for field '{field_name}'. "
                "The provided string is not valid Base-64."
            )
        super().__init__(message)
        self.field_name = field_name
        # PAS de self.original_value
```

---

## 2.2 Data Science -- Majeurs

---

### P-21 (DS-04) -- MAJEUR : Decodage Base64 en `latin-1` au lieu de `UTF-8` -- perte de caracteres accentues et emojis

**Fichier :** `email_suggestion_request.py` -- ligne 63

**Code incrimine :**

```python
return Base64EncoderDecoder("latin1").decode(value)
```

**Probleme :** Le contenu est decode en Latin-1 (ISO 8859-1). Ce codec ne couvre que les 256 premiers code points Unicode. Les caracteres suivants, courants dans les emails bancaires francais, sont **mal decodes ou perdus**.

Le symbole `EUR` est probablement le caractere le plus frequent apres les lettres dans un email bancaire. Son absence ou sa corruption dans le texte d'embedding **degrade la comprehension semantique** du modele sur tous les emails mentionnant des montants.

**Impact :** Degradation systematique de la qualite d'embedding pour les emails contenant `EUR`, `oe`, tirets cadratins, ou emojis. Le modele BGE-M3 a ete entraine sur du texte UTF-8 -- lui fournir du Latin-1 reinterprete cree un decalage distributional.

**Solution :**

```python
return Base64EncoderDecoder("utf-8").decode(value)
```

Si Outlook envoie effectivement du Latin-1 encode en Base64 (verifier le Content-Type), convertir vers UTF-8 apres decodage :

```python
raw_bytes = base64.b64decode(value)
try:
    return raw_bytes.decode("utf-8")
except UnicodeDecodeError:
    return raw_bytes.decode("latin-1")  # fallback
```

---

### P-22 (DS-05) -- MAJEUR : Concatenation `"{objet} {corps}"` sans structuration semantique

**Fichier :** `email_suggestion_request.py` -- ligne 115

**Code incrimine :**

```python
return f"{self.email_object} {self.email_content}"
```

**Probleme :** L'objet (sujet) et le corps de l'email sont concatenes avec un simple espace. Le modele d'embedding ne peut pas distinguer la contribution semantique du sujet (condense, intentionnel) de celle du corps (verbeux, contextuel).

Dans un email bancaire, le sujet porte souvent **la majorite de l'intention** :
- Sujet : `"Demande de rachat de credit immobilier"`
- Corps : `"Bonjour Madame, je vous contacte suite a notre conversation telephonique de mardi dernier concernant mon pret numero 12345678. Mon epouse et moi-meme souhaiterions explorer les options de rachat..."`

Avec la concatenation simple, le sujet (7 mots) est noye dans le corps (50+ mots). L'embedding final est domine par le contenu du corps, qui est plus verbeux mais moins informatif. Il y a dilution du signal du sujet, qui est souvent le meilleur predicteur de l'intention metier.

**Solution :** Structurer l'entree pour le modele :

```python
@property
def content(self) -> str:
    parts = []
    if self.email_object and self.email_object.strip():
        parts.append(f"Objet: {self.email_object.strip()}")
    if self.email_content and self.email_content.strip():
        parts.append(f"Contenu: {self.email_content.strip()}")
    return "\n".join(parts)
```

---

### P-23 (DS-08) -- MAJEUR : `email_sequence_index` non exploite -- pas d'adaptation premier contact vs relance

**Fichier :** `email_suggestion_request.py` -- ligne 26

**Code incrimine :**

```python
email_sequence_index: int = Field(gt=0, alias="emailSequenceIndex", ...)
```

**Probleme :** `email_sequence_index` indique la position de l'email dans la conversation : 1 = premier email, 2+ = echange en cours. Ce signal est extremement discriminant pour la suggestion. Le pipeline ignore completement ce signal et traite tous les emails de la meme maniere, quel que soit leur position dans la conversation.

**Impact :** Les memes modeles de reponse sont suggeres pour un premier contact et pour un 5eme echange de suivi -- ce qui est rarement pertinent.

**Solution :** Utiliser `email_sequence_index` comme signal de filtrage ou de boosting, eventuellement en le stockant comme metadata dans les questions de la knowledge base.

---

## 2.3 Robustesse -- Majeurs

---

### P-24 (ROB-02) -- MAJEUR : `IndexError` sur reponse LLMaaS reranker avec index hors bornes

**Fichier :** `llm_reranker.py` -- `rerank_documents` -- lignes 153-154

**Code incrimine :**

```python
# ##>: Pair each Document with its score (ignore any missing indices).
indexed_scores = {result.index: result.relevance_score for result in response.results}
scored_docs = [(documents[idx], indexed_scores[idx]) for idx in indexed_scores]
#               ^^^^^^^^^^^^^^^ IndexError si idx >= len(documents)
```

**Probleme :** Ce code est **hors du bloc try/except** (lignes 138-150). Si le LLMaaS retourne un `result.index` superieur ou egal a `len(documents)`, `documents[idx]` leve un `IndexError` non attrape qui remonte directement a Flask. Le commentaire « ignore any missing indices » est trompeur -- le code ne gere aucun index manquant ni hors bornes.

**Impact :** Crash non attrape, HTTP 400 generique retourne au client, perte de la requete.

**Solution :** Valider les index et ignorer les hors-bornes :

```python
# Filtrer les index valides
indexed_scores = {
    result.index: result.relevance_score
    for result in response.results
    if 0 <= result.index < len(documents)
}

if not indexed_scores:
    logger.warning("LLMaaS returned no valid indices -- falling back.")
    return self._fallback_rerank_documents(documents)

scored_docs = [(documents[idx], score) for idx, score in indexed_scores.items()]
```

---

### P-25 (ROB-08) -- MAJEUR : `response.json()` non protege -- crash si LLMaaS retourne du non-JSON

**Fichier :** `llm_service.py` -- lignes 73-80

**Code incrimine :**

```python
response = session.post(self._llm_settings.llm_url, data=data)
# ...
return response.json()     # <-- JSONDecodeError non attrape
```

**Probleme :** Si le serveur LLMaaS retourne une reponse non-JSON (page d'erreur HTML, timeout proxy, etc.), `response.json()` leve un `requests.exceptions.JSONDecodeError` (herite de `ValueError`).

**Solution :** Proteger le decodage JSON :

```python
def call_llm(self, data: dict[str, Any]) -> dict[str, Any]:
    with HttpSessionManager(...) as session:
        response = session.post(self._llm_settings.llm_url, data=data)
        try:
            return response.json()
        except ValueError as json_err:
            raise RequestException(
                f"LLMaaS returned non-JSON response "
                f"(status={response.status_code}, "
                f"content-type={response.headers.get('content-type')})"
            ) from json_err
```

---

### P-26 (ROB-22) -- MAJEUR : `_l2_normalise` modifie la matrice in-place -- corrompt les embeddings stockes si la matrice est cachee

**Fichier :** `question_store.py` -- `_l2_normalise` -- lignes 368-371

**Code incrimine :**

```python
# ##>: In-place division.
np.divide(query_emb, query_norm, out=query_emb)
np.divide(doc_matrix, doc_norm, out=doc_matrix)
return query_emb, doc_matrix
```

**Probleme :** L'operation `np.divide(..., out=doc_matrix)` modifie la matrice d'embeddings **in-place**. Dans l'implementation actuelle, la matrice est recreeee a chaque requete (PERF-01), donc la mutation est sans consequence.

Mais si la recommandation PERF-01 (cacher la matrice) est appliquee **sans corriger ce probleme**, la premiere requete normalise la matrice cache, et toutes les requetes suivantes re-normalisent une matrice deja normalisee. Apres N requetes, les embeddings convergent vers des vecteurs unitaires homogenes et les scores de similarite deviennent tous identiques (~1.0).

C'est un **bug dormant** : invisible actuellement, mais active par l'optimisation de performance la plus evidente (cache de la matrice).

**Impact :** Corruption progressive des scores de similarite si PERF-01 est applique sans corriger ce code. Degradation silencieuse de la qualite des suggestions.

**Solution :** Ne jamais modifier la matrice cache in-place : pre-normaliser la matrice une seule fois au chargement et ne normaliser que la query a chaque requete.

---

## 2.4 Performance -- Majeurs

---

### P-27 (PERF-02) -- MAJEUR : Normalisation L2 recalculee sur TOUS les documents a chaque requete

**Fichier :** `question_store.py` -- `_l2_normalise` -- lignes 361-371

**Code incrimine :**

```python
def _l2_normalise(self, query_emb, doc_matrix):
    query_norm = np.linalg.norm(query_emb, axis=1, keepdims=True)
    doc_norm = np.linalg.norm(doc_matrix, axis=1, keepdims=True)
    query_norm[query_norm == 0] = 1.0
    doc_norm[doc_norm == 0] = 1.0
    np.divide(query_emb, query_norm, out=query_emb)
    np.divide(doc_matrix, doc_norm, out=doc_matrix)
    return query_emb, doc_matrix
```

**Appele par :** `_compute_query_embedding_similarity_scores` L444-446, en mode `cosine` (qui est le mode configure dans `app_config.yml` L32).

**Probleme :** Les normes L2 des embeddings de documents sont **statiques** -- elles ne changent jamais entre deux requetes. Pourtant, `np.linalg.norm()` est recalcule sur la totalite de `doc_matrix` a chaque recherche.

**Solution :** Pre-normaliser une seule fois au chargement (integre dans la solution PERF-01 ci-dessus). Seul le query embedding doit etre normalise a chaque requete.

---

### P-28 (PERF-07) -- MAJEUR : `total_retry: 1` signifie zero retry -- premier timeout = echec definitif

**Fichier :** `app_config.yml` -- lignes 6-10 et 17-21

**Code incrimine :**

```yaml
embedder:
  retry_strategy:
    max_wait: 1
    timeout: 15
    total_retry: 1      # <-- UN SEUL essai
    backoff_factor: 0   # <-- PAS de backoff

reranker:
  retry_strategy:
    max_wait: 1
    timeout: 15
    total_retry: 1      # <-- UN SEUL essai
    backoff_factor: 0   # <-- PAS de backoff
```

**Fichier :** `session_manager.py` -- lignes 111-119

```python
retryer = Retrying(
    stop=stop_after_attempt(self._retry_strategy.total_retry),  # = 1
    wait=wait_exponential(
        multiplier=self._retry_strategy.backoff_factor,         # = 0
        max=self._retry_strategy.max_wait,
    ),
    retry=retry_if_exception_type(RequestException),
    ...
)
```

**Probleme :** `stop_after_attempt(1)` de la librairie `tenacity` signifie « **un seul essai, zero retry** ». Le moindre timeout reseau transitoire, erreur 502/503 de LLMaaS, ou pic de latence provoque un echec definitif de la requete.

Combine avec `backoff_factor: 0`, meme si `total_retry` etait corrige, le backoff serait de `0 x 2^n = 0` secondes -- c'est-a-dire un retry immediat sans attente, qui hammer le service en erreur.

En production, les services LLMaaS ont des pics de latence previsibles (deploiements, cold start, saturation). Sans retry avec backoff, chaque pic reseau provoque un rejet de requete visible par l'utilisateur final.

**Solution :** Configurer un retry realiste avec backoff exponentiel :

```yaml
embedder:
  retry_strategy:
    max_wait: 10
    timeout: 15
    total_retry: 3       # 3 tentatives = 1 + 2 retries
    backoff_factor: 0.5  # 0.5s --> 1s --> 2s

reranker:
  retry_strategy:
    max_wait: 10
    timeout: 15
    total_retry: 3
    backoff_factor: 0.5
```

---

### P-29 (PERF-10) -- MAJEUR : `TokenAuth()` et URL reconstruits a chaque appel LLM via `@property`

**Fichier :** `llm_settings.py` -- lignes 83-93

**Code incrimine :**

```python
@property
def llm_token(self) -> TokenAuth:
    return TokenAuth(self.api_key)  # <-- NOUVEL objet a chaque acces

@property
def llm_url(self) -> str:
    return f"{self.api_uri.rstrip('/')}/{self.api_endpoint.lstrip('/')}"
    # <-- Concatenation string + strip a chaque acces
```

**Fichier :** `llm_service.py` -- ligne 69

```python
with HttpSessionManager(
    token=self._llm_settings.llm_token,  # <-- appel property --> new TokenAuth
    retry_strategy=self._retry_strategy
) as session:
    response = session.post(
        self._llm_settings.llm_url,      # <-- appel property --> string concat
        data=data,
    )
```

**Probleme :** Chaque appel a `call_llm()` :

1. Cree un nouvel objet `TokenAuth(self.api_key)` -- allocation + init
2. Recalcule l'URL via `f-string` + `rstrip` + `lstrip` -- operations string
3. L'objet `TokenAuth` est passe au `HttpSessionManager`, utilise une fois, puis garbage-collected

Ces valeurs sont **strictement constantes** pendant toute la duree de vie du processus : la cle API et l'URL ne changent pas.

**Solution :** Cacher les valeurs avec `@functools.cached_property` :

```python
from functools import cached_property

@cached_property
def llm_token(self) -> TokenAuth:
    return TokenAuth(self.api_key)

@cached_property
def llm_url(self) -> str:
    return f"{self.api_uri.rstrip('/')}/{self.api_endpoint.lstrip('/')}"
```

---

## 2.5 Qualite de code -- Majeurs

---

### P-30 (CQ-02) -- MAJEUR : Faute de frappe persistante `emdedding` au lieu de `embedding` -- 7 occurrences

**Fichier :** `wide_event.py` -- lignes 55-57

**Code incrimine :**

```python
emdedding_total_tokens: Optional[int] = None
emdedding_prompt_tokens: Optional[int] = None
emdedding_completion_tokens: Optional[int] = None
```

**Fichier :** `llm_embedder.py` -- lignes 73-76

```python
enrich_event(
    **{
        "embedding_model": result.model,
        "emdedding_completion_tokens": result.usage.completion_tokens,  # <-- typo
        "emdedding_prompt_tokens": result.usage.prompt_tokens,          # <-- typo
        "emdedding_total_tokens": result.usage.total_tokens,            # <-- typo
    }
)
```

**Impact :** Champs de metriques mal nommes dans les logs structures -- requetes d'observabilite cassees.

**Solution :** Renommer les 7 occurrences. Attention : necessite de mettre a jour les dashboards Kibana existants.

---

### P-31 (CQ-14) -- MAJEUR : Trois mecanismes de chargement de configuration coexistent

**Fichiers :** `load_config.py`, `load_configuration.py`, `settings.py`

| Fichier | Mecanisme | Utilise par |
|---------|-----------|-------------|
| `load_config.py` (`common/`) | Charge YAML + dotenv manuellement avec `os.path` | `train.py`, `build_question_store.py` (via `api.py`) |
| `load_configuration.py` (`common/`) | Charge YAML + dotenv manuellement avec `os.path` | `api.py` --> `init_app()` |
| `settings.py` (`industrialisation/`) | `pydantic-settings` + `YamlConfigSettingsSource` | `api.py` --> `Settings()` |

**Probleme :** Trois modules differents chargent la configuration :

1. `load_config.py` : 190 lignes de logique manuelle de chargement YAML avec resolution d'environnement (`-prod`, `-pprod`, `-dev`). Utilise `os.path` partout au lieu de `pathlib`.
2. `load_configuration.py` : fait la meme chose en plus court, importe par `api.py`.
3. `settings.py` : utilise `pydantic-settings` avec `YamlConfigSettingsSource` -- l'approche moderne et correcte.

`load_config.py` et `load_configuration.py` sont largement redondants entre eux et avec `pydantic-settings`. Leur existence temoigne d'un refactoring inacheve : le template original utilisait le chargement manuel, puis `pydantic-settings` a ete introduit sans supprimer l'ancien code.

De plus, `load_service_config_file` et `load_config_domino_project_file` dans `load_config.py` partagent **80% de leur code** en duplication pure (pattern de resolution `{env}` copie-colle).

**Impact :** Confusion sur la source de verite de la configuration. Bug potentiel si les deux mecanismes chargent des valeurs differentes.

**Solution :** Supprimer `load_config.py`, unifier sur `pydantic-settings`.

---

### P-32 (CQ-15) -- MAJEUR : `request_llm_embedding.py` et `request_llm_reranker.py` -- code duplique inutilise

**Fichier :** `request_llm_embedding.py`

**Code incrimine :**

```python
def main(settings: ModelSettings, data: dict[str, Any]) -> dict[str, Any]:
    with HttpSessionManager(token=settings.settings.llm_token, retry_strategy=settings.retry_strategy) as session:
        response = session.post(settings.settings.llm_url, data=data)
        return response.json()
```

**Fichier :** `request_llm_reranker.py`

```python
def main(settings: ModelSettings, email_content: str, candidates_content: list[str]) -> dict[str, Any]:
    with HttpSessionManager(token=settings.settings.llm_token, retry_strategy=settings.retry_strategy) as session:
        response = session.post(settings.settings.llm_url, data=data)
        return response.json()
```

**Probleme :** Ces deux fichiers sont des **scripts standalone** qui dupliquent la logique de `LLMService.call_llm`. Ils ne sont importes par aucun module du pipeline.

**Solution :** Supprimer ces fichiers.

---

## 2.6 Documentation -- Majeurs

---

### P-33 (DOC-07) -- MAJEUR : `logging.md` affiche des noms de modeles OpenAI au lieu de BGE

**Fichier :** `logging.md` -- lignes 180-185

**Code incrimine :**

```json
{
  "embedding_model": "text-embedding-ada-002",
  "emdedding_total_tokens": 123,
  "embedding_latency": 0.215,
  "reranking_model": "gpt-4o-mini",
  "reranking_total_tokens": 78
}
```

**Probleme :** L'exemple JSON de log structure affiche `text-embedding-ada-002` (OpenAI) et `gpt-4o-mini` (OpenAI). Le projet utilise `bge-m3` et `bge-reranker-v2-m3` (conf. `app_config.yml` L4 et L15). Un ops qui configure les dashboards Kibana cherchera les mauvais noms de modeles. Fausse piste de monitoring.

**Solution :** Aligner l'exemple sur les modeles reels :

```json
{
  "embedding_model": "bge-m3",
  "reranking_model": "bge-reranker-v2-m3"
}
```

---

### P-34 (DOC-08) -- MAJEUR : `logging.md` propage la typo `emdedding` du code

**Fichier :** `logging.md` -- lignes 143-148 (extrait de code) et lignes 181-183 (exemple JSON)

**Code incrimine :**

```python
enrich_event(
    embedding_model=result.model,
    emdedding_completion_tokens=result.usage.completion_tokens,
    emdedding_prompt_tokens=result.usage.prompt_tokens,
    emdedding_total_tokens=result.usage.total_tokens,
)
```

**Probleme :** La documentation reproduit fidelement la typo `emdedding` (au lieu de `embedding`) presente dans `wide_event.py` L55-57 et `llm_embedder.py` L73-75 (cf. CQ-02 du rapport principal). La doc enterine le bug.

**Solution :** Corriger dans la doc :

```
emdedding_completion_tokens --> embedding_completion_tokens
emdedding_prompt_tokens     --> embedding_prompt_tokens
emdedding_total_tokens      --> embedding_total_tokens
```

---

### P-35 (DOC-09) -- MAJEUR : `troubleshooting.md` reference des variables d'environnement qui n'existent pas dans le code

**Fichier :** `troubleshooting.md` -- lignes 83-93

**Code incrimine :**

```markdown
- `LLMAAS_SANDBOX_ENDPOINT` ou `LLMAAS_SANDBOX_CR_AUTO_API_KEY` ne sont pas definies.

**Solution** :
  export LLMAAS_SANDBOX_ENDPOINT="https://my-llm-endpoint"
  export LLMAAS_SANDBOX_CR_AUTO_API_KEY='{"my_key":"abcd1234"}'
```

**Probleme :** Le troubleshooting guide vers les variables `LLMAAS_SANDBOX_ENDPOINT` et `LLMAAS_SANDBOX_CR_AUTO_API_KEY`. Or le code (`llm_settings.py`) utilise `LLMAAS_PROD_ENDPOINT` et `LLMAAS_API_KEY`. Le « sandbox » est utilise d'une ancienne version.

**Solution :** Aligner sur les variables reelles :

```markdown
- `LLMAAS_PROD_ENDPOINT` ou `LLMAAS_API_KEY` ne sont pas definies.

**Solution** :
  export LLMAAS_PROD_ENDPOINT="https://llmaas-ap88967-prod.data.cloud.net.intra/"
  export LLMAAS_API_KEY="votre-cle-api"
```

---

### P-36 (DOC-10) -- MAJEUR : `testing.md` vs `README.md` -- seuil de couverture incoherent (80% vs 60%)

**Fichier :** `testing.md` -- ligne 29

**Code incrimine :**

```markdown
* **Couverture** -- le seuil minimum impose par le pipeline GitLab est de 80 % de couverture globale.
```

**Fichier :** `README.md` -- ligne 200

```markdown
- Lancement des tests unitaires qui sont obligatoires avec verification de la couverture de code a 60%.
```

**Probleme :** `testing.md` indique un seuil de **80%**, le `README.md` indique **60%**. Un seul peut etre correct.

**Solution :** Verifier la configuration reelle du pipeline CI (`.gitlab-ci.yml`) et aligner les deux documents sur la meme valeur -> 60%.

---

### P-37 (DOC-12) -- MAJEUR : `wide_event.py` emet "Summarization" -- repris sans correction dans la doc

**Fichier :** `wide_event.py` -- ligne 202

**Code incrimine :**

```python
message = f"Summarization endpoint completed with {self.outcome.value} result"
```

**Aussi concerne :** `deployment_and_pipeline.md` L293 (description des logs emis)

**Probleme :** Le message de log dit « Summarization endpoint » alors que le projet est un service de **Suggestion**. Residu de copier-coller (probablement CR-AUTO). La doc de deploiement reprend ce comportement sans le corriger.

**Solution :** Corriger le code **et** la doc :

```python
message = f"Suggestion endpoint completed with {self.outcome.value} result"
```

---

### P-38 (DOC-25) -- MAJEUR : Pas de documentation de la construction de la knowledge base

**Fichiers concernes :** `build_question_store.py` (5.5 KB), `build_response_model_store.py` (2.5 KB) -- scripts existants, aucune doc

**Probleme :** Les scripts construisent les stores pickle qui alimentent le moteur de suggestion. Aucun document n'explique quel format de donnees d'entree ils attendent, comment les executer, quelle est la procedure de mise a jour en production, ni comment valider l'integrite des stores generes.

**Solution :** Creer `docs/knowledge_base.md` :

```markdown
# Mise a jour de la Knowledge Base

## Pre-requis
- CSV des questions : `question_id, question_text, response_model_id`
- CSV des modeles de reponse : `model_id, model_text`

## Construction
python build_question_store.py
python build_response_model_store.py

## Deploiement
1. Copier les `.pickle` dans `industrialisation/knowledge_base/`
2. Redemarrer le service
```

---
---

# PARTIE 3 -- PROBLEMES MINEURS

---

## 3.1 Data Science -- Mineurs

---

### P-39 (DS-07) -- MINEUR : Metadonnees metier disponibles mais non exploitees dans le retrieval

**Fichier :** `extra_parameters.py` -- lignes 10-12

**Code incrimine :**

```python
channel: str = Field(default="", alias="Channel", pattern=r"^\d{3}$")
media: str = Field(default="", alias="Media", pattern=r"^\d{3}$|^$")
client_id: str = Field(alias="ClientId")
```

**Fichier :** `email_suggestion_request.py` -- lignes 26-29

```python
email_sequence_index: int = Field(gt=0, alias="emailSequenceIndex", ...)
start_ts: datetime = Field(alias="startTs", ...)
```

**Probleme :** Cinq signaux metier sont disponibles dans chaque requete mais **jamais utilises** pour la suggestion.

Le pipeline utilise **uniquement** le texte brut de l'email pour la recherche semantique. Les metadonnees sont loguees dans le WideEvent a des fins d'observabilite, mais jamais exploitees pour ameliorer la pertinence. Un email de premier contact sur le canal agence devrait favoriser des modeles de reponse differents d'une relance sur messagerie securisee -- meme si le contenu textuel est similaire.

**Solution :** Implementer un **filtrage pre-retrieval** base sur les metadonnees.

---

### P-40 (DS-09) -- MINEUR : Aucune detection de langue -- emails en anglais, arabe, etc. traites comme du francais

**Probleme :** Le pipeline traite tous les emails de la meme maniere quelle que soit la langue. BGE-M3 est multilingue et produira un embedding correct pour un email en anglais, mais les questions du question store sont vraisemblablement en francais. La similarite cosine entre un email anglais et des questions francaises sera faible mais **non nulle** -- le modele trouvera des correspondances cross-linguales approximatives.

Dans un contexte bancaire, la detection de langue permettrait de :
1. Rediriger les emails non-francais vers un traitement specifique
2. Eviter de suggerer des modeles de reponse francais pour un email anglais
3. Logger les cas pour l'observabilite

**Impact :** Suggestions potentiellement en francais pour un email client en anglais -- perturbant pour le conseiller.

**Solution :** Ajouter une detection de langue legere :

```python
from langdetect import detect

def detect_language(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "unknown"

# Dans le pipeline
lang = detect_language(request.content)
if lang != "fr":
    enrich_event(detected_language=lang, language_mismatch=True)
    # Optionnel : retourner un resultat vide ou un avertissement
```

---

### P-41 (DS-18) -- MINEUR : Aucun signal de confiance global -- le client ne sait pas si les suggestions sont fiables

**Probleme :** La reponse API contient des `selectedCandidates` (avec scores de similarite) et des `rerankedCandidates` (avec scores de reranking), mais aucun **signal de confiance global** n'indique au client Outlook si les suggestions sont fiables :

- Toutes les similarites sont < 0.3 --> les suggestions sont probablement non pertinentes, mais aucun flag ne le dit
- Le fallback reranker a ete active --> les scores de reranking sont en realite des scores de similarite, mais le client ne le sait pas
- Le score maximum du meilleur candidat est un bon proxy de la confiance globale, mais n'est pas expose

**Impact :** Le client Outlook ne peut pas adapter son UX (ex : afficher un disclaimer « suggestions incertaines ») en fonction de la confiance du systeme.

**Solution :** Ajouter un champ de confiance dans la reponse :

```python
class EmailSuggestionResult(BaseDTO):
    ...
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Overall confidence in the suggestions (0=low, 1=high)"
    )
    fallback_used: bool = Field(
        default=False,
        description="True if the reranker failed and fallback was used"
    )
```

---

### P-42 (DS-20) -- MINEUR : `train.py` est un boilerplate Iris/XGBoost -- code mort sans rapport avec le projet

**Fichier :** `train.py`

**Code incrimine :**

```python
features = ["sepal.length", "sepal.width", "petal.length", "petal.width"]
target = "variety"
data = pd.read_csv(f"{DATASET_PROJECT}/train_data/iris.csv")

xgb_classifier = XGBClassifier(
    n_estimators=10,
    max_depth=3,
    learning_rate=0.5,
    objective="binary:logistic",
    random_state=123,
)
```

**Probleme :** `train.py` est un script de classification Iris avec XGBoost -- un **boilerplate de template de projet** qui n'a aucun rapport avec le pipeline de suggestion par embedding/reranking.

**Solution :** Supprimer `train.py` et les dependances associees (`xgboost`, `sklearn`) si elles ne sont pas utilisees ailleurs. Documenter clairement que le pipeline utilise des modeles pre-entraines via LLMaaS et ne necessite pas d'entrainement local.

---

## 3.2 Robustesse -- Mineurs

---

### P-43 (ROB-23) -- MINEUR : `_expit()` -- overflow numpy silencieux sur valeurs extremes de dot product

**Fichier :** `question_store.py` -- lignes 36-45

**Code incrimine :**

```python
def _expit(x):
    return 1 / (1 + np.exp(-x))
```

**Appele par :** `_scale_scores` -- ligne 417

```python
if self.similarity_function == "dot_product":
    return [_expit(float(score / DOT_PRODUCT_SCALING_FACTOR)) for score in scores]
```

**Probleme :** Pour des scores dot product tres negatifs (ex : `x = -1000`), `np.exp(-x) = np.exp(1000)` provoque un overflow --> `np.inf` --> `_expit = 1 / (1 + inf) = 0.0`. Cela fonctionne numeriquement mais genere un `RuntimeWarning: overflow encountered in exp`.

**Impact :** RuntimeWarning dans les logs si le mode dot_product est active. Pas de crash en configuration actuelle.

**Solution :** Utiliser `scipy.special.expit` (stable numeriquement) ou clamper l'entree :

```python
def _expit(x):
    # Clamp pour eviter l'overflow
    x = np.clip(x, -500, 500)
    return 1 / (1 + np.exp(-x))
```

---

## 3.3 Performance -- Mineurs

---

### P-44 (PERF-12) -- MINEUR : Fallback threshold --> envoie TOUS les resultats au reranker

**Fichier :** `suggestion_engine.py` -- lignes 190-195

**Code incrimine :**

```python
filtered_questions = [
    question for question in similar_questions
    if question.score >= self.settings.threshold  # threshold = 0.1
]
logger.info(f"Step 3: Filtered down to {len(filtered_questions)} questions ...")

if not filtered_questions:
    filtered_questions = similar_questions  # <-- FALLBACK : utilise TOUT
```

**Probleme :** Quand aucune question ne passe le seuil de 0.1 (cas frequent avec des emails hors domaine : plaintes en anglais, spam, emails internes non pertinents), le fallback **envoie les 30 resultats** (`similarity_top_k * 2 = 30`) au pipeline de reranking.

La chaine qui suit :
1. `_build_documents_to_rank` recupere le contenu texte pour chaque response model distinct
2. Le LLMaaS reranker recoit **tous ces textes** -- le cout de l'appel reranking augmente lineairement avec le nombre de documents

C'est precisement sur les requetes hors domaine (les plus frequentes en edge case) que le pipeline fait le plus de travail et que le resultat est le moins pertinent.

**Impact :** Les requetes les plus inutiles sont les plus couteuses en temps LLMaaS et en latence.

**Solution :** Quand le fallback s'active, limiter le nombre de candidats envoyes au reranker et enrichir l'observabilite :

```python
if not filtered_questions:
    # Prendre uniquement les N meilleurs meme sous le seuil
    filtered_questions = similar_questions[:self.settings.reranker_top_k]
    enrich_event(threshold_fallback=True)
    logger.warning(
        "No question above threshold %.2f -- using top %d by score.",
        self.settings.threshold,
        len(filtered_questions),
    )
```

---

### P-45 (PERF-14) -- MINEUR : Aucun cache d'embedding pour les requetes repetees

**Fichier :** `suggestion_engine.py` -- ligne 181

**Code incrimine :**

```python
embedding_result = self.embedder.embed_text(text=query.strip())
```

**Probleme :** Chaque requete declenche un appel LLMaaS pour l'embedding, meme si le meme email (ou un email tres similaire) a deja ete traite. Dans un contexte bancaire :

- Les conseillers traitent des reclamations avec des formulations recurrentes
- Un meme email peut etre soumis plusieurs fois (refresh, retry client)
- Les emails de test utilisent les memes corpus

Un cache LRU sur le contenu de l'email eviterait les appels LLMaaS redondants.

**Impact :** Appels LLMaaS inutiles (~100-300 ms + cout API) pour des requetes identiques.

**Solution :** Cache LRU en memoire, indexe par hash du contenu :

```python
from functools import lru_cache
import hashlib

class LLMaaSEmbedder(LLMService):
    @lru_cache(maxsize=512)
    def _embed_cached(self, content_hash: str, text: str) -> tuple[list[float], dict]:
        result = self.embed([text])
        return result.data[0].embedding, result.usage.model_dump()

    def embed_text(self, text: str) -> dict:
        content_hash = hashlib.md5(text.encode()).hexdigest()
        embedding, usage = self._embed_cached(content_hash, text)
        return {"embedding": embedding, "meta": {"model": self.model_name, **usage}}
```

---

### P-46 (PERF-20) -- MINEUR : `float64` par defaut pour les embeddings -- le double de la memoire necessaire

**Fichier :** `question_store.py` -- `_stack_document_embeddings` -- ligne 336

**Code incrimine :**

```python
matrix = np.array([doc.embedding for doc in documents])
# dtype par defaut = float64
```

**Fichier :** `document.py` -- ligne 39

```python
embedding: Optional[list[float]] = Field(...)
# Python float = float64
```

**Probleme :** Les embeddings sont stockes en Python `float` (64 bits) et convertis en `np.float64` par defaut. BGE-M3 produit des embeddings dont la precision utile est de **float32** (les modeles d'embedding travaillent en float32 ou float16 en interne).

**Impact :** Consommation memoire double, bandwidth memoire double dans les operations numpy.

**Solution :** Forcer `float32` au chargement et dans la construction de la matrice :

```python
# Dans _stack_document_embeddings (ou le cache)
matrix = np.array([doc.embedding for doc in documents], dtype=np.float32)

# Dans save_to_disk / load_from_disk, convertir au stockage
data["documents"] = [
    {**doc.model_dump(), "embedding": [float(x) for x in doc.embedding]}
    for doc in self.storage.values()
]
```

---

## 3.4 Qualite de code -- Mineurs

---

### P-47 (CQ-01) -- MINEUR : Membres d'enum incoherents -- mix `UPPER_CASE` / `lower_case` dans le meme fichier

**Fichier :** `enums.py`

**Code incrimine :**

```python
class DuplicatePolicy(Enum):
    NONE = "none"           # <-- UPPER_CASE
    SKIP = "skip"
    OVERWRITE = "overwrite"
    FAIL = "fail"

class RequestValidation(Enum):
    validated = "validated"  # <-- lower_case
    failed = "failed"

class Status(Enum):
    ok = "ok"               # <-- lower_case
    ko = "ko"

class Outcome(Enum):
    success = "success"     # <-- lower_case
    error = "error"
    timeout = "timeout"
```

**Probleme :** PEP 8 recommande `UPPER_CASE` pour les membres d'enum (car ce sont des constantes). `DuplicatePolicy` respecte la convention, mais `RequestValidation`, `Status` et `Outcome` utilisent `lower_case`. Trois conventions dans le meme fichier.

**Solution :**

```python
class RequestValidation(Enum):
    VALIDATED = "validated"
    FAILED = "failed"

class Status(Enum):
    OK = "ok"
    KO = "ko"

class Outcome(Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
```

---

### P-48 (CQ-03) -- MINEUR : Descriptions de Fields inversees dans `LLMSettings`

**Fichier :** `llm_settings.py` -- lignes 35-38

**Code incrimine :**

```python
api_uri: str = Field(
    default="", description="The API key used for authenticating requests..."
    #                        ^^^^^^^ C'est l'URI, pas la cle API
)
api_key: str = Field(
    default="", description="The base URL for accessing the API endpoints."
    #                        ^^^^^^^ C'est la cle, pas l'URL
)
```

**Probleme :** Les descriptions de `api_uri` et `api_key` sont **inversees** : `api_uri` est decrit comme « The API key » et `api_key` comme « The base URL ». C'est un copier-coller non relu.

**Solution :** Inverser les descriptions.

---

### P-49 (CQ-04) -- MINEUR : Nommage variable `question` pour une liste de documents

**Fichier :** `candidate_factory.py` -- lignes 98-99

**Code incrimine :**

```python
selected_candidates: list[SelectedCandidate] = [
    documents_to_selection_candidate(response_model_id=model_id, documents=question)
    #                                                            ^^^^^^^^^^^^^^^^^^
    # `question` est la variable d'iteration du for, mais elle represente une LISTE de Documents
    for model_id, question in questions_by_model.items()
]
```

**Probleme :** La variable `question` (singulier) contient en realite une `list[Document]` (pluriel). Le parametre `documents=question` est semantiquement deroutant.

**Solution :** Renommer en `questions` :

```python
for model_id, questions in questions_by_model.items()
```

---

### P-50 (CQ-05) -- MINEUR : Incoherence `_logger` vs `logger` pour le nom du logger

**Fichiers :** Tout le projet

**Code incrimine :**

```python
# 90% des fichiers :
logger = getLogger(LOGGER_NAME)

# Certains fichiers (load_config.py, train.py) :
_logger = logging.getLogger(LOGGER_NAME)
```

**Probleme :** La plupart des modules utilisent `logger` (sans underscore), mais `load_config.py` et `train.py` utilisent `_logger`. Les deux sont fonctionnellement identiques, mais la convention du projet est `logger`.

**Solution :** Uniformiser sur `logger` partout.

---

### P-51 (CQ-07) -- MINEUR : `abort(400)` dans le decorateur `@wide_event` -- melange des responsabilites

**Fichier :** `utils_wide_event.py` -- lignes 86-94

**Code incrimine :**

```python
except Exception as error:
    event.set_error(error)
    error_name = type(error).__name__
    message = f"API Internal Error - A {error_name} occurred..."
    logger.error(message)
    abort(400, description=f"{message}")    # <-- Logique HTTP dans un decorateur d'observabilite
    raise                                    # <-- Code mort
```

**Probleme :** Le decorateur `@wide_event` a deux responsabilites :
1. **Observabilite** : creer/emettre un WideEvent par requete --> legitime
2. **Gestion d'erreur HTTP** : appeler `abort(400)` pour retourner une reponse Flask --> hors perimetre

Le decorateur viole le **Single Responsibility Principle** (SRP). Un decorateur d'instrumentation ne devrait pas controler le comportement HTTP de l'API.

**Solution :** Separer les responsabilites : le decorateur ne fait que l'observabilite, la gestion d'erreur HTTP est geree par un error handler Flask dedie.

---

### P-52 (CQ-11) -- MINEUR : `self.storage.keys()` au lieu de `self.storage` dans les tests d'appartenance

**Fichier :** `question_store.py` -- lignes 206, 214, 230

**Code incrimine :**

```python
if document.id in self.storage.keys():    # <-- .keys() inutile
    ...
if doc_id not in self.storage.keys():     # <-- .keys() inutile
    continue
```

**Probleme :** En Python, `key in dict` est idiomatique et O(1). `key in dict.keys()` cree une vue inutile. Le resultat est identique, mais c'est un signe de code non pythonique.

**Solution :**

```python
if document.id in self.storage:
    ...
if doc_id not in self.storage:
    continue
```

---

### P-53 (CQ-12) -- MINEUR : Pattern `isinstance` en cascade sans branche par defaut

**Fichier :** `error_handler.py` -- `handle_http_error` -- lignes 81-88

**Code incrimine :**

```python
if isinstance(error, HTTPError):
    status = error.response.status_code
    text = error.response.content.decode("utf-8")
    message = ...
elif isinstance(error, (ConnectionError, Timeout)):
    message = ...
```

**Fichier :** `suggestion_factory.py` -- lignes 66-77

```python
if isinstance(error, FileNotFoundError):
    message = ...
elif isinstance(error, (ValueError, DeserializationError)):
    message = ...
else:
    message = ...
```

**Probleme :** Les cascades `isinstance` sont acceptables quand il y a 2-3 branches, mais quand elles se multiplient, le pattern standard est un **handler registry** ou un **dispatch dictionnaire**. Ici, le nombre de branches est encore raisonnable, mais l'absence de `else` dans `handle_http_error` (pas de branche par defaut pour les `RequestException` generiques qui ne sont ni `HTTPError` ni `ConnectionError`/`Timeout`) est un oubli.

**Impact :** Mineur. Le code est lisible mais pas extensible.

---

### P-54 (CQ-24) -- MINEUR : `project.description = "Template IA project"` -- pas adapte

**Fichier :** `pyproject.toml` -- ligne 4

**Code incrimine :**

```toml
description = "Template  IA project"
```

**Probleme :** La description du projet est celle du template (avec double espace). Elle devrait decrire SmartInbox Outlook.

**Solution :**

```toml
description = "SmartInbox Outlook - AI-powered email response suggestion for banking advisors"
```

---

## 3.5 Documentation -- Mineurs

---

### P-55 (DOC-13) -- MINEUR : `llm_settings.py` docstring dit "summarization" au lieu de "suggestion"

**Fichier :** `llm_settings.py` -- ligne 29 (docstring de la classe `LLMSettings`)

**Code incrimine :**

```python
"""
Attributes
----------
model_name : str
    The name of the model to use for summarization.
"""
```

**Probleme :** La docstring indique « model to use for summarization » -- meme residu de copier-coller.

**Solution :**

```python
"""The name of the model to use for the suggestion pipeline (embedding or reranking)."""
```

---

### P-56 (DOC-21) -- MINEUR : `troubleshooting.md` -- section « Support » vide

**Fichier :** `troubleshooting.md` -- lignes 184-187

**Code incrimine :**

```markdown
## Support

Fournissez des informations sur la facon dont les utilisateurs peuvent obtenir de l'aide
ou du support supplementaire si necessaire.
```

**Probleme :** La section Support est un placeholder jamais rempli. Il reste l'instruction au redacteur.

**Impact :** Un MLE bloque ne sait pas qui contacter.

**Solution :** Remplir avec les informations de contact reelles :

```markdown
## Support

- **Team SmartInbox** : canal Teams `#smartinbox-outlook-support`
- **Ops / Infra Domino** : creer un ticket Jira dans le projet AER_IA
```

---
---

# ANNEXE -- Liste des fichiers concernes

| Fichier | Nombre de problemes |
|---------|---------------------|
| `suggestion_engine.py` | 7 |
| `question_store.py` | 6 |
| `llm_settings.py` | 5 |
| `email_suggestion_request.py` | 5 |
| `llm_service.py` | 3 |
| `wide_event.py` | 3 |
| `io_utils.py` | 1 |
| `main.py` | 1 |
| `config_context.py` | 1 |
| `__init__.py` | 1 |
| `selected_candidate.py` | 1 |
| `candidate_factory.py` | 2 |
| `llm_reranker.py` | 1 |
| `llm_embedder.py` | 1 |
| `session_manager.py` | 2 |
| `validation_exception.py` | 1 |
| `token_auth.py` | 1 |
| `extra_parameters.py` | 1 |
| `enums.py` | 1 |
| `error_handler.py` | 1 |
| `utils_wide_event.py` | 1 |
| `load_config.py` | 1 |
| `request_llm_embedding.py` | 1 |
| `request_llm_reranker.py` | 1 |
| `train.py` | 1 |
| `app_config.yml` | 1 |
| `project_config_prod.yml` | 1 |
| `pyproject.toml` | 1 |
| Documentation (8 fichiers) | 12 |
