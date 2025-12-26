# 🔍 RAPPORT D'ANALYSE DES LOGIQUES MÉTIER
## Projet PDO - Éléments à Valider / Challenger

---

# 📖 Introduction

Ce rapport identifie toutes les **logiques métier** implémentées dans le code SQL et Python du projet PDO. Ces règles doivent être **validées par les experts métier** (Risk Management, Data Scientists, Analystes Crédit) car elles impactent directement le calcul de la Probabilité de Défaut.

## Classification des logiques métier

| Type | Description | Qui doit valider ? |
|------|-------------|-------------------|
| 🎯 **Critères d'éligibilité** | Qui entre dans le périmètre PDO | Risk Management |
| 📊 **Seuils de discrétisation** | Découpage des variables continues | Data Science |
| ⚖️ **Coefficients du modèle** | Poids de chaque variable | Data Science + Model Validation |
| 🧮 **Formules comptables** | Calcul des ratios financiers | Analystes Financiers |
| 🏷️ **Catégorisation** | Regroupement de codes | Métier + IT |

---

# 🎯 CRITÈRES D'ÉLIGIBILITÉ (preprocessing_filters.py)

Ces règles définissent **quelles entreprises** sont éligibles au calcul PDO.

## 1. Exclusion par Nature Juridique

### 📍 Localisation
- **Fichier** : `preprocessing_filters.py`, ligne 8

### 📝 Code
```python
df_main = df_main.filter(~pl.col("c_njur_prsne").is_in(["31", "32", "34", "35", "93", "95", "99"]))
```

### 📋 Règle métier
| Code | Nature Juridique | Exclu ? |
|------|-----------------|---------|
| 31 | GIE (Groupement d'Intérêt Économique) | ✅ Oui |
| 32 | Société Civile Immobilière | ✅ Oui |
| 34 | Foncière | ✅ Oui |
| 35 | Promotion Immobilière | ✅ Oui |
| 93 | Indivision (autre qu'entre époux) | ✅ Oui |
| 95 | Société de Fait | ✅ Oui |
| 99 | Autres clients collectifs | ✅ Oui |

### ❓ Questions à valider
1. **Pourquoi exclure les SCI ?** → Risque spécifique immobilier ?
2. **Les GIE sont-ils toujours exclus ?** → Quelle est la volumétrie ?
3. **Le code 99 "Autres" est-il bien défini ?** → Liste exhaustive ?

---

## 2. Exclusion par Code NAF

### 📍 Localisation
- **Fichier** : `preprocessing_filters.py`, lignes 10-11

### 📝 Code
```python
df_main = df_main.filter(~pl.col("c_naf").is_in(["6419Z"]))
df_main = df_main.filter(~(pl.col("c_sgmttn_nae").is_in(["AP"]) & (pl.col("c_naf").is_in(["8411Z"]))))
```

### 📋 Règle métier
| Code NAF | Activité | Condition | Exclu ? |
|----------|----------|-----------|---------|
| 6419Z | Autres intermédiations monétaires | Toujours | ✅ Oui |
| 8411Z | Administration publique générale | Si segment AP | ✅ Oui |

### ❓ Questions à valider
1. **6419Z = Banques concurrentes ?** → Pourquoi les exclure ?
2. **Segment AP = Administrations Publiques ?** → Logique de les exclure car pas de défaut ?
3. **Y a-t-il d'autres codes NAF à exclure ?** → Secteurs régulés ?

---

## 3. Sélection par Segmentation NAE

### 📍 Localisation
- **Fichier** : `preprocessing_filters.py`, ligne 13

### 📝 Code
```python
df_main = df_main.filter(pl.col("c_sgmttn_nae").is_in(["ME", "GR", "A3"]))
```

### 📋 Règle métier
| Segment | Description | Inclus ? |
|---------|-------------|----------|
| ME | Moyennes Entreprises | ✅ Oui |
| GR | Grandes Entreprises | ✅ Oui |
| A3 | ? (non documenté) | ✅ Oui |
| AP | Administrations Publiques | ❌ Non |
| Autres | Petites entreprises, TPE... | ❌ Non |

### ❓ Questions à valider
1. **Que signifie A3 ?** → Documentation manquante
2. **Pourquoi exclure les petites entreprises ?** → Modèle différent ?
3. **Les AP sont-elles exclues car risque nul ?**

---

## 4. Exclusion des Professionnels de l'Immobilier

### 📍 Localisation
- **Fichier** : `preprocessing_filters.py`, ligne 15

### 📝 Code
```python
df_main = df_main.filter(~pl.col("c_profl_immbr").is_not_null())
```

### ⚠️ ALERTE : Bug potentiel !

```python
# Ce code exclut les entreprises où c_profl_immbr N'EST PAS NULL
# C'est-à-dire : garde uniquement celles où c_profl_immbr EST NULL

# Logique actuelle (probablement incorrecte) :
~pl.col("c_profl_immbr").is_not_null()  # équivalent à is_null()

# Logique probablement voulue :
~pl.col("c_profl_immbr").is_in(["valeurs_à_exclure"])
```

### ❓ Questions à valider
1. **Quelles valeurs de `c_profl_immbr` doivent être exclues ?**
2. **Le code actuel est-il correct ou est-ce un bug ?**

---

## 5. Présence de Comptes

### 📍 Localisation
- **Fichier** : `preprocessing_filters.py`, ligne 17

### 📝 Code
```python
df_main = df_main.filter(pl.col("c_pres_cpt") == "1")
```

### 📋 Règle métier
Seules les entreprises ayant au moins un compte sont incluses.

### ❓ Questions à valider
1. **Est-ce un compte courant ou tout type de compte ?**
2. **Une entreprise avec seulement un crédit (pas de compte) est-elle exclue ?**

---

## 6. Exclusion des Créances Risquées

### 📍 Localisation
- **Fichier** : `preprocessing_filters.py`, lignes 18-19

### 📝 Code
```python
df_main = df_main.filter(~pl.col("c_crisq").is_in(["1", "2"]))
```

### 📋 Règle métier
| Code c_crisq | Signification | Exclu ? |
|--------------|---------------|---------|
| 1 | ? | ✅ Oui |
| 2 | ? | ✅ Oui |
| Autres | ? | ❌ Non |

### ❓ Questions à valider
1. **Que signifient les codes 1 et 2 ?** → Documentation manquante
2. **Pourquoi exclure ces créances ?** → Déjà en défaut ?
3. **Le PDO ne doit-il pas justement évaluer ces cas ?**

---

## 7. Exclusion par Code Économique (85 codes)

### 📍 Localisation
- **Fichier** : `preprocessing_filters.py`, lignes 21-87

### 📝 Code
```python
liste_code_eco = [
    "011", "012", "021", "031", "039", "111", "112", "121", 
    "131", "132", "133", "134", "135", "136", "137", "141", 
    "142", "161", "162", "163", "164", "165", "166", "167", 
    "168", "169", "171", "172", "181", "182", "183", "184", 
    "189", "231", "232", "233", "234", "235", "236", "237", 
    "238", "239", "251", "252", "253", "254", "261", "262", 
    "263", "264", "265", "266", "267", "268", "269", "270", 
    "271", "281", "291", "292", "293", "431", "432", "433"
]
df_main = df_main.filter(~pl.col("c_eco").is_in(liste_code_eco))
```

### ❓ Questions à valider
1. **Quelle est la signification de ces 85 codes ?** → Pas de documentation
2. **D'où vient cette liste ?** → Règle réglementaire ? Décision métier ?
3. **Cette liste est-elle à jour ?** → Dernière revue ?
4. **Pourquoi ces codes sont-ils hardcodés dans le code ?** → Devrait être externalisé

### ⚠️ Recommandation
Créer un fichier de référence `codes_eco_exclus.yml` avec la documentation de chaque code.

---

## 8. Nature de la Relation Client

### 📍 Localisation
- **Fichier** : `preprocessing_filters.py`, ligne 89

### 📝 Code
```python
df_main = df_main.filter(pl.col("c_nture_clt_entrp") != "00003")
```

### 📋 Règle métier
Exclut les entreprises avec `c_nture_clt_entrp = "00003"` (sans suivi commercial).

### ❓ Questions à valider
1. **Que signifie exactement "00003" ?** → Documentation ?
2. **Une entreprise sans suivi commercial peut-elle faire défaut ?**

---

# 📊 SEUILS DE DISCRÉTISATION (preprocessing_format_variables.py)

Ces seuils transforment des variables **continues** en variables **catégorielles** pour le modèle.

## 9. Discrétisation du Score REBOOT

### 📍 Localisation
- **Fichier** : `preprocessing_format_variables.py`, lignes 43-62

### 📝 Code
```python
df_main = df_main.with_columns(
    pl.when(pl.col("reboot_score2") < 0.00142771716).then(pl.lit("1"))
    .when((pl.col("reboot_score2") >= 0.00142771716) & (pl.col("reboot_score2") < 0.00274042692)).then(pl.lit("2"))
    .when((pl.col("reboot_score2") >= 0.00274042692) & (pl.col("reboot_score2") < 0.00563700218)).then(pl.lit("3"))
    .when((pl.col("reboot_score2") >= 0.00563700218) & (pl.col("reboot_score2") < 0.0102700535)).then(pl.lit("4"))
    .when((pl.col("reboot_score2") >= 0.0102700535) & (pl.col("reboot_score2") < 0.0129012)).then(pl.lit("5"))
    .when((pl.col("reboot_score2") >= 0.0129012) & (pl.col("reboot_score2") < 0.0147122974)).then(pl.lit("6"))
    .when((pl.col("reboot_score2") >= 0.0147122974) & (pl.col("reboot_score2") < 0.0159990136)).then(pl.lit("7"))
    .when((pl.col("reboot_score2") >= 0.0159990136) & (pl.col("reboot_score2") < 0.0456250459)).then(pl.lit("8"))
    .when(pl.col("reboot_score2") > 0.0456250459).then(pl.lit("9"))
    .alias("reboot_score_char2")
)
```

### 📋 Seuils de discrétisation

| Classe | Borne inférieure | Borne supérieure | Interprétation |
|--------|------------------|------------------|----------------|
| 1 | - | 0.00143 | Risque très élevé |
| 2 | 0.00143 | 0.00274 | Risque élevé |
| 3 | 0.00274 | 0.00564 | Risque significatif |
| 4 | 0.00564 | 0.01027 | Risque modéré-haut |
| 5 | 0.01027 | 0.01290 | Risque modéré |
| 6 | 0.01290 | 0.01471 | Risque modéré-bas |
| 7 | 0.01471 | 0.01600 | Risque faible |
| 8 | 0.01600 | 0.04563 | Risque très faible |
| 9 | 0.04563 | + | Risque minimal |

### ❓ Questions à valider
1. **Comment ces seuils ont-ils été déterminés ?** → Quantiles ? Expert ? Optimisation ?
2. **La précision à 11 décimales est-elle justifiée ?** → `0.00142771716`
3. **Ces seuils sont-ils stables dans le temps ?** → Recalibrage nécessaire ?
4. **Pourquoi 9 classes ?** → Impact sur le pouvoir discriminant ?

---

## 10. Discrétisation du Solde CAV

### 📍 Localisation
- **Fichier** : `preprocessing_format_variables.py`, lignes 31-39

### 📝 Code
```python
pl.when(pl.col("solde_cav") < -9.10499954).then(pl.lit("1"))
.when((pl.col("solde_cav") >= -9.10499954) & (pl.col("solde_cav") < 15235.6445)).then(pl.lit("2"))
.when((pl.col("solde_cav") >= 15235.6445) & (pl.col("solde_cav") < 76378.7031)).then(pl.lit("3"))
.otherwise(pl.lit("4"))
```

### 📋 Seuils de discrétisation

| Classe | Solde (€) | Coefficient PDO | Interprétation |
|--------|-----------|-----------------|----------------|
| 1 | < -9,10 € | 0 (référence) | Solde très négatif |
| 2 | -9,10 € à 15 235 € | +0.138 | Solde faible |
| 3 | 15 235 € à 76 378 € | +0.476 | Solde moyen |
| 4 | > 76 378 € | +0.924 | Solde élevé |

### ⚠️ ALERTE : Logique contre-intuitive !

**Plus le solde est élevé, plus le coefficient PDO est élevé** → Plus le risque est élevé ?

C'est **contre-intuitif** : normalement, un solde bancaire élevé devrait **réduire** le risque de défaut.

### ❓ Questions à valider
1. **Cette logique est-elle correcte ?** → Peut-être une inversion dans l'interprétation
2. **Le coefficient PDO est-il bien un facteur de risque ?**
3. **Le seuil -9,10 € est-il un arrondi ou une valeur calculée ?**

---

## 11. Discrétisation des Jours de Dépassement (nbj)

### 📍 Localisation
- **Fichier** : `preprocessing_format_variables.py`, lignes 21-27

### 📝 Code
```python
pl.when((pl.col("Q_JJ_DEPST_MM") >= 0) & (pl.col("Q_JJ_DEPST_MM") <= 12)).then(pl.lit("<=12"))
.when(pl.col("Q_JJ_DEPST_MM") > 12).then(pl.lit(">12"))
.otherwise(pl.lit("<=12"))  # ⚠️ Valeur par défaut
```

### ❓ Questions à valider
1. **Pourquoi le seuil est-il à 12 jours ?** → Règle des 10 jours dans RSC ?
2. **Le `.otherwise("<=12")` est-il correct ?** → Les valeurs NULL sont traitées comme ≤12
3. **Les valeurs négatives sont-elles possibles ?**

---

## 12. Discrétisation des Ratios SAFIR

### 📍 Localisation
- **Fichier** : `preprocessing_format_variables.py`, lignes 66-108

### 📋 Seuils pour VB023 (Marge nette consolidée)

```python
pl.when(pl.col("VB023") < 0.430999994).then(pl.lit("1"))
.when((pl.col("VB023") >= 0.430999994) & (pl.col("VB023") < 2.99849987)).then(pl.lit("2"))
.when(pl.col("VB023") >= 2.99849987).then(pl.lit("3"))
.otherwise(pl.lit("2"))  # ⚠️ Valeur par défaut = classe 2
```

| Classe | VB023 (%) | Coefficient | Interprétation |
|--------|-----------|-------------|----------------|
| 1 | < 0.43% | 0 (référence) | Marge faible → Moins de risque ? |
| 2 | 0.43% à 3% | +1.17 | Marge moyenne |
| 3 | > 3% | +1.64 | Marge élevée → Plus de risque ? |

### ⚠️ ALERTE : Logique potentiellement inversée

Une marge nette élevée devrait **réduire** le risque, pas l'augmenter.

### 📋 Seuils pour VB005 (CAF / Service de la dette)

```python
pl.when(pl.col("VB005") < 66.2200012).then(pl.lit("1"))
.when(pl.col("VB005") >= 66.2200012).then(pl.lit("2"))
```

| Classe | VB005 (%) | Coefficient | Interprétation |
|--------|-----------|-------------|----------------|
| 1 | < 66.22% | 0 (référence) | Couverture faible |
| 2 | ≥ 66.22% | +0.55 | Bonne couverture → Plus de risque ? |

### ❓ Questions à valider
1. **Les coefficients sont-ils dans le bon sens ?**
2. **D'où viennent ces seuils précis (66.22%, 0.43%, etc.) ?**
3. **Pourquoi les valeurs par défaut sont-elles en classe 2 ?**

---

## 13. Seuil pour Remboursement SEPA Maximum

### 📍 Localisation
- **Fichier** : `preprocessing_transac.py`, lignes 64-68

### 📝 Code
```python
pl.when(pl.col("rembt_prlv_sepa__max_amount") > 3493.57007)
.then(pl.lit("1"))
.otherwise(pl.lit("2"))
```

### ❓ Questions à valider
1. **D'où vient le seuil 3493,57 € ?** → Calcul statistique ? Règle métier ?
2. **La précision à 5 décimales est-elle justifiée ?**

---

## 14. Seuil pour Ratio Intérêts/Turnover

### 📍 Localisation
- **Fichier** : `preprocessing_transac.py`, lignes 100-108

### 📝 Code
```python
pl.when(
    (pl.col("nops") >= 60)  # ⚠️ Condition sur le nombre d'opérations
    & (pl.col("net_interets_sur_turnover").is_not_null())
    & (pl.col("net_interets_sur_turnover") < -0.00143675995)
)
.then(pl.lit("1"))
.otherwise(pl.lit("2"))
```

### ❓ Questions à valider
1. **Pourquoi le seuil de 60 opérations ?** → Fiabilité statistique ?
2. **D'où vient -0.00143675995 ?** → Presque égal au seuil Reboot ?
3. **Un ratio négatif signifie quoi ?** → Intérêts créditeurs > débiteurs ?

---

# ⚖️ COEFFICIENTS DU MODÈLE (calcul_pdo.py)

Ces coefficients sont le **cœur du modèle de scoring**. Ils doivent être validés par Model Validation.

## 15. Table des Coefficients PDO

### 📍 Localisation
- **Fichier** : `calcul_pdo.py`, lignes 1-168

### 📋 Coefficients complets

| Variable | Modalité | Coefficient | Impact sur PDO |
|----------|----------|-------------|----------------|
| **Intercept** | - | -3.864 | Base |
| **nat_jur_a** | 1-3 | 0 (réf) | - |
| | 4-6 | +0.243 | ↗ Risque |
| | >=7 | +1.146 | ↗↗ Risque |
| **secto_b** | 4 | 0 (réf) | - |
| | 1 | +0.946 | ↗↗ Risque |
| | 2 | +0.946 | ↗↗ Risque |
| | 3 | +0.302 | ↗ Risque |
| **seg_nae** | ME | 0 (réf) | - |
| | autres | +0.699 | ↗ Risque |
| **top_ga** | 0 (pas de groupe) | 0 (réf) | - |
| | 1 (dans un groupe) | +0.382 | ↗ Risque |
| **nbj** | >12 | 0 (réf) | - |
| | <=12 | +0.739 | ↗ Risque |
| **solde_cav_char** | 1 | 0 (réf) | - |
| | 2 | +0.138 | ↗ Risque |
| | 3 | +0.476 | ↗ Risque |
| | 4 | +0.924 | ↗↗ Risque |
| **reboot_score_char2** | 9 | 0 (réf) | - |
| | 1 | +3.924 | ↗↗↗ Risque |
| | 2 | +1.748 | ↗↗ Risque |
| | 3 | +1.343 | ↗↗ Risque |
| | 4 | +1.099 | ↗↗ Risque |
| | 5 | +0.756 | ↗ Risque |
| | 6 | +0.756 | ↗ Risque |
| | 7 | +0.756 | ↗ Risque |
| | 8 | +0.340 | ↗ Risque |
| **remb_sepa_max** | 1 | 0 (réf) | - |
| | 2 | +1.346 | ↗↗ Risque |
| **pres_prlv_retourne** | 1 | 0 (réf) | - |
| | 2 | +0.917 | ↗ Risque |
| **pres_saisie** | 1 | 0 (réf) | - |
| | 2 | +0.805 | ↗ Risque |
| **net_int_turnover** | 1 | 0 (réf) | - |
| | 2 | +0.479 | ↗ Risque |
| **rn_ca_conso_023b** | 1 | 0 (réf) | - |
| | 2 | +1.171 | ↗↗ Risque |
| | 3 | +1.645 | ↗↗ Risque |
| **caf_dmlt_005** | 1 | 0 (réf) | - |
| | 2 | +0.553 | ↗ Risque |
| **res_total_passif_035** | 1 | 0 (réf) | - |
| | 2 | +0.333 | ↗ Risque |
| | 3 | +0.676 | ↗ Risque |
| | 4 | +0.977 | ↗↗ Risque |
| **immob_total_passif_055** | 1 | 0 (réf) | - |
| | 2 | +0.329 | ↗ Risque |
| | 3 | +0.573 | ↗ Risque |

### ❓ Questions à valider

1. **D'où viennent ces coefficients ?** → Régression logistique ? Quelle date d'entraînement ?
2. **La précision à 15 décimales est-elle justifiée ?** → `0.242841372870074`
3. **Les coefficients sont-ils recalibrés régulièrement ?**
4. **Y a-t-il un document de validation du modèle ?**
5. **Les modalités de référence (coeff = 0) sont-elles les bonnes ?**

---

## 16. Formule PDO Finale

### 📍 Localisation
- **Fichier** : `calcul_pdo.py`, lignes 158-165

### 📝 Code
```python
# Somme des coefficients (sans l'intercept !)
df_main_ilc = df_main_ilc.with_columns(
    (
        pl.col("nat_jur_a_coeffs")
        + pl.col("secto_b_coeffs")
        + ... # autres coefficients
    ).alias("sum_total_coeffs")
)

# Transformation logistique
df_main_ilc = df_main_ilc.with_columns(
    (1 - 1 / (1 + ((-1 * pl.col("sum_total_coeffs")).exp()))).alias("PDO_compute")
)

# Plancher à 0.0001
df_main_ilc = df_main_ilc.with_columns(
    pl.when(pl.col("PDO_compute") < 0.0001)
    .then(pl.lit(0.0001))
    .otherwise(pl.col("PDO_compute").round(4))
    .alias("PDO")
)
```

### ⚠️ ALERTE : L'intercept n'est pas utilisé !

```python
# Ligne 136 : L'intercept est défini
df_main_ilc = df_main_ilc.with_columns(pl.lit(-3.86402362750751).alias("intercept"))

# Lignes 139-156 : Mais il n'est PAS inclus dans la somme !
(
    pl.col("nat_jur_a_coeffs")
    + pl.col("secto_b_coeffs")
    + ... 
    # ⚠️ MANQUE : + pl.col("intercept")
).alias("sum_total_coeffs")
```

### ❓ Questions à valider
1. **L'intercept doit-il être inclus ?** → Probablement OUI pour une régression logistique
2. **Le plancher à 0.0001 (0.01%) est-il justifié ?** → Règle prudentielle ?
3. **Pourquoi arrondir à 4 décimales ?**

---

# 🧮 FORMULES COMPTABLES (preprocessing_safir_*.py)

Ces formules calculent les ratios financiers à partir des bilans SAFIR.

## 17. Formule du Résultat Net Consolidé

### 📍 Localisation
- **Fichier** : `preprocessing_safir_conso.py`, lignes 50-94

### 📝 Formule
```
res_net_conso = (mt_310 + mt_26 - mt_27 - mt_28 - mt_29 - mt_30 - mt_31 
                 + mt_32 + mt_33 - mt_34 - mt_35 + mt_36 - mt_37 + mt_38 - mt_39) 
                / duree_exercice * 12
```

### 📋 Décomposition comptable

| Code | Poste comptable | Signe |
|------|-----------------|-------|
| mt_310 | Chiffre d'affaires consolidé | + |
| mt_26 | ? | + |
| mt_27 | ? | - |
| mt_28 | ? | - |
| mt_29 | ? | - |
| mt_30 | ? | - |
| mt_31 | ? | - |
| mt_32 | ? | + |
| mt_33 | ? | + |
| mt_34 | ? | - |
| mt_35 | ? | - |
| mt_36 | ? | + |
| mt_37 | ? | - |
| mt_38 | ? | + |
| mt_39 | ? | - |

### ❓ Questions à valider
1. **Quelle est la signification de chaque code mt_XX ?** → Documentation comptable ?
2. **Cette formule correspond-elle à la définition standard du résultat net ?**
3. **L'annualisation (× 12 / durée) est-elle correcte ?**

---

## 18. Formule de la CAF (Capacité d'Autofinancement)

### 📍 Localisation
- **Fichier** : `preprocessing_safir_soc.py`, lignes 94-114

### 📝 Formule (régime fiscal 1 - réel normal)
```python
CAF = (mt_182 - mt_469 + mt_287 + mt_290 + mt_289 + mt_288 
       - mt_471 + mt_286 - mt_470 + mt_294) / duree * 12
```

### 📝 Formule (régime fiscal 2 - simplifié)
```python
CAF = (mt_182 + mt_285 + mt_295) / duree * 12
```

### ❓ Questions à valider
1. **Les deux formules sont-elles équivalentes ?** → Différences de plan comptable ?
2. **Le mapping mt_XXX → poste SAFIR est-il correct ?**
3. **Pourquoi une formule différente selon le régime fiscal ?**

---

# 🏷️ CATÉGORISATION DE TRANSACTIONS (query_starburst_transac.sql)

## 19. Classification des Opérations Bancaires

### 📍 Localisation
- **Fichier** : `query_starburst_transac.sql`, lignes 3-38

### 📋 Catégories définies

| Catégorie | Codes | Description |
|-----------|-------|-------------|
| agios | 9 (débit) | Frais bancaires |
| amort_pret | 32, 37, 46... (crédit) + libellé | Amortissement de prêt |
| atd_tres_pub | libellé LIKE | Avis à Tiers Détenteur |
| attri_blocage | libellé LIKE | Saisie attribution |
| centr_treso | Multiples codes | Centralisation trésorerie |
| cost | Multiples codes | Charges |
| interets | 29, 54, 70... (débit) | Intérêts débiteurs |
| prlv_sepa_retourne | 856, 859 (crédit) | Prélèvement rejeté |
| tax | Codes + libellé DGFIP | Impôts |
| turnover | Multiples codes (crédit) | Chiffre d'affaires |
| urssaf | Codes + libellé | Cotisations sociales |

### ❓ Questions à valider
1. **La liste des codes est-elle exhaustive et à jour ?**
2. **Les libellés LIKE sont-ils tous les patterns possibles ?**
3. **Certaines transactions peuvent-elles appartenir à plusieurs catégories ?**
4. **Les codes ont-ils changé depuis la création du modèle ?**

---

# 🔗 RÈGLES DE JOINTURE ET DÉDUPLICATION

## 20. Dédoublonnage des Groupes d'Affaires

### 📍 Localisation
- **Fichier** : `query_starburst_unfiltered_df_main.sql`, lignes 128-218

### 📋 Règles de priorité

1. **Règle 1** : Priorité au lien CAPITALISTIQUE (`c_nre_rel_kpi_regrp = 'CAPIT'`)
2. **Règle 2** : En cas d'égalité, prendre la date de début la plus récente (`max(d_deb_rel_kpi_regrp)`)
3. **Règle 3** : En cas d'égalité, prendre la date de MAJ la plus récente (`max(d_maj_nture_rtcht)`)

### ❓ Questions à valider
1. **Pourquoi CAPITALISTIQUE a la priorité ?** → Règle réglementaire ?
2. **Que faire si aucun lien n'est CAPITALISTIQUE ?** → Actuellement exclu ?
3. **Les autres types de liens (filiale, participation) sont-ils ignorés ?**

---

## 21. Sélection du Bilan le Plus Récent

### 📍 Localisation
- **Fichier** : `preprocessing_safir_soc.py`, lignes 49-52

### 📝 Code
```python
df_soc = df_soc.with_columns(
    [pl.col("d_fin_excce_soc").rank(method="ordinal", descending=True).over("i_siren").alias("N_bilan_soc")]
)
df_soc = df_soc.filter(pl.col("N_bilan_soc").is_in([1, 2]))  # Garde les 2 derniers bilans
```

### ❓ Questions à valider
1. **Pourquoi garder les 2 derniers bilans ?** → Calcul d'évolution ?
2. **Seul le bilan 1 (le plus récent) est finalement utilisé ?**
3. **Que faire si un bilan est incomplet ?**

---

# 📊 SYNTHÈSE DES POINTS À VALIDER

## Par niveau de criticité

### 🔴 Critique (Impact direct sur le PDO)

| # | Point | Fichier | Qui doit valider |
|---|-------|---------|------------------|
| 16 | **Intercept non inclus dans la formule** | calcul_pdo.py | Data Science |
| 10 | Sens des coefficients solde_cav (contre-intuitif) | calcul_pdo.py | Data Science |
| 12 | Sens des coefficients SAFIR (contre-intuitif) | calcul_pdo.py | Data Science |
| 4 | Bug potentiel filtre c_profl_immbr | preprocessing_filters.py | IT + Métier |

### 🟠 Important (Impact sur le périmètre ou les variables)

| # | Point | Fichier | Qui doit valider |
|---|-------|---------|------------------|
| 7 | 85 codes économiques non documentés | preprocessing_filters.py | Métier |
| 9 | Seuils de discrétisation REBOOT | preprocessing_format_variables.py | Data Science |
| 17-18 | Formules comptables SAFIR | preprocessing_safir_*.py | Analystes Financiers |
| 19 | Classification des opérations | query_starburst_transac.sql | Métier bancaire |

### 🟡 Moyen (Documentation et traçabilité)

| # | Point | Fichier | Qui doit valider |
|---|-------|---------|------------------|
| 1-6, 8 | Critères d'éligibilité non documentés | preprocessing_filters.py | Risk Management |
| 15 | Origine et date des coefficients | calcul_pdo.py | Model Validation |
| 20 | Règles de dédoublonnage GA | query_starburst_unfiltered_df_main.sql | Métier |

---

## Actions recommandées

1. **Organiser une revue avec Data Science** pour valider :
   - Le sens des coefficients (solde, SAFIR)
   - L'inclusion de l'intercept
   - Les seuils de discrétisation

2. **Organiser une revue avec le Métier** pour valider :
   - Les critères d'éligibilité
   - Les codes économiques exclus
   - La classification des transactions

3. **Documenter** :
   - Créer un dictionnaire de données
   - Créer un fichier de configuration externalisé pour les codes et seuils
   - Documenter les formules comptables avec les références SAFIR

4. **Corriger les bugs potentiels** :
   - Vérifier le filtre `c_profl_immbr`
   - Vérifier l'inclusion de l'intercept
