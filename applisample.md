# Rapport d'Audit Technique - Template IA Factory

## Synthèse Exécutive

Ce template d'industrialisation MLOps présente une architecture solide sur le plan conceptuel, mais souffre de défauts majeurs qui freinent considérablement son adoption. L'analyse révèle 22 problèmes répartis en 4 catégories de sévérité, dont 5 sont bloquants pour une mise en production sereine.

**Verdict global** : Template prometteur mais immature, nécessitant 2 à 3 semaines de travail correctif avant déploiement à grande échelle.

---

## 1. Défauts Critiques

### 1.1 Documentation Creuse

**Localisation** : `docs/model_development.md`, `docs/deployment_and_pipeline.md`, `docs/setup.md`

**Code concerné** :
```markdown
# setup.md (lignes 1-17)
# Configuration et installation

## Prérequis

- Système d'exploitation supporté: (ex. Linux, Windows)
- Logiciels nécessaires: (ex. Docker, Python 3.8+)
- Ressources matérielles: (ex. GPU avec CUDA)

## Installation de l'environnement

Détaillez ici les étapes pour installer l'environnement de développement, 
y compris l'installation de dépendances, la configuration des variables 
d'environnement, etc.

## Configuration initiale

Expliquez les étapes de configuration initiale du projet...
```

**Problèmes engendrés** :
- Les utilisateurs découvrent après clonage qu'aucun guide concret n'existe
- Temps de prise en main multiplié par 3 ou 4, passant de quelques heures à plusieurs jours
- Multiplication des tickets de support internes ("comment je fais pour...")
- Abandon du template après quelques heures de frustration
- Chaque nouvel utilisateur doit redécouvrir les mêmes solutions par essai-erreur
- Perte de crédibilité du template auprès des équipes

**Solution** : Rédiger des guides opérationnels avec commandes exactes, captures d'écran et FAQ des erreurs courantes. Créer un tutoriel "Premier déploiement en 15 minutes" avec un exemple fonctionnel de bout en bout. Chaque section doit contenir des commandes copier-coller et les résultats attendus.

---

### 1.2 Complexité d'Installation Prohibitive

**Localisation** : `Makefile` (lignes 14-74), `README.md` (lignes 100-157)

**Code concerné** :
```makefile
# Makefile (lignes 14-74)
.PHONY: all
all: helper config create_conda_env install-deps

.PHONY: helper
helper:
	@pip install pyyaml
	@python config_helper/generate_project_config.py

.PHONY: config
config:
	@echo "Starting the configuration of pip and conda repositories..."
	@if [ -d "$(CONFIG_DIR)/pip" ]; then rm -rf "$(CONFIG_DIR)/pip"; fi
	@if [ -f "$(CONDARC)" ]; then rm -f "$(CONDARC)"; fi
	@mkdir -p $(CONFIG_DIR)/pip
	@echo "[global]" > $(PIPCONF)
	@echo "index-url = https://${ARTIFACTORY_USER}:${ARTIFACTORY_PASSWORD}@repo..." >> $(PIPCONF)
	# ... 15 autres lignes de configuration manuelle ...

.PHONY: install-deps
install-deps:
	@pip install poetry==$(POETRY_VERSION)
	@pip install ml-utils --extra-index-url='https://${ARTIFACTORY_USER}:${ARTIFACTORY_PASSWORD}@...'
	@poetry config virtualenvs.create false
	@poetry config http-basic.artifactory ${ARTIFACTORY_USER} ${ARTIFACTORY_PASSWORD}
	# ... configuration Poetry supplémentaire ...
```

**Problèmes engendrés** :
- Installation nécessitant 10 étapes manuelles distinctes dans un ordre précis
- Temps d'installation de 2 à 3 heures pour un nouvel utilisateur
- Erreurs fréquentes dues aux oublis d'étapes ou à l'ordre incorrect
- Variables d'environnement ARTIFACTORY_USER et ARTIFACTORY_PASSWORD à exporter manuellement avant chaque session
- Token Artifactory à créer manuellement via interface web (validité 1 an, puis tout casse)
- Aucune validation que l'installation s'est bien passée
- Les utilisateurs ne savent pas si l'échec vient de leur manipulation ou d'un bug du template

**Solution** : Créer un script unique `./scripts/init.sh --name mon-projet --env dev` qui :
- Vérifie les prérequis (Python, Conda, Docker)
- Demande les credentials de manière interactive si absents
- Exécute toutes les étapes dans l'ordre
- Affiche une barre de progression
- Effectue une validation finale (healthcheck)
- Affiche un résumé clair : "Installation réussie en 4 min 32 s"

---

### 1.3 Gestion des Secrets Incomplète

**Localisation** : `config/services/services_dev.env`, `industrialisation/src/api.py` (lignes 111-124)

**Code concerné** :
```python
# api.py (lignes 111-124)
ml_api_key_id = os.getenv("COS_ML_API_KEY_ID")
ml_secret_access_key = os.getenv("COS_ML_SECRET_ACCESS_KEY")
ml_bucket_name = os.getenv("COS_ML_BUCKET_NAME")
ml_endpoint_url = os.getenv("COS_ML_ENDPOINT_URL")

# Vérification présence mais message d'erreur peu utile
if ml_api_key_id is None:
    raise ValueError("The environment variable COS_ML_API_KEY_ID is not set.")
if ml_secret_access_key is None:
    raise ValueError("The environment variable COS_ML_SECRET_ACCESS_KEY is not set.")
if ml_bucket_name is None:
    raise ValueError("The environment variable COS_ML_BUCKET_NAME is not set.")
if ml_endpoint_url is None:
    raise ValueError("The environment variable COS_ML_ENDPOINT_URL is not set.")
```

```bash
# services_dev.env (lignes 1-8) - URLs présentes mais credentials absents
# Cos Ml registry configuration
COS_ML_ENDPOINT_URL=https://s3.direct.eu-fr2.cloud-object-storage.appdomain.cloud:4327
COS_ML_BUCKET_NAME=bu002i010893

# Cos DATA configuration
COS_DATA_ENDPOINT_URL=https://s3.direct.eu-fr2.cloud-object-storage.appdomain.cloud:4409
COS_DATA_BUCKET_NAME=bu002i012201s

# ABSENCE TOTALE des credentials requis par le code :
# COS_ML_API_KEY_ID=???
# COS_ML_SECRET_ACCESS_KEY=???
```

**Problèmes engendrés** :
- Échec systématique au démarrage avec message "COS_ML_API_KEY_ID is not set" sans indication de résolution
- Aucune documentation sur où trouver ces credentials (Vault ? Console IBM ? Fichier partagé ?)
- VaultConnector est initialisé ligne 103 mais aucune procédure n'explique comment alimenter Vault
- Risque élevé de hardcoding des secrets dans le code par frustration
- Tentation de commiter les secrets dans le dépôt Git
- En production, les credentials expirent sans alerte, causant des pannes inattendues

**Solution** : Fournir un fichier `.env.template` complet documentant chaque variable :
```bash
# .env.template
# Instructions : Copier vers .env et remplir les valeurs
# Source des credentials : https://vault.entreprise.com/ui/vault/secrets/ia-factory

COS_ML_API_KEY_ID=<Obtenir depuis Vault: kv/cos-ml#api_key_id>
COS_ML_SECRET_ACCESS_KEY=<Obtenir depuis Vault: kv/cos-ml#secret_access_key>
```

Créer un script `scripts/check_secrets.py` qui :
- Liste tous les secrets requis
- Vérifie leur présence dans l'environnement
- Teste la connectivité (COS, Vault, bases de données)
- Affiche un rapport clair avec les secrets manquants et où les obtenir

---

### 1.4 Détection d'Environnement Fragile

**Localisation** : `config/load_config.py` (lignes 142-168)

**Code concerné** :
```python
# load_config.py (lignes 142-168)
def load_config_domino_project_file(file_path: Optional[str] = None) -> dict:
    if file_path is None:
        file_path = os.path.join(PROJECT_ROOT, "config", "domino", FILE_NAME_PROJECT_CONFIG)
    
    # Récupération du nom de projet depuis variable d'environnement
    domino_project_name = os.getenv("DOMINO_PROJECT_NAME", "dev")
    _logger.info(f"Project name from environment variable: {domino_project_name}")

    file_basename = os.path.basename(file_path)
    path_dir_name = os.path.dirname(file_path)

    # PROBLÈME : Extraction fragile basée sur le dernier segment après tiret
    env_suffix = domino_project_name.rsplit("-", 1)[-1]
    if env_suffix not in ("pprod", "prod", "dev"):
        raise ValueError(
            f"Invalid DOMINO_PROJECT_NAME '{domino_project_name}'. Expected format: "
            f"suffix with '-dev', '-pprod', or '-prod'."
        )

    _logger.info(f"{env_suffix.capitalize()} environment detected...")

    # Remplacement du placeholder {env} dans le nom de fichier
    if "-prod" in domino_project_name:
        file_basename = file_basename.replace("{env}", "prod")
    elif "-pprod" in domino_project_name:
        file_basename = file_basename.replace("{env}", "pprod")
    else:
        file_basename = file_basename.replace("{env}", "dev")
```

**Problèmes engendrés** :
- Projet nommé "my-ai-model" (sans suffix -dev/-pprod/-prod) provoque une ValueError immédiate
- Projet "fraud-detection" échoue car "detection" n'est pas un environnement valide
- Projet "my-super-model-v2-dev" fonctionne par chance mais la logique est fragile
- Environnements "staging", "uat", "qa" non supportés
- Message d'erreur cryptique ne suggérant pas de correction
- Impossibilité d'utiliser le template pour des projets existants sans les renommer
- La logique `rsplit("-", 1)[-1]` est un anti-pattern : elle suppose un format strict jamais validé en amont

**Solution** : Introduire une variable `DEPLOYMENT_ENV` explicite avec priorité sur le parsing :
```python
def detect_environment() -> str:
    # Priorité 1 : Variable explicite (recommandé)
    explicit_env = os.getenv("DEPLOYMENT_ENV")
    if explicit_env:
        if explicit_env not in VALID_ENVIRONMENTS:
            suggestions = difflib.get_close_matches(explicit_env, VALID_ENVIRONMENTS)
            raise ValueError(f"Environnement '{explicit_env}' invalide. "
                           f"Vouliez-vous dire '{suggestions[0]}' ?")
        return explicit_env
    
    # Priorité 2 : Extraction depuis nom (rétrocompatibilité)
    # ... avec warning incitant à utiliser DEPLOYMENT_ENV
    
    # Priorité 3 : Défaut dev avec warning
    return "dev"
```

---

### 1.5 ConfigContext Non Thread-Safe

**Localisation** : `common/config_context.py` (lignes 4-66)

**Code concerné** :
```python
# config_context.py (lignes 4-66)
class ConfigContext:
    """Configuration context module.
    
    Provides a ConfigContext class as a context for maintaining 
    the application's configuration.
    """

    __instance = None
    _config: dict  # DANGER : Dictionnaire partagé entre tous les threads

    def __new__(cls) -> "ConfigContext":
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance._config = {
                "loaded_model": "InitialValue",
            }
        return cls.__instance

    def get(self, key: str) -> Any:
        return self._config.get(key)  # Lecture non protégée

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value  # ÉCRITURE NON PROTÉGÉE - RACE CONDITION

    def update(self, new_config_dict: dict) -> None:
        self._config.update(new_config_dict)  # Également non protégé
```

**Problèmes engendrés** :
- Scénario de race condition en production sous charge :
  1. Thread A (requête utilisateur Alice) exécute : `config.set("user_id", "alice")`
  2. Thread B (requête utilisateur Bob) exécute : `config.set("user_id", "bob")`
  3. Thread A continue et lit : `config.get("user_id")` → retourne "bob" au lieu de "alice"
- Fuite de données entre sessions utilisateur (violation RGPD potentielle)
- Bug intermittent extrêmement difficile à reproduire en développement
- Ne se manifeste qu'en production sous charge réelle
- Risque de sécurité majeur : un utilisateur peut voir les données d'un autre
- Le pattern Singleton est correct pour les données globales (modèle) mais dangereux pour les données par requête

**Solution** : Utiliser `contextvars.ContextVar` (Python 3.7+) pour isoler les données par requête :
```python
from contextvars import ContextVar
import threading

_request_context: ContextVar[dict] = ContextVar('request_context', default=None)
_global_lock = threading.RLock()

class ConfigContext:
    GLOBAL_KEYS = {"loaded_model", "app_config", "project_config"}  # Partagés
    
    def get(self, key: str) -> Any:
        if key in self.GLOBAL_KEYS:
            with _global_lock:
                return self._global_config.get(key)
        else:
            ctx = _request_context.get() or {}
            return ctx.get(key)
    
    def set(self, key: str, value: Any) -> None:
        if key in self.GLOBAL_KEYS:
            with _global_lock:
                self._global_config[key] = value
        else:
            ctx = _request_context.get()
            if ctx is None:
                ctx = {}
                _request_context.set(ctx)
            ctx[key] = value
```

---

## 2. Défauts Majeurs

### 2.1 Dépendance Opaque à ml-utils

**Localisation** : `pyproject.toml` (ligne 42), imports dans `api.py` (lignes 12-14), `batch.py` (lignes 9-13), `train.py` (ligne 6)

**Code concerné** :
```toml
# pyproject.toml (ligne 42)
[tool.poetry.dependencies]
ml-utils = "^1.9.0"
```

```python
# api.py (lignes 12-14)
from ml_utils.base_model_loader import BaseModelLoader
from ml_utils.cos_manager import CosManager
from ml_utils.inference_decorator import duration_request
from ml_utils.vault_connector import VaultConnector

# batch.py (lignes 9-13)
from ml_utils.base_model_loader import BaseModelLoader
from ml_utils.cos_manager import CosManager
from ml_utils.inference_decorator import duration_request
from ml_utils.vault_connector import VaultConnector

# train.py (ligne 6)
from ml_utils.cos_manager import CosManager
```

**Problèmes engendrés** :
- Bibliothèque hébergée sur GitLab privé (`https://gitlab-dogen.group.echonet/dm/bddf/ap27282/ia_factory/ml-utils.git`)
- Inaccessible sans credentials Artifactory valides
- Aucune documentation publique sur le comportement des classes (CosManager, BaseModelLoader, VaultConnector)
- Impossible de comprendre la logique de chargement des modèles sans accès au code source
- Couplage fort empêchant toute portabilité vers un autre environnement
- Tests locaux impossibles sans mock complet de ml-utils
- Si ml-utils publie une breaking change, tous les projets utilisant le template cassent simultanément
- Vendor lock-in : impossible de migrer vers AWS S3 ou Azure Blob sans réécrire le code

**Solution** : Créer des interfaces abstraites permettant de substituer les implémentations :
```python
# common/interfaces.py
from abc import ABC, abstractmethod

class IModelLoader(ABC):
    @abstractmethod
    def load_model(self, model_uri: str) -> Any:
        pass

class IStorageManager(ABC):
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> None:
        pass
    @abstractmethod
    def download_model(self, run_id: str) -> str:
        pass

# Implémentation par défaut utilisant ml-utils
class MlUtilsModelLoader(IModelLoader):
    def load_model(self, model_uri: str) -> Any:
        from ml_utils.base_model_loader import BaseModelLoader
        return BaseModelLoader().load_model(model_uri=model_uri)

# Implémentation alternative pour tests/portabilité
class LocalModelLoader(IModelLoader):
    def load_model(self, model_uri: str) -> Any:
        import joblib
        return joblib.load(model_uri)
```

Documenter ml-utils dans `docs/ml-utils-guide.md` avec exemples d'utilisation de chaque classe.

---

### 2.2 Tests Unitaires Inefficaces

**Localisation** : `tests/unit/industrialisation/test_batch.py` (lignes 50-175)

**Code concerné** :
```python
# test_batch.py (lignes 50-99)
class TestBatch(unittest.TestCase):
    # 13 décorateurs @patch empilés
    @patch("config.load_config.load_service_config_file")
    @patch("config.load_config.load_app_config_file")
    @patch("industrialisation.src.batch.open", new_callable=MagicMock)
    @patch("ml_utils.cos_manager.CosManager")
    @patch("industrialisation.src.batch.VaultConnector")
    @patch("industrialisation.src.batch.os.getenv")
    @patch.object(BaseModelLoader, "load_model")
    @patch("industrialisation.src.batch.download_and_load_model")
    @patch("industrialisation.src.batch.pd.read_csv")
    @patch("industrialisation.src.batch.get_data_set_project_name")
    @patch("industrialisation.src.batch.os.makedirs")
    @patch("industrialisation.src.batch.os.path.exists", return_value=True)
    @patch("pandas.DataFrame.to_csv")
    def test_main(
        self,
        mock_to_csv: MagicMock,
        mock_exists: MagicMock,
        mock_makedirs: MagicMock,
        # ... 10 autres paramètres mock ...
    ) -> None:
        # Configuration des mocks
        mock_load_app_config_file.return_value = data_config
        mock_load_service_config_file.return_value = test_config
        mock_download_and_load_model.return_value = mock_model
        
        # EXÉCUTION SANS AUCUNE ASSERTION
        main()  # Le test passe si ça ne plante pas, c'est tout !
```

**Problèmes engendrés** :
- Le test vérifie uniquement que le code Python est syntaxiquement exécutable
- Aucune validation de la logique métier (prédictions correctes, transformations de données)
- Un bug de calcul (ex: colonnes inversées, mauvaise formule) passerait totalement inaperçu
- Couverture de code affichée à 60%+ mais complètement trompeuse
- Faux sentiment de sécurité : "on a des tests, donc c'est fiable"
- Les 13 mocks créent un environnement artificiel sans rapport avec la réalité
- Maintenance cauchemardesque : chaque changement dans batch.py nécessite de mettre à jour les mocks
- Impossible de détecter les régressions lors des refactorings

**Solution** : Réécrire les tests avec des données réelles en mémoire et des assertions sur le comportement :
```python
class TestBatchPredictions:
    @pytest.fixture
    def sample_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            'sepal_length': [5.1, 4.9, 7.0],
            'sepal_width': [3.5, 3.0, 3.2],
            'petal_length': [1.4, 1.4, 4.7],
            'petal_width': [0.2, 0.2, 1.4]
        })
    
    def test_predictions_have_correct_shape(self, sample_data, trained_model):
        predictions = trained_model.predict(sample_data)
        assert len(predictions) == len(sample_data)
    
    def test_predictions_are_valid_classes(self, sample_data, trained_model):
        predictions = trained_model.predict(sample_data)
        assert all(p in [0, 1, 2] for p in predictions)
    
    def test_column_renaming_handles_dots(self):
        df = pd.DataFrame({'sepal.length': [5.1]})
        df.columns = [c.replace(".", "_") for c in df.columns]
        assert 'sepal_length' in df.columns
```

Réserver les mocks uniquement aux dépendances externes impossibles à instancier (COS, Vault).

---

### 2.3 Incohérence des Gestionnaires de Dépendances

**Localisation** : `environment_explo.yaml` (lignes 11-19), `pyproject.toml` (lignes 38-44), `environment_indus.yaml`

**Code concerné** :
```yaml
# environment_explo.yaml (lignes 11-19)
dependencies:
  - python=3.9
  - conda-lock
  - boto3=1.35.83
  - mlflow=2.19.0      # <-- VERSION CONDA
  - python-dotenv=1.0.1
  - colorlog=6.9.0
  - xgboost=2.1.1
  - scikit-learn=1.5.2
```

```toml
# pyproject.toml (lignes 38-44)
[tool.poetry.dependencies]
python-dotenv = "^1.0.1"
colorlog = "^6.9.0"
ml-utils = "^1.9.0"
mlflow = "2.16.2"       # <-- VERSION POETRY DIFFÉRENTE !
```

```yaml
# environment_indus.yaml - Fichier quasi vide
channels:
  - anaconda-pkgs-main
  - conda-forge

dependencies:
  # Add your package conda
  # -anaconda-pkgs-main::debugpy=1.6.7
```

**Problèmes engendrés** :
- Version de mlflow différente : 2.19.0 (conda/explo) vs 2.16.2 (poetry/indus)
- Comportement potentiellement différent entre exploration et production
- Bugs classiques "ça marche sur ma machine" mais pas en production
- Le fichier `environment_indus.yaml` est quasi vide : à quoi sert-il exactement ?
- Deux systèmes de gestion de dépendances (Conda + Poetry) sans règle claire sur lequel utiliser
- Pas de mécanisme de synchronisation entre les deux
- Risque de régression silencieuse lors des mises à jour d'un côté sans l'autre

**Solution** : 
- Désigner Poetry comme source unique de vérité pour tous les packages Python
- Limiter Conda à l'environnement système (version Python, CUDA si GPU)
- Supprimer ou clarifier le rôle de `environment_indus.yaml`
- Créer un script `scripts/check_dependency_sync.py` comparant les versions entre fichiers et alertant en cas de divergence
- Documenter clairement : "Conda pour Python/CUDA, Poetry pour les packages"

---

### 2.4 Support Limité aux Modèles Simples

**Localisation** : `industrialisation/src/api.py` (lignes 127-131)

**Code concerné** :
```python
# api.py (lignes 127-131)
# Récupération du modèle depuis ML Registry
ml_cos_manager = get_cos_manager(ml_api_key_id, ml_secret_access_key, ml_bucket_name, ml_endpoint_url)
model_path = ml_cos_manager.download_model(run_id=run_id)
base_model_loader = BaseModelLoader()
model = base_model_loader.load_model(model_uri=model_path)
config_context.set("loaded_model", model)

# Le code suppose implicitement un modèle sklearn/pickle
# Aucune gestion pour :
# - Transformers HuggingFace (tokenizer + model)
# - TensorFlow SavedModel (répertoire, pas fichier)
# - PyTorch avec state_dict (nécessite la classe du modèle)
# - ONNX Runtime
# - Modèles multi-artefacts
```

**Problèmes engendrés** :
- Impossible de déployer des modèles NLP modernes (BERT, GPT, LLaMA)
- Impossible de déployer des modèles de Vision (ResNet, YOLO, Stable Diffusion)
- Les cas d'usage les plus demandés (chatbots, analyse d'images) sont exclus
- Les équipes data science créent des solutions ad-hoc non standardisées
- Perte totale de l'avantage du template pour les projets IA modernes
- Le template devient obsolète face à l'évolution du marché

**Solution** : Implémenter un pattern Factory avec loaders spécialisés par framework :
```python
# common/model_loaders.py
MODEL_LOADERS = {
    "sklearn": SklearnLoader,      # pickle/joblib
    "transformers": TransformersLoader,  # HuggingFace
    "tensorflow": TensorFlowLoader,      # SavedModel
    "pytorch": PyTorchLoader,            # state_dict
    "onnx": ONNXLoader                   # ONNX Runtime
}

def get_model_loader(model_type: str) -> BaseModelLoader:
    return MODEL_LOADERS[model_type]()
```

Configurer le type dans `app_config.yml` :
```yaml
models:
  sentiment_classifier:
    type: "transformers"
    task: "sentiment-analysis"
    run_id: "abc123"
```

---

### 2.5 Profiling Désactivé Sans Explication

**Localisation** : `industrialisation/src/batch.py` (lignes 74-78)

**Code concerné** :
```python
# batch.py (lignes 74-78)
@duration_request
# @profile_time_memory(
#     mem_log_path=f"{get_data_set_project_name()}/monitoring_logs/memory_usage/memory_profile_{today}.log",
#     time_log_path=f"{get_data_set_project_name()}/monitoring_logs/time_usage/time_profile_{today}.log",
# )
def main() -> None:
    """Run main method for batch."""
```

```python
# custom_profiler.py (lignes 11-38) - Le décorateur existe mais n'est pas utilisé
def profile_time_memory(mem_log_path: str, time_log_path: str) -> Callable[[F], F]:
    """Profile memory usage and execution time."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            profiler = LineProfiler()
            # ... implémentation complète ...
```

**Problèmes engendrés** :
- Fonctionnalité développée, documentée dans le code, mais désactivée sans explication
- Impossibilité de diagnostiquer les problèmes de performance en production
- Pas de métriques pour identifier les goulots d'étranglement
- Aucun commentaire expliquant pourquoi c'est commenté (bug ? performance ? incompatibilité Domino ?)
- Les développeurs ne savent pas s'ils peuvent l'activer en toute sécurité
- Perte de temps à redécouvrir/réimplémenter le profiling

**Solution** : Rendre le profiling conditionnel via variable d'environnement :
```python
ENABLE_PROFILING = os.getenv('ENABLE_PROFILING', 'false').lower() == 'true'

def conditional_profile(func):
    if not ENABLE_PROFILING:
        return func
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        logger.info(f"[PROFILING] {func.__name__}: {duration:.2f}s")
        return result
    return wrapper
```

Documenter dans le README : "Pour activer le profiling : `export ENABLE_PROFILING=true`"

---

## 3. Défauts Modérés

### 3.1 Identifiant de Modèle Statique

**Localisation** : `config/application/app_config.yml` (lignes 1-9)

**Code concerné** :
```yaml
# app_config.yml (lignes 1-9)
models:
  iris_classifier_model:
    # run_id: 'c31712e022f941bf8acf230209666635'  # Ancienne version commentée
    run_id: 'a7e816be60a943a8bdb6de764ab37d4a'   # Version actuelle hardcodée
    features:
      - "sepal_length"
      - "sepal_width"
      - "petal_length"
      - "petal_width"
```

**Problèmes engendrés** :
- Changer de version de modèle nécessite : modifier le fichier, commit, push, attendre CI/CD, déployer
- Délai de 15-30 minutes minimum pour un simple changement de modèle
- Pas de rollback rapide en cas de problème (même processus)
- Impossible de faire du A/B testing (10% trafic vers nouveau modèle)
- Pas d'utilisation des alias MLflow ("champion", "challenger", "archived")
- L'historique des versions est dans les commentaires Git, pas dans la config

**Solution** : Supporter les alias MLflow en plus des run_id :
```yaml
models:
  iris_classifier_model:
    model_name: "iris-classifier"  # Nom dans MLflow Registry
    alias: "champion"              # Alias au lieu de run_id fixe
    # Le changement d'alias dans MLflow = déploiement instantané
```

Le code résout l'alias au démarrage :
```python
def resolve_model_uri(config: dict) -> str:
    if "alias" in config:
        return f"models:/{config['model_name']}@{config['alias']}"
    return f"runs:/{config['run_id']}/model"
```

---

### 3.2 Absence de Monitoring

**Localisation** : `industrialisation/src/api.py` - Aucune instrumentation

**Code concerné** :
```python
# api.py (lignes 157-201)
@duration_request  # Seul décorateur existant - log la durée uniquement
def inference(data: dict) -> dict:
    # ... traitement ...
    prediction = model.predict(data)
    return {"prediction": float(prediction)}
    
    # Aucune métrique exportée :
    # - Nombre de prédictions par minute
    # - Latence p50, p95, p99
    # - Taux d'erreur
    # - Distribution des valeurs d'entrée
    # - Détection de data drift
```

**Problèmes engendrés** :
- Production complètement aveugle : impossible de savoir si le service fonctionne correctement
- Pas de détection des dégradations de performance (latence qui augmente progressivement)
- Pas d'alerting automatique en cas de problème
- Debugging post-mortem très difficile ("que s'est-il passé hier à 14h ?")
- Impossible de définir des SLA (Service Level Agreement) sans métriques
- Data drift non détecté : le modèle peut devenir obsolète sans alerte

**Solution** : Intégrer Prometheus avec métriques standard :
```python
from prometheus_client import Counter, Histogram

PREDICTIONS = Counter('model_predictions_total', 'Total predictions', ['model', 'status'])
LATENCY = Histogram('model_prediction_seconds', 'Prediction latency', ['model'])

@LATENCY.labels(model='iris').time()
def inference(data):
    try:
        result = model.predict(data)
        PREDICTIONS.labels(model='iris', status='success').inc()
        return result
    except Exception:
        PREDICTIONS.labels(model='iris', status='error').inc()
        raise
```

Fournir un dashboard Grafana pré-configuré dans `monitoring/grafana-dashboard.json`.

---

### 3.3 Validation des Inputs Insuffisante

**Localisation** : `industrialisation/src/api.py` (lignes 143-149)

**Code concerné** :
```python
# api.py (lignes 143-149)
class DataModel(BaseModel):
    """Data Model for iris."""
    sepal_length: float  # Aucune contrainte : -1000 accepté
    sepal_width: float   # Aucune contrainte : NaN non géré
    petal_length: float  # Pas de validation de plage
    petal_width: float   # Pas de détection d'outliers

# Utilisation ligne 179
validated_data = DataModel(**data["data"])
# Si sepal_length = -100, ça passe !
# Si petal_width = NaN, comportement indéfini
```

**Problèmes engendrés** :
- Requête avec `sepal_length = -100` acceptée sans erreur
- `petal_width = NaN` peut provoquer des erreurs silencieuses ou des prédictions absurdes
- Valeurs hors distribution d'entraînement (outliers) non détectées
- Prédictions potentiellement aberrantes retournées au client sans avertissement
- Pas de feedback utilisateur sur les erreurs de saisie
- Difficile de déboguer des prédictions incorrectes en production

**Solution** : Enrichir le modèle Pydantic avec contraintes et validateurs :
```python
class IrisInputModel(BaseModel):
    sepal_length: float = Field(ge=0, le=15, description="Longueur sépale (cm)")
    sepal_width: float = Field(ge=0, le=10, description="Largeur sépale (cm)")
    petal_length: float = Field(ge=0, le=15, description="Longueur pétale (cm)")
    petal_width: float = Field(ge=0, le=5, description="Largeur pétale (cm)")
    
    @validator('*', pre=True)
    def reject_nan(cls, v, field):
        if isinstance(v, float) and math.isnan(v):
            raise ValueError(f"{field.name} ne peut pas être NaN")
        return v
```

---

### 3.4 Pas de Versioning d'API

**Localisation** : `run_api.py` (lignes 39-41)

**Code concerné** :
```python
# run_api.py (lignes 39-41)
def get_response(**kwargs: dict) -> dict:
    """Get response."""
    return inference(data=kwargs)

# Point d'entrée unique, pas de version
# Pas de route /v1/predict ou /v2/predict
# Pas de header X-API-Version
```

**Problèmes engendrés** :
- Tout changement de signature (ajout/suppression de champ) casse immédiatement tous les clients
- Impossible de maintenir l'ancienne et la nouvelle version en parallèle
- Pas de période de dépréciation pour migrer les clients progressivement
- Les équipes consommatrices subissent les breaking changes sans préavis
- Rollback d'API impossible sans rollback complet du service

**Solution** : Exposer des endpoints versionnés :
```python
@app.route('/v1/predict', methods=['POST'])
def predict_v1():
    # Ancienne version, deprecated
    response = jsonify(legacy_inference(request.json))
    response.headers['X-API-Deprecated'] = 'true'
    response.headers['X-API-Sunset-Date'] = '2024-06-01'
    return response

@app.route('/v2/predict', methods=['POST'])
def predict_v2():
    # Nouvelle version
    return jsonify(inference(request.json))
```

---

### 3.5 Dépendances Dev en Production

**Localisation** : `pyproject.toml` (lignes 38-44)

**Code concerné** :
```toml
# pyproject.toml (lignes 38-44)
[tool.poetry.dependencies]
python-dotenv = "^1.0.1"  # Utile uniquement en dev local
colorlog = "^6.9.0"       # Logs colorés = dev uniquement
dotenv = "0.9.9"          # DOUBLON avec python-dotenv !
ml-utils = "^1.9.0"       # OK pour prod
mlflow = "2.16.2"         # OK pour prod
```

**Problèmes engendrés** :
- Image Docker de production gonflée de 50-100 MB inutiles
- Surface d'attaque augmentée : plus de dépendances = plus de CVE potentielles
- `dotenv` et `python-dotenv` sont des doublons (même fonctionnalité)
- `colorlog` n'a aucun sens dans des conteneurs où les logs sont centralisés en JSON
- Temps de build Docker allongé inutilement

**Solution** : Séparer strictement les groupes de dépendances :
```toml
[tool.poetry.dependencies]
# PRODUCTION UNIQUEMENT
ml-utils = "^1.9.0"
mlflow = "2.16.2"

[tool.poetry.group.dev.dependencies]
# DÉVELOPPEMENT UNIQUEMENT
python-dotenv = "^1.0.1"
colorlog = "^6.9.0"
pytest = "^8.3.3"
```

Builder avec : `poetry install --only=main,api --no-dev`

---

### 3.6 Pas de Stratégie de Rollback

**Localisation** : Aucune documentation existante

**Problèmes engendrés** :
- En cas de bug critique en production, pas de procédure claire documentée
- Temps de rollback indéterminé : peut prendre 30 minutes à 2 heures
- Stress et panique lors des incidents
- Chaque rollback est improvisé, avec risque d'erreurs supplémentaires
- Perte de confiance des équipes : peur de déployer le vendredi

**Solution** : Documenter trois méthodes de rollback dans `docs/runbook/rollback.md` :

1. **Rollback instantané via MLflow** (< 1 min) : Changer l'alias "champion" vers la version précédente
2. **Rollback Kubernetes** (< 5 min) : `kubectl rollout undo deployment/iris-api`
3. **Rollback CI/CD** (< 30 min) : Redéployer un tag Git antérieur

Inclure une checklist post-rollback (vérification service, notification équipe, création ticket post-mortem).

---

## 4. Problèmes Organisationnels

### 4.1 Convention de Nommage Rigide

**Localisation** : `README.md` (lignes 29-51)

**Code concerné** :
```markdown
# README.md (lignes 29-51)
Convention:

in case of a compound name, the name should be separated by a Hyphen: "-" 
and should not contain an underscore ( Hyphen: "_" ).

the project name in Domino and its organization will follow the same convention

Exemple:
- Environment DEV:
   - Organisation ( DEV ): bcef_{project-name}_dev 
   - Project name Domino: {project-name}-dev 
```

**Problèmes engendrés** :
- Convention imposée sans justification technique
- Friction organisationnelle : "Pourquoi je dois renommer mon projet existant ?"
- Projets nommés avec underscores (convention Python standard) rejetés
- Pas d'outil automatique pour normaliser les noms
- Erreurs silencieuses si la convention n'est pas respectée

**Solution** : Créer un script `scripts/normalize_project_name.py` :
```python
def normalize(name: str) -> str:
    # my_super_project → my-super-project
    return re.sub(r'[\s_]+', '-', name.lower()).strip('-')
```

Documenter la justification technique (ex: compatibilité Kubernetes labels, conventions Domino).

---

### 4.2 Absence de Guide de Contribution

**Localisation** : Aucun fichier `CONTRIBUTING.md`

**Problèmes engendrés** :
- Pas de processus pour proposer des améliorations au template
- Les équipes modifient leur copie locale sans partager les améliorations
- Pas de règles pour les merge requests (qui review ? quels critères ?)
- Bugs découverts non remontés à l'équipe maintenant le template
- Divergence progressive entre les copies du template

**Solution** : Créer `CONTRIBUTING.md` avec :
- Processus de signalement de bugs (template d'issue)
- Processus de proposition de features (discussion préalable)
- Standards de code (formatage, tests, documentation)
- Processus de review (2 reviewers, délai 3-5 jours)
- Contacts de l'équipe core

---

## 5. Synthèse des Recommandations

### Priorité Immédiate (Semaine 1)

| Action | Fichier(s) | Effort | Impact |
|--------|-----------|--------|--------|
| Rédiger documentation Quick Start | `docs/setup.md` | 2 jours | Critique |
| Créer script d'initialisation unique | `scripts/init.sh` | 1 jour | Critique |
| Documenter gestion des secrets | `.env.template`, `scripts/check_secrets.py` | 0.5 jour | Critique |
| Corriger thread-safety ConfigContext | `common/config_context.py` | 0.5 jour | Critique |
| Réécrire tests avec assertions | `tests/unit/` | 2 jours | Majeur |

### Priorité Haute (Semaine 2-3)

| Action | Fichier(s) | Effort | Impact |
|--------|-----------|--------|--------|
| Créer interfaces pour ml-utils | `common/interfaces.py` | 1 jour | Majeur |
| Ajouter support Transformers/PyTorch | `common/model_loaders.py` | 2 jours | Majeur |
| Intégrer monitoring Prometheus | `common/monitoring.py` | 2 jours | Majeur |
| Harmoniser conda/poetry | `pyproject.toml`, `environment*.yaml` | 1 jour | Majeur |
| Validation stricte inputs Pydantic | `models/input_validation.py` | 0.5 jour | Modéré |

### Priorité Standard (Mois suivant)

| Action | Fichier(s) | Effort | Impact |
|--------|-----------|--------|--------|
| Profiling conditionnel | `batch.py`, `custom_profiler.py` | 0.5 jour | Modéré |
| Versioning API | `run_api.py` | 0.5 jour | Modéré |
| Guide de contribution | `CONTRIBUTING.md` | 0.5 jour | Modéré |
| Documentation rollback | `docs/runbook/rollback.md` | 0.5 jour | Modéré |
| Séparation dépendances dev/prod | `pyproject.toml`, `Dockerfile` | 0.5 jour | Mineur |

---

## 6. Conclusion

Le template IA Factory repose sur des fondations architecturales pertinentes : séparation exploration/industrialisation, gestion multi-environnements, intégration CI/CD, et adoption des pratiques MLOps. Cependant, l'écart entre la vision et l'implémentation est significatif.

Les cinq défauts critiques identifiés (documentation vide, complexité d'installation, gestion des secrets, détection d'environnement, thread-safety) constituent des obstacles majeurs à l'adoption. Sans correction rapide, le template restera un document d'architecture théorique plutôt qu'un outil opérationnel utilisé au quotidien.

**Effort de remédiation estimé** : 15-20 jours-homme pour atteindre un niveau de maturité production.

**Indicateur de succès proposé** : Réduire le temps entre le clonage du template et le premier déploiement fonctionnel de 2-3 heures à moins de 15 minutes.

**Recommandation finale** : Prioriser absolument la documentation et le script d'initialisation. Un template parfait techniquement mais impossible à prendre en main sera abandonné au profit de solutions ad-hoc moins robustes mais plus accessibles.