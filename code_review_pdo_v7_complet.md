# CODE REVIEW EXHAUSTIF - Projet PDO (ap01202-record-pdo)
## VERSION 7 - RAPPORT COMPLET FUSIONNÉ

**Date :** 27 janvier 2026  
**Reviewer :** Tech Lead IA  
**Fichiers analysés :** 103  
**Lignes de code :** ~13 290 (Python)

---

# ⛔ VERDICT : NON APPROUVÉ POUR PRODUCTION

| Catégorie | Nombre |
|-----------|--------|
| 🔴 Issues Critiques | 8 |
| 🟠 Issues Haute Priorité | 11 |
| 🟡 Issues Moyenne Priorité | 15 |
| 🟢 Issues Basse Priorité | 2 |
| **Total** | **36** |

---

# 🔴 ISSUES CRITIQUES

---

## CRITIQUE-001 : Mot de passe Artifactory en clair

| Attribut | Valeur |
|----------|--------|
| **Script** | `config/services/services_dev.env`, `services_pprod.env`, `services_prod.env` |
| **Ligne** | 14 (dev), 12 (pprod), 12 (prod) |

**Code problématique :**
```properties
ARTIFACTORY_PASSWORD=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Ce qu'il y a à corriger :**  
Le mot de passe Artifactory est stocké en clair dans les fichiers de configuration. De plus, c'est le **même mot de passe** pour les 3 environnements (dev, pprod, prod), ce qui viole le principe de séparation des environnements.

**Impact potentiel :**  
- Compromission de l'infrastructure Artifactory si le repo est exposé
- Accès non autorisé aux packages privés BNP
- Violation des politiques de sécurité (PCI-DSS, SOX)
- Un attaquant avec accès au repo peut compromettre les 3 environnements

**Solution proposée :**  
Stocker les credentials dans un gestionnaire de secrets (Vault, AWS Secrets Manager) et les injecter via variables d'environnement au runtime. Révoquer immédiatement le token actuel et en générer un nouveau par environnement.

```python
# Injection via Vault au démarrage
vault = VaultConnector(config_path)
artifactory_password = os.getenv("ARTIFACTORY_PASSWORD")  # Injecté par Vault
```

---

## CRITIQUE-002 : Fichiers .env NON ignorés par Git

| Attribut | Valeur |
|----------|--------|
| **Script** | `_gitignore` |
| **Ligne** | 1-2 |

**Code problématique :**
```gitignore
.env
.env.*
```

**Ce qu'il y a à corriger :**  
Le pattern `.env.*` ne matche PAS les fichiers `services_dev.env`, `services_pprod.env`, `services_prod.env`. Ces fichiers sont donc trackés dans Git avec leurs credentials.

**Impact potentiel :**  
- Les credentials sont dans l'historique Git, même après suppression
- Tout développeur avec accès au repo voit les mots de passe
- Impossible de révoquer l'accès sans nettoyer tout l'historique Git

**Solution proposée :**  
Ajouter les patterns corrects au `.gitignore` et nettoyer l'historique Git avec BFG Repo Cleaner.

```gitignore
services_*.env
config/services/*.env
```

---

## CRITIQUE-003 : Données RGPD écrites en clair

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/base_transformation.py` |
| **Lignes** | 85-95, 237-251, 260, 269, 278-293 |

**Code problématique :**
```python
df_dict["unfiltered_df_main"].write_csv(
    f"{LOCAL_PATH}/unfiltered_df_main.csv", separator=",", include_header=True
)
```

**Ce qu'il y a à corriger :**  
22 écritures CSV de données bancaires sensibles (SIREN, soldes, scores de risque, transactions) sont effectuées en clair sur le système de fichiers, dans un chemin hardcodé `/mnt/data/output`.

**Impact potentiel :**  
- Non-conformité RGPD (données personnelles non chiffrées)
- Exposition des données en cas de compromission du serveur
- Pas de contrôle d'accès sur les fichiers
- Risque d'amende jusqu'à 4% du CA annuel

**Solution proposée :**  
Supprimer les écritures de debug en production, ou les conditionner à un flag `DEBUG`. Si nécessaire, chiffrer les fichiers.

```python
if os.getenv("DEBUG_MODE", "false").lower() == "true":
    df_dict["unfiltered_df_main"].write_csv(f"{LOCAL_PATH}/debug.csv")
```

---

## CRITIQUE-004 : Lazy Loading NON utilisé

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/base_transformation.py` |
| **Lignes** | 112-215 |

**Code problématique :**
```python
df_main_encoded = df_encoding(df_main)       # Matérialise
df_main_reboot = add_reboot_features(...)    # Matérialise
df_main_transac = add_transac_features(...)  # Matérialise
# ... 8 autres matérialisations
```

**Ce qu'il y a à corriger :**  
Le pipeline effectue 11 matérialisations successives de DataFrames Polars (mode eager). Chaque étape crée une copie complète en mémoire au lieu d'utiliser le lazy evaluation de Polars.

**Impact potentiel :**  
- Perte de 30-50% de performance sur le pipeline complet
- Consommation mémoire 3x supérieure à l'optimal
- Risque d'OOM sur gros volumes

**Solution proposée :**  
Refactorer le pipeline pour utiliser des LazyFrames Polars et ne matérialiser qu'une seule fois à la fin avec `.collect()`.

```python
df_lazy = unfiltered_df_main.lazy()
df_lazy = df_encoding_lazy(df_lazy)
df_lazy = add_reboot_features_lazy(df_lazy, reboot.lazy())
df_final = df_lazy.collect()  # Une seule matérialisation
```

---

## CRITIQUE-005 : SQL Injection via .replace()

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/sql/retrieve_sql_query_transac.py` |
| **Lignes** | 78-79 |

**Code problématique :**
```python
sql_query = sql_query.replace("start_date", start_date)
sql_query = sql_query.replace("end_date", end_date)
```

**Ce qu'il y a à corriger :**  
Les paramètres `start_date` et `end_date` sont injectés dans la requête SQL via un simple `replace()` sans aucune validation ni échappement.

**Impact potentiel :**  
- Exécution de code SQL arbitraire
- Exfiltration de données (SELECT *)
- Modification/suppression de données (DROP, DELETE)

**Solution proposée :**  
Valider strictement le format des dates avec une regex avant injection.

```python
import re
def validate_date(date_str: str) -> str:
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError(f"Invalid date format: {date_str}")
    return date_str

sql_query = sql_query.replace("start_date", validate_date(start_date))
```

---

## CRITIQUE-006 : Faux lazy_query() trompeur

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/con_starburst.py` |
| **Lignes** | 70-76 |

**Code problématique :**
```python
def lazy_query(self, query: str) -> pl.LazyFrame:
    eager_df = self.starburst_manager.get_engine(query)  # Charge TOUT
    return eager_df.lazy()  # Conversion APRÈS = inutile
```

**Ce qu'il y a à corriger :**  
La méthode `lazy_query()` suggère une évaluation différée, mais charge d'abord 100% des données en mémoire puis convertit en LazyFrame. Le "lazy" est trompeur.

**Impact potentiel :**  
- Développeurs trompés pensant bénéficier du lazy loading
- Aucun gain de performance malgré le nom
- Dette technique et confusion

**Solution proposée :**  
Supprimer cette méthode ou la renommer avec un docstring explicite.

```python
def query_as_lazyframe(self, query: str) -> pl.LazyFrame:
    """WARNING: Data is fully loaded first. No true lazy evaluation."""
    eager_df = self.starburst_manager.get_engine(query)
    return eager_df.lazy()
```

---

## CRITIQUE-007 : app.sh référence fichier inexistant

| Attribut | Valeur |
|----------|--------|
| **Script** | `app.sh` |
| **Ligne** | (référence à stream.py) |

**Code problématique :**
```bash
python stream.py  # Fichier inexistant
```

**Ce qu'il y a à corriger :**  
Le script de démarrage `app.sh` référence un fichier `stream.py` qui n'existe pas dans l'arborescence du projet.

**Impact potentiel :**  
- Échec du déploiement en production
- Erreur `FileNotFoundError` au runtime
- Pipeline CI/CD cassé

**Solution proposée :**  
Supprimer la référence à `stream.py` ou créer le fichier si nécessaire.

```bash
# Supprimer ou commenter la ligne
# python stream.py  # SUPPRIMÉ
```

---

## CRITIQUE-008 : Division par zéro non protégée (SAFIR CONSO)

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/preprocessing/preprocessing_safir_conso.py` |
| **Lignes** | 37, 38, 60, 82 |

**Code problématique :**
```python
# Ligne 37
.then(pl.col("mt_310_conso") / pl.col("c_duree_excce_conso") * 12)

# Ligne 38
.otherwise((pl.col("mt_24") + pl.col("mt_309")) / pl.col("c_duree_excce_conso") * 12)

# Ligne 60
/ pl.col("c_duree_excce_conso")

# Ligne 82
/ pl.col("c_duree_excce_conso")
```

**Ce qu'il y a à corriger :**  
La colonne `c_duree_excce_conso` est utilisée comme diviseur à 4 endroits **sans aucune vérification** que la valeur n'est pas zéro ou null. Si cette durée d'exercice comptable est 0 (exercice de durée nulle) ou null (donnée manquante), une division par zéro se produit.

**Impact potentiel :**  
- **Crash du batch** si une seule ligne a `c_duree_excce_conso = 0`
- Production de valeurs `inf` (infini) si Polars ne lève pas d'exception
- **Corruption silencieuse des données** : les ratios financiers deviennent invalides
- Propagation des erreurs jusqu'au calcul PDO final
- **Scores PDO incorrects** pour les entreprises concernées

**Solution proposée :**  
Ajouter une protection avant les divisions : remplacer les valeurs 0 ou null par une valeur par défaut (12 mois standard) ou exclure ces lignes du calcul.

```python
# Ajouter AVANT les calculs (après ligne 29)
df_conso = df_conso.with_columns(
    pl.when((pl.col("c_duree_excce_conso").is_null()) | (pl.col("c_duree_excce_conso") == 0))
    .then(pl.lit(12))  # Durée standard de 12 mois
    .otherwise(pl.col("c_duree_excce_conso"))
    .alias("c_duree_excce_conso")
)
```

---

# 🟠 ISSUES HAUTE PRIORITÉ

---

## HAUTE-009 : Window functions Polars séparées

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/sql/retrieve_sql_query_transac.py` |
| **Lignes** | 149-157 |

**Code problématique :**
```python
df = df.with_columns(pl.col("amount").sum().over(["i_uniq_kpi", "category"]).alias("netamount"))
df = df.with_columns(pl.col("amount").min().over(["i_uniq_kpi", "category"]).alias("min_amount"))
df = df.with_columns(pl.col("amount").max().over(["i_uniq_kpi", "category"]).alias("max_amount"))
```

**Ce qu'il y a à corriger :**  
5 appels séparés à `with_columns()` avec des window functions. Chaque appel déclenche un scan complet du DataFrame.

**Impact potentiel :**  
- 5 scans au lieu de 1 = ~400% de travail inutile
- Perte de 20-40% de performance sur cette étape

**Solution proposée :**  
Regrouper toutes les window functions dans un seul appel avec une liste.

```python
df = df.with_columns([
    pl.col("amount").sum().over(["i_uniq_kpi", "category"]).alias("netamount"),
    pl.col("amount").min().over(["i_uniq_kpi", "category"]).alias("min_amount"),
    pl.col("amount").max().over(["i_uniq_kpi", "category"]).alias("max_amount"),
])
```

---

## HAUTE-010 : 5 scans aggregate_category répétés

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/preprocessing/preprocessing_transac.py` |
| **Lignes** | 98-102 |

**Code problématique :**
```python
df_interets = aggregate_category(donnees_transac_filtered, "interets__", "interets__")
df_turnover = aggregate_category(donnees_transac_filtered, "turnover__", "turnover__")
df_prlv_retourne = aggregate_category(donnees_transac_filtered, "prlv_sepa_retourne__", ...)
```

**Ce qu'il y a à corriger :**  
La fonction `aggregate_category()` est appelée 5 fois sur le même DataFrame, provoquant 5 scans complets.

**Impact potentiel :**  
- 5 scans complets au lieu de 1
- ~20% de perte de performance sur cette étape

**Solution proposée :**  
Restructurer pour faire toutes les agrégations en une seule passe.

```python
categories = ["interets__", "turnover__", "prlv_sepa_retourne__", ...]
df_aggregated = aggregate_all_categories(donnees_transac_filtered, categories)
```

---

## HAUTE-011 : 280+ codes sectoriels hardcodés

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/preprocessing/preprocessing_df_main.py` |
| **Lignes** | 21-301 |

**Code problématique :**
```python
.when(pl.col("c_sectrl_1").is_in([
    "420053", "420051", "420050", "420052", "420040", ...
]))
```

**Ce qu'il y a à corriger :**  
Plus de 280 codes sectoriels sont hardcodés directement dans le code Python sans fichier de référence ni versioning.

**Impact potentiel :**  
- Maintenance impossible
- Pas d'audit trail des changements
- Risque d'erreur lors de modifications

**Solution proposée :**  
Externaliser les codes dans un fichier YAML versionné.

```yaml
# config/application/sector_codes.yml
sector_encoding:
  class_1:
    - "420053"
    - "420051"
```

---

## HAUTE-012 : Seuils ML hardcodés (Magic Values)

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/preprocessing/preprocessing_format_variables.py` |
| **Lignes** | 32-133 |

**Code problématique :**
```python
pl.when(pl.col("reboot_score2") < 0.00142771716)
.then(pl.lit("1"))
```

**Ce qu'il y a à corriger :**  
15+ seuils numériques issus de la calibration ML sont hardcodés (0.00142771716, 76378.7031, etc.) sans documentation de leur origine.

**Impact potentiel :**  
- Risque de régression silencieuse si seuils modifiés
- Audit ML impossible
- Pas de traçabilité des calibrations

**Solution proposée :**  
Externaliser dans un fichier de configuration avec métadonnées.

```yaml
# config/application/ml_thresholds.yml
reboot_score:
  calibration_date: "2025-06-15"
  thresholds:
    class_1: 0.00142771716
```

---

## HAUTE-013 : Zéro tests d'intégration

| Attribut | Valeur |
|----------|--------|
| **Script** | `tests/intégration/` |
| **Ligne** | N/A (dossier vide) |

**Code problématique :**
```
tests/intégration/
├── __init__.py  # Vide
└── industrialisation/
    └── __init__.py  # Vide
```

**Ce qu'il y a à corriger :**  
Le dossier de tests d'intégration existe mais ne contient aucun test. Le flux complet SQL → Preprocessing → PDO → COS n'est jamais testé.

**Impact potentiel :**  
- Régressions non détectées avant production
- Bugs découverts uniquement en production
- Confiance réduite dans les déploiements

**Solution proposée :**  
Créer des tests d'intégration avec données mockées.

```python
# tests/intégration/test_pipeline_e2e.py
def test_full_pipeline_with_mock_data():
    mock_data = create_mock_starburst_data()
    result = run_full_pipeline(mock_data)
    assert result["df_main_pdo"]["PDO"].is_not_null().all()
```

---

## HAUTE-014 : Duplication code 99.5%

| Attribut | Valeur |
|----------|--------|
| **Scripts** | `common/config_context.py`, `config/config_models.py` |
| **Lignes** | 1-70 (les deux fichiers) |

**Code problématique :**
```python
# config_context.py
class ConfigContext:
    _instance = None
    _config: dict = {}
    
# config_models.py - IDENTIQUE sauf le nom
class ConfigModels:
    _instance = None
    _config: dict = {}
```

**Ce qu'il y a à corriger :**  
Les deux fichiers sont identiques à 99.5% (seul le nom de classe change). Violation flagrante du principe DRY.

**Impact potentiel :**  
- Maintenance double
- Risque de divergence entre les deux classes
- Code inutilement dupliqué

**Solution proposée :**  
Créer une classe de base abstraite et en hériter.

```python
# common/base_config.py
class BaseConfigSingleton:
    _instance = None
    _config: dict[str, Any] = {}

# common/config_context.py
class ConfigContext(BaseConfigSingleton):
    pass
```

---

## HAUTE-015 : Exception générique catch-all

| Attribut | Valeur |
|----------|--------|
| **Script** | `industrialisation/src/batch.py` |
| **Ligne** | 146 |

**Code problématique :**
```python
except Exception as e:
    log_batch_error(e)
    print_final_summary()
    raise
```

**Ce qu'il y a à corriger :**  
Le catch-all `except Exception` capture toutes les exceptions sans distinction, masquant les erreurs spécifiques.

**Impact potentiel :**  
- Erreurs spécifiques masquées
- Debugging difficile
- Logs peu informatifs

**Solution proposée :**  
Capturer les exceptions spécifiques d'abord.

```python
except DatabaseConnectionError as e:
    logger.error("Database error: %s", e)
    raise
except Exception as e:
    logger.exception("Unexpected error")
    raise RuntimeError(f"Batch failed: {e}") from e
```

---

## HAUTE-016 : Code mort (train.py 100% commenté)

| Attribut | Valeur |
|----------|--------|
| **Script** | `exploration/scripts/train.py` |
| **Lignes** | 1-91 |

**Code problématique :**
```python
# import logging
# import os
# import mlflow
# ... 91 lignes commentées
```

**Ce qu'il y a à corriger :**  
Le fichier contient 91 lignes de code, toutes commentées. C'est du code mort.

**Impact potentiel :**  
- Confusion pour les développeurs
- Dette technique
- Faux positifs dans les analyses de code

**Solution proposée :**  
Supprimer le fichier ou le réactiver s'il est nécessaire.

```bash
git rm exploration/scripts/train.py
```

---

## HAUTE-017 : Division par zéro partiellement protégée (SAFIR SOC)

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/preprocessing/preprocessing_safir_soc.py` |
| **Lignes** | 85, 89, 127, 129 |

**Code problématique :**
```python
# Ligne 85
/ pl.col("c_duree_excce_soc")

# Ligne 89
.then((pl.col("mt_182") + pl.col("mt_285") + pl.col("mt_295")) / pl.col("c_duree_excce_soc") * 12)

# Ligne 127
.then(pl.col("mt_479") / pl.col("c_duree_excce_soc") * 12)

# Ligne 129
.then((pl.col("mt_480") + pl.col("mt_435") - pl.col("mt_209")) / pl.col("c_duree_excce_soc") * 12)
```

**Ce qu'il y a à corriger :**  
Une protection existe aux lignes 56-63 qui remplace `c_duree_excce_soc = 0` ou `null` par `duree_excce_imp`. **MAIS** cette protection est incomplète car `duree_excce_imp` est calculé comme :
```python
(d_fin_excce_soc - leg_d_fin_excce).dt.total_days() / 30.44
```
Si les deux dates sont identiques (bilan de durée 0), `duree_excce_imp = 0`, et la division par zéro reste possible.

**Impact potentiel :**  
- Division par zéro dans des cas edge (bilans de durée 0)
- Valeurs `inf` ou crash
- Données financières corrompues

**Solution proposée :**  
Ajouter une protection supplémentaire après le calcul de `duree_excce_imp` pour garantir une valeur minimale.

```python
# Après ligne 63, ajouter une protection finale
df_soc = df_soc.with_columns(
    pl.when(pl.col("c_duree_excce_soc") <= 0)
    .then(pl.lit(12))  # Valeur par défaut si toujours <= 0
    .otherwise(pl.col("c_duree_excce_soc"))
    .alias("c_duree_excce_soc")
)
```

---

## HAUTE-018 : Propagation de NaN dans le modèle ML

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/calcul_pdo.py` |
| **Lignes** | 497-499 |

**Code problématique :**
```python
X = df_encoded.select(feature_order).to_numpy()
probas = model.predict_proba(X)[:, 0]
```

**Ce qu'il y a à corriger :**  
La conversion `.to_numpy()` transforme les valeurs `null` Polars en `NaN` numpy. Ces `NaN` sont ensuite passés au modèle sklearn `predict_proba()` qui :
1. Peut retourner `NaN` pour les lignes concernées
2. Peut lever une exception selon la version sklearn
3. Peut produire des probabilités aberrantes

Aucune vérification n'est faite avant ou après la prédiction.

**Impact potentiel :**  
- Scores PDO = `NaN` pour certaines entreprises
- Crash du modèle sklearn
- Données envoyées au COS avec des valeurs manquantes/incorrectes
- **Décisions de crédit basées sur des données corrompues**

**Solution proposée :**  
Vérifier l'absence de NaN avant la prédiction et gérer les cas problématiques.

```python
X = df_encoded.select(feature_order).to_numpy()

# Vérifier les NaN
if np.isnan(X).any():
    nan_rows = np.where(np.isnan(X).any(axis=1))[0]
    logger.warning("Found %d rows with NaN values in features", len(nan_rows))
    X = np.nan_to_num(X, nan=0.0)  # Ou stratégie métier appropriée

probas = model.predict_proba(X)[:, 0]
```

---

## HAUTE-019 : Overflow potentiel avec exp()

| Attribut | Valeur |
|----------|--------|
| **Scripts** | `common/calcul_pdo.py`, `common/preprocessing/preprocessing_reboot.py` |
| **Lignes** | calcul_pdo.py:206, 504 / preprocessing_reboot.py:29 |

**Code problématique :**
```python
# calcul_pdo.py:206
(1 - 1 / (1 + (pl.col("score").exp()))).alias("PDO_compute")

# calcul_pdo.py:504
(1 - 1 / (1 + (pl.col("score").exp()))).alias("PDO_compute")

# preprocessing_reboot.py:29
(1 / (1 + ((-1 * pl.col("q_score")).exp()))).alias("q_score2")
```

**Ce qu'il y a à corriger :**  
La fonction exponentielle `exp(x)` overflow quand `x > 709` (limite float64). Si le score calculé est très grand (positif ou négatif selon le signe), `exp(score)` produit `inf`, ce qui corrompt le calcul de probabilité.

**Impact potentiel :**  
- Valeurs `inf` ou `NaN` dans les scores
- Instabilité numérique
- Probabilités incorrectes

**Solution proposée :**  
Utiliser une implémentation stable de la sigmoïde qui évite les overflow.

```python
# Implémentation stable de la sigmoïde
def stable_sigmoid(x):
    return pl.when(x >= 0)
        .then(1 / (1 + (-x).exp()))
        .otherwise(x.exp() / (1 + x.exp()))

# Utilisation
df_main = df_main.with_columns(
    (1 - stable_sigmoid(pl.col("score"))).alias("PDO_compute")
)
```

---

# 🟡 ISSUES MOYENNE PRIORITÉ

---

## MOYENNE-020 : Fonctions sans docstring

| Attribut | Valeur |
|----------|--------|
| **Scripts** | `base_transformation.py:41`, `version.py:9,17,21`, `custom_profiler.py:14,16`, `generate_confluence_doc.py:41,57,111`, `logging_utils.py:85` |

**Code problématique :**
```python
def __init__(self, app_config: dict, ...):
    self.app_config = app_config  # Pas de docstring
```

**Ce qu'il y a à corriger :**  
10 fonctions publiques n'ont pas de docstring.

**Impact potentiel :**  
- Code difficile à comprendre
- Documentation auto-générée incomplète

**Solution proposée :**  
Ajouter des docstrings Google-style.

```python
def __init__(self, app_config: dict, ...):
    """Initialize the BaseTransformation pipeline.
    
    Args:
        app_config: Application configuration with model coefficients.
    """
```

---

## MOYENNE-021 : Type hints incomplets

| Attribut | Valeur |
|----------|--------|
| **Scripts** | 23 fichiers |
| **Lignes** | 74 erreurs Mypy |

**Code problématique :**
```python
def load_data(self) -> dict:  # dict sans paramètres
def get_prefix_files(self) -> list:  # list sans paramètres
```

**Ce qu'il y a à corriger :**  
74 erreurs Mypy : `dict` et `list` sans paramètres de type.

**Impact potentiel :**  
- Pas de vérification de type statique
- IDE moins efficace

**Solution proposée :**  
Compléter les type hints avec les paramètres génériques.

```python
def load_data(self) -> dict[str, pl.DataFrame]:
def get_prefix_files(self) -> list[str]:
```

---

## MOYENNE-022 : Nommage FR/EN incohérent

| Attribut | Valeur |
|----------|--------|
| **Scripts** | Tout le projet |

**Code problématique :**
```python
donnees_transac = extract_starburst_transactions(...)  # FR
df_main = unfiltered_df_main.filter(...)               # EN
```

**Ce qu'il y a à corriger :**  
Mélange de français et anglais dans les noms de variables et fonctions.

**Impact potentiel :**  
- Code moins lisible
- Recherche dans le code difficile

**Solution proposée :**  
Standardiser en anglais.

```python
transaction_data = extract_starburst_transactions(...)
filter_main_df(df)
```

---

## MOYENNE-023 : SELECT DISTINCT excessifs

| Attribut | Valeur |
|----------|--------|
| **Scripts** | `common/sql/queries/*.sql` |
| **Lignes** | 7 occurrences (query_starburst_transac.sql) |

**Code problématique :**
```sql
SELECT DISTINCT column1, column2 FROM table
```

**Ce qu'il y a à corriger :**  
Utilisation de `SELECT DISTINCT` potentiellement inutile si la clé primaire garantit l'unicité.

**Impact potentiel :**  
- Performance SQL dégradée
- Tri inutile côté base

**Solution proposée :**  
Vérifier si DISTINCT est vraiment nécessaire.

```sql
SELECT column1, column2 FROM table  -- Sans DISTINCT si unicité garantie
```

---

## MOYENNE-024 : print() au lieu de logger

| Attribut | Valeur |
|----------|--------|
| **Script** | `config_helper/generate_project_config.py` |
| **Lignes** | 25 occurrences |

**Code problématique :**
```python
print("Bienvenue dans l'assistant de génération...")
```

**Ce qu'il y a à corriger :**  
25 `print()` au lieu du logger. Messages non structurés, non filtrables.

**Impact potentiel :**  
- Pas de logs structurés
- Impossible de filtrer par niveau

**Solution proposée :**  
Remplacer par le logger.

```python
logger.info("Bienvenue dans l'assistant de génération...")
```

---

## MOYENNE-025 : Fichiers sans tests correspondants

| Attribut | Valeur |
|----------|--------|
| **Scripts** | 8 modules sans tests |

**Ce qu'il y a à corriger :**  
8 modules n'ont pas de fichier de test : `config_models.py`, `log_model.py`, `get_env_var.py`, `train.py`, `constants.py`, `generate_project_config.py`, `extra_parameters_dto.py`, `generate_confluence_doc.py`.

**Impact potentiel :**  
- Couverture de tests incomplète
- Régressions non détectées

**Solution proposée :**  
Créer les fichiers de tests manquants.

```python
# tests/unit/config/test_config_models.py
def test_singleton_pattern():
    instance1 = ConfigModels()
    instance2 = ConfigModels()
    assert instance1 is instance2
```

---

## MOYENNE-026 : Encodage UTF-8 cassé dans docstrings

| Attribut | Valeur |
|----------|--------|
| **Scripts** | `calcul_pdo.py`, `batch.py`, `preprocessing_transac.py` |
| **Lignes** | 284 occurrences |

**Code problématique :**
```python
"""LOGIQUE DES COEFFICIENTS - MODÃˆLE P(NON-DÃ‰FAUT)"""
```

**Ce qu'il y a à corriger :**  
284 caractères UTF-8 mal encodés (`Ã©` au lieu de `é`).

**Impact potentiel :**  
- Documentation illisible
- Professionnalisme dégradé

**Solution proposée :**  
Ré-encoder en UTF-8 correct.

```python
"""LOGIQUE DES COEFFICIENTS - MODÈLE P(NON-DÉFAUT)"""
```

---

## MOYENNE-027 : Imports non triés (I001)

| Attribut | Valeur |
|----------|--------|
| **Scripts** | 23 fichiers |

**Ce qu'il y a à corriger :**  
Imports non triés selon l'ordre standard (stdlib → third-party → local).

**Impact potentiel :**  
- Non-conformité PEP8
- CI/CD qui échoue si isort activé

**Solution proposée :**  
Exécuter ruff avec `--fix` pour corriger automatiquement.

```bash
ruff check --select I001 --fix .
```

---

## MOYENNE-028 : Logging f-string (G004)

| Attribut | Valeur |
|----------|--------|
| **Scripts** | `con_cos.py`, `load_config.py`, etc. |
| **Lignes** | 70 occurrences |

**Code problématique :**
```python
logger.info(f"Downloading file: {cos_key}")
```

**Ce qu'il y a à corriger :**  
f-strings dans les appels de logging. Évaluation immédiate même si le niveau de log est désactivé.

**Impact potentiel :**  
- Performance dégradée
- Non-conformité aux bonnes pratiques

**Solution proposée :**  
Utiliser la substitution lazy.

```python
logger.info("Downloading file: %s", cos_key)
```

---

## MOYENNE-029 : Datetime sans timezone (DTZ001/DTZ005)

| Attribut | Valeur |
|----------|--------|
| **Scripts** | `batch.py:131`, `logging_utils.py:56,215,261`, `preprocessing_reboot.py:36` |
| **Lignes** | 47 occurrences |

**Code problématique :**
```python
now = datetime.now()
```

**Ce qu'il y a à corriger :**  
`datetime.now()` sans timezone explicite. Ambiguïté en production multi-région.

**Impact potentiel :**  
- Bugs subtils entre timezones
- Logs avec horodatage ambigu

**Solution proposée :**  
Spécifier une timezone explicite.

```python
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
```

---

## MOYENNE-030 : os.path au lieu de pathlib (PTH*)

| Attribut | Valeur |
|----------|--------|
| **Scripts** | Multiples |
| **Lignes** | 95 occurrences |

**Code problématique :**
```python
path = os.path.join(PROJECT_ROOT, "config", "app.yml")
```

**Ce qu'il y a à corriger :**  
95 occurrences de `os.path` au lieu de `pathlib.Path`.

**Impact potentiel :**  
- Code moins moderne
- Manipulation de chemins verbeuse

**Solution proposée :**  
Migrer vers pathlib.

```python
from pathlib import Path
path = Path(PROJECT_ROOT) / "config" / "app.yml"
```

---

## MOYENNE-031 : Fonctions trop longues (>50 lignes)

| Attribut | Valeur |
|----------|--------|
| **Scripts** | 18 fonctions |
| **Exemple** | `preprocessing_df_main.py:4` - `df_encoding()` = 319 lignes |

**Ce qu'il y a à corriger :**  
18 fonctions dépassent 50 lignes. La plus longue (`df_encoding`) fait 319 lignes.

**Impact potentiel :**  
- Tests unitaires difficiles
- Compréhension difficile
- Risque de bugs élevé

**Solution proposée :**  
Décomposer en sous-fonctions de 20-30 lignes.

```python
def df_encoding(df: pl.DataFrame) -> pl.DataFrame:
    df = _encode_sector_codes(df)
    df = _encode_legal_nature(df)
    return df
```

---

## MOYENNE-032 : Complexité cyclomatique élevée (CC=20)

| Attribut | Valeur |
|----------|--------|
| **Script** | `config_helper/generate_project_config.py` |
| **Ligne** | 58 |

**Code problématique :**
```python
def generate_process_mode_yaml(config, mode):
    if mode == "batch":
        if config.get("schedule"):
            # ... 20+ branches imbriquées
```

**Ce qu'il y a à corriger :**  
La fonction a une complexité cyclomatique de 20 (limite: 10).

**Impact potentiel :**  
- Difficile à tester exhaustivement
- Risque élevé de bugs

**Solution proposée :**  
Décomposer en fonctions spécialisées par mode.

```python
def generate_process_mode_yaml(config: dict, mode: str) -> dict:
    handlers = {"batch": _gen_batch, "stream": _gen_stream}
    return handlers[mode](config)
```

---

## MOYENNE-033 : Fichiers Black non conformes

| Attribut | Valeur |
|----------|--------|
| **Scripts** | 7 fichiers |

**Ce qu'il y a à corriger :**  
7 fichiers ne sont pas conformes au formatage Black.

**Impact potentiel :**  
- Échec des hooks pre-commit
- Incohérence de formatage

**Solution proposée :**  
Exécuter Black.

```bash
black --line-length 120 .
```

---

## MOYENNE-034 : Accès index sans vérification

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/calcul_pdo.py` |
| **Lignes** | 268-269 |

**Code problématique :**
```python
coeffs = dict(zip(feature_order, model.coef_[0]))
intercept = model.intercept_[0]
```

**Ce qu'il y a à corriger :**  
L'accès `model.coef_[0]` et `model.intercept_[0]` suppose que le modèle de régression logistique a bien des coefficients. Si le modèle est mal chargé (fichier pickle corrompu) ou incompatible, ces accès peuvent lever une `IndexError`.

**Impact potentiel :**  
- Crash du batch si le modèle est corrompu
- Pas de message d'erreur explicite

**Solution proposée :**  
Valider la structure du modèle avant utilisation.

```python
if not hasattr(model, 'coef_') or model.coef_.shape[0] == 0:
    raise ValueError("Model has no coefficients - may be corrupted")

coeffs = dict(zip(feature_order, model.coef_[0]))
intercept = model.intercept_[0]
```

---

# 🟢 ISSUES BASSE PRIORITÉ

---

## BASSE-035 : Import inutilisé

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/con_starburst.py` |
| **Ligne** | 1 |

**Code problématique :**
```python
from __future__ import annotations
```

**Ce qu'il y a à corriger :**  
Import non utilisé.

**Solution proposée :**  
Supprimer l'import.

---

## BASSE-036 : return None explicite inutile

| Attribut | Valeur |
|----------|--------|
| **Script** | `common/base_transformation.py` |
| **Ligne** | 253 |

**Code problématique :**
```python
def save_data_for_validation(self, df_dict: dict) -> None:
    ...
    return None  # Inutile
```

**Ce qu'il y a à corriger :**  
`return None` explicite superflu.

**Solution proposée :**  
Supprimer le `return None`.

---

# 📋 POINTS POSITIFS

✅ Architecture modulaire claire (common/, config/, industrialisation/)  
✅ Séparation preprocessing par domaine fonctionnel  
✅ Tests unitaires présents (~8000 lignes)  
✅ Logging structuré avec StepTracker  
✅ Context managers utilisés (StarburstConnector)  
✅ Configuration par environnement (dev/pprod/prod)  
✅ Documentation présente (README, docs/)  
✅ Pre-commit hooks configurés (Black, Ruff, Mypy)  

---

# 📊 MÉTRIQUES CIBLES

| Métrique | Actuel | Cible |
|----------|--------|-------|
| Issues critiques | 8 | 0 |
| Issues haute priorité | 11 | 0 |
| Issues moyenne priorité | 15 | 0 |
| Erreurs Ruff | 1631 | 0 |
| Erreurs Mypy | 74 | 0 |
| Fichiers Black | 7 | 0 |
| Fonctions sans docstring | 10 | 0 |
| Fonctions >50 lignes | 18 | 0 |
| Max CC | 20 | ≤10 |
| Tests intégration | 0 | ≥10 |
| Secrets en clair | 3 | 0 |
| Divisions non protégées | 8 | 0 |
| Gestion NaN/Inf | 0 | 100% |

---

# 🚀 PLAN DE REMÉDIATION

## Phase 0 : IMMÉDIAT (J+0) - Sécurité Critique

| Action | Fichier | Effort |
|--------|---------|--------|
| Révoquer token Artifactory | - | 10 min |
| Nettoyer historique Git (BFG) | - | 30 min |
| Ajouter services_*.env au .gitignore | `_gitignore` | 5 min |

## Phase 1 : URGENT (J+1) - Runtime Errors

| Action | Fichier | Effort |
|--------|---------|--------|
| Protéger divisions c_duree_excce_conso | `preprocessing_safir_conso.py` | 30 min |
| Renforcer protection c_duree_excce_soc | `preprocessing_safir_soc.py` | 30 min |
| Valider SQL injection | `retrieve_sql_query_transac.py` | 1h |
| Fix app.sh stream.py | `app.sh` | 5 min |
| Ajouter validation NaN avant ML | `calcul_pdo.py` | 1h |

## Phase 2 : COURT TERME (J+7) - Qualité

| Action | Fichier | Effort |
|--------|---------|--------|
| `ruff check --fix .` | Tous | 10 min |
| `black .` | Tous | 5 min |
| Corriger types Mypy | 23 fichiers | 2h |
| Regrouper window functions | `retrieve_sql_query_transac.py` | 1h |

## Phase 3 : MOYEN TERME (J+30) - Maintenabilité

| Action | Fichier | Effort |
|--------|---------|--------|
| Refactorer lazy evaluation | `base_transformation.py` | 3-5j |
| Externaliser codes sectoriels | YAML | 2h |
| Externaliser seuils ML | YAML | 1h |
| Ajouter tests intégration | `tests/intégration/` | 3j |
| Décomposer fonctions >50 lignes | 18 fonctions | 5j |

---

**Signature Tech Lead :** ________________  
**Date :** 27/01/2026  
**Version :** 7.0 - Rapport Complet Fusionné
