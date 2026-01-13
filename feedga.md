Excellente initiative de me montrer les specs originales. Cela permet une analyse comparative précise.

---

## Comparaison Specs vs Tests Implémentés

### **Test 1 : `test_saisie_category_merge`**

| Spec | Test Implémenté |
|------|-----------------|
| `i_uniq_kpi='E001'` (1 entreprise, 4 lignes) | `i_uniq_kpi=[1000004151300000, 3920010525200000]` (2 entreprises, 2 lignes) |
| `category=['attri_blocage', 'atd_tres_pub', 'interets', 'turnover']` | `category=['attri_blocage', 'atd_tres_pub']` |
| `nops_category=[1,2,1,1]` | `nops_category=[1, 2]` |

**Verdict : ❌ NON CONFORME**

Le test utilise **2 entreprises différentes** au lieu d'une seule. La somme `saisie__nops=3` est impossible car le `group_by("i_uniq_kpi")` sépare les données.

---

### **Test 2 : `test_remb_sepa_max_threshold`**

| Spec | Test Implémenté |
|------|-----------------|
| `i_uniq_kpi='E001','E002'` | `i_uniq_kpi=[1000004151300000, 3920010525200000]` |
| `category='rembt_prlv_sepa'` pour les 2 | ✅ Correct |
| `max_amount=[5000.0, 3000.0]` | ✅ Correct |

**Verdict : ✅ CONFORME**

---

### **Test 3 : `test_remb_sepa_max_exact_threshold`**

| Spec | Test Implémenté |
|------|-----------------|
| `max_amount=3493.57007` | ✅ Correct |
| Attendu : `remb_sepa_max='2'` | ✅ Correct |

**Verdict : ✅ CONFORME**

---

### **Test 4 : `test_net_int_turnover_double_condition`**

| Spec | Test Implémenté |
|------|-----------------|
| E001: `interets=-100, turnover=50000, nops=70` | `interets=-200, turnover=100000, nops_total=70` sur 2 lignes |
| E002: `interets=-100, turnover=50000, nops=50` | `interets=-100, turnover=50000, nops_total=50` sur 2 lignes |
| E003: `interets=-10, turnover=50000, nops=70` | `interets=-10, turnover=50000, nops_total=70` sur 2 lignes |

**Problème** : Le code calcule `nops = SUM(nops_total)` par entreprise. Avec 2 lignes par entreprise ayant `nops_total=70`, on obtient `nops=140`, pas `70`.

**Verdict : ⚠️ PARTIELLEMENT CONFORME** - Le test passe mais pour les mauvaises raisons.

---

### **Test 5 : `test_division_by_zero_turnover`**

| Spec | Test Implémenté |
|------|-----------------|
| `1 entreprise E001` avec 2 transactions | `2 entreprises différentes` avec 1 transaction chacune |
| `category='turnover' netamount=0` ET `category='interets' netamount=-100` | `interets` pour E1, `turnover` pour E2 |

**Verdict : ❌ NON CONFORME - GRAVE**

Le test **ne teste pas** la division par zéro. E001 a `interets` mais pas `turnover` (→ NULL). E002 a `turnover=0` mais pas `interets` (→ NULL). Aucune entreprise n'a les deux.

---

### **Test 6 : `test_null_interets_and_turnover`**

| Spec | Test Implémenté |
|------|-----------------|
| `1 ligne i_uniq_kpi='E001' category='prlv_sepa_retourne'` | ✅ Correct |
| Attendu : `net_interets_sur_turnover=0.0`, `net_int_turnover='2'` | ✅ Correct |

**Verdict : ✅ CONFORME**

---

### **Test 7 : `test_null_vs_zero_nops_prlv_retourne`**

| Spec | Test Implémenté |
|------|-----------------|
| E001 sans ligne `prlv_sepa_retourne` | E001 avec `category='turnover'` |
| E002 avec `prlv_sepa_retourne__nops=0` | E002 avec `category='prlv_sepa_retourne', nops_category=0` |

**Problème technique** :
```python
self.assertTrue(result.filter(...)["prlv_sepa_retourne__nops"][0] is None)
```
En Polars, `[0]` retourne la valeur Python, mais la comparaison `is None` peut être fragile.

**Verdict : ⚠️ CONFORME MAIS FRAGILE**

---

### **Test 8 : `test_non_model_categories_only`**

| Spec | Test Implémenté |
|------|-----------------|
| Attendu : "toutes colonnes NULL" puis "remb_sepa_max='2'" | Vérifie `remb_sepa_max='2'` |

**Problème GRAVE** : La spec dit `remb_sepa_max='2'` mais le code **ne fait pas ça**.

Quand une entreprise est dans `df_main` mais **pas** dans `df_transac` (car toutes ses transactions sont filtrées), la jointure LEFT produit **NULL** pour toutes les colonnes transac, **pas '2'**.

```python
df_transac = donnees_transac_filtered.select("i_uniq_kpi").unique()  # VIDE si tout filtré
# ...
df_main = df_main.join(df_transac, on="i_uniq_kpi", how="left")  # Colonnes à NULL
```

**Verdict : ❌ SPEC INCORRECTE OU BUG DANS LE CODE**

La spec attend `remb_sepa_max='2'` mais le code produit `NULL`. Il faut soit :
1. Corriger la spec pour dire "colonnes à NULL"
2. Corriger le code pour appliquer des valeurs par défaut après la jointure

---

### **Test 9 : `test_aggregation_sum_not_max`**

| Spec | Test Implémenté |
|------|-----------------|
| `3 lignes i_uniq_kpi='E001' category='interets__'` | `3 lignes i_uniq_kpi=1000004151300000 category='interets'` |
| `netamount=[-100,-50,-25]`, `nops_category=[1,2,1]` | ✅ Correct |
| Attendu : `interets__netamount=-175`, `interets__nops=4` | ✅ Correct |

**Note** : La spec dit `category='interets__'` mais le code attend `category='interets'` (sans suffixe). Le test utilise correctement `'interets'`.

**Verdict : ✅ CONFORME** (malgré l'erreur dans la spec)

---

## Résumé

| Test | Conformité | Action |
|------|------------|--------|
| 1. saisie_category_merge | ❌ | Réécrire avec 1 entreprise, 4 lignes |
| 2. remb_sepa_max_threshold | ✅ | OK |
| 3. remb_sepa_max_exact_threshold | ✅ | OK |
| 4. net_int_turnover_double_condition | ⚠️ | Revoir le calcul de nops |
| 5. division_by_zero_turnover | ❌ | Réécrire avec 1 entreprise, 2 lignes |
| 6. null_interets_and_turnover | ✅ | OK |
| 7. null_vs_zero_nops | ⚠️ | Vérifier syntaxe `is None` |
| 8. non_model_categories_only | ❌ | Spec ou code à corriger |
| 9. aggregation_sum_not_max | ✅ | OK |

**Problèmes systémiques** :
1. `print("aaaa", result)` dans le code
2. Confusion récurrente entre "1 entreprise avec N transactions" vs "N entreprises avec 1 transaction"
3. Incohérence spec/code sur le comportement avec catégories non-modèle
