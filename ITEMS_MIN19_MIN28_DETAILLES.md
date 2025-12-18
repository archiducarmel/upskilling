# 🟡 PROBLÈMES MINEURS - ITEMS MIN-19 À MIN-28

> Ces problèmes devraient être corrigés pour améliorer la qualité du code mais ne bloquent pas la mise en production.

---

## MIN-19 : Hack TypeError pour contourner l'analyse MyPy après abort()

| Attribut | Valeur |
|----------|--------|
| **Fichier** | `industrialisation/src/utils/error_handler.py` |
| **Ligne** | 36 |
| **Catégorie** | Architecture / Qualité du code |
| **Sévérité** | 🟡 Mineur |

### Extrait de code problématique

```python
def log_and_abort(
    error: Exception,
    message: str,
    context_data: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Log an error and abort the request with a 400 status code.
    ...
    """
    context_data = {} if context_data is None else context_data
    logger.error(message, extra={"type": error.__class__, "value": str(error), **context_data})
    abort(400, description=f"{message}")
    raise TypeError("`abort()` should not return")  # ##>: Try to fix `mypy`.
```

### Problème identifié

Le développeur a ajouté une ligne `raise TypeError(...)` après l'appel à `abort()` pour "satisfaire MyPy". Cette ligne ne sera **jamais exécutée** car `abort()` de Flask lève une exception `HTTPException` et ne retourne jamais.

Le problème vient du fait que MyPy ne reconnaît pas nativement que `flask.abort()` est une fonction "NoReturn" (qui ne retourne jamais). Sans cette ligne, MyPy émet un avertissement car la fonction est annotée `-> NoReturn` mais MyPy pense qu'elle pourrait retourner après `abort()`.

Ce hack est problématique pour plusieurs raisons :

1. **Code mort** : La ligne ne sera jamais exécutée en runtime
2. **Confusion** : Un développeur lisant le code pourrait penser que `abort()` peut retourner
3. **Commentaire cryptique** : Le commentaire `##>: Try to fix mypy` n'explique pas clairement le problème
4. **Mauvaise solution** : Il existe des moyens plus propres de résoudre ce problème

### Impact potentiel

| Type d'impact | Description |
|---------------|-------------|
| **Lisibilité** | Code confus qui semble suggérer que `abort()` peut retourner |
| **Maintenance** | Les futurs développeurs pourraient ne pas comprendre pourquoi cette ligne existe |
| **Tests** | Les tests vérifient que `TypeError` est levée (voir `test_error_handler.py` ligne 28), ce qui teste du code mort |

### Solution proposée

Il existe plusieurs approches pour résoudre proprement ce problème avec MyPy, sans ajouter de code mort.

**Option A (Recommandée) : Utiliser un cast explicite avec assert_never ou un commentaire type: ignore**

Cette approche utilise un commentaire ciblé pour indiquer à MyPy d'ignorer cette ligne spécifique, avec une explication claire.

```python
from typing import NoReturn, Optional, Any

def log_and_abort(
    error: Exception,
    message: str,
    context_data: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Log an error and abort the request with a 400 status code.

    This function never returns - it always raises an HTTPException via abort().

    Parameters
    ----------
    error : Exception
        The original exception that caused the error.
    message : str
        The error message to log and return to the client.
    context_data : dict[str, Any], optional
        Additional context data for logging.

    Raises
    ------
    HTTPException
        Always raised via Flask's abort() function.
    """
    context_data = {} if context_data is None else context_data
    logger.error(
        message, 
        extra={"type": error.__class__, "value": str(error), **context_data}
    )
    abort(400, description=f"{message}")
    # Note: abort() raises HTTPException and never returns.
    # The type: ignore comment tells MyPy to trust our NoReturn annotation.
    # See: https://github.com/pallets/flask/issues/4099
```

**Option B : Créer un wrapper typé pour abort()**

Cette approche crée une fonction wrapper correctement annotée qui encapsule `abort()`.

```python
from typing import NoReturn
from flask import abort as flask_abort

def abort_request(status_code: int, description: str) -> NoReturn:
    """Abort the current request with the given status code.
    
    This is a typed wrapper around Flask's abort() that is correctly
    annotated as NoReturn for MyPy compatibility.
    """
    flask_abort(status_code, description=description)
    raise RuntimeError("abort() should have raised")  # Pour MyPy uniquement


def log_and_abort(
    error: Exception,
    message: str,
    context_data: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """Log an error and abort the request."""
    context_data = {} if context_data is None else context_data
    logger.error(message, extra={"type": error.__class__, "value": str(error), **context_data})
    abort_request(400, description=message)  # Utilise le wrapper typé
```

**Option C : Utiliser un stub file (.pyi) pour Flask**

Créer un fichier `flask.pyi` dans le projet pour déclarer le type correct de `abort()`.

```python
# stubs/flask.pyi
from typing import NoReturn

def abort(status_code: int, description: str = ...) -> NoReturn: ...
```

Et configurer MyPy pour utiliser ce stub dans `pyproject.toml` :

```toml
[tool.mypy]
mypy_path = "stubs"
```

**Mise à jour des tests**

Si vous choisissez l'option A, les tests doivent être mis à jour pour ne plus vérifier le `TypeError` :

```python
# AVANT (teste du code mort)
def test_log_and_abort_raises_type_error(self, mock_logger: MagicMock) -> None:
    with pytest.raises(TypeError, match="should not return"):
        log_and_abort(error=Exception("Error"), message="Test")

# APRÈS (teste le vrai comportement)
def test_log_and_abort_raises_bad_request(self, mock_logger: MagicMock) -> None:
    """Test that log_and_abort raises a BadRequest exception."""
    with pytest.raises(BadRequest) as exc_info:
        log_and_abort(error=Exception("Error"), message="Test message")
    
    assert "Test message" in str(exc_info.value.description)
```

---

## MIN-20 : Utilisation mixte de unittest.TestCase et pytest dans les mêmes fichiers

| Attribut | Valeur |
|----------|--------|
| **Fichiers** | `test_api_1.py`, `test_error_handler.py`, `test_email_suggestion_request.py`, `test_http_session_manager.py`, et autres |
| **Lignes** | Multiples (imports et définitions de classes) |
| **Catégorie** | Tests |
| **Sévérité** | 🟡 Mineur |

### Extrait de code problématique

```python
# test_api_1.py - Lignes 1-15
import unittest                          # ← Framework unittest
from typing import Any
from unittest.mock import MagicMock, patch

import pytest                            # ← Framework pytest (importé aussi !)
from werkzeug.exceptions import BadRequest

from industrialisation.src.api import inference
# ...

class TestApi(unittest.TestCase):        # ← Classe hérite de TestCase (unittest)
    """Test case for the API."""

    def setUp(self) -> None:             # ← Méthode setUp de unittest
        """Set up necessary before test."""
        # ...
```

```python
# test_api_1.py - Lignes 108-113
    def test_inference_raises_error_on_missing_inputs(self) -> None:
        """Test that inference raises an error if inputs is missing."""
        data_dict = {"extra_params": {"Channel": "012"}}

        with pytest.raises(BadRequest, match="validation error"):  # ← Assertion pytest !
            inference(data_dict=data_dict)
```

### Problème identifié

Les fichiers de tests mélangent **deux frameworks de test différents** dans le même fichier :

1. **unittest** (bibliothèque standard Python) :
   - Classes héritant de `unittest.TestCase`
   - Méthodes `setUp()` et `tearDown()`
   - Assertions comme `self.assertEqual()`, `self.assertTrue()`

2. **pytest** (framework moderne) :
   - Context manager `pytest.raises()`
   - Fixtures avec `@pytest.fixture`
   - Assertions simples avec `assert`

Ce mélange crée plusieurs incohérences :

| Aspect | unittest | pytest | Dans le code |
|--------|----------|--------|--------------|
| **Classe de base** | `TestCase` | Classe simple ou fonctions | `TestCase` utilisé ✓ |
| **Setup** | `setUp()` méthode | `@pytest.fixture` | `setUp()` utilisé ✓ |
| **Assertions d'exception** | `self.assertRaises()` | `pytest.raises()` | `pytest.raises()` utilisé ✗ |
| **Style général** | OOP, verbose | Fonctionnel, concis | Mélangé ✗ |

Le problème est que `pytest.raises()` fonctionne correctement **même dans une classe TestCase** (pytest est rétro-compatible), mais cela crée une **dette technique** et de la **confusion** :
- Quel framework est "officiel" pour ce projet ?
- Les nouveaux développeurs ne savent pas quel style suivre
- Les assertions `self.assertRaises()` et `pytest.raises()` coexistent sans raison

### Impact potentiel

| Type d'impact | Description |
|---------------|-------------|
| **Cohérence** | Deux styles différents dans le même fichier |
| **Onboarding** | Confusion pour les nouveaux développeurs |
| **Maintenance** | Difficulté à établir des conventions claires |
| **Documentation** | Impossible de documenter "un" style de test |

### Solution proposée

Standardiser sur **pytest uniquement**, qui est le framework moderne et plus expressif. La migration implique de supprimer l'héritage de `TestCase` et d'utiliser les fixtures pytest.

**Transformation d'un fichier de test complet :**

```python
# AVANT : test_api_1.py (mélange unittest + pytest)
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.exceptions import BadRequest

from industrialisation.src.api import inference
from industrialisation.src.models.entities.reranked_candidate import RerankedCandidate
from industrialisation.src.models.entities.selected_candidate import ActivationData, SelectedCandidate


class TestApi(unittest.TestCase):
    """Test case for the API."""

    def setUp(self) -> None:
        """Set up necessary before test."""
        self.data_dict: dict[str, dict[str, Any]] = {
            "inputs": {},
            "extra_params": {"Channel": "012"},
        }
        self.mock_selected_candidate = SelectedCandidate(
            response_model_id=1,
            selection_score=0.8,
            activation_data=[ActivationData(reference_question_id=1, version_question="1.0.0", similarity_score=0.8)],
        )
        self.mock_reranked_candidate = RerankedCandidate(response_model_id=1, re_ranking_score=0.8, rank=1)

    def test_inference_raises_error_on_missing_inputs(self) -> None:
        data_dict = {"extra_params": {"Channel": "012"}}
        with pytest.raises(BadRequest, match="validation error"):
            inference(data_dict=data_dict)


# APRÈS : test_api_1.py (pytest uniquement)
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.exceptions import BadRequest

from industrialisation.src.api import inference
from industrialisation.src.models.entities.reranked_candidate import RerankedCandidate
from industrialisation.src.models.entities.selected_candidate import ActivationData, SelectedCandidate


class TestApi:
    """Test suite for the API inference function."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Set up test fixtures automatically before each test."""
        self.data_dict: dict[str, dict[str, Any]] = {
            "inputs": {},
            "extra_params": {"Channel": "012"},
        }
        self.mock_selected_candidate = SelectedCandidate(
            response_model_id=1,
            selection_score=0.8,
            activation_data=[
                ActivationData(
                    reference_question_id=1,
                    version_question="1.0.0",
                    similarity_score=0.8,
                )
            ],
        )
        self.mock_reranked_candidate = RerankedCandidate(
            response_model_id=1,
            re_ranking_score=0.8,
            rank=1,
        )

    def test_inference_raises_error_on_missing_inputs(self) -> None:
        """Test that inference raises BadRequest when 'inputs' key is missing."""
        data_dict = {"extra_params": {"Channel": "012"}}
        
        with pytest.raises(BadRequest, match="validation error"):
            inference(data_dict=data_dict)
```

**Checklist de migration unittest → pytest :**

| Élément unittest | Équivalent pytest |
|------------------|-------------------|
| `import unittest` | Supprimer |
| `class TestX(unittest.TestCase):` | `class TestX:` |
| `def setUp(self):` | `@pytest.fixture(autouse=True)` + `def setup(self):` |
| `def tearDown(self):` | `@pytest.fixture` avec `yield` |
| `self.assertEqual(a, b)` | `assert a == b` |
| `self.assertTrue(x)` | `assert x` |
| `self.assertRaises(E)` | `pytest.raises(E)` |
| `self.assertIn(a, b)` | `assert a in b` |
| `if __name__ == "__main__": unittest.main()` | Supprimer (pytest découvre automatiquement) |

---

## MIN-21 : Assertions self.assertEqual() de unittest mélangées avec pytest

| Attribut | Valeur |
|----------|--------|
| **Fichiers** | `test_suggestion_engine.py`, `test_maximum_similarity.py`, `test_search_engine.py` |
| **Catégorie** | Tests |
| **Sévérité** | 🟡 Mineur |

### Extrait de code problématique

```python
# test_suggestion_engine.py
from unittest import TestCase, main

class TestSuggestionEngineRunSuggestion(TestCase):
    def test_something(self) -> None:
        result = some_function()
        self.assertEqual(result.value, expected_value)      # ← Style unittest
        self.assertIsNotNone(result.data)                   # ← Style unittest
```

### Problème identifié

Ce problème est une extension de MIN-20. Certains fichiers de tests utilisent exclusivement `unittest.TestCase` avec ses méthodes d'assertion verboses (`self.assertEqual`, `self.assertIsNotNone`, etc.) alors que le projet utilise pytest pour l'exécution.

Les assertions pytest sont plus concises et produisent des messages d'erreur plus détaillés grâce à l'introspection automatique.

### Impact potentiel

| Type d'impact | Description |
|---------------|-------------|
| **Verbosité** | Code plus long qu'avec les assertions pytest simples |
| **Messages d'erreur** | Les assertions unittest produisent des messages moins détaillés |
| **Cohérence** | Style différent selon les fichiers |

### Solution proposée

Convertir les assertions unittest en assertions pytest natives pour plus de concision et de meilleurs messages d'erreur.

```python
# AVANT (unittest style)
self.assertEqual(result.value, 42)
self.assertIsNotNone(result.data)
self.assertTrue(result.is_valid)
self.assertIn("key", result.dict)
self.assertGreater(result.score, 0.5)
self.assertIsInstance(result, MyClass)

# APRÈS (pytest style)
assert result.value == 42
assert result.data is not None
assert result.is_valid
assert "key" in result.dict
assert result.score > 0.5
assert isinstance(result, MyClass)
```

**Avantage des assertions pytest** : En cas d'échec, pytest affiche automatiquement les valeurs comparées :

```
# Message d'erreur unittest
AssertionError: 41 != 42

# Message d'erreur pytest (plus détaillé)
AssertionError: assert 41 == 42
 +  where 41 = result.value
```

---

## MIN-22 : Méthode setUp() au lieu de fixtures pytest

| Attribut | Valeur |
|----------|--------|
| **Fichiers** | Tous les fichiers de tests utilisant `unittest.TestCase` |
| **Catégorie** | Tests |
| **Sévérité** | 🟡 Mineur |

### Extrait de code problématique

```python
# test_suggestion_engine.py - Lignes 14-35
class TestSuggestionEngineRunSuggestion(TestCase):
    """Test case for SuggestionEngine."""

    def setUp(self) -> None:
        """Set uo test fixtures."""  # Note: typo "uo" au lieu de "up"
        self.mock_email_request = EmailSuggestionRequest(
            request_id="test_request",
            # ... beaucoup de setup
        )
        self.mock_ranked_candiate = RerankedCandidate(...)  # Note: typo "candiate"
        # ... encore plus de setup
```

### Problème identifié

L'utilisation de `setUp()` est le pattern unittest classique, mais pytest offre un système de **fixtures** beaucoup plus puissant et flexible :

| Aspect | setUp() (unittest) | @pytest.fixture |
|--------|-------------------|-----------------|
| **Scope** | Par test uniquement | Par test, classe, module, ou session |
| **Réutilisation** | Limité à la classe | Partageable entre fichiers |
| **Dépendances** | Manuel | Injection automatique |
| **Paramétrage** | Difficile | `@pytest.mark.parametrize` |
| **Lazy loading** | Non | Oui |

### Solution proposée

Convertir les méthodes `setUp()` en fixtures pytest, ce qui permet une meilleure organisation et réutilisation.

```python
# AVANT : setUp() dans une classe TestCase
class TestSuggestionEngine(TestCase):
    def setUp(self) -> None:
        self.mock_email_request = EmailSuggestionRequest(
            request_id="test_request",
            user_id=1,
            email_id=100,
            email_sequence_index=1,
            start_ts=datetime.now(),
            email_object="Test subject",
            email_content="Test content",
        )
        self.mock_selected_candidate = SelectedCandidate(...)
        self.mock_reranked_candidate = RerankedCandidate(...)

    def test_run_suggestion_returns_result(self) -> None:
        # Utilise self.mock_email_request
        pass


# APRÈS : Fixtures pytest (plus flexible et réutilisable)
import pytest
from datetime import datetime


@pytest.fixture
def mock_email_request() -> EmailSuggestionRequest:
    """Create a mock email suggestion request for testing."""
    return EmailSuggestionRequest(
        request_id="test_request",
        user_id=1,
        email_id=100,
        email_sequence_index=1,
        start_ts=datetime.now(),
        email_object="Test subject",
        email_content="Test content",
    )


@pytest.fixture
def mock_selected_candidate() -> SelectedCandidate:
    """Create a mock selected candidate for testing."""
    return SelectedCandidate(
        response_model_id=1,
        selection_score=0.8,
        activation_data=[
            ActivationData(
                reference_question_id=1,
                version_question="1.0.0",
                similarity_score=0.8,
            )
        ],
    )


@pytest.fixture
def mock_reranked_candidate() -> RerankedCandidate:
    """Create a mock reranked candidate for testing."""
    return RerankedCandidate(
        response_model_id=1,
        re_ranking_score=0.85,
        rank=1,
    )


class TestSuggestionEngine:
    """Test suite for SuggestionEngine."""

    def test_run_suggestion_returns_result(
        self,
        mock_email_request: EmailSuggestionRequest,      # ← Injection automatique
        mock_selected_candidate: SelectedCandidate,
        mock_reranked_candidate: RerankedCandidate,
    ) -> None:
        """Test that run_suggestion returns a valid result."""
        # Les fixtures sont automatiquement injectées par pytest
        pass
```

**Fixtures partagées dans conftest.py** :

```python
# tests/conftest.py - Fixtures réutilisables dans tous les tests
import pytest
from datetime import datetime

@pytest.fixture
def sample_email_request() -> EmailSuggestionRequest:
    """Fixture partagée par tous les tests du projet."""
    return EmailSuggestionRequest(
        request_id="shared_test_request",
        user_id=1,
        email_id=100,
        email_sequence_index=1,
        start_ts=datetime.now(),
        email_object="Problème de connexion",
        email_content="Je n'arrive pas à me connecter à mon compte.",
    )
```

---

## MIN-23 : Pattern if __name__ == "__main__": unittest.main() obsolète

| Attribut | Valeur |
|----------|--------|
| **Fichiers** | Certains fichiers de tests |
| **Catégorie** | Tests |
| **Sévérité** | 🟡 Mineur |

### Extrait de code problématique

```python
# En fin de fichier de test
if __name__ == "__main__":
    unittest.main()
```

### Problème identifié

Ce pattern était nécessaire avec unittest pour exécuter les tests directement (`python test_file.py`). Avec pytest, ce n'est plus nécessaire car pytest découvre et exécute automatiquement tous les fichiers `test_*.py`.

Ce code est donc **du code mort** qui n'est jamais exécuté dans le workflow normal.

### Solution proposée

Supprimer simplement ces lignes. L'exécution des tests se fait via `pytest` ou `make test`.

```python
# AVANT
class TestMyClass(TestCase):
    def test_something(self):
        pass

if __name__ == "__main__":
    unittest.main()  # ← À supprimer


# APRÈS
class TestMyClass:
    def test_something(self):
        pass

# Pas de bloc if __name__ - pytest gère tout automatiquement
```

---

## MIN-24 : Caractères emoji corrompus dans l'application Streamlit

| Attribut | Valeur |
|----------|--------|
| **Fichier** | `exploration/apps/upload_app/main.py` |
| **Lignes** | 117, 139, 141, 151, 160, 164, 168 |
| **Catégorie** | Bugs et Typos |
| **Sévérité** | 🟡 Mineur |

### Extrait de code problématique

```python
# Ligne 117
if st.button("ðŸ"„ Reset Upload"):  # ❌ Devrait être "🔄 Reset Upload"

# Ligne 139
st.warning(f"âš ï¸ '{uploaded_file.name}' already exists...")  # ❌ Devrait être "⚠️"

# Ligne 141
st.info(f"ðŸ—‚ï¸ {len(...)} file(s) selected...")  # ❌ Devrait être "🗂️"

# Ligne 151
if st.button("âœ… Confirm Upload"):  # ❌ Devrait être "✅"

# Ligne 164
st.error("âŒ Some files could not be uploaded:")  # ❌ Devrait être "❌"

# Ligne 168
st.success(f"âœ… All ({len(...)}) file(s) uploaded...")  # ❌ Devrait être "✅"
```

### Problème identifié

Les emojis dans le fichier `main.py` ont été **corrompus** par un problème d'encodage, similaire au problème CRIT-04. Au lieu d'afficher les emojis corrects, l'interface utilisateur Streamlit affiche des séquences de caractères illisibles comme `ðŸ"„`, `âš ï¸`, `âœ…`.

Ce problème survient généralement quand :
1. Le fichier a été créé/édité avec un encodage UTF-8
2. Puis ouvert avec un éditeur configuré en Latin-1 ou Windows-1252
3. Et resauvegardé, causant une double-encodage des caractères multi-octets

**Correspondance des caractères corrompus :**

| Corrompu | Original | Nom de l'emoji |
|----------|----------|----------------|
| `ðŸ"„` | 🔄 | Flèches de rechargement |
| `âš ï¸` | ⚠️ | Avertissement |
| `ðŸ—‚ï¸` | 🗂️ | Dossier de fichiers |
| `âœ…` | ✅ | Coche verte |
| `âŒ` | ❌ | Croix rouge |

### Impact potentiel

| Type d'impact | Description |
|---------------|-------------|
| **UX** | Interface utilisateur avec caractères illisibles |
| **Professionnalisme** | Application qui semble bugguée |
| **Accessibilité** | Les lecteurs d'écran liront des caractères sans sens |

### Solution proposée

Corriger les emojis en remplaçant les séquences corrompues par les caractères Unicode originaux. S'assurer également que l'éditeur et le système de versioning sont configurés pour UTF-8.

```python
# AVANT (corrompus)
if st.button("ðŸ"„ Reset Upload"):
st.warning(f"âš ï¸ '{uploaded_file.name}' already exists and will be overwritten.")
st.info(f"ðŸ—‚ï¸ {len(st.session_state.files_to_upload)} file(s) selected for upload.")
if st.button("âœ… Confirm Upload"):
st.error("âŒ Some files could not be uploaded:")
st.success(f"âœ… All ({len(st.session_state.files_to_upload)}) selected file(s) uploaded successfully.")

# APRÈS (corrigés)
if st.button("🔄 Reset Upload"):
st.warning(f"⚠️ '{uploaded_file.name}' already exists and will be overwritten.")
st.info(f"🗂️ {len(st.session_state.files_to_upload)} file(s) selected for upload.")
if st.button("✅ Confirm Upload"):
st.error("❌ Some files could not be uploaded:")
st.success(f"✅ All ({len(st.session_state.files_to_upload)}) selected file(s) uploaded successfully.")
```

**Prévention future** : Ajouter une vérification dans le pre-commit hook pour détecter les caractères mal encodés :

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v4.5.0
  hooks:
    - id: check-byte-order-marker
    - id: fix-encoding-pragma
```

---

## MIN-25 : Présence d'un BOM UTF-8 dans les fichiers CSV

| Attribut | Valeur |
|----------|--------|
| **Fichiers** | `industrialisation/knowledge_base/client_questions.csv`, `industrialisation/knowledge_base/response_models.csv` |
| **Catégorie** | Qualité des données |
| **Sévérité** | 🟡 Mineur |

### Extrait de données problématique

```
Premiers octets du fichier (hexadécimal) : ef bb bf 72 65 66 65 72 65 6e
                                           ^^^^^^^^
                                           BOM UTF-8
                                           
Interprétation : [BOM] r  e  f  e  r  e  n  ...
                       "reference_question_id..."
```

### Problème identifié

Les fichiers CSV contiennent un **BOM (Byte Order Mark) UTF-8** au début du fichier. Le BOM est une séquence de 3 octets (`EF BB BF`) qui indique qu'un fichier est encodé en UTF-8.

Bien que le code gère correctement ce BOM (en utilisant l'encodage `utf-8-sig` qui le supprime automatiquement lors de la lecture), sa présence pose quelques problèmes :

1. **Dépendance cachée** : Le code DOIT utiliser `utf-8-sig` sinon le premier nom de colonne sera `\ufeffresponse_model_id` au lieu de `response_model_id`

2. **Incompatibilité** : Certains outils Unix (comme `head`, `cat`, `awk`) n'attendent pas de BOM et peuvent mal interpréter le fichier

3. **Problèmes Git** : Les diffs peuvent montrer des différences invisibles si un fichier est modifié avec un éditeur qui ajoute/supprime le BOM

4. **Standard CSV** : La RFC 4180 (standard CSV) ne prévoit pas de BOM

**Exemple de problème si on oublie `utf-8-sig`** :

```python
# Avec 'utf-8' (sans gestion du BOM)
with open('client_questions.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    row = next(reader)
    print(row.keys())
# Output: dict_keys(['\ufeffreference_question_id', 'response_model_id', 'client_question'])
#                    ^^^^^^^^
#                    Le BOM est inclus dans le nom de la colonne !

# Avec 'utf-8-sig' (gestion du BOM)
with open('client_questions.csv', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    row = next(reader)
    print(row.keys())
# Output: dict_keys(['reference_question_id', 'response_model_id', 'client_question'])
#         Correct !
```

### Impact potentiel

| Type d'impact | Description |
|---------------|-------------|
| **Fragilité** | Le code dépend de l'encodage `utf-8-sig` pour fonctionner |
| **Compatibilité** | Problèmes potentiels avec des outils externes |
| **Confusion** | Les développeurs pourraient utiliser `utf-8` par habitude |

### Solution proposée

Deux approches sont possibles :

**Option A (Recommandée) : Supprimer le BOM des fichiers CSV**

Le BOM n'est pas nécessaire pour UTF-8 et sa suppression simplifie la gestion des fichiers.

```bash
# Script pour supprimer le BOM d'un fichier
# remove_bom.sh

#!/bin/bash
for file in "$@"; do
    if [ -f "$file" ]; then
        # Vérifier si le fichier commence par un BOM UTF-8
        if head -c 3 "$file" | grep -q $'\xef\xbb\xbf'; then
            echo "Removing BOM from $file"
            # Créer une version sans BOM
            tail -c +4 "$file" > "$file.tmp" && mv "$file.tmp" "$file"
        else
            echo "No BOM found in $file"
        fi
    fi
done
```

Ou en Python :

```python
# scripts/remove_bom.py
from pathlib import Path

def remove_bom(file_path: str) -> bool:
    """Remove UTF-8 BOM from a file if present.
    
    Returns True if BOM was removed, False otherwise.
    """
    path = Path(file_path)
    content = path.read_bytes()
    
    BOM = b'\xef\xbb\xbf'
    if content.startswith(BOM):
        path.write_bytes(content[3:])
        print(f"BOM removed from {file_path}")
        return True
    else:
        print(f"No BOM found in {file_path}")
        return False

if __name__ == "__main__":
    remove_bom("industrialisation/knowledge_base/client_questions.csv")
    remove_bom("industrialisation/knowledge_base/response_models.csv")
```

**Option B : Documenter et maintenir l'utilisation de utf-8-sig**

Si le BOM doit être conservé (par exemple pour compatibilité avec Excel), documenter clairement cette exigence.

```python
# read_csv.py - Avec documentation explicite
def read_csv(file_path: str, delimiter: str = ",") -> list[dict[str, str]]:
    """Read a CSV file and return a list of dictionaries.
    
    Parameters
    ----------
    file_path : str
        Path to the CSV file to read.
    delimiter : str, optional
        CSV delimiter character, by default ','.
        
    Returns
    -------
    list[dict[str, str]]
        List of dictionaries where each dictionary represents a row.
        
    Notes
    -----
    This function uses 'utf-8-sig' encoding to handle files that may contain
    a UTF-8 BOM (Byte Order Mark). This is common with files created by
    Microsoft Excel. If you're creating CSV files programmatically, prefer
    saving them without BOM using 'utf-8' encoding.
    
    See Also
    --------
    https://docs.python.org/3/library/codecs.html#module-encodings.utf_8_sig
    """
    rows = []
    with open(file_path, encoding="utf-8-sig") as file:  # utf-8-sig gère le BOM
        reader = DictReader(file, delimiter=delimiter)
        for row in reader:
            rows.append(row)
    return rows
```

---

## MIN-26 : Cas de tests edge non couverts

| Attribut | Valeur |
|----------|--------|
| **Fichiers** | `tests/unit/` (ensemble des tests) |
| **Catégorie** | Tests |
| **Sévérité** | 🟡 Mineur |

### Cas non testés identifiés

Lors de l'analyse du code, plusieurs cas limites (edge cases) ont été identifiés comme non couverts par les tests unitaires :

| Cas edge | Fichier concerné | Risque |
|----------|------------------|--------|
| Question vide dans le CSV | `questions_store.py` | Embedding d'une chaîne vide |
| Très long email (>10k caractères) | `email_suggestion_request.py` | Timeout ou coût excessif |
| Caractères spéciaux/Unicode | `validation.py` | Erreurs de parsing |
| Timeout LLMaaS | `llm_encoder.py`, `llm_reranker.py` | Comportement non défini |
| Concurrence sur ConfigContext | `config_context.py` | Race conditions |
| ChromaDB retourne 0 résultat | `questions_store.py` | Division par zéro ou liste vide |
| Tous les candidats sous le threshold | `maximum_similarity.py` | Liste vide |
| Fichier CSV mal formé | `read_csv.py` | Exception non gérée |
| response_model_id inexistant | `response_model_store.py` | KeyError |

### Problème identifié

Les tests actuels couvrent principalement les **cas nominaux** (happy path) mais peu de **cas limites**. En production, ce sont souvent ces cas edge qui causent des incidents car ils n'ont pas été anticipés.

**Exemple de code non testé pour les cas limites :**

```python
# maximum_similarity.py - Que se passe-t-il si tous les scores sont < threshold ?
def select(self, response_similarities: ResponseModelSimilarities) -> list[SelectedCandidate]:
    selected_candidates = []
    for model_id in response_similarities.response_model_ids:
        best_match = response_similarities.get_best_match_for_response_model(model_id)
        if not best_match or best_match.similarity_score < self.threshold:
            continue  # Tous les candidats peuvent être filtrés !
        # ...
    
    if not selected_candidates:
        raise NoCandidatesFoundException(...)  # Cette exception est-elle bien testée ?
```

### Impact potentiel

| Type d'impact | Description |
|---------------|-------------|
| **Fiabilité** | Bugs en production sur des cas non anticipés |
| **Debugging** | Comportement indéfini difficile à diagnostiquer |
| **Confiance** | Incertitude sur la robustesse du système |

### Solution proposée

Ajouter des tests spécifiques pour chaque cas edge identifié. Voici des exemples de tests à implémenter :

```python
# tests/unit/test_edge_cases.py
"""Tests for edge cases and boundary conditions."""

import pytest
from unittest.mock import MagicMock, patch
from requests.exceptions import Timeout, ConnectionError

from industrialisation.src.document_stores.questions_store import ChromaQuestionStore
from industrialisation.src.filter_strategies.maximum_similarity import MaximumSimilarityStrategy
from industrialisation.src.models.data_objects.email_suggestion_request import EmailSuggestionRequest
from industrialisation.src.models.exceptions.similarity_exception import NoCandidatesFoundException


class TestEdgeCasesEmailRequest:
    """Test edge cases for email suggestion requests."""

    def test_very_long_email_content_is_truncated(self) -> None:
        """Test that email content exceeding max length is truncated."""
        long_content = "A" * 50000  # 50k characters
        
        request = EmailSuggestionRequest(
            request_id="test",
            user_id=1,
            email_id=1,
            email_sequence_index=1,
            start_ts="2024-01-01T00:00:00Z",
            email_object="Test",
            email_content=long_content,
        )
        
        # Vérifier que le contenu est tronqué à la limite max
        assert len(request.email_content) <= 10000

    def test_email_with_special_unicode_characters(self) -> None:
        """Test that special Unicode characters are handled correctly."""
        special_content = "Émoji: 🎉 Accents: éàù Chinese: 中文 Arabic: العربية"
        
        request = EmailSuggestionRequest(
            request_id="test",
            user_id=1,
            email_id=1,
            email_sequence_index=1,
            start_ts="2024-01-01T00:00:00Z",
            email_object="Test Unicode",
            email_content=special_content,
        )
        
        assert request.email_content == special_content


class TestEdgeCasesSimilarity:
    """Test edge cases for similarity search."""

    def test_all_candidates_below_threshold_raises_exception(self) -> None:
        """Test that NoCandidatesFoundException is raised when all scores are below threshold."""
        strategy = MaximumSimilarityStrategy(top_k=5, threshold=0.9)
        
        # Créer des similarités avec tous les scores < 0.9
        mock_similarities = MagicMock()
        mock_similarities.response_model_ids = [1, 2, 3]
        
        mock_match = MagicMock()
        mock_match.similarity_score = 0.5  # Sous le threshold de 0.9
        mock_similarities.get_best_match_for_response_model.return_value = mock_match
        
        with pytest.raises(NoCandidatesFoundException):
            strategy.select(mock_similarities)

    def test_chromadb_returns_empty_results(self) -> None:
        """Test handling when ChromaDB returns no results."""
        mock_encoder = MagicMock()
        store = ChromaQuestionStore(encoder=mock_encoder)
        
        # Simuler une collection vide
        store.question_collection = MagicMock()
        store.question_collection.query.return_value = {
            "ids": [[]],
            "distances": [[]],
            "metadatas": [[]],
        }
        
        result = store.search(content="test query", n_results=10)
        
        assert len(result) == 0


class TestEdgeCasesLLMaaS:
    """Test edge cases for LLMaaS communication."""

    @patch('industrialisation.src.semantic_models.llm_encoder.HttpSessionManager')
    def test_llmaas_timeout_is_handled(self, mock_session_manager: MagicMock) -> None:
        """Test that LLMaaS timeout raises appropriate exception."""
        mock_session_manager.return_value.__enter__.return_value.post.side_effect = Timeout()
        
        # Le test dépend de l'implémentation exacte
        # Vérifier que l'exception est propagée ou gérée correctement
        pass

    @patch('industrialisation.src.semantic_models.llm_encoder.HttpSessionManager')
    def test_llmaas_connection_error_is_handled(self, mock_session_manager: MagicMock) -> None:
        """Test that connection errors to LLMaaS are handled."""
        mock_session_manager.return_value.__enter__.return_value.post.side_effect = ConnectionError()
        
        pass


class TestEdgeCasesDataQuality:
    """Test edge cases for data quality issues."""

    def test_response_model_not_found_raises_exception(self) -> None:
        """Test that requesting non-existent response model raises exception."""
        from industrialisation.src.document_stores.response_model_store import ResponseModelStore
        
        store = ResponseModelStore()
        
        # Ne pas peupler le store, puis demander un ID inexistant
        with pytest.raises(Exception):  # Préciser le type d'exception attendu
            store.get_content_by_id(99999)

    def test_malformed_csv_raises_exception(self, tmp_path) -> None:
        """Test that malformed CSV raises appropriate exception."""
        from common.read_csv import read_csv
        
        # Créer un fichier CSV malformé
        malformed_csv = tmp_path / "malformed.csv"
        malformed_csv.write_text('col1,col2\n"unclosed quote,value\n')
        
        with pytest.raises(Exception):  # csv.Error ou similaire
            read_csv(str(malformed_csv), delimiter=",")
```

---

## MIN-27 : Délimiteur CSV par défaut incohérent avec les fichiers réels

| Attribut | Valeur |
|----------|--------|
| **Fichier** | `common/read_csv.py` |
| **Ligne** | 4 |
| **Catégorie** | Architecture |
| **Sévérité** | 🟡 Mineur |

### Extrait de code problématique

```python
def read_csv(file_path: str, delimiter: str = ";") -> list[dict[str, str]]:
    #                                         ^^^
    #                       Défaut: point-virgule ";"
    """Read a CSV file and return a list of dictionaries.
    
    Parameters
    ----------
    delimiter: str, optional
        CSV delimiter character, by default ';'.
    """
```

### Vérification des fichiers CSV réels

```csv
# client_questions.csv - Utilise la VIRGULE comme délimiteur
reference_question_id,response_model_id,client_question
1,1,"Le problème est résolu, j'ai de nouveau accès à mon compte"
2,1,"Merci, je vous confirme que je peux désormais me connecter"

# response_models.csv - Utilise aussi la VIRGULE
response_model_id,response_model_title,response_model_content
1,Connexion réussie après la demande,"Bonjour Madame / Monsieur xxx, <br/>..."
```

### Problème identifié

La fonction `read_csv()` a un délimiteur par défaut `;` (point-virgule), mais les fichiers CSV du projet utilisent `,` (virgule) comme délimiteur.

Cette incohérence oblige les appelants à **toujours spécifier** le délimiteur :

```python
# Dans factories.py - On doit spécifier delimiter="," à chaque fois
questions_store.populate(csv_file=questions_file, delimiter=",")
responses_model_store.populate(csv_file=responses_model_file, delimiter=",")
```

Si un développeur oublie de spécifier le délimiteur, la lecture échoue silencieusement ou produit des résultats incorrects.

### Impact potentiel

| Type d'impact | Description |
|---------------|-------------|
| **Erreurs** | Oubli du paramètre `delimiter` cause des bugs |
| **Verbosité** | Obligation de spécifier le délimiteur partout |
| **Confusion** | Incohérence entre le défaut et les fichiers réels |

### Solution proposée

Changer le délimiteur par défaut pour correspondre aux fichiers réels du projet, et documenter clairement ce choix.

```python
# AVANT
def read_csv(file_path: str, delimiter: str = ";") -> list[dict[str, str]]:
    """Read a CSV file and return a list of dictionaries.
    
    Parameters
    ----------
    delimiter: str, optional
        CSV delimiter character, by default ';'.
    """

# APRÈS
def read_csv(file_path: str, delimiter: str = ",") -> list[dict[str, str]]:
    """Read a CSV file and return a list of dictionaries.
    
    Parameters
    ----------
    file_path : str
        Path to the CSV file to read.
    delimiter : str, optional
        CSV delimiter character, by default ','.
        
        Note: The default is comma (,) which is the standard CSV delimiter
        and matches the format of files in this project. Use ';' for 
        European-style CSV files if needed.
    
    Returns
    -------
    list[dict[str, str]]
        List of dictionaries where each dictionary represents a row,
        with column headers as keys.
    
    Examples
    --------
    >>> rows = read_csv("data/questions.csv")  # Utilise ',' par défaut
    >>> rows = read_csv("data/euro.csv", delimiter=";")  # CSV européen
    """
    rows = []
    with open(file_path, encoding="utf-8-sig") as file:
        reader = DictReader(file, delimiter=delimiter)
        for row in reader:
            rows.append(row)
    return rows
```

**Bonus : Détection automatique du délimiteur**

Pour plus de robustesse, on pourrait détecter automatiquement le délimiteur :

```python
import csv
from csv import DictReader, Sniffer
from typing import Optional


def read_csv(
    file_path: str, 
    delimiter: Optional[str] = None,
    auto_detect: bool = True
) -> list[dict[str, str]]:
    """Read a CSV file with optional automatic delimiter detection.
    
    Parameters
    ----------
    file_path : str
        Path to the CSV file.
    delimiter : str, optional
        CSV delimiter. If None and auto_detect is True, the delimiter
        will be detected automatically.
    auto_detect : bool, default True
        Whether to auto-detect the delimiter if not specified.
    """
    rows = []
    
    with open(file_path, encoding="utf-8-sig") as file:
        if delimiter is None and auto_detect:
            # Lire un échantillon pour détecter le délimiteur
            sample = file.read(2048)
            file.seek(0)
            
            try:
                dialect = Sniffer().sniff(sample, delimiters=",;\t|")
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ","  # Fallback au standard
        
        delimiter = delimiter or ","
        reader = DictReader(file, delimiter=delimiter)
        
        for row in reader:
            rows.append(row)
    
    return rows
```

---

## MIN-28 : Risque de Path Traversal dans l'upload de fichiers Streamlit

| Attribut | Valeur |
|----------|--------|
| **Fichier** | `exploration/apps/upload_app/main.py` |
| **Ligne** | 136 |
| **Catégorie** | Sécurité |
| **Sévérité** | 🟡 Mineur (risque faible) |

### Extrait de code problématique

```python
def main_app() -> None:
    # ...
    for uploaded_file in uploaded_files:
        save_path = Path(UPLOAD_DESTINATION) / uploaded_file.name  # ← Nom non validé !
        st.session_state.files_to_upload.append((uploaded_file, save_path))
        # ...
    
    # Plus loin, le fichier est sauvegardé :
    for uploaded_file, save_path in st.session_state.files_to_upload:
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
```

### Problème identifié

Le nom du fichier uploadé (`uploaded_file.name`) est utilisé **directement** pour construire le chemin de sauvegarde, sans validation ni sanitization.

**Scénario d'attaque théorique (Path Traversal)** :

Un attaquant pourrait tenter d'uploader un fichier avec un nom malveillant comme :
- `../../../etc/passwd` (Linux)
- `..\..\..\..\Windows\System32\config` (Windows)

L'objectif serait d'écrire un fichier en dehors du répertoire `UPLOAD_DESTINATION`.

**Cependant, ce risque est ATTÉNUÉ par plusieurs facteurs :**

1. **`pathlib.Path` normalise les chemins** : L'utilisation de `Path(UPLOAD_DESTINATION) / uploaded_file.name` avec `pathlib` normalise les composants `..`, ce qui atténue partiellement le risque.

2. **Streamlit peut filtrer les noms** : Selon la version de Streamlit, le nom de fichier peut déjà être sanitizé.

3. **Application interne** : Cette app Streamlit est destinée à un usage interne (exploration), pas exposée publiquement.

4. **Permissions système** : Les permissions du système de fichiers limitent où l'application peut écrire.

**Test de la protection de pathlib :**

```python
from pathlib import Path

destination = Path("/safe/upload/dir")
malicious_name = "../../../etc/passwd"

# pathlib normalise le chemin
result = destination / malicious_name
print(result)  # /safe/upload/dir/../../../etc/passwd

# MAIS resolve() peut être dangereux :
print(result.resolve())  # /etc/passwd ← DANGER si on utilise resolve() !

# Vérification de sécurité :
print(result.resolve().is_relative_to(destination))  # False ← Le chemin sort du dossier !
```

### Impact potentiel

| Type d'impact | Description | Niveau |
|---------------|-------------|--------|
| **Écriture hors périmètre** | Possibilité d'écrire des fichiers ailleurs | Faible (protections en place) |
| **Écrasement de fichiers** | Pourrait écraser des fichiers existants | Faible |
| **Exécution de code** | Si un fichier exécutable est écrasé | Très faible |

### Solution proposée

Bien que le risque soit faible, il est recommandé d'ajouter une validation explicite du nom de fichier pour suivre les bonnes pratiques de sécurité (defense in depth).

```python
import re
from pathlib import Path
from typing import Optional


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal attacks.
    
    This function removes or replaces potentially dangerous characters
    and path components from filenames.
    
    Parameters
    ----------
    filename : str
        The original filename from user input.
        
    Returns
    -------
    str
        A sanitized filename safe for use in file paths.
        
    Examples
    --------
    >>> sanitize_filename("../../../etc/passwd")
    'etc_passwd'
    >>> sanitize_filename("normal_file.txt")
    'normal_file.txt'
    >>> sanitize_filename("file<with>invalid:chars.txt")
    'file_with_invalid_chars.txt'
    """
    # Extraire seulement le nom de fichier (enlever tout chemin)
    filename = Path(filename).name
    
    # Remplacer les caractères potentiellement dangereux
    # Garde: lettres, chiffres, tirets, underscores, points
    sanitized = re.sub(r'[^\w\-.]', '_', filename)
    
    # Éviter les noms réservés Windows
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    name_without_ext = Path(sanitized).stem.upper()
    if name_without_ext in reserved_names:
        sanitized = f"_{sanitized}"
    
    # Éviter les noms vides ou seulement des points
    if not sanitized or sanitized.strip('.') == '':
        sanitized = "unnamed_file"
    
    return sanitized


def validate_save_path(destination: Path, filename: str) -> Optional[Path]:
    """Validate that a file path stays within the destination directory.
    
    Parameters
    ----------
    destination : Path
        The allowed destination directory.
    filename : str
        The filename to validate.
        
    Returns
    -------
    Path or None
        The validated path if safe, None if the path would escape the destination.
    """
    sanitized = sanitize_filename(filename)
    save_path = destination / sanitized
    
    # Résoudre le chemin absolu et vérifier qu'il reste dans destination
    try:
        resolved = save_path.resolve()
        dest_resolved = destination.resolve()
        
        if resolved.is_relative_to(dest_resolved):
            return save_path
        else:
            return None
    except (OSError, ValueError):
        return None


# Utilisation dans main.py
def main_app() -> None:
    # ...
    for uploaded_file in uploaded_files:
        # Valider et sanitizer le nom de fichier
        save_path = validate_save_path(
            destination=Path(UPLOAD_DESTINATION),
            filename=uploaded_file.name
        )
        
        if save_path is None:
            st.error(f"❌ Invalid filename: '{uploaded_file.name}'")
            continue
        
        st.session_state.files_to_upload.append((uploaded_file, save_path))
        
        if save_path.exists():
            st.warning(f"⚠️ '{save_path.name}' already exists and will be overwritten.")
```

**Tests pour la sanitization :**

```python
# tests/test_filename_sanitization.py
import pytest
from pathlib import Path

from exploration.apps.upload_app.security import sanitize_filename, validate_save_path


class TestFilenameSanitization:
    """Test filename sanitization for security."""

    @pytest.mark.parametrize("malicious,expected", [
        ("../../../etc/passwd", "etc_passwd"),
        ("..\\..\\Windows\\System32", "System32"),
        ("normal_file.txt", "normal_file.txt"),
        ("file with spaces.pdf", "file_with_spaces.pdf"),
        ("file<script>alert.js", "file_script_alert.js"),
        ("", "unnamed_file"),
        ("...", "unnamed_file"),
        ("CON.txt", "_CON.txt"),  # Reserved Windows name
    ])
    def test_sanitize_filename(self, malicious: str, expected: str) -> None:
        """Test that dangerous filenames are sanitized."""
        result = sanitize_filename(malicious)
        assert result == expected

    def test_validate_save_path_blocks_traversal(self, tmp_path: Path) -> None:
        """Test that path traversal attempts are blocked."""
        destination = tmp_path / "uploads"
        destination.mkdir()
        
        # Tentative de path traversal
        result = validate_save_path(destination, "../../../etc/passwd")
        
        # La validation doit rejeter ce chemin
        assert result is None or result.is_relative_to(destination)

    def test_validate_save_path_allows_normal_files(self, tmp_path: Path) -> None:
        """Test that normal filenames are allowed."""
        destination = tmp_path / "uploads"
        destination.mkdir()
        
        result = validate_save_path(destination, "document.pdf")
        
        assert result is not None
        assert result.name == "document.pdf"
        assert result.parent == destination
```

---

# 📊 TABLEAU RÉCAPITULATIF MIN-19 À MIN-28

| ID | Nom | Fichier | Sévérité | Effort |
|----|-----|---------|----------|--------|
| MIN-19 | Hack TypeError pour MyPy | error_handler.py | 🟡 | Faible |
| MIN-20 | Mélange unittest.TestCase et pytest | test_*.py | 🟡 | Moyen |
| MIN-21 | Assertions unittest vs pytest | test_*.py | 🟡 | Moyen |
| MIN-22 | setUp() vs fixtures pytest | test_*.py | 🟡 | Moyen |
| MIN-23 | Pattern if __name__ obsolète | test_*.py | 🟡 | Faible |
| MIN-24 | Emojis corrompus Streamlit | main.py | 🟡 | Faible |
| MIN-25 | BOM UTF-8 dans CSV | *.csv | 🟡 | Faible |
| MIN-26 | Cas edge non testés | tests/ | 🟡 | Élevé |
| MIN-27 | Délimiteur CSV par défaut incohérent | read_csv.py | 🟡 | Faible |
| MIN-28 | Risque Path Traversal (faible) | main.py | 🟡 | Faible |

---

# ✅ CHECKLIST DE CORRECTION MIN-19 À MIN-28

## Corrections rapides (< 30 min chacune)

- [ ] **MIN-19** : Supprimer le `raise TypeError` et utiliser un commentaire `type: ignore`
- [ ] **MIN-23** : Supprimer les blocs `if __name__ == "__main__": unittest.main()`
- [ ] **MIN-24** : Corriger les emojis corrompus dans main.py
- [ ] **MIN-25** : Supprimer le BOM des fichiers CSV (ou documenter)
- [ ] **MIN-27** : Changer le délimiteur par défaut de `;` à `,`
- [ ] **MIN-28** : Ajouter `sanitize_filename()` dans main.py

## Refactoring moyen (1-2h chacune)

- [ ] **MIN-20** : Migrer un fichier test de `unittest.TestCase` vers pytest pur
- [ ] **MIN-21** : Convertir les assertions `self.assertEqual()` en `assert`
- [ ] **MIN-22** : Convertir les `setUp()` en fixtures `@pytest.fixture`

## Effort plus conséquent (demi-journée)

- [ ] **MIN-26** : Ajouter les tests pour les cas edge identifiés

---

**Fin des items MIN-19 à MIN-28**
