test_preprocessing_transac.py => ALL GOOD !

======

test_preprocessing_safir_soc.py

---

**1. `test_vb005_division_by_zero_servicedette` → NOK**

Ce que la spec prévoit :
- Quand `servicedette = 0` (annuités d'emprunt nulles), division par zéro à gérer
- `VB005` devrait être `0` ou `NULL`, pas `Inf`
- Pas de crash

Ce qui est implémenté :
- Le test vérifie `self.assertTrue(vb005 is None)`
- Attend `None` comme résultat

Pourquoi c'est faux : Le code source fait :
```python
.when(pl.col("servicedette") == 0)
.then(pl.lit("0"))  # ← String "0"
...
df_soc = df_soc.cast({"VB005": pl.Float64})  # ← Cast en 0.0
```
Quand `servicedette = 0`, le code retourne `"0"` (string) qui est ensuite casté en `0.0` (float). Le test attend `None` mais le code produit `0.0`. Le test va échouer.

---

**2. `test_vb035_vb055_division_by_zero_total_passif` → NOK**

Ce que la spec prévoit :
- Quand `mt_534` (total passif) = 0, division par zéro à gérer pour VB035 et VB055
- Les deux ratios devraient être `0` ou `NULL`, pas `Inf`

Ce qui est implémenté :
- Le test vérifie `self.assertTrue(vb035 is None)` et `self.assertTrue(vb055 is None)`
- Attend `None` pour les deux

Pourquoi c'est faux : Même logique que ci-dessus. Le code source fait :
```python
.when(pl.col("totb") == 0)
.then(pl.lit("0"))
```
Quand `totb = 0`, le code retourne `"0"` → casté en `0.0`. Le test attend `None` mais le code produit `0.0`. Le test va échouer.

---

**3. `test_unexpected_regime_fiscal` → PARTIELLEMENT NOK**

Ce que la spec prévoit :
- Quand `c_regme_fisc` a une valeur inattendue (ni "1" ni "2"), CAF = NULL
- Les ratios financiers (VB005, VB035, VB055) sont aussi NULL ou valeurs par défaut

Ce qui est implémenté :
- Le test vérifie `self.assertIsNone(caf)` ✅
- Le test vérifie `self.assertTrue(vb005 is None)` ❌

Pourquoi c'est partiellement faux : 
- La vérification de CAF est correcte : le code retourne bien `None` pour un régime fiscal inconnu via la clause `otherwise(None)`
- Mais pour VB005, le code fait :
```python
.when(pl.col("CAF").is_null())
.then(pl.lit("0"))
```
Si `CAF = None`, alors `VB005 = "0"` → casté en `0.0`. Le test attend `None` mais le code produit `0.0`.

=======
test_preprocessing_safir_conso.py

**4. `test_vb023_division_by_zero_ca` → NOK**

Ce que la spec prévoit :
- Quand `ca_conso = 0` ou `NULL`, VB023 ne doit pas crasher
- VB023 devrait être `NULL` (pas `Inf`)

Ce qui est implémenté :
- Le test attend `self.assertTrue(vb023 is None)`
- Les données : `mt_310 = None`, `mt_309 = -1000000`, `mt_24 = 1000000`
- ca_conso = (mt_24 + mt_309) / 12 × 12 = 0

Pourquoi c'est faux : Le code source fait :
```python
df_conso = df_conso.with_columns(
    [(pl.col("res_net_conso").cast(pl.Float64) / pl.col("ca_conso").cast(pl.Float64) * 100).alias("VB023")]
)
```

**Il n'y a AUCUNE protection contre la division par zéro !** Quand `ca_conso = 0`, le code retourne `Inf` ou `NaN`, pas `None`. Le test attend `None` mais le code produit `Inf`.

=========
test_preprocessing_format_variables.py

**1. `test_nature_juridique_encoding` → NOK**

Ce que la spec prévoit :
- `c_njur_prsne_enc='7'` → `nat_jur_a='>=7'`
- Autres valeurs restent inchangées

Ce qui est implémenté :
- Données : `c_njur_prsne_enc = ["1", "5", "7"]`
- Attendu : `nat_jur = ["1", "5", ">=7"]`

Pourquoi c'est faux : Le code source (lignes 8-12) convertit uniquement "7" en ">=7", les autres valeurs passent telles quelles. **MAIS** le test utilise `"1"` et `"5"` comme valeurs. Or dans le contexte du modèle, `c_njur_prsne_enc` devrait contenir des valeurs comme `"1-3"`, `"4-6"`, `"7"`. Le test avec `"1"` et `"5"` ne correspond pas aux vraies valeurs métier (voir `setUp` qui utilise `"1-3"`).

Le test passe techniquement mais ne teste pas les vraies valeurs métier attendues.

**2. `test_reboot_score_null_handling` → NOK**

Ce que la spec prévoit :
- `reboot_score2 = NULL` → `reboot_score_char2 = NULL`

Ce qui est implémenté :
- Données : `reboot_score2 = [0.5, None]`
- Attendu : `[classe valide, None]`

Pourquoi c'est faux : Le code source (lignes 43-63) n'a **PAS** de clause `otherwise()` pour `reboot_score_char2`. Toutes les conditions utilisent des comparaisons numériques :
```python
.when(pl.col("reboot_score2") < 0.00142771716)
...
.when(pl.col("reboot_score2") > 0.0456250459)
.then(pl.lit("9"))
.alias("reboot_score_char2")  # PAS de .otherwise()
```

Si `reboot_score2 = NULL`, aucune condition ne match (les comparaisons avec NULL retournent NULL), donc `reboot_score_char2 = NULL`. **Le test est correct** mais il documente un comportement implicite, pas explicite.

**Problème potentiel** : `0.5 > 0.0456250459` → classe '9'. Mais le test attend juste `assertIsNotNone(reboot_classes[0])`. C'est faible comme assertion.

===========
test_preprocessing_filters.py

**3. `test_exclusion_creances_risquees` → NOK**

Ce que la spec prévoit :
- `c_crisq='0'` (sain), NULL conservés
- `c_crisq='1'` (douteux), `'2'` (défaut) exclus

Ce qui est implémenté :
- Données : `c_crisq = ["0", "1", "2", None]`
- Attendu : 2 entreprises conservées (0, NULL)

Pourquoi c'est faux : Le code source (ligne 25) fait :
```python
df_main = df_main.filter(~pl.col("c_crisq").is_in(["1", "2"]))
```

Cette condition `~is_in(["1", "2"])` retourne `True` si la valeur n'est **PAS** dans ["1", "2"]. Pour `NULL`, le comportement de Polars est :
- `NULL.is_in(["1", "2"])` → `NULL`
- `~NULL` → `NULL`
- Filtrage sur `NULL` → **ligne exclue**

**Le test attend que NULL soit conservé mais le code va l'exclure.** Le test va échouer.

---

**4. `test_profil_immobilier_null_handling` → NOK**

Ce que la spec prévoit :
- `c_profl_immbr='1'` exclu
- `c_profl_immbr='0'`, NULL, '' conservés
- Attendu : 3 entreprises

Ce qui est implémenté :
- Données : `c_profl_immbr = ["1", "0", None, ""]`
- Le code convertit NULL en "" puis filtre `!= "1"`

Pourquoi c'est faux : Le `setUp` utilise `"c_profl_immbr": [2] * 10` (entiers), mais le test utilise `pl.Series("c_profl_immbr", ["1", "0", None, ""])` (strings).

De plus, il y a d'autres filtres dans la fonction qui peuvent exclure des lignes :
- Ligne 23 : `df_main.filter(pl.col("c_pres_cpt") == "1")` - `setUp` utilise `["1"] * 10` mais c'est un integer `[1] * 10`
- Ligne 25 : `df_main.filter(~pl.col("c_crisq").is_in(["1", "2"]))` - `setUp` utilise `["3"] * 10` (OK)

Les types de données (`int` vs `str`) peuvent causer des problèmes de comparaison.

======
test_postprocessing.py ==> ALL GOOD !