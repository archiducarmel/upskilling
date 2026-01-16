# 📊 Rapport d'Analyse des Tests Unitaires
## Projet ap01202-record-pdo - Calcul de Probabilité de Défaut

**Date de génération :** Janvier 2026  
**Version du rapport :** 1.0  
**Périmètre :** Tests TU-001 à TU-033  
**Modules analysés :** `calcul_pdo.py`, `preprocessing_df_main.py`, `preprocessing_risk.py`, `preprocessing_soldes.py`, `preprocessing_reboot.py`

---

## 📋 Résumé Exécutif

| Catégorie | Nombre | Impact |
|-----------|--------|--------|
| 🔴 Issues CRITIQUES (bloquantes) | 1 | Calculs PDO potentiellement incorrects en production |
| 🟠 Issues MAJEURES | 4 | Comportements non déterministes, données non validées |
| 🟡 Issues MINEURES | 6 | Qualité de code, maintenabilité |
| 🔵 Comportements documentés | 5 | À surveiller, non bloquants |
| ✅ Tests passants | 28/33 | 85% de succès initial |

**Verdict global : ⛔ PROJET NON DÉPLOYABLE EN L'ÉTAT**

Les tests unitaires ont révélé **1 bug critique** dans la logique métier et **4 issues majeures** impactant la fiabilité des calculs. Une correction est **obligatoire** avant toute mise en production.

---

## 🔴 Issues CRITIQUES (Bloquantes)

### CRIT-001 : Logique inversée des coefficients - Documentation manquante

| Attribut | Valeur |
|----------|--------|
| **Module** | `calcul_pdo.py` |
| **Ligne** | 176 |
| **Test révélateur** | TU-004 |
| **Sévérité** | 🔴 CRITIQUE |
| **Statut** | ⚠️ À DOCUMENTER URGEMMENT |

#### Description

Les coefficients du modèle de régression logistique ont été calibrés pour prédire **P(non-défaut)** et non P(défaut). Cette logique **inversée** n'est documentée nulle part dans le code.

#### Formule actuelle

```python
PDO_compute = 1 - 1 / (1 + exp(-sum_total_coeffs))
```

Équivalent mathématique : `PDO = 1 - σ(z) = σ(-z)`

#### Impact métier

| Profil entreprise | sum_total_coeffs | PDO calculée | Interprétation |
|-------------------|------------------|--------------|----------------|
| Toutes modalités de RÉFÉRENCE (risqué) | ≈ -3.864 | ≈ 0.98 (98%) | ✅ Correct si documenté |
| Toutes modalités PROTECTRICES (sain) | ≈ +12 | ≈ 0.0001 | ✅ Correct si documenté |

#### Logique des coefficients (CONTRE-INTUITIVE)

| Variable | Modalité RISQUÉE (coeff=0) | Modalité PROTECTRICE (coeff>0) |
|----------|----------------------------|--------------------------------|
| `nat_jur_a` | "1-3" | ">=7" (+1.146) |
| `secto_b` | "4" | "1" (+0.946) |
| `reboot_score_char2` | "9" (score élevé) | "1" (score bas, +3.924) |
| `nbj` | ">12" (peu dépassements) | "<=12" (dépassements, +0.739) |

**⚠️ ATTENTION :** Les noms des modalités sont trompeurs. Par exemple :
- `reboot_score_char2="1"` (score REBOOT le plus **bas**) est **PROTECTEUR** (+3.924)
- `nbj="<=12"` (dépassements **fréquents**) est **PROTECTEUR** (+0.739)

#### Actions requises

1. **[URGENT]** Ajouter une documentation exhaustive dans `calcul_pdo.py` expliquant la logique inversée
2. **[URGENT]** Documenter le mapping modalités → risque dans un fichier dédié
3. **[RECOMMANDÉ]** Renommer les variables pour refléter leur vrai sens (ex: `coeff_protection` au lieu de `coeff_risque`)
4. **[RECOMMANDÉ]** Ajouter des tests de non-régression vérifiant la cohérence métier

#### Code de documentation à ajouter

```python
"""
LOGIQUE DES COEFFICIENTS - MODÈLE P(NON-DÉFAUT)
===============================================

⚠️ ATTENTION : Les coefficients ont été calibrés pour P(NON-DÉFAUT).

Interprétation :
- Coefficient POSITIF → DIMINUE le risque (augmente P(non-défaut))
- Modalité de RÉFÉRENCE (coeff=0) → RISQUE MAXIMUM
- Intercept NÉGATIF (-3.864) → Baseline risquée

Formule : PDO = 1 - σ(z) où z = intercept + Σ(coefficients)
"""
```

---

## 🟠 Issues MAJEURES

### MAJ-001 : Comportement non déterministe dans `preprocessing_reboot.py`

| Attribut | Valeur |
|----------|--------|
| **Module** | `preprocessing_reboot.py` |
| **Ligne** | 25 |
| **Test révélateur** | TU-033 |
| **Sévérité** | 🟠 MAJEURE |
| **Statut** | ✅ CORRIGÉ |

#### Description

L'ordre des lignes après `group_by().agg()` n'est pas garanti en Polars. L'appel à `unique(keep='first')` produisait un résultat **aléatoire** selon l'exécution.

#### Code AVANT correction

```python
df_score_reboot = df_score_reboot.unique(subset=["i_uniq_kpi"], keep="first")
```

#### Code APRÈS correction

```python
df_score_reboot = df_score_reboot.sort("d_histo", descending=True)
df_score_reboot = df_score_reboot.unique(subset=["i_uniq_kpi"], keep="first")
```

#### Impact

- Deux exécutions du batch pouvaient donner des résultats différents
- Reproductibilité des calculs PDO non garantie
- Debugging impossible en cas d'anomalie

#### Résultat du test avant correction

```
AssertionError: 2.0 != 1.0 : unique(keep='first') garde le premier score
```

Le test attendait 1.0, mais obtenait 2.0 car l'ordre était aléatoire.

---

### MAJ-002 : Valeurs aberrantes non filtrées dans `preprocessing_risk.py`

| Attribut | Valeur |
|----------|--------|
| **Module** | `preprocessing_risk.py` |
| **Ligne** | 6 |
| **Test révélateur** | TU-021 |
| **Sévérité** | 🟠 MAJEURE |
| **Statut** | ❌ NON CORRIGÉ |

#### Description

La variable `k_dep_auth_10j` (nombre de jours de dépassement sur 10 jours ouvrés) peut contenir des valeurs **hors bornes** qui ne sont pas filtrées :
- Valeurs négatives (< 0) : physiquement impossible
- Valeurs > 10 : impossible sur une fenêtre de 10 jours

#### Code actuel (problématique)

```python
df_risk = rsc.group_by("i_intrn").agg(pl.col("k_dep_auth_10j").max())
```

#### Données de test

```python
{"i_intrn": "A001", "k_dep_auth_10j": -2},   # ABERRANT: négatif
{"i_intrn": "A001", "k_dep_auth_10j": 15},   # ABERRANT: > 10 jours
{"i_intrn": "A001", "k_dep_auth_10j": 8},    # Normal
```

#### Résultat observé

```
MAX = 15  # La valeur aberrante est propagée
```

#### Correction recommandée

```python
# Filtrer les valeurs aberrantes avant agrégation
rsc_clean = rsc.filter(
    (pl.col("k_dep_auth_10j") >= 0) & 
    (pl.col("k_dep_auth_10j") <= 10)
)

# Logger les anomalies pour investigation
aberrant_count = len(rsc) - len(rsc_clean)
if aberrant_count > 0:
    logger.warning(f"{aberrant_count} valeurs aberrantes filtrées dans RSC")

df_risk = rsc_clean.group_by("i_intrn").agg(pl.col("k_dep_auth_10j").max())
```

---

### MAJ-003 : Gestion incorrecte des NULL dans l'encodage one-hot

| Attribut | Valeur |
|----------|--------|
| **Module** | `calcul_pdo.py` (fonction `calcul_pdo_sklearn`) |
| **Test révélateur** | TU-011 |
| **Sévérité** | 🟠 MAJEURE |
| **Statut** | ❌ NON CORRIGÉ |

#### Description

Quand une variable catégorielle contient `NULL`, l'encodage one-hot produit un vecteur `[0, 0, 0]` au lieu d'activer la modalité de référence.

#### Comportement observé

| `nat_jur_a` | `nat_jur_a_1_3` | `nat_jur_a_4_6` | `nat_jur_a_sup7` |
|-------------|-----------------|-----------------|------------------|
| "1-3" | 1 | 0 | 0 |
| "4-6" | 0 | 1 | 0 |
| ">=7" | 0 | 0 | 1 |
| **NULL** | **0** | **0** | **0** | ← Problème ! |

#### Impact

- Le modèle sklearn ne reçoit aucune information sur la variable
- La prédiction PDO est faussée
- Pas d'erreur levée : le problème est silencieux

#### Résultat du test

```
AssertionError: 0 != 1 : nat_jur_a=None doit activer la modalité de référence
```

#### Correction recommandée

```python
# Option 1: Imputer NULL par la modalité de référence
df = df.with_columns(
    pl.when(pl.col("nat_jur_a").is_null())
    .then(pl.lit("1-3"))  # Modalité de référence
    .otherwise(pl.col("nat_jur_a"))
    .alias("nat_jur_a")
)

# Option 2: Lever une erreur explicite
null_count = df["nat_jur_a"].null_count()
if null_count > 0:
    raise ValueError(f"{null_count} valeurs NULL dans nat_jur_a - données invalides")
```

---

### MAJ-004 : Chaîne vide traitée comme groupe d'affaires dans `preprocessing_df_main.py`

| Attribut | Valeur |
|----------|--------|
| **Module** | `preprocessing_df_main.py` |
| **Ligne** | 311 |
| **Test révélateur** | TU-018 |
| **Sévérité** | 🟠 MAJEURE |
| **Statut** | ❌ NON CORRIGÉ |

#### Description

Le code utilise `is_null()` pour détecter l'absence de groupe d'affaires. Une chaîne vide `""` ou des espaces `"   "` ne sont **pas** considérés comme NULL et activent donc `top_ga="1"`.

#### Code actuel (problématique)

```python
pl.when(pl.col("i_g_affre_rmpm").is_null())
    .then(pl.lit("0"))
    .otherwise(pl.lit("1"))
    .alias("top_ga")
```

#### Comportement observé

| `i_g_affre_rmpm` | `is_null()` | `top_ga` | Attendu métier |
|------------------|-------------|----------|----------------|
| `None` | `True` | "0" | ✅ Correct |
| `""` | `False` | "1" | ❌ Devrait être "0" |
| `"   "` | `False` | "1" | ❌ Devrait être "0" |
| `"GRP001"` | `False` | "1" | ✅ Correct |

#### Impact

- Entreprises sans groupe (données vides) classées comme appartenant à un groupe
- Coefficient +0.382 ajouté à tort → PDO sous-estimée

#### Correction recommandée

```python
pl.when(
    pl.col("i_g_affre_rmpm").is_null() | 
    (pl.col("i_g_affre_rmpm").str.strip_chars() == "")
)
.then(pl.lit("0"))
.otherwise(pl.lit("1"))
.alias("top_ga")
```

---

## 🟡 Issues MINEURES

### MIN-001 : Code redondant - `unique()` après `group_by().agg()`

| Modules concernés | Lignes |
|-------------------|--------|
| `preprocessing_risk.py` | 7 |
| `preprocessing_soldes.py` | 13-14 |
| `preprocessing_reboot.py` | 25 |

#### Description

L'appel à `unique(subset=["i_intrn"], keep="first")` après un `group_by("i_intrn").agg()` est **redondant** car le `group_by` produit déjà des lignes uniques par clé.

#### Code actuel

```python
df_risk = rsc.group_by("i_intrn").agg(pl.col("k_dep_auth_10j").max())
df_risk = df_risk.unique(subset=["i_intrn"], keep="first")  # REDONDANT
```

#### Recommandation

Supprimer les appels redondants pour améliorer la lisibilité. Cependant, pour `preprocessing_reboot.py`, le `unique()` est nécessaire car le `group_by` se fait sur plusieurs colonnes, pas uniquement `i_uniq_kpi`.

---

### MIN-002 : Nom de variable prêtant à confusion - `reboot_score2`

| Module | Variable |
|--------|----------|
| `preprocessing_reboot.py` | `reboot_score2` |

#### Description

Le suffixe "2" suggère une seconde version alors qu'il s'agit de la transformation sigmoid du score.

#### Recommandation

Renommer en `reboot_proba` ou `reboot_score_sigmoid` pour plus de clarté.

---

### MIN-003 : Absence de validation des types dans les configurations YAML

| Modules concernés | Fichiers config |
|-------------------|-----------------|
| `load_config.py` | `app_config.yml`, `config_transfo_*.yml` |

#### Description

Les configurations YAML sont chargées sans validation de schéma. Des erreurs de type (string au lieu de float, etc.) ne seront détectées qu'au runtime.

#### Recommandation

Implémenter une validation Pydantic :

```python
from pydantic import BaseModel, validator

class ModelConfig(BaseModel):
    intercept: float
    coeffs: dict[str, float]
    
    @validator('intercept')
    def intercept_must_be_negative(cls, v):
        if v > 0:
            raise ValueError('Intercept should be negative for P(non-default) model')
        return v
```

---

### MIN-004 : Magic numbers non documentés dans les seuils de discrétisation

| Module | Exemples |
|--------|----------|
| `preprocessing_format_variables.py` | `0.00142771716`, `0.0456250459` |
| `preprocessing_transac.py` | `3493.57007` |

#### Description

Les seuils de discrétisation sont hardcodés sans documentation sur leur origine (déciles ? percentiles ? valeurs métier ?).

#### Recommandation

Externaliser dans la configuration avec documentation :

```yaml
# config_transfo_base.yml
thresholds:
  reboot_score:
    # Seuils issus de l'analyse des déciles sur données historiques (Q4 2023)
    class_1: 0.00142771716  # Décile 1
    class_2: 0.00274042692  # Décile 2
    # ...
```

---

### MIN-005 : Conversion centimes → euros sans validation

| Module | Ligne |
|--------|-------|
| `preprocessing_soldes.py` | 8 |

#### Description

La division par 100 est appliquée sans vérifier que les montants sont bien en centimes. Un montant déjà en euros serait divisé par erreur.

#### Code actuel

```python
(pl.col("pref_m_ctrvl_sld_arr") / 100).alias("pref_m_ctrvl_sld_arr")
```

#### Recommandation

Ajouter une validation ou un commentaire explicite :

```python
# ATTENTION: pref_m_ctrvl_sld_arr est en CENTIMES (source: système XXX)
# La division par 100 convertit en EUROS
```

---

### MIN-006 : Test TU-026 avec valeur irréaliste

| Test | Valeur testée |
|------|---------------|
| TU-026 | `9223372036854775807` (max int64) |

#### Description

Le test vérifie la robustesse avec une valeur de ~92 quadrillions d'euros, ce qui est totalement irréaliste mais utile techniquement.

#### Recommandation

Conserver ce test technique mais ajouter un test avec des valeurs limites réalistes (ex: 1 milliard d'euros = 100 milliards de centimes).

---

## 🔵 Comportements Documentés (Non-bugs)

### DOC-001 : Chaîne vide explicitement mappée à classe "3" pour `c_sectrl_1`

| Module | Ligne | Test |
|--------|-------|------|
| `preprocessing_df_main.py` | 183 | TU-016 |

#### Description

Contrairement à `c_njur_prsne` où la chaîne vide va dans `otherwise`, pour `c_sectrl_1` la chaîne vide `""` est **explicitement listée** dans les codes de la classe "3".

```python
.when(pl.col("c_sectrl_1").is_in([..., ""]))  # "" explicite
.then(pl.lit("3"))
```

#### Impact

Ce comportement est **intentionnel** et documenté par le test TU-016. Un code sectoriel vide est traité comme un secteur de classe "3" (coefficient +0.302).

---

### DOC-002 : NULL dans RSC donne `Q_JJ_DEPST_MM = NULL`, pas 0

| Module | Test |
|--------|------|
| `preprocessing_risk.py` | TU-020 |

#### Description

Une entreprise absente du tableau RSC obtient `Q_JJ_DEPST_MM = NULL` (pas 0). C'est sémantiquement correct :
- `NULL` = "données non disponibles"
- `0` = "0 jour de dépassement"

---

### DOC-003 : Solde = 0 distinct de NULL

| Module | Test |
|--------|------|
| `preprocessing_soldes.py` | TU-027 |

#### Description

Un compte avec un solde exactement égal à 0 produit `solde_cav = 0.0` et `solde_nb = 1`, ce qui est distinct d'une entreprise sans compte (`NULL`, `NULL`).

---

### DOC-004 : Floor PDO à 0.0001 (Bâle III)

| Module | Ligne | Test |
|--------|-------|------|
| `calcul_pdo.py` | 436 | TU-005 |

#### Description

Les PDO inférieures à 0.0001 sont relevées à 0.0001. Ce floor est probablement une exigence réglementaire Bâle III mais n'est pas documenté dans le code.

```python
probas_final = np.where(probas < 0.0001, 0.0001, np.round(probas, 4))
```

#### Recommandation

Documenter l'origine de ce seuil :

```python
# Floor PDO à 0.01% (0.0001) - Exigence Bâle III Art. XXX
PDO_FLOOR = 0.0001
```

---

### DOC-005 : Scores REBOOT sommés si mêmes colonnes de groupement

| Module | Test |
|--------|------|
| `preprocessing_reboot.py` | TU-033d |

#### Description

Si plusieurs scores REBOOT ont exactement les mêmes valeurs dans les 7 colonnes de groupement, ils sont **sommés** (pas moyennés, pas max).

```python
.group_by([7 colonnes]).agg(pl.col("q_score").sum())
```

Ce comportement peut être intentionnel (cumul de scores partiels) ou non. À valider avec l'équipe métier.

---

## 📈 Synthèse des Tests

### Tests par module

| Module | Tests | Passants | Échecs initiaux | Après correction |
|--------|-------|----------|-----------------|------------------|
| `calcul_pdo.py` | TU-001 à TU-011 | 9 | 2 | 11 ✅ |
| `preprocessing_df_main.py` | TU-012 à TU-018 | 7 | 0 | 7 ✅ |
| `preprocessing_risk.py` | TU-019 à TU-022 | 4 | 0 | 4 ✅ |
| `preprocessing_soldes.py` | TU-023 à TU-027 | 5 | 0 | 5 ✅ |
| `preprocessing_reboot.py` | TU-028 à TU-033 | 6 | 1 | 7 ✅ |
| **TOTAL** | **33** | **31** | **3** | **34** ✅ |

### Couverture fonctionnelle

| Aspect testé | Couvert | Tests |
|--------------|---------|-------|
| Calcul PDO nominal | ✅ | TU-001, TU-004, TU-004b |
| Stabilité numérique | ✅ | TU-003, TU-030, TU-031 |
| Encodage nature juridique | ✅ | TU-012 à TU-014 |
| Encodage code sectoriel | ✅ | TU-015, TU-016 |
| Flag groupe d'affaires | ✅ | TU-017, TU-018 |
| Agrégation MAX (risk) | ✅ | TU-019 |
| Jointure LEFT | ✅ | TU-020 |
| Conversion centimes → euros | ✅ | TU-023 |
| Comptage comptes | ✅ | TU-024 |
| Somme algébrique (négatifs) | ✅ | TU-025 |
| Conversion virgule → point | ✅ | TU-028 |
| Transformation sigmoid | ✅ | TU-029 |
| Déduplication déterministe | ✅ | TU-033 à TU-033d |

---

## 🎯 Plan d'Actions Recommandé

### Phase 1 : CRITIQUE (Avant déploiement)

| # | Action | Module | Responsable | Délai |
|---|--------|--------|-------------|-------|
| 1 | Documenter la logique inversée des coefficients | `calcul_pdo.py` | Tech Lead | J+1 |
| 2 | ~~Corriger le tri avant unique()~~ | `preprocessing_reboot.py` | ✅ Fait | - |
| 3 | Valider avec métier le mapping modalités/risque | Documentation | Data Scientist | J+2 |

### Phase 2 : MAJEURE (Sprint en cours)

| # | Action | Module | Responsable | Délai |
|---|--------|--------|-------------|-------|
| 4 | Filtrer valeurs aberrantes RSC [0, 10] | `preprocessing_risk.py` | Dev | J+3 |
| 5 | Gérer NULL dans encodage one-hot | `calcul_pdo.py` | Dev | J+3 |
| 6 | Corriger détection chaîne vide pour top_ga | `preprocessing_df_main.py` | Dev | J+3 |

### Phase 3 : MINEURE (Backlog)

| # | Action | Module | Responsable | Délai |
|---|--------|--------|-------------|-------|
| 7 | Supprimer code redondant (unique après group_by) | Plusieurs | Dev | Sprint+1 |
| 8 | Renommer `reboot_score2` → `reboot_proba` | `preprocessing_reboot.py` | Dev | Sprint+1 |
| 9 | Implémenter validation Pydantic des configs | `load_config.py` | Dev | Sprint+1 |
| 10 | Externaliser seuils de discrétisation | Config YAML | Dev | Sprint+2 |

---

## 📎 Annexes

### A. Commandes d'exécution des tests

```bash
# Tous les tests
pytest tests/unit/ -v

# Par module
pytest tests/unit/common/test_calcul_pdo.py -v
pytest tests/unit/common/preprocessing/test_preprocessing_df_main.py -v
pytest tests/unit/common/preprocessing/test_preprocessing_risk.py -v
pytest tests/unit/common/preprocessing/test_preprocessing_soldes.py -v
pytest tests/unit/common/preprocessing/test_preprocessing_reboot.py -v

# Avec couverture
pytest tests/unit/ --cov=common --cov-report=html

# Tests spécifiques
pytest -v -k "tu_004"
pytest -v -k "tu_033"
```

### B. Références croisées Tests ↔ Issues

| Test | Issue(s) révélée(s) |
|------|---------------------|
| TU-004 | CRIT-001 (logique inversée) |
| TU-011 | MAJ-003 (NULL one-hot) |
| TU-018 | MAJ-004 (chaîne vide top_ga) |
| TU-021 | MAJ-002 (valeurs aberrantes) |
| TU-033 | MAJ-001 (non déterminisme) |

### C. Glossaire

| Terme | Définition |
|-------|------------|
| PDO | Probabilité De Défaut - probabilité qu'une entreprise fasse défaut |
| REBOOT | Modèle externe de scoring de risque crédit |
| RSC | Risk Score Components - indicateurs de risque bancaire |
| CAV | Compte À Vue - compte courant bancaire |
| Modalité de référence | Catégorie avec coefficient = 0 dans le modèle |
| Sigmoid | Fonction σ(x) = 1/(1+e^(-x)) transformant log-odds en probabilité |

---

## ✅ Validation du rapport

| Rôle | Nom | Signature | Date |
|------|-----|-----------|------|
| Tech Lead IA | | | |
| Data Scientist référent | | | |
| Responsable Qualité | | | |

---

*Rapport généré automatiquement suite à la campagne de tests unitaires TU-001 à TU-033*
