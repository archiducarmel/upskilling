"""
Tests unitaires pour le module preprocessing_soldes.py

Ce module contient les tests pour la fonction add_soldes_features() qui enrichit
le DataFrame principal avec les indicateurs de soldes bancaires des comptes à vue.

Les tests couvrent:
- TU-023: Conversion centimes → euros et somme par entreprise
- TU-024: Comptage du nombre de comptes (solde_nb)
- TU-025: Somme algébrique avec soldes positifs et négatifs
- TU-026: Robustesse avec valeurs très grandes (overflow)
- TU-027: Traitement du solde exactement égal à zéro

Contexte métier:
----------------
Les soldes des comptes à vue (CAV) sont un indicateur de la santé financière
de l'entreprise. Un solde positif élevé indique une trésorerie confortable,
tandis qu'un solde négatif (découvert) peut indiquer des difficultés.

La variable solde_cav_char (solde catégorisé) est dérivée de solde_cav:
- Classe "1": Découvert important (< -9.10€) - coefficient PDO: 0 (référence)
- Classe "2": Solde faible (-9.10€ à 15,235€) - coefficient PDO: +0.138
- Classe "3": Solde moyen (15,235€ à 76,378€) - coefficient PDO: +0.476
- Classe "4": Trésorerie confortable (> 76,378€) - coefficient PDO: +0.924

Note importante: Les montants sont stockés en CENTIMES dans le système source
et doivent être convertis en euros avant utilisation.

Auteur: Équipe MLOps - Fab IA
Date: Janvier 2026
Version: 1.0.0
"""

from unittest import TestCase, main
from typing import Any
import polars as pl
import numpy as np


class TestAddSoldesFeatures(TestCase):
    """
    Tests unitaires pour la fonction add_soldes_features().
    
    Cette fonction:
    1. Convertit les montants de centimes en euros (÷ 100)
    2. Agrège les soldes par entreprise (SUM)
    3. Compte le nombre de comptes par entreprise (COUNT)
    4. Joint les résultats au DataFrame principal via jointure LEFT
    5. Renomme les colonnes: pref_m_ctrvl_sld_arr → solde_cav, pref_i_uniq_cpt → solde_nb
    
    Colonnes d'entrée du tableau soldes:
    - i_intrn: Identifiant interne RMPM de l'entreprise (clé de jointure)
    - pref_i_uniq_cpt: Identifiant unique du compte bancaire
    - pref_m_ctrvl_sld_arr: Solde du compte en CENTIMES (entier)
    
    Colonnes de sortie ajoutées au df_main:
    - solde_cav: Somme des soldes en EUROS (Float64)
    - solde_nb: Nombre de comptes (Int64)
    - check: Flag de contrôle ("flag_soldes_OK")
    """

    def setUp(self) -> None:
        """
        Initialise les fixtures de test.
        
        Configure:
        - Colonnes requises pour df_main
        - Colonnes requises pour le tableau soldes
        - Facteur de conversion centimes → euros
        """
        # =======================================================================
        # Configuration des colonnes et facteurs
        # =======================================================================
        
        # Facteur de conversion: centimes → euros
        self.CENTIMES_TO_EUROS = 100
        
        # Colonnes requises pour le tableau soldes
        self.soldes_required_columns = [
            "i_intrn",            # Clé de jointure (ID entreprise)
            "pref_i_uniq_cpt",    # ID unique du compte
            "pref_m_ctrvl_sld_arr"  # Solde en centimes
        ]

    def _create_df_main(self, i_intrn_values: list[str]) -> pl.DataFrame:
        """
        Crée un DataFrame principal de test avec les identifiants spécifiés.
        
        Args:
            i_intrn_values: Liste des identifiants internes RMPM des entreprises
        
        Returns:
            DataFrame Polars avec la colonne i_intrn et des colonnes additionnelles
        """
        n_rows = len(i_intrn_values)
        return pl.DataFrame({
            "i_intrn": i_intrn_values,
            "i_uniq_kpi": [f"KPI_{i}" for i in range(n_rows)],
            "i_siren": [f"SIREN_{i}" for i in range(n_rows)],
        })

    def _create_soldes(self, data: list[dict[str, Any]]) -> pl.DataFrame:
        """
        Crée un DataFrame soldes de test avec les données spécifiées.
        
        Args:
            data: Liste de dictionnaires avec les colonnes requises
                  Exemple: [{"i_intrn": "A001", "pref_i_uniq_cpt": "CPT001", 
                            "pref_m_ctrvl_sld_arr": 100000}, ...]
        
        Returns:
            DataFrame Polars avec les colonnes soldes requises
        """
        if not data:
            # Cas spécial: DataFrame vide mais avec les colonnes requises
            return pl.DataFrame(
                schema={
                    "i_intrn": pl.Utf8,
                    "pref_i_uniq_cpt": pl.Utf8,
                    "pref_m_ctrvl_sld_arr": pl.Int64,
                }
            )
        return pl.DataFrame(data)

    def _centimes_to_euros(self, centimes: int) -> float:
        """
        Convertit un montant de centimes en euros.
        
        Args:
            centimes: Montant en centimes (entier)
        
        Returns:
            Montant en euros (float)
        """
        return centimes / self.CENTIMES_TO_EUROS

    # ===========================================================================
    # TU-023: Test nominal - Conversion centimes → euros et somme par entreprise
    # ===========================================================================
    def test_tu_023_add_soldes_features_conversion_and_sum(self) -> None:
        """
        TU-023: Vérifier la conversion centimes → euros et la somme par entreprise.
        
        OBJECTIF:
        ---------
        Vérifier que pref_m_ctrvl_sld_arr (solde du compte stocké en CENTIMES
        dans le système source) est correctement converti en euros (÷100) puis
        sommé par entreprise.
        
        DONNÉES D'ENTRÉE:
        -----------------
        1. df_main avec 2 entreprises:
           - i_intrn = 'A001'
           - i_intrn = 'A002'
        
        2. Tableau soldes:
           - A001: 2 comptes avec pref_m_ctrvl_sld_arr = 100000 centimes (1000€)
                   et 50000 centimes (500€)
           - A002: 1 compte avec 200000 centimes (2000€)
        
        RÉSULTAT ATTENDU:
        -----------------
        Après conversion et agrégation:
        - A001: solde_cav = 1000 + 500 = 1500.00€
        - A002: solde_cav = 2000.00€
        
        La colonne solde_cav est en Float64 avec montants en euros.
        
        RISQUE COUVERT:
        ---------------
        Une erreur de conversion (oubli de diviser par 100) multiplierait tous
        les soldes par 100, faussant complètement la catégorisation:
        - 1500€ → classe "2" (solde faible)
        - 150000€ (si non converti) → classe "4" (trésorerie confortable)
        """
        # ===== ARRANGE =====
        from preprocessing_soldes import add_soldes_features
        
        # DataFrame principal avec 2 entreprises
        df_main = self._create_df_main(["A001", "A002"])
        
        # Tableau soldes avec montants en CENTIMES
        soldes_data = [
            # Entreprise A001: 2 comptes
            {
                "i_intrn": "A001",
                "pref_i_uniq_cpt": "CPT001",
                "pref_m_ctrvl_sld_arr": 100000,  # 1000€ en centimes
            },
            {
                "i_intrn": "A001",
                "pref_i_uniq_cpt": "CPT002",
                "pref_m_ctrvl_sld_arr": 50000,   # 500€ en centimes
            },
            # Entreprise A002: 1 compte
            {
                "i_intrn": "A002",
                "pref_i_uniq_cpt": "CPT003",
                "pref_m_ctrvl_sld_arr": 200000,  # 2000€ en centimes
            },
        ]
        soldes = self._create_soldes(soldes_data)
        
        # Calcul des valeurs attendues en euros
        expected_results = {
            "A001": self._centimes_to_euros(100000 + 50000),  # 1500.00€
            "A002": self._centimes_to_euros(200000),          # 2000.00€
        }
        
        # ===== ACT =====
        result = add_soldes_features(df_main, soldes)
        
        # ===== ASSERT =====
        # Vérification de la présence de la colonne solde_cav
        self.assertIn(
            "solde_cav",
            result.columns,
            "La colonne solde_cav doit être créée (renommage de pref_m_ctrvl_sld_arr agrégé)"
        )
        
        # Vérification du type de données
        self.assertEqual(
            result["solde_cav"].dtype,
            pl.Float64,
            "La colonne solde_cav doit être de type Float64 (montants en euros)"
        )
        
        # Vérification du flag de contrôle
        self.assertTrue(
            all(result["check"] == "flag_soldes_OK"),
            "Toutes les valeurs de check doivent être 'flag_soldes_OK'"
        )
        
        # Vérification des valeurs pour chaque entreprise
        for i_intrn, expected_euros in expected_results.items():
            with self.subTest(i_intrn=i_intrn, expected_euros=expected_euros):
                row = result.filter(pl.col("i_intrn") == i_intrn)
                
                self.assertEqual(
                    len(row),
                    1,
                    f"L'entreprise {i_intrn} doit apparaître exactement 1 fois"
                )
                
                actual_euros = row["solde_cav"][0]
                self.assertAlmostEqual(
                    actual_euros,
                    expected_euros,
                    places=2,
                    msg=f"Entreprise {i_intrn}: solde_cav doit être {expected_euros:.2f}€, "
                        f"obtenu: {actual_euros:.2f}€"
                )
        
        # Vérification que les valeurs ne sont PAS en centimes (erreur courante)
        row_a001 = result.filter(pl.col("i_intrn") == "A001")
        self.assertLess(
            row_a001["solde_cav"][0],
            10000,
            "La valeur doit être en euros (1500), pas en centimes (150000)"
        )

    # ===========================================================================
    # TU-024: Test nominal - Comptage du nombre de comptes (solde_nb)
    # ===========================================================================
    def test_tu_024_add_soldes_features_count_accounts(self) -> None:
        """
        TU-024: Vérifier le comptage du nombre de comptes bancaires.
        
        OBJECTIF:
        ---------
        Vérifier que solde_nb (nombre de comptes bancaires) est correctement
        compté en utilisant pref_i_uniq_cpt (identifiant unique de chaque compte).
        
        DONNÉES D'ENTRÉE:
        -----------------
        Tableau soldes avec:
        - A001: 3 comptes différents (pref_i_uniq_cpt = 'CPT001', 'CPT002', 'CPT003')
        - A002: 1 seul compte ('CPT004')
        
        RÉSULTAT ATTENDU:
        -----------------
        Après agrégation:
        - A001: solde_nb = 3
        - A002: solde_nb = 1
        
        Note: Le code actuel utilise COUNT (pas COUNT DISTINCT), donc si un
        même compte apparaît plusieurs fois, il sera compté plusieurs fois.
        
        RISQUE COUVERT:
        ---------------
        Le nombre de comptes peut être utilisé comme indicateur:
        - Plus de comptes → entreprise plus diversifiée
        - Un seul compte → concentration du risque
        
        Un comptage incorrect fausse cette analyse.
        """
        # ===== ARRANGE =====
        from preprocessing_soldes import add_soldes_features
        
        # DataFrame principal avec 2 entreprises
        df_main = self._create_df_main(["A001", "A002"])
        
        # Tableau soldes avec différents nombres de comptes
        soldes_data = [
            # Entreprise A001: 3 comptes distincts
            {"i_intrn": "A001", "pref_i_uniq_cpt": "CPT001", "pref_m_ctrvl_sld_arr": 10000},
            {"i_intrn": "A001", "pref_i_uniq_cpt": "CPT002", "pref_m_ctrvl_sld_arr": 20000},
            {"i_intrn": "A001", "pref_i_uniq_cpt": "CPT003", "pref_m_ctrvl_sld_arr": 30000},
            # Entreprise A002: 1 seul compte
            {"i_intrn": "A002", "pref_i_uniq_cpt": "CPT004", "pref_m_ctrvl_sld_arr": 50000},
        ]
        soldes = self._create_soldes(soldes_data)
        
        # Valeurs attendues pour solde_nb
        expected_counts = {
            "A001": 3,  # 3 comptes
            "A002": 1,  # 1 compte
        }
        
        # ===== ACT =====
        result = add_soldes_features(df_main, soldes)
        
        # ===== ASSERT =====
        # Vérification de la présence de la colonne solde_nb
        self.assertIn(
            "solde_nb",
            result.columns,
            "La colonne solde_nb doit être créée (renommage de pref_i_uniq_cpt agrégé)"
        )
        
        # Vérification des comptages pour chaque entreprise
        for i_intrn, expected_count in expected_counts.items():
            with self.subTest(i_intrn=i_intrn, expected_count=expected_count):
                row = result.filter(pl.col("i_intrn") == i_intrn)
                actual_count = row["solde_nb"][0]
                
                self.assertEqual(
                    actual_count,
                    expected_count,
                    f"Entreprise {i_intrn}: solde_nb doit être {expected_count}, "
                    f"obtenu: {actual_count}"
                )

    # ===========================================================================
    # TU-025: Test nominal - Somme algébrique avec soldes positifs et négatifs
    # ===========================================================================
    def test_tu_025_add_soldes_features_algebraic_sum(self) -> None:
        """
        TU-025: Vérifier la somme algébrique avec compensation positif/négatif.
        
        OBJECTIF:
        ---------
        Vérifier que la somme algébrique des soldes fonctionne quand des soldes
        positifs et négatifs se compensent. Un solde négatif = découvert.
        
        DONNÉES D'ENTRÉE:
        -----------------
        Une entreprise avec 3 comptes:
        - Compte 1: +500000 centimes (+5000€, créditeur)
        - Compte 2: -300000 centimes (-3000€, découvert)
        - Compte 3: -200000 centimes (-2000€, découvert)
        
        Total théorique: 5000 - 3000 - 2000 = 0€
        
        RÉSULTAT ATTENDU:
        -----------------
        solde_cav doit valoir exactement 0.00€.
        Les soldes négatifs (découverts) sont correctement soustraits.
        
        RISQUE COUVERT:
        ---------------
        Un traitement incorrect des négatifs (valeur absolue, filtrage) pourrait:
        - Ignorer les découverts → surestimer la santé financière
        - Prendre |valeur| → ne pas voir la compensation
        
        C'est critique car le signe détermine si l'entreprise est en difficulté.
        """
        # ===== ARRANGE =====
        from preprocessing_soldes import add_soldes_features
        
        # DataFrame principal avec 1 entreprise
        df_main = self._create_df_main(["A001"])
        
        # Tableau soldes avec soldes positifs et négatifs qui se compensent
        soldes_data = [
            # Compte créditeur (+5000€)
            {
                "i_intrn": "A001",
                "pref_i_uniq_cpt": "CPT001",
                "pref_m_ctrvl_sld_arr": 500000,  # +5000€
            },
            # Compte en découvert (-3000€)
            {
                "i_intrn": "A001",
                "pref_i_uniq_cpt": "CPT002",
                "pref_m_ctrvl_sld_arr": -300000,  # -3000€
            },
            # Compte en découvert (-2000€)
            {
                "i_intrn": "A001",
                "pref_i_uniq_cpt": "CPT003",
                "pref_m_ctrvl_sld_arr": -200000,  # -2000€
            },
        ]
        soldes = self._create_soldes(soldes_data)
        
        # Calcul attendu: 5000 - 3000 - 2000 = 0€
        expected_solde = 0.0
        
        # ===== ACT =====
        result = add_soldes_features(df_main, soldes)
        
        # ===== ASSERT =====
        actual_solde = result.filter(pl.col("i_intrn") == "A001")["solde_cav"][0]
        
        self.assertAlmostEqual(
            actual_solde,
            expected_solde,
            places=2,
            msg=f"La somme algébrique doit être exactement 0€ "
                f"(+5000 - 3000 - 2000 = 0), obtenu: {actual_solde}€"
        )
        
        # Vérification supplémentaire: les 3 comptes sont comptés
        actual_nb = result.filter(pl.col("i_intrn") == "A001")["solde_nb"][0]
        self.assertEqual(
            actual_nb,
            3,
            "Les 3 comptes doivent être comptés même si le solde total est 0"
        )
        
        # Test complémentaire: vérifier qu'un solde négatif net fonctionne aussi
        soldes_negative = self._create_soldes([
            {"i_intrn": "B001", "pref_i_uniq_cpt": "CPT010", "pref_m_ctrvl_sld_arr": 100000},  # +1000€
            {"i_intrn": "B001", "pref_i_uniq_cpt": "CPT011", "pref_m_ctrvl_sld_arr": -500000}, # -5000€
        ])
        df_main_b = self._create_df_main(["B001"])
        result_b = add_soldes_features(df_main_b, soldes_negative)
        
        # 1000 - 5000 = -4000€
        expected_negative = -4000.0
        actual_negative = result_b.filter(pl.col("i_intrn") == "B001")["solde_cav"][0]
        
        self.assertAlmostEqual(
            actual_negative,
            expected_negative,
            places=2,
            msg=f"Un solde net négatif (-4000€) doit être correctement calculé, "
                f"obtenu: {actual_negative}€"
        )

    # ===========================================================================
    # TU-026: Edge Case - Valeurs très grandes (test d'overflow)
    # ===========================================================================
    def test_tu_026_add_soldes_features_large_values_overflow(self) -> None:
        """
        TU-026: Tester la robustesse avec des valeurs très grandes.
        
        OBJECTIF:
        ---------
        Tester avec des valeurs très grandes (proches du maximum int64:
        2^63-1 ≈ 9.2×10^18) pour vérifier l'absence d'overflow.
        
        DONNÉES D'ENTRÉE:
        -----------------
        Un solde de 9223372036854775807 centimes (max int64).
        Irréaliste mais test technique de robustesse.
        
        Note: En réalité, un tel montant (≈92 quadrillions d'euros) est absurde,
        mais ce test vérifie que le code ne plante pas avec des données aberrantes.
        
        RÉSULTAT ATTENDU:
        -----------------
        La conversion en Float64 doit fonctionner sans erreur:
        - Pas de 'Inf' (infinity)
        - Pas de 'NaN' (not a number)
        - La précision peut être réduite pour les très grands nombres (acceptable)
        
        RISQUE COUVERT:
        ---------------
        Un overflow non géré peut:
        - Planter le batch complet
        - Produire des NaN qui se propagent dans tout le pipeline
        - Générer des valeurs négatives incorrectes (overflow signé)
        """
        # ===== ARRANGE =====
        from preprocessing_soldes import add_soldes_features
        
        # DataFrame principal
        df_main = self._create_df_main(["A001"])
        
        # Valeur maximale int64 (9,223,372,036,854,775,807)
        max_int64 = 9223372036854775807
        
        # Tableau soldes avec valeur extrême
        soldes_data = [
            {
                "i_intrn": "A001",
                "pref_i_uniq_cpt": "CPT001",
                "pref_m_ctrvl_sld_arr": max_int64,
            },
        ]
        soldes = self._create_soldes(soldes_data)
        
        # Valeur attendue en euros (avec perte de précision acceptable)
        expected_euros = max_int64 / 100  # ≈ 9.22e16 euros
        
        # ===== ACT =====
        # La fonction ne doit pas lever d'exception
        try:
            result = add_soldes_features(df_main, soldes)
        except Exception as e:
            self.fail(
                f"add_soldes_features() a levé une exception avec une valeur "
                f"très grande: {e}"
            )
        
        # ===== ASSERT =====
        actual_solde = result["solde_cav"][0]
        
        # Vérification: pas de NaN
        self.assertFalse(
            np.isnan(actual_solde),
            "La valeur ne doit pas être NaN malgré la grande taille"
        )
        
        # Vérification: pas d'Inf
        self.assertFalse(
            np.isinf(actual_solde),
            "La valeur ne doit pas être Inf (infinity)"
        )
        
        # Vérification: ordre de grandeur correct (perte de précision acceptable)
        # Float64 a ~15 chiffres significatifs, donc pour 9.22e16, on attend
        # une précision relative d'environ 1e-15
        self.assertGreater(
            actual_solde,
            0,
            "La valeur doit être positive (pas d'overflow négatif)"
        )
        
        # Vérification de l'ordre de grandeur (tolérance large pour Float64)
        relative_error = abs(actual_solde - expected_euros) / expected_euros
        self.assertLess(
            relative_error,
            1e-10,
            f"L'erreur relative doit être faible. "
            f"Attendu: {expected_euros:.2e}, obtenu: {actual_solde:.2e}"
        )

    # ===========================================================================
    # TU-027: Edge Case - Solde exactement égal à zéro
    # ===========================================================================
    def test_tu_027_add_soldes_features_zero_balance(self) -> None:
        """
        TU-027: Vérifier le traitement d'un solde exactement égal à zéro.
        
        OBJECTIF:
        ---------
        Vérifier qu'un solde exactement égal à zéro (0) est traité comme
        valeur valide, distinct de NULL.
        
        DONNÉES D'ENTRÉE:
        -----------------
        Un compte avec pref_m_ctrvl_sld_arr = 0 (exactement zéro centimes, pas NULL).
        
        RÉSULTAT ATTENDU:
        -----------------
        - solde_cav = 0.00€ (valeur zéro explicite)
        - solde_nb = 1 (le compte existe)
        
        Zéro = "compte à l'équilibre", différent de "pas de compte" (NULL).
        
        RISQUE COUVERT:
        ---------------
        Certains systèmes confondent 0 et NULL:
        - NULL: Pas de données → jointure LEFT échoue → NULL en sortie
        - 0: Données présentes, valeur = 0 → doit donner 0 en sortie
        
        Cette distinction est importante pour la catégorisation:
        - 0€ est dans la classe "2" (solde faible, seuil > -9.10€)
        - NULL nécessite un traitement spécifique (imputation, exclusion)
        """
        # ===== ARRANGE =====
        from preprocessing_soldes import add_soldes_features
        
        # DataFrame principal avec 2 entreprises
        df_main = self._create_df_main(["A001", "A002"])
        
        # Tableau soldes:
        # - A001: compte avec solde = 0
        # - A002: pas de compte (absence totale)
        soldes_data = [
            {
                "i_intrn": "A001",
                "pref_i_uniq_cpt": "CPT001",
                "pref_m_ctrvl_sld_arr": 0,  # Exactement zéro centimes
            },
            # A002 volontairement absente du tableau soldes
        ]
        soldes = self._create_soldes(soldes_data)
        
        # ===== ACT =====
        result = add_soldes_features(df_main, soldes)
        
        # ===== ASSERT =====
        # Vérification pour A001: solde = 0 (pas NULL)
        row_a001 = result.filter(pl.col("i_intrn") == "A001")
        actual_solde_a001 = row_a001["solde_cav"][0]
        actual_nb_a001 = row_a001["solde_nb"][0]
        
        self.assertEqual(
            actual_solde_a001,
            0.0,
            f"A001 doit avoir solde_cav = 0.00€ (valeur zéro explicite), "
            f"obtenu: {actual_solde_a001}"
        )
        
        self.assertEqual(
            actual_nb_a001,
            1,
            f"A001 doit avoir solde_nb = 1 (le compte existe avec solde 0), "
            f"obtenu: {actual_nb_a001}"
        )
        
        # Vérification critique: 0 n'est PAS None
        self.assertIsNotNone(
            actual_solde_a001,
            "Un solde de 0 doit être distinct de NULL"
        )
        
        # Vérification pour A002: NULL (pas de compte)
        row_a002 = result.filter(pl.col("i_intrn") == "A002")
        actual_solde_a002 = row_a002["solde_cav"][0]
        actual_nb_a002 = row_a002["solde_nb"][0]
        
        self.assertIsNone(
            actual_solde_a002,
            f"A002 (sans compte) doit avoir solde_cav = NULL, "
            f"obtenu: {actual_solde_a002}"
        )
        
        self.assertIsNone(
            actual_nb_a002,
            f"A002 (sans compte) doit avoir solde_nb = NULL, "
            f"obtenu: {actual_nb_a002}"
        )
        
        # ===== DOCUMENTATION DE LA DISTINCTION =====
        # Ce test vérifie une distinction sémantique importante:
        #
        # | Situation                    | solde_cav | solde_nb | Signification          |
        # |------------------------------|-----------|----------|------------------------|
        # | Compte avec solde = 0        | 0.0       | 1        | Compte à l'équilibre   |
        # | Pas de compte (non client)   | NULL      | NULL     | Données non disponibles|
        #
        # Cette distinction impacte la catégorisation aval:
        # - 0€ → classe "2" (coefficient +0.138)
        # - NULL → traitement spécifique nécessaire


class TestAddSoldesFeaturesIntegration(TestCase):
    """
    Tests d'intégration complémentaires pour add_soldes_features().
    """

    def test_add_soldes_features_preserves_original_columns(self) -> None:
        """
        Vérifier que les colonnes originales du df_main sont préservées.
        """
        # ===== ARRANGE =====
        from preprocessing_soldes import add_soldes_features
        
        df_main = pl.DataFrame({
            "i_intrn": ["A001"],
            "i_uniq_kpi": ["KPI001"],
            "custom_column": ["custom_value"],
        })
        
        soldes = pl.DataFrame({
            "i_intrn": ["A001"],
            "pref_i_uniq_cpt": ["CPT001"],
            "pref_m_ctrvl_sld_arr": [100000],
        })
        
        original_columns = df_main.columns
        
        # ===== ACT =====
        result = add_soldes_features(df_main, soldes)
        
        # ===== ASSERT =====
        for col in original_columns:
            self.assertIn(
                col,
                result.columns,
                f"La colonne originale '{col}' doit être préservée"
            )

    def test_add_soldes_features_columns_renamed_correctly(self) -> None:
        """
        Vérifier que les colonnes sont correctement renommées.
        """
        # ===== ARRANGE =====
        from preprocessing_soldes import add_soldes_features
        
        df_main = pl.DataFrame({"i_intrn": ["A001"]})
        soldes = pl.DataFrame({
            "i_intrn": ["A001"],
            "pref_i_uniq_cpt": ["CPT001"],
            "pref_m_ctrvl_sld_arr": [100000],
        })
        
        # ===== ACT =====
        result = add_soldes_features(df_main, soldes)
        
        # ===== ASSERT =====
        # Les colonnes originales ne doivent plus exister
        self.assertNotIn(
            "pref_m_ctrvl_sld_arr",
            result.columns,
            "pref_m_ctrvl_sld_arr doit être renommée en solde_cav"
        )
        self.assertNotIn(
            "pref_i_uniq_cpt",
            result.columns,
            "pref_i_uniq_cpt doit être renommée en solde_nb"
        )
        
        # Les nouvelles colonnes doivent exister
        self.assertIn("solde_cav", result.columns)
        self.assertIn("solde_nb", result.columns)

    def test_add_soldes_features_empty_soldes_table(self) -> None:
        """
        Vérifier le comportement avec un tableau soldes vide.
        """
        # ===== ARRANGE =====
        from preprocessing_soldes import add_soldes_features
        
        df_main = pl.DataFrame({"i_intrn": ["A001", "A002"]})
        soldes = pl.DataFrame(
            schema={
                "i_intrn": pl.Utf8,
                "pref_i_uniq_cpt": pl.Utf8,
                "pref_m_ctrvl_sld_arr": pl.Int64,
            }
        )
        
        # ===== ACT =====
        result = add_soldes_features(df_main, soldes)
        
        # ===== ASSERT =====
        self.assertEqual(len(result), 2)
        self.assertEqual(result["solde_cav"].null_count(), 2)
        self.assertEqual(result["solde_nb"].null_count(), 2)


# =============================================================================
# Point d'entrée pour l'exécution des tests
# =============================================================================
if __name__ == "__main__":
    main(verbosity=2)
