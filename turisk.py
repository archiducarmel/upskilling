"""
Tests unitaires pour le module preprocessing_risk.py

Ce module contient les tests pour la fonction add_risk_features() qui enrichit
le DataFrame principal avec les indicateurs de risque RSC (Risk Score Components),
notamment le nombre de jours de dépassement de découvert autorisé.

Les tests couvrent:
- TU-019: Agrégation MAX sur plusieurs comptes (cas nominal)
- TU-020: Jointure LEFT avec entreprise absente du RSC
- TU-021: Valeurs aberrantes (hors bornes [0, 10])
- TU-022: Tableau RSC vide (simulation panne source)

Contexte métier:
----------------
La variable k_dep_auth_10j représente le nombre de jours où l'entreprise a été
en dépassement de son autorisation de découvert sur les 10 derniers jours ouvrés.
C'est un signal d'alerte précoce de difficultés de trésorerie.

Une entreprise peut avoir plusieurs comptes bancaires. On prend le MAXIMUM
des jours de dépassement car un seul épisode grave sur un compte est un
signal d'alerte, même si les autres comptes sont sains.

Auteur: Équipe MLOps - Fab IA
Date: Janvier 2026
Version: 1.0.0
"""

from unittest import TestCase, main
from typing import Any
import polars as pl


class TestAddRiskFeatures(TestCase):
    """
    Tests unitaires pour la fonction add_risk_features().
    
    Cette fonction:
    1. Agrège les données RSC par entreprise (i_intrn) en prenant le MAX
       de k_dep_auth_10j (jours de dépassement)
    2. Joint le résultat au DataFrame principal via une jointure LEFT
    3. Renomme la colonne en Q_JJ_DEPST_MM (Quantité Jours Dépassement Maximum Mensuel)
    
    Impact sur le modèle PDO:
    - La variable nbj (nombre de jours) est dérivée de Q_JJ_DEPST_MM
    - nbj = "<=12" (dépassements fréquents) → coefficient +0.739
    - nbj = ">12" (peu de dépassements) → coefficient 0 (référence)
    
    Note: Le seuil de 12 jours semble incohérent avec une fenêtre de 10 jours,
    ce qui suggère une agrégation sur une période plus longue en amont.
    """

    def setUp(self) -> None:
        """
        Initialise les fixtures de test.
        
        Configure:
        - Colonnes minimales requises pour df_main
        - Colonnes requises pour le tableau RSC
        - Valeurs de test de référence
        """
        # =======================================================================
        # Colonnes requises pour chaque DataFrame
        # =======================================================================
        
        # df_main: tableau principal des entreprises
        # i_intrn = identifiant interne RMPM (clé de jointure avec RSC)
        self.df_main_required_columns = ["i_intrn"]
        
        # rsc: tableau des indicateurs de risque RSC
        # k_dep_auth_10j = nombre de jours de dépassement sur 10 jours ouvrés
        self.rsc_required_columns = ["i_intrn", "k_dep_auth_10j"]

    def _create_df_main(self, i_intrn_values: list[str]) -> pl.DataFrame:
        """
        Crée un DataFrame principal de test avec les identifiants spécifiés.
        
        Args:
            i_intrn_values: Liste des identifiants internes RMPM des entreprises
        
        Returns:
            DataFrame Polars avec la colonne i_intrn et des colonnes additionnelles
            simulant un vrai df_main
        """
        n_rows = len(i_intrn_values)
        return pl.DataFrame({
            "i_intrn": i_intrn_values,
            # Colonnes additionnelles pour simuler un vrai df_main
            "i_uniq_kpi": [f"KPI_{i}" for i in range(n_rows)],
            "i_siren": [f"SIREN_{i}" for i in range(n_rows)],
        })

    def _create_rsc(
        self, 
        data: list[dict[str, Any]]
    ) -> pl.DataFrame:
        """
        Crée un DataFrame RSC de test avec les données spécifiées.
        
        Args:
            data: Liste de dictionnaires avec les colonnes i_intrn et k_dep_auth_10j
                  Exemple: [{"i_intrn": "A001", "k_dep_auth_10j": 5}, ...]
        
        Returns:
            DataFrame Polars avec les colonnes RSC requises
        """
        if not data:
            # Cas spécial: DataFrame vide mais avec les colonnes requises
            return pl.DataFrame(
                schema={
                    "i_intrn": pl.Utf8,
                    "k_dep_auth_10j": pl.Int64,
                }
            )
        return pl.DataFrame(data)

    # ===========================================================================
    # TU-019: Test nominal - Agrégation MAX sur plusieurs comptes
    # ===========================================================================
    def test_tu_019_add_risk_features_max_aggregation(self) -> None:
        """
        TU-019: Vérifier l'agrégation MAX de k_dep_auth_10j par entreprise.
        
        OBJECTIF:
        ---------
        Vérifier que k_dep_auth_10j (nombre de jours de dépassement de découvert
        autorisé sur les 10 derniers jours ouvrés) est correctement agrégé par
        MAX quand une entreprise a plusieurs comptes bancaires.
        
        DONNÉES D'ENTRÉE:
        -----------------
        1. df_main avec 2 entreprises:
           - i_intrn = 'A001'
           - i_intrn = 'A002'
        
        2. Tableau RSC (Risk Score Components) avec:
           - Pour A001: 3 lignes avec k_dep_auth_10j = 3, 7, 5 (3 comptes bancaires)
           - Pour A002: 1 ligne avec k_dep_auth_10j = 2 (1 seul compte)
        
        Clé de jointure: i_intrn (identifiant interne RMPM)
        
        RÉSULTAT ATTENDU:
        -----------------
        Après jointure et agrégation, la colonne Q_JJ_DEPST_MM (maximum jours
        dépassement) doit contenir:
        - A001: Q_JJ_DEPST_MM = 7 (MAX de 3, 7, 5)
        - A002: Q_JJ_DEPST_MM = 2 (valeur unique)
        
        On prend le MAXIMUM car un seul épisode grave sur un compte est un
        signal d'alerte, même si les autres comptes sont sains.
        
        RISQUE COUVERT:
        ---------------
        Une mauvaise agrégation (SUM, AVG, MIN au lieu de MAX) diluerait le
        signal de risque. Par exemple, prendre la moyenne (3+7+5)/3 = 5 au lieu
        du MAX 7 sous-estimerait le risque de l'entreprise A001.
        """
        # ===== ARRANGE =====
        from preprocessing_risk import add_risk_features
        
        # DataFrame principal avec 2 entreprises
        df_main = self._create_df_main(["A001", "A002"])
        
        # Tableau RSC avec plusieurs lignes pour A001 (simule plusieurs comptes)
        # et une seule ligne pour A002
        rsc_data = [
            # Entreprise A001: 3 comptes avec différents niveaux de dépassement
            {"i_intrn": "A001", "k_dep_auth_10j": 3},   # Compte 1: 3 jours
            {"i_intrn": "A001", "k_dep_auth_10j": 7},   # Compte 2: 7 jours (MAX)
            {"i_intrn": "A001", "k_dep_auth_10j": 5},   # Compte 3: 5 jours
            # Entreprise A002: 1 seul compte
            {"i_intrn": "A002", "k_dep_auth_10j": 2},   # Compte unique: 2 jours
        ]
        rsc = self._create_rsc(rsc_data)
        
        # Valeurs attendues après agrégation MAX
        expected_results = {
            "A001": 7,  # MAX(3, 7, 5) = 7
            "A002": 2,  # Valeur unique = 2
        }
        
        # ===== ACT =====
        result = add_risk_features(df_main, rsc)
        
        # ===== ASSERT =====
        # Vérification de la présence de la colonne résultat
        self.assertIn(
            "Q_JJ_DEPST_MM",
            result.columns,
            "La colonne Q_JJ_DEPST_MM doit être créée (renommage de k_dep_auth_10j)"
        )
        
        # Vérification du flag de contrôle
        self.assertIn(
            "check",
            result.columns,
            "La colonne check doit être présente"
        )
        self.assertTrue(
            all(result["check"] == "flag_risk_OK"),
            "Toutes les valeurs de check doivent être 'flag_risk_OK'"
        )
        
        # Vérification des valeurs agrégées pour chaque entreprise
        for i_intrn, expected_max in expected_results.items():
            with self.subTest(i_intrn=i_intrn, expected_max=expected_max):
                # Filtrer la ligne correspondante
                row = result.filter(pl.col("i_intrn") == i_intrn)
                
                self.assertEqual(
                    len(row),
                    1,
                    f"L'entreprise {i_intrn} doit apparaître exactement 1 fois"
                )
                
                actual_max = row["Q_JJ_DEPST_MM"][0]
                self.assertEqual(
                    actual_max,
                    expected_max,
                    f"Entreprise {i_intrn}: Q_JJ_DEPST_MM doit être {expected_max} "
                    f"(MAX des jours de dépassement), obtenu: {actual_max}"
                )
        
        # Vérification que le nombre de lignes est préservé
        self.assertEqual(
            len(result),
            len(df_main),
            "Le nombre d'entreprises doit être préservé après la jointure"
        )

    # ===========================================================================
    # TU-020: Test nominal - Jointure LEFT avec entreprise absente du RSC
    # ===========================================================================
    def test_tu_020_add_risk_features_left_join_missing_enterprise(self) -> None:
        """
        TU-020: Vérifier le comportement de la jointure LEFT avec entreprise absente.
        
        OBJECTIF:
        ---------
        Vérifier le comportement de la jointure LEFT quand une entreprise du
        tableau principal n'a aucune donnée dans le tableau RSC (pas d'historique
        de dépassement connu).
        
        DONNÉES D'ENTRÉE:
        -----------------
        1. df_main avec 2 entreprises:
           - i_intrn = 'A001'
           - i_intrn = 'A002'
        
        2. Tableau RSC avec données uniquement pour A001:
           - A001: k_dep_auth_10j = 5
           - A002: ABSENTE du tableau RSC
        
        RÉSULTAT ATTENDU:
        -----------------
        Après jointure LEFT:
        - A001: Q_JJ_DEPST_MM = 5 (valeur du RSC)
        - A002: Q_JJ_DEPST_MM = NULL (pas 0!)
        
        IMPORTANT: NULL signifie "données non disponibles", ce qui est
        sémantiquement différent de "0 jour de dépassement".
        
        RISQUE COUVERT:
        ---------------
        Confondre NULL (données manquantes) avec 0 (aucun dépassement) peut
        créer un biais:
        - NULL → l'entreprise n'est peut-être pas cliente de la banque
        - 0 → l'entreprise est cliente et n'a jamais dépassé
        
        Le traitement aval doit gérer ces deux cas différemment.
        """
        # ===== ARRANGE =====
        from preprocessing_risk import add_risk_features
        
        # DataFrame principal avec 2 entreprises
        df_main = self._create_df_main(["A001", "A002"])
        
        # Tableau RSC avec données UNIQUEMENT pour A001
        # A002 est absente → simuler une nouvelle entreprise sans historique RSC
        rsc_data = [
            {"i_intrn": "A001", "k_dep_auth_10j": 5},
            # A002 volontairement absente
        ]
        rsc = self._create_rsc(rsc_data)
        
        # ===== ACT =====
        result = add_risk_features(df_main, rsc)
        
        # ===== ASSERT =====
        # Vérification que toutes les entreprises du df_main sont préservées
        self.assertEqual(
            len(result),
            len(df_main),
            "La jointure LEFT doit préserver toutes les entreprises du df_main"
        )
        
        # Vérification pour A001: valeur présente
        row_a001 = result.filter(pl.col("i_intrn") == "A001")
        self.assertEqual(
            row_a001["Q_JJ_DEPST_MM"][0],
            5,
            "A001 doit avoir Q_JJ_DEPST_MM = 5 (valeur du RSC)"
        )
        
        # Vérification pour A002: valeur NULL (pas 0!)
        row_a002 = result.filter(pl.col("i_intrn") == "A002")
        actual_value_a002 = row_a002["Q_JJ_DEPST_MM"][0]
        
        self.assertIsNone(
            actual_value_a002,
            f"A002 (absente du RSC) doit avoir Q_JJ_DEPST_MM = NULL, "
            f"pas 0! Obtenu: {actual_value_a002}. "
            f"NULL = 'données non disponibles' ≠ '0 jours de dépassement'"
        )
        
        # Vérification supplémentaire: le type de la colonne permet NULL
        self.assertTrue(
            result["Q_JJ_DEPST_MM"].null_count() > 0,
            "La colonne Q_JJ_DEPST_MM doit contenir au moins un NULL"
        )

    # ===========================================================================
    # TU-021: Edge Case - Valeurs aberrantes hors bornes [0, 10]
    # ===========================================================================
    def test_tu_021_add_risk_features_aberrant_values(self) -> None:
        """
        TU-021: Tester le comportement avec des valeurs aberrantes.
        
        OBJECTIF:
        ---------
        Tester le comportement avec des valeurs aberrantes dans k_dep_auth_10j:
        valeurs négatives (< 0) ou supérieures à 10 (impossible sur 10 jours).
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame RSC avec des valeurs aberrantes:
        - Ligne 1: k_dep_auth_10j = -2 (valeur négative impossible)
        - Ligne 2: k_dep_auth_10j = 15 (> 10 jours impossible sur fenêtre de 10j)
        - Ligne 3: k_dep_auth_10j = 8 (valeur normale dans [0, 10])
        
        Toutes les lignes pour la même entreprise 'A001'.
        
        RÉSULTAT ATTENDU:
        -----------------
        COMPORTEMENT ACTUEL: Le MAX est 15. Les valeurs aberrantes NE SONT PAS
        filtrées par la fonction.
        
        Ce test DOCUMENTE ce comportement qui pourrait nécessiter une correction:
        - Option 1: Filtrer les valeurs hors bornes [0, 10] avant agrégation
        - Option 2: Capper les valeurs (min=0, max=10)
        - Option 3: Lever une alerte/log pour investigation
        
        RISQUE COUVERT:
        ---------------
        Des données aberrantes non filtrées peuvent propager des erreurs dans
        tout le pipeline:
        - Une valeur de 15 jours sur 10 indique un problème de qualité de données
        - Une valeur négative est physiquement impossible
        
        Sans filtre, le modèle PDO utilisera ces valeurs incorrectes.
        """
        # ===== ARRANGE =====
        from preprocessing_risk import add_risk_features
        
        # DataFrame principal avec 1 entreprise
        df_main = self._create_df_main(["A001"])
        
        # Tableau RSC avec valeurs aberrantes (toutes pour A001)
        rsc_data = [
            {"i_intrn": "A001", "k_dep_auth_10j": -2},   # ABERRANT: négatif
            {"i_intrn": "A001", "k_dep_auth_10j": 15},   # ABERRANT: > 10 jours
            {"i_intrn": "A001", "k_dep_auth_10j": 8},    # Normal: dans [0, 10]
        ]
        rsc = self._create_rsc(rsc_data)
        
        # ===== ACT =====
        result = add_risk_features(df_main, rsc)
        
        # ===== ASSERT =====
        actual_max = result["Q_JJ_DEPST_MM"][0]
        
        # Documentation du comportement ACTUEL (pas de filtrage)
        # Le MAX inclut la valeur aberrante 15
        self.assertEqual(
            actual_max,
            15,
            "COMPORTEMENT ACTUEL: Le MAX inclut les valeurs aberrantes. "
            "La valeur 15 (> 10 jours) n'est pas filtrée. "
            "Ce comportement devrait être revu."
        )
        
        # ===== DOCUMENTATION DU COMPORTEMENT À CORRIGER =====
        # Ce test documente une faiblesse du code actuel:
        #
        # PROBLÈME:
        # - k_dep_auth_10j représente les jours de dépassement sur 10 jours ouvrés
        # - Les valeurs valides sont donc dans l'intervalle [0, 10]
        # - Des valeurs hors de cet intervalle indiquent un problème de données
        #
        # COMPORTEMENT ACTUEL:
        # - Aucune validation des bornes
        # - Les valeurs aberrantes sont incluses dans le MAX
        #
        # CORRECTION RECOMMANDÉE (à implémenter):
        # ```python
        # # Option 1: Filtrer les valeurs aberrantes
        # rsc_clean = rsc.filter(
        #     (pl.col("k_dep_auth_10j") >= 0) & 
        #     (pl.col("k_dep_auth_10j") <= 10)
        # )
        #
        # # Option 2: Logger les valeurs aberrantes pour investigation
        # aberrant_count = rsc.filter(
        #     (pl.col("k_dep_auth_10j") < 0) | 
        #     (pl.col("k_dep_auth_10j") > 10)
        # ).height
        # if aberrant_count > 0:
        #     logger.warning(f"{aberrant_count} valeurs aberrantes dans RSC")
        # ```
        
        # Vérification que la valeur n'est pas cappée automatiquement
        self.assertNotEqual(
            actual_max,
            10,
            "La valeur n'est PAS cappée à 10 (comportement actuel)"
        )
        self.assertNotEqual(
            actual_max,
            8,
            "La valeur aberrante 15 n'est PAS ignorée (comportement actuel)"
        )

    # ===========================================================================
    # TU-022: Edge Case - Tableau RSC complètement vide
    # ===========================================================================
    def test_tu_022_add_risk_features_empty_rsc(self) -> None:
        """
        TU-022: Tester avec un tableau RSC complètement vide.
        
        OBJECTIF:
        ---------
        Tester avec un tableau RSC complètement vide (0 lignes, mais colonnes
        i_intrn et k_dep_auth_10j présentes). Simule une panne de la source RSC
        ou une extraction vide.
        
        DONNÉES D'ENTRÉE:
        -----------------
        1. df_main avec 3 entreprises:
           - i_intrn = 'A001', 'A002', 'A003'
        
        2. Tableau RSC vide:
           - 0 lignes
           - Colonnes i_intrn et k_dep_auth_10j présentes (schéma valide)
        
        RÉSULTAT ATTENDU:
        -----------------
        - Les 3 entreprises sont conservées (jointure LEFT préserve le côté gauche)
        - Toutes ont Q_JJ_DEPST_MM = NULL
        - Aucune exception levée
        - Le traitement continue normalement
        - Le flag check = 'flag_risk_OK' est présent
        
        RISQUE COUVERT:
        ---------------
        Une panne de la source RSC ne doit pas faire échouer tout le batch PDO.
        Le comportement gracieux (NULL pour tous) permet:
        - De continuer le traitement
        - D'identifier le problème via les NULL massifs
        - De relancer uniquement la partie RSC si nécessaire
        """
        # ===== ARRANGE =====
        from preprocessing_risk import add_risk_features
        
        # DataFrame principal avec 3 entreprises
        df_main = self._create_df_main(["A001", "A002", "A003"])
        
        # Tableau RSC VIDE (0 lignes, schéma présent)
        # Simule une extraction vide ou une panne de source
        rsc = self._create_rsc([])  # Liste vide → DataFrame vide avec colonnes
        
        # Vérification que le RSC est bien vide
        self.assertEqual(
            len(rsc),
            0,
            "Le tableau RSC de test doit être vide (0 lignes)"
        )
        self.assertIn(
            "i_intrn",
            rsc.columns,
            "Le tableau RSC vide doit avoir la colonne i_intrn (schéma valide)"
        )
        self.assertIn(
            "k_dep_auth_10j",
            rsc.columns,
            "Le tableau RSC vide doit avoir la colonne k_dep_auth_10j (schéma valide)"
        )
        
        # ===== ACT =====
        # La fonction ne doit pas lever d'exception
        try:
            result = add_risk_features(df_main, rsc)
        except Exception as e:
            self.fail(
                f"add_risk_features() a levé une exception avec un RSC vide: {e}. "
                f"Le traitement devrait continuer gracieusement."
            )
        
        # ===== ASSERT =====
        # Vérification que toutes les entreprises sont préservées
        self.assertEqual(
            len(result),
            len(df_main),
            "Les 3 entreprises doivent être conservées malgré le RSC vide"
        )
        
        # Vérification que la colonne Q_JJ_DEPST_MM existe
        self.assertIn(
            "Q_JJ_DEPST_MM",
            result.columns,
            "La colonne Q_JJ_DEPST_MM doit être créée même avec un RSC vide"
        )
        
        # Vérification que toutes les valeurs sont NULL
        null_count = result["Q_JJ_DEPST_MM"].null_count()
        self.assertEqual(
            null_count,
            len(df_main),
            f"Toutes les entreprises doivent avoir Q_JJ_DEPST_MM = NULL "
            f"quand le RSC est vide. NULL trouvés: {null_count}/{len(df_main)}"
        )
        
        # Vérification du flag de contrôle (le traitement a réussi)
        self.assertIn(
            "check",
            result.columns,
            "La colonne check doit être présente"
        )
        self.assertTrue(
            all(result["check"] == "flag_risk_OK"),
            "Le flag check doit être 'flag_risk_OK' même avec un RSC vide"
        )
        
        # Vérification des identifiants préservés
        result_ids = set(result["i_intrn"].to_list())
        expected_ids = {"A001", "A002", "A003"}
        self.assertEqual(
            result_ids,
            expected_ids,
            "Tous les identifiants d'entreprise doivent être préservés"
        )


class TestAddRiskFeaturesIntegration(TestCase):
    """
    Tests d'intégration complémentaires pour add_risk_features().
    """

    def test_add_risk_features_column_renamed_correctly(self) -> None:
        """
        Vérifier que k_dep_auth_10j est bien renommée en Q_JJ_DEPST_MM.
        """
        # ===== ARRANGE =====
        from preprocessing_risk import add_risk_features
        
        df_main = pl.DataFrame({
            "i_intrn": ["A001"],
            "other_col": ["value"],
        })
        
        rsc = pl.DataFrame({
            "i_intrn": ["A001"],
            "k_dep_auth_10j": [5],
        })
        
        # ===== ACT =====
        result = add_risk_features(df_main, rsc)
        
        # ===== ASSERT =====
        # La colonne originale ne doit plus exister
        self.assertNotIn(
            "k_dep_auth_10j",
            result.columns,
            "La colonne k_dep_auth_10j doit être renommée, pas conservée"
        )
        
        # La nouvelle colonne doit exister
        self.assertIn(
            "Q_JJ_DEPST_MM",
            result.columns,
            "La colonne Q_JJ_DEPST_MM doit être créée par renommage"
        )

    def test_add_risk_features_preserves_original_columns(self) -> None:
        """
        Vérifier que les colonnes originales du df_main sont préservées.
        """
        # ===== ARRANGE =====
        from preprocessing_risk import add_risk_features
        
        df_main = pl.DataFrame({
            "i_intrn": ["A001"],
            "i_uniq_kpi": ["KPI001"],
            "i_siren": ["123456789"],
            "custom_column": ["custom_value"],
        })
        
        rsc = pl.DataFrame({
            "i_intrn": ["A001"],
            "k_dep_auth_10j": [3],
        })
        
        original_columns = df_main.columns
        
        # ===== ACT =====
        result = add_risk_features(df_main, rsc)
        
        # ===== ASSERT =====
        for col in original_columns:
            self.assertIn(
                col,
                result.columns,
                f"La colonne originale '{col}' doit être préservée"
            )

    def test_add_risk_features_handles_duplicate_entries_in_rsc(self) -> None:
        """
        Vérifier le comportement avec des entrées dupliquées dans RSC.
        
        Note: Après group_by().agg(max()), il n'y a plus de doublons,
        mais le code appelle aussi unique() qui est redondant.
        """
        # ===== ARRANGE =====
        from preprocessing_risk import add_risk_features
        
        df_main = pl.DataFrame({
            "i_intrn": ["A001"],
        })
        
        # RSC avec entrées "dupliquées" (même i_intrn, valeurs différentes)
        rsc = pl.DataFrame({
            "i_intrn": ["A001", "A001", "A001"],
            "k_dep_auth_10j": [2, 8, 5],
        })
        
        # ===== ACT =====
        result = add_risk_features(df_main, rsc)
        
        # ===== ASSERT =====
        # Une seule ligne pour A001 (pas de duplication)
        self.assertEqual(
            len(result),
            1,
            "Le résultat doit avoir exactement 1 ligne pour A001"
        )
        
        # La valeur doit être le MAX
        self.assertEqual(
            result["Q_JJ_DEPST_MM"][0],
            8,
            "La valeur doit être le MAX (8) des entrées RSC"
        )


# =============================================================================
# Point d'entrée pour l'exécution des tests
# =============================================================================
if __name__ == "__main__":
    # Exécution avec verbosité élevée pour voir le détail des tests
    main(verbosity=2)
