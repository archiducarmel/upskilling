"""
Tests unitaires pour le module preprocessing_reboot.py

Ce module contient les tests pour la fonction add_reboot_features() qui enrichit
le DataFrame principal avec les scores de risque REBOOT (modèle externe de scoring).

Les tests couvrent:
- TU-028: Conversion virgule décimale → point décimal
- TU-029: Transformation sigmoid (log-odds → probabilité)
- TU-030: Stabilité numérique avec score très négatif
- TU-031: Stabilité numérique avec score très positif
- TU-032: Gestion des valeurs non numériques
- TU-033: Déduplication avec plusieurs scores par entreprise

Contexte métier:
----------------
Le score REBOOT est un modèle externe de scoring de risque de crédit.
Il produit un score brut (q_score) en log-odds qui est ensuite transformé
en probabilité via la fonction sigmoid.

La variable reboot_score_char2 (score catégorisé en 9 classes) est la
variable la plus discriminante du modèle PDO avec un coefficient de +3.924
pour la classe la plus risquée ("1").

Format des données:
- q_score est exporté au format européen avec VIRGULE décimale ("1,5")
- Il doit être converti au format informatique avec POINT ("1.5")

Auteur: Équipe MLOps - Fab IA
Date: Janvier 2026
Version: 1.0.0
"""

from unittest import TestCase, main
from typing import Any
import polars as pl
import numpy as np
import math


class TestAddRebootFeatures(TestCase):
    """
    Tests unitaires pour la fonction add_reboot_features().
    
    Cette fonction:
    1. Convertit q_score du format européen (virgule) au format informatique (point)
    2. Agrège les scores par groupe de colonnes puis par entreprise
    3. Applique la transformation sigmoid: reboot_score2 = 1 / (1 + exp(-q_score))
    4. Joint les résultats au DataFrame principal via jointure LEFT
    5. Renomme les colonnes: q_score → reboot_score, q_score2 → reboot_score2
    
    Formule mathématique:
    ---------------------
    La fonction sigmoid σ(x) = 1 / (1 + e^(-x)) transforme un score en log-odds
    en une probabilité dans l'intervalle ]0, 1[.
    
    Propriétés:
    - σ(0) = 0.5 (score neutre → 50% de probabilité)
    - σ(x) → 1 quand x → +∞ (score favorable → probabilité proche de 1)
    - σ(x) → 0 quand x → -∞ (score défavorable → probabilité proche de 0)
    - σ(-x) = 1 - σ(x) (symétrie)
    """

    def setUp(self) -> None:
        """
        Initialise les fixtures de test.
        
        Configure:
        - Colonnes requises pour le DataFrame reboot (selon le code source)
        - Valeurs par défaut pour les colonnes non testées
        - Tolérance numérique pour les comparaisons de flottants
        """
        # =======================================================================
        # Colonnes requises par le group_by du code source (lignes 11-22)
        # =======================================================================
        self.reboot_group_columns = [
            "d_histo",              # Date historique
            "i_uniq_kpi",           # ID unique entreprise (clé de jointure)
            "c_int_modele",         # Code interne du modèle
            "d_rev_notation",       # Date de révision de la notation
            "c_not",                # Code notation
            "c_type_prsne",         # Code type de personne
            "b_bddf_gestionnaire",  # Flag BDDF gestionnaire
        ]
        
        # Tolérance pour les comparaisons de flottants
        self.FLOAT_TOLERANCE = 1e-10

    def _create_df_main(self, i_uniq_kpi_values: list[str]) -> pl.DataFrame:
        """
        Crée un DataFrame principal de test avec les identifiants spécifiés.
        
        Args:
            i_uniq_kpi_values: Liste des identifiants uniques des entreprises
        
        Returns:
            DataFrame Polars avec la colonne i_uniq_kpi et des colonnes additionnelles
        """
        n_rows = len(i_uniq_kpi_values)
        return pl.DataFrame({
            "i_uniq_kpi": i_uniq_kpi_values,
            "i_intrn": [f"INTRN_{i}" for i in range(n_rows)],
            "i_siren": [f"SIREN_{i}" for i in range(n_rows)],
        })

    def _create_reboot(
        self, 
        data: list[dict[str, Any]],
        default_values: dict[str, Any] | None = None
    ) -> pl.DataFrame:
        """
        Crée un DataFrame REBOOT de test avec les données spécifiées.
        
        Args:
            data: Liste de dictionnaires avec au minimum i_uniq_kpi et q_score
            default_values: Valeurs par défaut pour les colonnes non spécifiées
        
        Returns:
            DataFrame Polars avec toutes les colonnes REBOOT requises
        """
        if default_values is None:
            default_values = {
                "d_histo": "2024-01-01",
                "c_int_modele": "011",
                "d_rev_notation": "2024-01-01",
                "c_not": "A",
                "c_type_prsne": "PM",
                "b_bddf_gestionnaire": "N",
            }
        
        # Compléter chaque ligne avec les valeurs par défaut
        complete_data = []
        for row in data:
            complete_row = {**default_values, **row}
            complete_data.append(complete_row)
        
        if not complete_data:
            # Retourner un DataFrame vide avec le bon schéma
            return pl.DataFrame(
                schema={
                    "d_histo": pl.Utf8,
                    "i_uniq_kpi": pl.Utf8,
                    "c_int_modele": pl.Utf8,
                    "d_rev_notation": pl.Utf8,
                    "c_not": pl.Utf8,
                    "c_type_prsne": pl.Utf8,
                    "b_bddf_gestionnaire": pl.Utf8,
                    "q_score": pl.Utf8,
                }
            )
        
        return pl.DataFrame(complete_data)

    def _sigmoid(self, x: float) -> float:
        """
        Calcule la fonction sigmoid σ(x) = 1 / (1 + e^(-x)).
        
        Args:
            x: Score en log-odds
        
        Returns:
            Probabilité dans ]0, 1[
        """
        return 1 / (1 + math.exp(-x))

    # ===========================================================================
    # TU-028: Test nominal - Conversion virgule décimale → point décimal
    # ===========================================================================
    def test_tu_028_add_reboot_features_decimal_comma_conversion(self) -> None:
        """
        TU-028: Vérifier la conversion du format européen au format informatique.
        
        OBJECTIF:
        ---------
        Vérifier que q_score (score REBOOT brut, exporté au format européen avec
        VIRGULE décimale: '1,5') est correctement converti au format informatique
        avec POINT décimal (1.5).
        
        DONNÉES D'ENTRÉE:
        -----------------
        Tableau REBOOT avec 2 entreprises:
        - q_score = '1,5' (format européen, score favorable)
        - q_score = '-0,75' (format européen, négatif, défavorable)
        
        Ces scores viennent d'un modèle externe appelé REBOOT qui exporte
        les données au format européen (virgule comme séparateur décimal).
        
        RÉSULTAT ATTENDU:
        -----------------
        Après conversion (str.replace(',', '.') puis cast Float64):
        - q_score devient 1.5 (Float64)
        - q_score devient -0.75 (Float64)
        
        La virgule est remplacée par un point.
        
        RISQUE COUVERT:
        ---------------
        Une erreur de conversion peut:
        - Produire des NaN si le cast échoue
        - Interpréter "1,5" comme deux nombres (1 et 5) si mal parsé
        - Produire 15 au lieu de 1.5 si la virgule est supprimée
        """
        # ===== ARRANGE =====
        from preprocessing_reboot import add_reboot_features
        
        # DataFrame principal avec 2 entreprises
        df_main = self._create_df_main(["E001", "E002"])
        
        # Tableau REBOOT avec scores au format européen (virgule décimale)
        reboot_data = [
            {"i_uniq_kpi": "E001", "q_score": "1,5"},    # Format européen: 1,5 → 1.5
            {"i_uniq_kpi": "E002", "q_score": "-0,75"},  # Format européen: -0,75 → -0.75
        ]
        reboot = self._create_reboot(reboot_data)
        
        # Valeurs attendues après conversion
        expected_scores = {
            "E001": 1.5,
            "E002": -0.75,
        }
        
        # ===== ACT =====
        result = add_reboot_features(df_main, reboot)
        
        # ===== ASSERT =====
        # Vérification de la présence de la colonne reboot_score
        self.assertIn(
            "reboot_score",
            result.columns,
            "La colonne reboot_score doit être créée (renommage de q_score)"
        )
        
        # Vérification du type de données
        self.assertEqual(
            result["reboot_score"].dtype,
            pl.Float64,
            "La colonne reboot_score doit être de type Float64 après conversion"
        )
        
        # Vérification des valeurs converties pour chaque entreprise
        for i_uniq_kpi, expected_score in expected_scores.items():
            with self.subTest(i_uniq_kpi=i_uniq_kpi, expected=expected_score):
                row = result.filter(pl.col("i_uniq_kpi") == i_uniq_kpi)
                actual_score = row["reboot_score"][0]
                
                self.assertAlmostEqual(
                    actual_score,
                    expected_score,
                    places=4,
                    msg=f"Entreprise {i_uniq_kpi}: q_score '{reboot_data[0 if i_uniq_kpi == 'E001' else 1]['q_score']}' "
                        f"doit être converti en {expected_score}, obtenu: {actual_score}"
                )
        
        # Vérification que la conversion n'a pas produit de valeurs aberrantes
        # (ex: "1,5" interprété comme 15)
        row_e001 = result.filter(pl.col("i_uniq_kpi") == "E001")
        self.assertLess(
            row_e001["reboot_score"][0],
            10,
            "La valeur '1,5' doit être 1.5, pas 15 (erreur de parsing virgule)"
        )

    # ===========================================================================
    # TU-029: Test nominal - Transformation sigmoid
    # ===========================================================================
    def test_tu_029_add_reboot_features_sigmoid_transformation(self) -> None:
        """
        TU-029: Vérifier l'application correcte de la transformation sigmoid.
        
        OBJECTIF:
        ---------
        Vérifier que la transformation sigmoid est appliquée:
        reboot_score2 = 1 / (1 + exp(-q_score))
        
        Cette formule transforme le score brut (log-odds) en probabilité.
        
        DONNÉES D'ENTRÉE:
        -----------------
        3 entreprises avec différents q_score:
        - q_score = 0.0 (neutre)
        - q_score = 2.0 (favorable)
        - q_score = -2.0 (défavorable)
        
        RÉSULTAT ATTENDU:
        -----------------
        Vérifier la fonction sigmoid:
        - q_score = 0 → reboot_score2 = 1/(1+exp(0)) = 0.5 (50%)
        - q_score = 2 → reboot_score2 = 1/(1+exp(-2)) ≈ 0.8808 (88%)
        - q_score = -2 → reboot_score2 = 1/(1+exp(2)) ≈ 0.1192 (12%)
        
        Formule mathématiquement exacte.
        
        RISQUE COUVERT:
        ---------------
        Une erreur dans la formule sigmoid (signe incorrect, parenthèses mal
        placées) fausse complètement la transformation:
        - exp(x) au lieu de exp(-x) inverse la relation
        - 1 - sigmoid au lieu de sigmoid inverse les probabilités
        """
        # ===== ARRANGE =====
        from preprocessing_reboot import add_reboot_features
        
        # DataFrame principal avec 3 entreprises
        df_main = self._create_df_main(["E001", "E002", "E003"])
        
        # Tableau REBOOT avec scores de test (format point, pas virgule)
        # Note: le code fait str.replace(',', '.') donc "0.0" reste "0.0"
        reboot_data = [
            {"i_uniq_kpi": "E001", "q_score": "0,0"},   # Score neutre
            {"i_uniq_kpi": "E002", "q_score": "2,0"},   # Score favorable
            {"i_uniq_kpi": "E003", "q_score": "-2,0"},  # Score défavorable
        ]
        reboot = self._create_reboot(reboot_data)
        
        # Calcul des valeurs attendues avec la fonction sigmoid
        expected_results = {
            "E001": {
                "q_score": 0.0,
                "sigmoid": self._sigmoid(0.0),  # = 0.5 exactement
            },
            "E002": {
                "q_score": 2.0,
                "sigmoid": self._sigmoid(2.0),  # ≈ 0.8808
            },
            "E003": {
                "q_score": -2.0,
                "sigmoid": self._sigmoid(-2.0), # ≈ 0.1192
            },
        }
        
        # ===== ACT =====
        result = add_reboot_features(df_main, reboot)
        
        # ===== ASSERT =====
        # Vérification de la présence de la colonne reboot_score2
        self.assertIn(
            "reboot_score2",
            result.columns,
            "La colonne reboot_score2 doit être créée (transformation sigmoid)"
        )
        
        # Vérification des valeurs sigmoid pour chaque entreprise
        for i_uniq_kpi, expected in expected_results.items():
            with self.subTest(i_uniq_kpi=i_uniq_kpi, q_score=expected["q_score"]):
                row = result.filter(pl.col("i_uniq_kpi") == i_uniq_kpi)
                actual_sigmoid = row["reboot_score2"][0]
                expected_sigmoid = expected["sigmoid"]
                
                self.assertAlmostEqual(
                    actual_sigmoid,
                    expected_sigmoid,
                    places=4,
                    msg=f"Entreprise {i_uniq_kpi} (q_score={expected['q_score']}): "
                        f"sigmoid doit être {expected_sigmoid:.4f}, obtenu: {actual_sigmoid:.4f}"
                )
        
        # Vérification des propriétés mathématiques de sigmoid
        # σ(0) = 0.5 exactement
        row_e001 = result.filter(pl.col("i_uniq_kpi") == "E001")
        self.assertEqual(
            row_e001["reboot_score2"][0],
            0.5,
            "sigmoid(0) doit être exactement 0.5"
        )
        
        # σ(x) + σ(-x) = 1 (propriété de symétrie)
        row_e002 = result.filter(pl.col("i_uniq_kpi") == "E002")
        row_e003 = result.filter(pl.col("i_uniq_kpi") == "E003")
        sum_symmetric = row_e002["reboot_score2"][0] + row_e003["reboot_score2"][0]
        self.assertAlmostEqual(
            sum_symmetric,
            1.0,
            places=10,
            msg="sigmoid(2) + sigmoid(-2) doit égaler 1 (propriété de symétrie)"
        )

    # ===========================================================================
    # TU-030: Edge Case - Score extrêmement négatif (stabilité numérique)
    # ===========================================================================
    def test_tu_030_add_reboot_features_extreme_negative_score(self) -> None:
        """
        TU-030: Tester la stabilité numérique avec un score très négatif.
        
        OBJECTIF:
        ---------
        Tester la stabilité numérique avec q_score = -100 (score extrêmement
        défavorable). exp(-(-100)) = exp(100) ≈ 2.7×10^43.
        
        DONNÉES D'ENTRÉE:
        -----------------
        q_score = -100 (score très défavorable, entreprise à très haut risque)
        
        RÉSULTAT ATTENDU:
        -----------------
        reboot_score2 = 1/(1+exp(100)) doit être un nombre valide très proche
        de 0 (≈3.7×10^-44).
        
        Contraintes:
        - Pas de 'Inf' (infinity)
        - Pas de 'NaN' (not a number)
        - Pas de division par zéro
        - Valeur strictement positive (> 0)
        
        RISQUE COUVERT:
        ---------------
        exp(100) est un nombre énorme (≈2.7×10^43) qui peut causer:
        - Overflow en Float64 → Inf
        - Division 1/Inf → 0.0 exact (perte de précision)
        - Erreurs de calcul si mal géré
        """
        # ===== ARRANGE =====
        from preprocessing_reboot import add_reboot_features
        
        # DataFrame principal
        df_main = self._create_df_main(["E001"])
        
        # Score extrêmement négatif
        reboot_data = [
            {"i_uniq_kpi": "E001", "q_score": "-100"},  # Score très défavorable
        ]
        reboot = self._create_reboot(reboot_data)
        
        # Valeur attendue: très proche de 0
        # sigmoid(-100) = 1/(1+exp(100)) ≈ 3.72×10^-44
        expected_sigmoid = self._sigmoid(-100)
        
        # ===== ACT =====
        result = add_reboot_features(df_main, reboot)
        
        # ===== ASSERT =====
        actual_sigmoid = result["reboot_score2"][0]
        
        # Vérification: pas de NaN
        self.assertFalse(
            np.isnan(actual_sigmoid),
            "reboot_score2 ne doit pas être NaN pour q_score=-100"
        )
        
        # Vérification: pas de Inf
        self.assertFalse(
            np.isinf(actual_sigmoid),
            "reboot_score2 ne doit pas être Inf pour q_score=-100"
        )
        
        # Vérification: valeur positive (sigmoid est toujours > 0)
        self.assertGreater(
            actual_sigmoid,
            0,
            "reboot_score2 doit être strictement positif (sigmoid > 0 toujours)"
        )
        
        # Vérification: valeur très proche de 0
        self.assertLess(
            actual_sigmoid,
            1e-40,
            f"sigmoid(-100) doit être très proche de 0, obtenu: {actual_sigmoid}"
        )
        
        # Vérification de la cohérence numérique
        self.assertAlmostEqual(
            actual_sigmoid,
            expected_sigmoid,
            places=45,
            msg=f"sigmoid(-100) attendu: {expected_sigmoid:.2e}, obtenu: {actual_sigmoid:.2e}"
        )

    # ===========================================================================
    # TU-031: Edge Case - Score extrêmement positif (stabilité numérique)
    # ===========================================================================
    def test_tu_031_add_reboot_features_extreme_positive_score(self) -> None:
        """
        TU-031: Tester la stabilité numérique avec un score très positif.
        
        OBJECTIF:
        ---------
        Tester la stabilité avec q_score = +100 (score extrêmement favorable).
        La probabilité doit rester ≤ 1.
        
        DONNÉES D'ENTRÉE:
        -----------------
        q_score = +100 (score très favorable, entreprise à très faible risque)
        
        RÉSULTAT ATTENDU:
        -----------------
        reboot_score2 = 1/(1+exp(-100)) ≈ 0.99999...999 (très proche de 1).
        
        Contraintes:
        - La valeur ne doit PAS dépasser 1
        - Pas de 'Inf'
        - Pas de 'NaN'
        - Pas d'erreur
        
        RISQUE COUVERT:
        ---------------
        exp(-100) est un nombre très petit (≈3.7×10^-44) qui peut causer:
        - Underflow → 0.0 exact
        - 1/(1+0) = 1.0 exact (ce qui est acceptable mais limite)
        - Erreurs d'arrondi donnant > 1
        """
        # ===== ARRANGE =====
        from preprocessing_reboot import add_reboot_features
        
        # DataFrame principal
        df_main = self._create_df_main(["E001"])
        
        # Score extrêmement positif
        reboot_data = [
            {"i_uniq_kpi": "E001", "q_score": "100"},  # Score très favorable
        ]
        reboot = self._create_reboot(reboot_data)
        
        # ===== ACT =====
        result = add_reboot_features(df_main, reboot)
        
        # ===== ASSERT =====
        actual_sigmoid = result["reboot_score2"][0]
        
        # Vérification: pas de NaN
        self.assertFalse(
            np.isnan(actual_sigmoid),
            "reboot_score2 ne doit pas être NaN pour q_score=+100"
        )
        
        # Vérification: pas de Inf
        self.assertFalse(
            np.isinf(actual_sigmoid),
            "reboot_score2 ne doit pas être Inf pour q_score=+100"
        )
        
        # Vérification CRITIQUE: la valeur ne doit PAS dépasser 1
        self.assertLessEqual(
            actual_sigmoid,
            1.0,
            f"reboot_score2 ne doit JAMAIS dépasser 1 (probabilité). "
            f"Obtenu: {actual_sigmoid}"
        )
        
        # Vérification: valeur très proche de 1
        self.assertGreater(
            actual_sigmoid,
            0.9999,
            f"sigmoid(+100) doit être très proche de 1, obtenu: {actual_sigmoid}"
        )
        
        # Vérification: valeur dans l'intervalle valide ]0, 1[
        self.assertGreater(actual_sigmoid, 0, "sigmoid doit être > 0")
        self.assertLess(actual_sigmoid, 1.0 + 1e-10, "sigmoid doit être ≤ 1")

    # ===========================================================================
    # TU-032: Edge Case - Valeurs non numériques dans q_score
    # ===========================================================================
    def test_tu_032_add_reboot_features_non_numeric_values(self) -> None:
        """
        TU-032: Tester la gestion des valeurs non numériques.
        
        OBJECTIF:
        ---------
        Tester avec des valeurs non numériques dans q_score: 'N/A', 'ERROR',
        '#REF!'. Ces valeurs apparaissent dans les exports Excel en cas d'erreur.
        
        DONNÉES D'ENTRÉE:
        -----------------
        - q_score = 'N/A' (valeur Excel "Not Available")
        - q_score = 'ERROR' (valeur textuelle d'erreur)
        - q_score = '#REF!' (erreur de référence Excel)
        
        RÉSULTAT ATTENDU:
        -----------------
        Après conversion (str.replace puis cast), ces valeurs deviennent NULL.
        reboot_score2 = NULL également (sigmoid de NULL = NULL).
        Aucune exception levée, le traitement continue.
        
        RISQUE COUVERT:
        ---------------
        Des valeurs corrompues dans les données sources peuvent:
        - Planter le cast en Float64 → exception
        - Produire des NaN qui se propagent
        - Faire échouer le batch complet
        
        Le comportement gracieux (NULL) permet de continuer le traitement.
        """
        # ===== ARRANGE =====
        from preprocessing_reboot import add_reboot_features
        
        # DataFrame principal avec entreprises ayant des scores invalides
        # et une entreprise avec score valide pour comparaison
        df_main = self._create_df_main(["E001", "E002", "E003", "E004"])
        
        # Tableau REBOOT avec valeurs invalides
        reboot_data = [
            {"i_uniq_kpi": "E001", "q_score": "N/A"},      # Valeur Excel
            {"i_uniq_kpi": "E002", "q_score": "ERROR"},    # Erreur textuelle
            {"i_uniq_kpi": "E003", "q_score": "#REF!"},    # Erreur référence Excel
            {"i_uniq_kpi": "E004", "q_score": "1,5"},      # Valeur valide pour comparaison
        ]
        reboot = self._create_reboot(reboot_data)
        
        # ===== ACT =====
        # La fonction ne doit pas lever d'exception
        try:
            result = add_reboot_features(df_main, reboot)
        except Exception as e:
            self.fail(
                f"add_reboot_features() a levé une exception avec des valeurs "
                f"non numériques: {e}. Le traitement devrait gérer ces cas gracieusement."
            )
        
        # ===== ASSERT =====
        # Vérification pour les valeurs invalides: NULL attendu
        invalid_enterprises = ["E001", "E002", "E003"]
        
        for i_uniq_kpi in invalid_enterprises:
            with self.subTest(i_uniq_kpi=i_uniq_kpi):
                row = result.filter(pl.col("i_uniq_kpi") == i_uniq_kpi)
                
                if len(row) > 0:
                    actual_score = row["reboot_score"][0]
                    actual_sigmoid = row["reboot_score2"][0]
                    
                    # reboot_score doit être NULL après cast échoué
                    self.assertIsNone(
                        actual_score,
                        f"Entreprise {i_uniq_kpi}: reboot_score doit être NULL "
                        f"pour une valeur non numérique, obtenu: {actual_score}"
                    )
                    
                    # reboot_score2 doit aussi être NULL (sigmoid de NULL)
                    self.assertIsNone(
                        actual_sigmoid,
                        f"Entreprise {i_uniq_kpi}: reboot_score2 doit être NULL "
                        f"quand reboot_score est NULL, obtenu: {actual_sigmoid}"
                    )
        
        # Vérification que la valeur valide fonctionne toujours
        row_e004 = result.filter(pl.col("i_uniq_kpi") == "E004")
        if len(row_e004) > 0:
            self.assertIsNotNone(
                row_e004["reboot_score"][0],
                "E004 (score valide '1,5') doit avoir un reboot_score non NULL"
            )
            self.assertAlmostEqual(
                row_e004["reboot_score"][0],
                1.5,
                places=4,
                msg="E004 doit avoir reboot_score = 1.5"
            )

    # ===========================================================================
    # TU-033: Edge Case - Déduplication avec plusieurs scores par entreprise
    # ===========================================================================
    def test_tu_033_add_reboot_features_deduplication(self) -> None:
        """
        TU-033: Tester la déduplication avec plusieurs scores par entreprise.
        
        OBJECTIF:
        ---------
        Tester la déduplication quand plusieurs scores REBOOT existent pour
        la même entreprise. Le code utilise .unique(subset=["i_uniq_kpi"], keep='first').
        
        DONNÉES D'ENTRÉE:
        -----------------
        3 scores REBOOT pour la même entreprise (i_uniq_kpi='E001'):
        - q_score = '1,0' (1er)
        - q_score = '2,0' (2ème)
        - q_score = '3,0' (3ème)
        
        Note: Le code effectue d'abord un group_by().agg(sum()) donc si les
        lignes ont les mêmes valeurs dans les colonnes de groupement, elles
        seront sommées. Sinon, elles seront distinctes et unique() gardera
        la première.
        
        RÉSULTAT ATTENDU:
        -----------------
        Le comportement dépend des colonnes de groupement:
        - Si toutes les colonnes de groupement sont identiques: scores sommés
        - Sinon: unique(keep='first') garde le premier score
        
        Ce test vérifie le comportement avec des colonnes de groupement identiques,
        donc les scores devraient être SOMMÉS.
        
        RISQUE COUVERT:
        ---------------
        Une entreprise peut avoir plusieurs notations REBOOT dans le temps ou
        provenant de différentes sources. Le comportement de déduplication
        doit être déterministe et documenté.
        """
        # ===== ARRANGE =====
        from preprocessing_reboot import add_reboot_features
        
        # DataFrame principal avec 1 entreprise
        df_main = self._create_df_main(["E001"])
        
        # Tableau REBOOT avec plusieurs scores pour la même entreprise
        # MÊMES valeurs dans les colonnes de groupement → scores sommés
        common_values = {
            "d_histo": "2024-01-01",
            "c_int_modele": "011",
            "d_rev_notation": "2024-01-01",
            "c_not": "A",
            "c_type_prsne": "PM",
            "b_bddf_gestionnaire": "N",
        }
        
        reboot_data = [
            {**common_values, "i_uniq_kpi": "E001", "q_score": "1,0"},  # 1er score
            {**common_values, "i_uniq_kpi": "E001", "q_score": "2,0"},  # 2ème score
            {**common_values, "i_uniq_kpi": "E001", "q_score": "3,0"},  # 3ème score
        ]
        reboot = self._create_reboot(reboot_data, default_values={})
        
        # Avec les mêmes colonnes de groupement, le group_by().agg(sum())
        # va sommer les scores: 1.0 + 2.0 + 3.0 = 6.0
        expected_summed_score = 1.0 + 2.0 + 3.0  # = 6.0
        
        # ===== ACT =====
        result = add_reboot_features(df_main, reboot)
        
        # ===== ASSERT =====
        # Vérification qu'il n'y a qu'une seule ligne pour E001
        self.assertEqual(
            len(result),
            1,
            "L'entreprise E001 doit apparaître exactement 1 fois après déduplication"
        )
        
        # Vérification du score (comportement actuel: somme)
        actual_score = result["reboot_score"][0]
        
        self.assertAlmostEqual(
            actual_score,
            expected_summed_score,
            places=4,
            msg=f"Avec les mêmes colonnes de groupement, les scores sont sommés. "
                f"Attendu: {expected_summed_score}, obtenu: {actual_score}"
        )
        
        # ===== TEST COMPLÉMENTAIRE: colonnes de groupement différentes =====
        # Si les colonnes de groupement diffèrent, unique(keep='first') s'applique
        
        df_main_2 = self._create_df_main(["E002"])
        
        # Scores avec des colonnes de groupement DIFFÉRENTES
        reboot_data_2 = [
            {"i_uniq_kpi": "E002", "q_score": "1,0", "d_histo": "2024-01-01"},
            {"i_uniq_kpi": "E002", "q_score": "2,0", "d_histo": "2024-01-02"},  # Date différente
            {"i_uniq_kpi": "E002", "q_score": "3,0", "d_histo": "2024-01-03"},  # Date différente
        ]
        reboot_2 = self._create_reboot(reboot_data_2)
        
        result_2 = add_reboot_features(df_main_2, reboot_2)
        
        # Avec des dates différentes, les lignes ne sont pas groupées ensemble
        # unique(keep='first') garde la première
        actual_score_2 = result_2["reboot_score"][0]
        
        # Le score doit être 1.0 (première ligne gardée par unique)
        self.assertAlmostEqual(
            actual_score_2,
            1.0,
            places=4,
            msg=f"Avec des colonnes de groupement différentes, unique(keep='first') "
                f"garde le premier score. Attendu: 1.0, obtenu: {actual_score_2}"
        )


class TestAddRebootFeaturesIntegration(TestCase):
    """
    Tests d'intégration complémentaires pour add_reboot_features().
    """

    def test_add_reboot_features_preserves_original_columns(self) -> None:
        """
        Vérifier que les colonnes originales du df_main sont préservées.
        """
        # ===== ARRANGE =====
        from preprocessing_reboot import add_reboot_features
        
        df_main = pl.DataFrame({
            "i_uniq_kpi": ["E001"],
            "i_intrn": ["INTRN001"],
            "custom_column": ["custom_value"],
        })
        
        reboot = pl.DataFrame({
            "d_histo": ["2024-01-01"],
            "i_uniq_kpi": ["E001"],
            "c_int_modele": ["011"],
            "d_rev_notation": ["2024-01-01"],
            "c_not": ["A"],
            "c_type_prsne": ["PM"],
            "b_bddf_gestionnaire": ["N"],
            "q_score": ["1,5"],
        })
        
        original_columns = df_main.columns
        
        # ===== ACT =====
        result = add_reboot_features(df_main, reboot)
        
        # ===== ASSERT =====
        for col in original_columns:
            self.assertIn(
                col,
                result.columns,
                f"La colonne originale '{col}' doit être préservée"
            )

    def test_add_reboot_features_left_join_missing_enterprise(self) -> None:
        """
        Vérifier le comportement quand une entreprise n'a pas de score REBOOT.
        """
        # ===== ARRANGE =====
        from preprocessing_reboot import add_reboot_features
        
        df_main = pl.DataFrame({
            "i_uniq_kpi": ["E001", "E002"],  # E002 n'a pas de score
        })
        
        reboot = pl.DataFrame({
            "d_histo": ["2024-01-01"],
            "i_uniq_kpi": ["E001"],  # Seulement E001
            "c_int_modele": ["011"],
            "d_rev_notation": ["2024-01-01"],
            "c_not": ["A"],
            "c_type_prsne": ["PM"],
            "b_bddf_gestionnaire": ["N"],
            "q_score": ["1,5"],
        })
        
        # ===== ACT =====
        result = add_reboot_features(df_main, reboot)
        
        # ===== ASSERT =====
        self.assertEqual(len(result), 2, "Les 2 entreprises doivent être préservées")
        
        # E002 doit avoir des valeurs NULL
        row_e002 = result.filter(pl.col("i_uniq_kpi") == "E002")
        self.assertIsNone(row_e002["reboot_score"][0])
        self.assertIsNone(row_e002["reboot_score2"][0])


# =============================================================================
# Point d'entrée pour l'exécution des tests
# =============================================================================
if __name__ == "__main__":
    main(verbosity=2)
