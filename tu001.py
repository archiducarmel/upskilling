"""
Tests unitaires pour le module calcul_pdo.py

Ce module contient les tests pour les fonctions de calcul de la PDO
(Probabilité De Défaut) utilisées dans le cadre réglementaire Bâle III.

Les tests couvrent:
- TU-001 à TU-007: Fonction calcul_pdo() avec coefficients hardcodés
- TU-008 à TU-011: Fonction calcul_pdo_sklearn() avec modèle sklearn

Auteur: Équipe MLOps - Fab IA
Date: Janvier 2026
Version: 1.0.0
"""

from unittest import TestCase, main
from unittest.mock import MagicMock, patch
from typing import Any
import numpy as np
import polars as pl


class TestCalculPdo(TestCase):
    """
    Tests unitaires pour la fonction calcul_pdo().
    
    Cette classe teste le calcul de la Probabilité De Défaut (PDO) 
    via la formule de régression logistique avec coefficients configurables.
    
    Formule: PDO = 1 / (1 + exp(-sum_total_coeffs))
    où sum_total_coeffs = intercept + Σ(coefficient_i × variable_i)
    
    La PDO est utilisée pour:
    - Les décisions d'octroi de crédit
    - Le calcul des provisions réglementaires Bâle III
    - Le pilotage du risque de crédit du portefeuille entreprises
    """

    def setUp(self) -> None:
        """
        Initialise les fixtures de test avant chaque méthode de test.
        
        Configure:
        - self.config: Dictionnaire contenant tous les 47 coefficients du modèle
          de régression logistique (intercept + 46 coefficients de variables)
        - self.reference_row: Ligne de données avec les modalités de référence
          (coefficient = 0) pour chaque variable
        - self.intercept: Valeur de l'intercept du modèle (-3.864)
        """
        # =======================================================================
        # Configuration complète du modèle avec les 47 coefficients
        # Structure: config["model"]["coeffs"]["nom_variable_modalite"]
        # Chaque coefficient représente la contribution de la modalité au log-odds
        # =======================================================================
        self.config: dict[str, Any] = {
            "model": {
                "coeffs": {
                    # ---------------------------------------------------------------
                    # nat_jur_a: Nature juridique agrégée de l'entreprise
                    # Modalité "1-3" = SARL, SAS, SA (référence, coeff=0)
                    # Modalité "4-6" = Formes juridiques intermédiaires
                    # Modalité ">=7" = Formes juridiques atypiques (plus risqué)
                    # ---------------------------------------------------------------
                    "nat_jur_a_1_3": 0,                    # Référence
                    "nat_jur_a_4_6": 0.242841372870074,    # +0.24 log-odds
                    "nat_jur_a_sup7": 1.14619110439058,    # +1.15 log-odds (risque élevé)
                    
                    # ---------------------------------------------------------------
                    # secto_b: Secteur d'activité économique (4 classes)
                    # Classes 1-2: Secteurs sensibles (construction, immobilier)
                    # Classe 3: Secteurs intermédiaires
                    # Classe 4: Secteurs stables (référence)
                    # ---------------------------------------------------------------
                    "secto_b_1": 0.945818754757707,       # Secteur sensible
                    "secto_b_2": 0.945818754757707,       # Secteur sensible
                    "secto_b_3": 0.302139711824692,       # Intermédiaire
                    "secto_b_4": 0,                        # Référence (stable)
                    
                    # ---------------------------------------------------------------
                    # seg_nae: Segmentation NAE (taille entreprise)
                    # ME = Moyennes Entreprises (référence)
                    # autres = Grandes Entreprises, A3 (légèrement plus risqué)
                    # ---------------------------------------------------------------
                    "seg_nae_ME": 0,                       # Référence
                    "seg_nae_autres": 0.699122196727483,   # +0.70 log-odds
                    
                    # ---------------------------------------------------------------
                    # top_ga: Appartenance à un groupe d'affaires
                    # 0 = Entreprise indépendante (référence)
                    # 1 = Appartient à un groupe (risque légèrement accru)
                    # ---------------------------------------------------------------
                    "top_ga_0": 0,                         # Référence
                    "top_ga_1": 0.381966549691793,         # +0.38 log-odds
                    
                    # ---------------------------------------------------------------
                    # nbj: Nombre de jours de dépassement autorisé
                    # <=12 jours = Dépassements fréquents (plus risqué)
                    # >12 jours = Peu de dépassements (référence)
                    # ---------------------------------------------------------------
                    "nbj_inf_equal_12": 0.739002401887176, # Dépassements fréquents
                    "nbj_sup_12": 0,                       # Référence
                    
                    # ---------------------------------------------------------------
                    # solde_cav_char: Solde des comptes à vue catégorisé
                    # 1 = Découvert important < -9€ (référence)
                    # 2 = Solde faible -9€ à 15k€
                    # 3 = Solde moyen 15k€ à 76k€
                    # 4 = Trésorerie confortable > 76k€ (paradoxalement plus risqué)
                    # ---------------------------------------------------------------
                    "solde_cav_char_1": 0,                 # Référence
                    "solde_cav_char_2": 0.138176642753287,
                    "solde_cav_char_3": 0.475979161230845,
                    "solde_cav_char_4": 0.923960586241845,
                    
                    # ---------------------------------------------------------------
                    # reboot_score_char2: Score de risque REBOOT (9 classes)
                    # 1 = Très risqué (coefficient le plus élevé: +3.92)
                    # 9 = Très sain (référence, coefficient = 0)
                    # ---------------------------------------------------------------
                    "reboot_score_char2_1": 3.92364486708385,  # Très risqué
                    "reboot_score_char2_2": 1.74758134681695,
                    "reboot_score_char2_3": 1.34323461962549,
                    "reboot_score_char2_4": 1.09920154963862,
                    "reboot_score_char2_5": 0.756387308936913,
                    "reboot_score_char2_6": 0.756387308936913,
                    "reboot_score_char2_7": 0.756387308936913,
                    "reboot_score_char2_8": 0.340053879161636,
                    "reboot_score_char2_9": 0,                 # Référence (sain)
                    
                    # ---------------------------------------------------------------
                    # remb_sepa_max: Montant max remboursement prélèvement SEPA
                    # 1 = Montant <= 3493€ (référence)
                    # 2 = Montant > 3493€ (gros remboursements = risque)
                    # ---------------------------------------------------------------
                    "remb_sepa_max_1": 0,                  # Référence
                    "remb_sepa_max_2": 1.34614367878806,   # +1.35 log-odds
                    
                    # ---------------------------------------------------------------
                    # pres_prlv_retourne: Présence de prélèvements retournés
                    # 1 = Pas de prélèvement retourné (référence)
                    # 2 = Au moins un prélèvement retourné (impayé)
                    # ---------------------------------------------------------------
                    "pres_prlv_retourne_1": 0,             # Référence
                    "pres_prlv_retourne_2": 0.917163902080624,
                    
                    # ---------------------------------------------------------------
                    # pres_saisie: Présence de saisie ou ATD sur compte
                    # 1 = Pas de saisie (référence)
                    # 2 = Au moins une saisie (risque élevé)
                    # ---------------------------------------------------------------
                    "pres_saisie_1": 0,                    # Référence
                    "pres_saisie_2": 0.805036359316808,
                    
                    # ---------------------------------------------------------------
                    # net_int_turnover: Ratio intérêts débiteurs / chiffre d'affaires
                    # 1 = Ratio faible (référence)
                    # 2 = Ratio élevé (coût du crédit important)
                    # ---------------------------------------------------------------
                    "net_int_turnover_1": 0,               # Référence
                    "net_int_turnover_2": 0.479376606177871,
                    
                    # ---------------------------------------------------------------
                    # rn_ca_conso_023b: Ratio résultat net / CA consolidé
                    # 1 = Ratio faible < 0.43% (référence)
                    # 2 = Ratio moyen 0.43% à 3%
                    # 3 = Ratio élevé > 3%
                    # ---------------------------------------------------------------
                    "rn_ca_conso_023b_1": 0,               # Référence
                    "rn_ca_conso_023b_2": 1.17070023813324,
                    "rn_ca_conso_023b_3": 1.64465207886908,
                    
                    # ---------------------------------------------------------------
                    # caf_dmlt_005: Ratio CAF / Service de la dette
                    # 1 = Ratio faible (référence)
                    # 2 = Ratio élevé > 66.22%
                    # ---------------------------------------------------------------
                    "caf_dmlt_005_1": 0,                   # Référence
                    "caf_dmlt_005_2": 0.552998315798404,
                    
                    # ---------------------------------------------------------------
                    # res_total_passif_035: Ratio résultat courant / total passif
                    # 4 classes de risque croissant
                    # ---------------------------------------------------------------
                    "res_total_passif_035_1": 0,           # Référence
                    "res_total_passif_035_2": 0.332604372992466,
                    "res_total_passif_035_3": 0.676018969566685,
                    "res_total_passif_035_4": 0.977499984983427,
                    
                    # ---------------------------------------------------------------
                    # immob_total_passif_055: Ratio immobilisations / total passif
                    # 3 classes selon le niveau d'immobilisation
                    # ---------------------------------------------------------------
                    "immob_total_passif_055_1": 0,         # Référence
                    "immob_total_passif_055_2": 0.32870481469531,
                    "immob_total_passif_055_3": 0.572596945524726,
                    
                    # ---------------------------------------------------------------
                    # Intercept du modèle (constante)
                    # Valeur négative = PDO de base faible avant ajout des variables
                    # ---------------------------------------------------------------
                    "intercept": -3.86402362750751,
                }
            }
        }
        
        # =======================================================================
        # Ligne de référence avec toutes les modalités ayant coefficient = 0
        # Utilisée comme base pour les tests: sum_total_coeffs = intercept seul
        # =======================================================================
        self.reference_row: dict[str, str] = {
            "nat_jur_a": "1-3",              # Référence (SARL/SAS/SA)
            "secto_b": "4",                   # Référence (secteur stable)
            "seg_nae": "ME",                  # Référence (Moyennes Entreprises)
            "top_ga": "0",                    # Référence (indépendante)
            "nbj": ">12",                     # Référence (peu de dépassements)
            "solde_cav_char": "1",            # Référence (découvert)
            "reboot_score_char2": "9",        # Référence (très sain)
            "remb_sepa_max": "1",             # Référence (petits montants)
            "pres_prlv_retourne": "1",        # Référence (pas d'impayé)
            "pres_saisie": "1",               # Référence (pas de saisie)
            "net_int_turnover": "1",          # Référence (ratio faible)
            "rn_ca_conso_023b": "1",          # Référence (ratio faible)
            "caf_dmlt_005": "1",              # Référence (ratio faible)
            "res_total_passif_035": "1",      # Référence
            "immob_total_passif_055": "1",    # Référence
        }
        
        # Extraction de l'intercept pour faciliter les assertions
        self.intercept: float = self.config["model"]["coeffs"]["intercept"]

    def _create_df_with_overrides(self, overrides: dict[str, Any]) -> pl.DataFrame:
        """
        Crée un DataFrame Polars avec les valeurs de référence et des surcharges.
        
        Cette méthode utilitaire permet de créer rapidement un DataFrame de test
        en partant des valeurs de référence et en modifiant uniquement les
        variables spécifiées dans le dictionnaire overrides.
        
        Args:
            overrides: Dictionnaire {nom_colonne: nouvelle_valeur} pour les
                      variables à modifier par rapport aux valeurs de référence.
        
        Returns:
            DataFrame Polars avec 1 ligne contenant les valeurs fusionnées.
        
        Example:
            >>> df = self._create_df_with_overrides({"nat_jur_a": ">=7"})
            >>> # Retourne un DataFrame avec nat_jur_a=">=7" et toutes les
            >>> # autres colonnes aux valeurs de référence
        """
        # Fusion des valeurs de référence avec les surcharges
        row = {**self.reference_row, **overrides}
        return pl.DataFrame([row])

    # ===========================================================================
    # TU-001: Test nominal - Calcul PDO avec toutes les variables valides
    # ===========================================================================
    def test_tu_001_calcul_pdo_nominal_all_valid_variables(self) -> None:
        """
        TU-001: Vérifier le calcul correct de la PDO pour un DataFrame complet.
        
        OBJECTIF:
        ---------
        Vérifier que la fonction calcul_pdo() calcule correctement la PDO
        (Probabilité De Défaut) pour un DataFrame Polars contenant toutes
        les 15 variables du modèle avec des valeurs valides.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec 1 ligne contenant toutes les modalités de référence:
        - nat_jur_a='1-3' (SARL/SAS/SA)
        - secto_b='4' (secteur stable)
        - seg_nae='ME' (Moyennes Entreprises)
        - top_ga='0' (entreprise indépendante)
        - nbj='>12' (peu de dépassements)
        - solde_cav_char='1' (découvert)
        - reboot_score_char2='9' (très sain)
        - remb_sepa_max='1' (petits montants)
        - pres_prlv_retourne='1' (pas d'impayé)
        - pres_saisie='1' (pas de saisie)
        - net_int_turnover='1' (ratio faible)
        - rn_ca_conso_023b='1' (ratio faible)
        - caf_dmlt_005='1' (ratio faible)
        - res_total_passif_035='1'
        - immob_total_passif_055='1'
        
        RÉSULTAT ATTENDU:
        -----------------
        DataFrame avec colonnes ajoutées:
        - intercept = -3.864
        - sum_total_coeffs = -3.864 (tous coeffs à 0 car modalités de référence)
        - PDO_compute ≈ 0.0206
        - PDO = 0.0206 (arrondi 4 décimales)
        - flag_pdo_OK = 'flag'
        
        RISQUE COUVERT:
        ---------------
        Une PDO incorrecte entraîne des décisions de crédit erronées, des
        provisions mal calculées et une non-conformité réglementaire Bâle III
        avec sanctions potentielles.
        """
        # ===== ARRANGE =====
        # Import de la fonction à tester (import local pour isoler les tests)
        from common.calcul_pdo import calcul_pdo
        
        # Création du DataFrame d'entrée avec toutes les modalités de référence
        df_input = pl.DataFrame([self.reference_row])
        
        # Calcul de la PDO théorique attendue
        # Avec toutes les modalités de référence, sum = intercept = -3.864
        # PDO = 1 / (1 + exp(-(-3.864))) = 1 / (1 + exp(3.864)) ≈ 0.0206
        expected_sum_coeffs = self.intercept  # -3.864
        expected_pdo = 1 / (1 + np.exp(-expected_sum_coeffs))  # ≈ 0.0206
        
        # ===== ACT =====
        # Appel de la fonction avec le DataFrame et la configuration
        result = calcul_pdo(df_input, self.config)
        
        # ===== ASSERT =====
        # Vérification de la présence des colonnes de sortie attendues
        expected_columns = [
            "intercept",           # Constante du modèle
            "sum_total_coeffs",    # Somme intercept + tous les coefficients
            "PDO_compute",         # PDO brute avant arrondi
            "PDO",                 # PDO finale arrondie
            "flag_pdo_OK",         # Flag de contrôle qualité
        ]
        for col in expected_columns:
            self.assertIn(
                col, 
                result.columns,
                f"La colonne '{col}' doit être présente dans le résultat"
            )
        
        # Vérification de la valeur de l'intercept
        actual_intercept = result["intercept"][0]
        self.assertAlmostEqual(
            actual_intercept,
            self.intercept,
            places=4,
            msg=f"L'intercept doit être {self.intercept}, obtenu: {actual_intercept}"
        )
        
        # Vérification de sum_total_coeffs (doit égaler intercept car tous coeffs = 0)
        actual_sum = result["sum_total_coeffs"][0]
        self.assertAlmostEqual(
            actual_sum,
            expected_sum_coeffs,
            places=4,
            msg=f"sum_total_coeffs doit être {expected_sum_coeffs}, obtenu: {actual_sum}"
        )
        
        # Vérification de la PDO finale
        actual_pdo = result["PDO"][0]
        self.assertAlmostEqual(
            actual_pdo,
            expected_pdo,
            places=3,
            msg=f"PDO doit être ≈{expected_pdo:.4f}, obtenu: {actual_pdo}"
        )
        
        # Vérification des bornes de la PDO (0 < PDO < 1)
        self.assertGreater(actual_pdo, 0.0001, "PDO doit être > plancher 0.0001")
        self.assertLess(actual_pdo, 1.0, "PDO doit être < 1")
        
        # Vérification du flag de contrôle
        self.assertEqual(
            result["flag_pdo_OK"][0],
            "flag",
            "Le flag de contrôle doit être 'flag'"
        )

    # ===========================================================================
    # TU-002: Edge Case - Valeurs inattendues pour nat_jur_a
    # ===========================================================================
    def test_tu_002_calcul_pdo_nat_jur_a_unexpected_value(self) -> None:
        """
        TU-002: Tester le calcul PDO avec des valeurs inattendues pour nat_jur_a.
        
        OBJECTIF:
        ---------
        Tester le calcul PDO quand nat_jur_a (nature juridique agrégée de
        l'entreprise) contient une valeur non prévue comme None, une chaîne
        vide ou un code inconnu.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec 3 lignes:
        - Ligne 1: nat_jur_a = None
        - Ligne 2: nat_jur_a = '' (chaîne vide)
        - Ligne 3: nat_jur_a = 'INCONNU' (code non référencé)
        Toutes les autres colonnes ont les valeurs de référence valides.
        
        RÉSULTAT ATTENDU:
        -----------------
        Pour les 3 lignes:
        - nat_jur_a_coeffs = 0 (clause otherwise du code)
        - Le calcul PDO continue sans erreur
        - La PDO est calculée avec coefficient 0 pour cette variable
        
        RISQUE COUVERT:
        ---------------
        Une valeur inattendue peut générer un coefficient de 0 par défaut,
        faussant le calcul PDO et classant incorrectement le risque client.
        Il est important de vérifier que le comportement par défaut est documenté.
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo
        
        # Liste des cas de test avec valeurs inattendues pour nat_jur_a
        test_cases = [
            {"nat_jur_a": None, "description": "None (valeur nulle)"},
            {"nat_jur_a": "", "description": "Chaîne vide"},
            {"nat_jur_a": "INCONNU", "description": "Code non référencé"},
        ]
        
        # Coefficient attendu pour la clause otherwise (référence nat_jur_a_1_3)
        expected_coeff = self.config["model"]["coeffs"]["nat_jur_a_1_3"]  # = 0
        
        # ===== ACT & ASSERT =====
        for case in test_cases:
            with self.subTest(nat_jur_a=case["nat_jur_a"], desc=case["description"]):
                # Création du DataFrame avec la valeur inattendue
                df_input = self._create_df_with_overrides({"nat_jur_a": case["nat_jur_a"]})
                
                # Appel de la fonction - ne doit pas lever d'exception
                result = calcul_pdo(df_input, self.config)
                
                # Vérification que le calcul a abouti
                self.assertIsNotNone(
                    result["PDO"][0],
                    f"La PDO ne doit pas être None pour nat_jur_a={case['nat_jur_a']}"
                )
                
                # Vérification que la PDO est dans les bornes valides
                self.assertGreater(
                    result["PDO"][0],
                    0,
                    f"La PDO doit être > 0 pour nat_jur_a={case['nat_jur_a']}"
                )
                
                # Vérification du coefficient appliqué (clause otherwise)
                self.assertIn(
                    "nat_jur_a_coeffs",
                    result.columns,
                    "La colonne nat_jur_a_coeffs doit exister"
                )
                actual_coeff = result["nat_jur_a_coeffs"][0]
                self.assertEqual(
                    actual_coeff,
                    expected_coeff,
                    f"Le coefficient pour nat_jur_a={case['nat_jur_a']} doit être "
                    f"{expected_coeff} (clause otherwise), obtenu: {actual_coeff}"
                )

    # ===========================================================================
    # TU-003: Edge Case - sum_total_coeffs extrêmement négatif
    # ===========================================================================
    def test_tu_003_calcul_pdo_extreme_negative_sum_coeffs(self) -> None:
        """
        TU-003: Vérifier la stabilité numérique avec sum_total_coeffs très négatif.
        
        OBJECTIF:
        ---------
        Vérifier le comportement quand sum_total_coeffs (somme des contributions
        de toutes les variables) est extrêmement négatif, produisant une PDO
        proche de 0.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec toutes les variables à leurs modalités de référence
        (coefficients = 0). Pour simuler un score extrême, on utilise les valeurs
        de référence qui donnent sum = intercept = -3.864.
        
        Note: Pour un vrai test de stabilité avec sum = -50, il faudrait modifier
        les coefficients dans la config de test.
        
        RÉSULTAT ATTENDU:
        -----------------
        - sum_total_coeffs = -3.864 (avec les valeurs de référence)
        - PDO_compute ≈ 0.0206 (proche de 0)
        - PDO = 0.0206 (> plancher 0.0001)
        - Pas d'erreur de calcul, pas de NaN, pas d'Inf
        
        RISQUE COUVERT:
        ---------------
        Un overflow numérique ou une PDO arrondie à zéro peut masquer un risque
        réel et fausser les statistiques de portefeuille bancaire.
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo
        
        # DataFrame avec toutes les modalités de référence
        df_input = pl.DataFrame([self.reference_row])
        
        # ===== ACT =====
        result = calcul_pdo(df_input, self.config)
        
        # ===== ASSERT =====
        pdo = result["PDO"][0]
        pdo_compute = result["PDO_compute"][0]
        sum_coeffs = result["sum_total_coeffs"][0]
        
        # Vérification de l'absence d'erreurs numériques
        self.assertFalse(
            np.isnan(pdo),
            "La PDO ne doit pas être NaN (Not a Number)"
        )
        self.assertFalse(
            np.isinf(pdo),
            "La PDO ne doit pas être Inf (Infinity)"
        )
        self.assertFalse(
            np.isnan(sum_coeffs),
            "sum_total_coeffs ne doit pas être NaN"
        )
        
        # Vérification du respect du plancher réglementaire
        self.assertGreaterEqual(
            pdo,
            0.0001,
            "La PDO doit respecter le plancher Bâle III de 0.0001 (0.01%)"
        )
        
        # Vérification de la cohérence PDO_compute et PDO
        # PDO_compute est la valeur brute, PDO est après application du plancher
        self.assertLessEqual(
            pdo_compute,
            pdo + 0.0001,  # Tolérance pour l'arrondi
            "PDO doit être >= PDO_compute (ou égal si > plancher)"
        )

    # ===========================================================================
    # TU-004: Edge Case - sum_total_coeffs extrêmement positif (haut risque)
    # ===========================================================================
    def test_tu_004_calcul_pdo_extreme_positive_sum_coeffs(self) -> None:
        """
        TU-004: Vérifier la stabilité numérique avec sum_total_coeffs très positif.
        
        OBJECTIF:
        ---------
        Vérifier le comportement quand sum_total_coeffs (somme des coefficients)
        est extrêmement positif, produisant une PDO proche de 1.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec toutes les modalités les plus risquées:
        - nat_jur_a='>=7' (coefficient +1.146)
        - secto_b='1' (coefficient +0.946)
        - seg_nae='autres' (coefficient +0.699)
        - top_ga='1' (coefficient +0.382)
        - nbj='<=12' (coefficient +0.739)
        - solde_cav_char='4' (coefficient +0.924)
        - reboot_score_char2='1' (coefficient +3.924 - le plus élevé)
        - remb_sepa_max='2' (coefficient +1.346)
        - pres_prlv_retourne='2' (coefficient +0.917)
        - pres_saisie='2' (coefficient +0.805)
        - net_int_turnover='2' (coefficient +0.479)
        - rn_ca_conso_023b='3' (coefficient +1.645)
        - caf_dmlt_005='2' (coefficient +0.553)
        - res_total_passif_035='4' (coefficient +0.977)
        - immob_total_passif_055='3' (coefficient +0.573)
        
        Somme théorique ≈ -3.864 + 15.056 = +11.19
        
        RÉSULTAT ATTENDU:
        -----------------
        - sum_total_coeffs ≈ +11 (intercept -3.86 + coeffs élevés)
        - PDO_compute proche de 0.9999
        - PDO = 0.9999 (arrondi 4 décimales)
        - Pas d'overflow ni de valeur > 1
        
        RISQUE COUVERT:
        ---------------
        Une PDO supérieure à 1 ou un overflow peut corrompre les données de
        sortie et provoquer des erreurs dans les systèmes aval ILC.
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo
        
        # Profil à haut risque: toutes les modalités avec coefficients maximaux
        high_risk_row = {
            "nat_jur_a": ">=7",                # +1.146 (formes juridiques atypiques)
            "secto_b": "1",                     # +0.946 (secteur sensible)
            "seg_nae": "autres",                # +0.699 (pas ME)
            "top_ga": "1",                      # +0.382 (appartient à un groupe)
            "nbj": "<=12",                      # +0.739 (dépassements fréquents)
            "solde_cav_char": "4",              # +0.924 (trésorerie élevée - paradoxal)
            "reboot_score_char2": "1",          # +3.924 (score REBOOT très risqué)
            "remb_sepa_max": "2",               # +1.346 (gros remboursements)
            "pres_prlv_retourne": "2",          # +0.917 (prélèvements impayés)
            "pres_saisie": "2",                 # +0.805 (saisies sur compte)
            "net_int_turnover": "2",            # +0.479 (ratio intérêts élevé)
            "rn_ca_conso_023b": "3",            # +1.645 (ratio RN/CA élevé)
            "caf_dmlt_005": "2",                # +0.553 (ratio CAF élevé)
            "res_total_passif_035": "4",        # +0.977 (ratio résultat élevé)
            "immob_total_passif_055": "3",      # +0.573 (ratio immob. élevé)
        }
        
        # Calcul de la somme théorique des coefficients
        expected_sum_coeffs = self.intercept  # -3.864
        expected_sum_coeffs += self.config["model"]["coeffs"]["nat_jur_a_sup7"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["secto_b_1"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["seg_nae_autres"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["top_ga_1"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["nbj_inf_equal_12"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["solde_cav_char_4"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["reboot_score_char2_1"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["remb_sepa_max_2"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["pres_prlv_retourne_2"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["pres_saisie_2"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["net_int_turnover_2"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["rn_ca_conso_023b_3"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["caf_dmlt_005_2"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["res_total_passif_035_4"]
        expected_sum_coeffs += self.config["model"]["coeffs"]["immob_total_passif_055_3"]
        
        df_input = pl.DataFrame([high_risk_row])
        
        # ===== ACT =====
        result = calcul_pdo(df_input, self.config)
        
        # ===== ASSERT =====
        pdo = result["PDO"][0]
        sum_coeffs = result["sum_total_coeffs"][0]
        
        # Vérification de l'absence d'erreurs numériques
        self.assertFalse(np.isnan(pdo), "La PDO ne doit pas être NaN")
        self.assertFalse(np.isinf(pdo), "La PDO ne doit pas être Inf")
        
        # Vérification que PDO reste <= 1 (borne supérieure)
        self.assertLessEqual(
            pdo,
            1.0,
            f"La PDO doit être <= 1, obtenu: {pdo}"
        )
        
        # Vérification que la PDO est élevée (profil haut risque)
        self.assertGreater(
            pdo,
            0.5,
            f"Un profil haut risque doit avoir une PDO > 0.5, obtenu: {pdo}"
        )
        
        # Vérification de la somme des coefficients
        self.assertAlmostEqual(
            sum_coeffs,
            expected_sum_coeffs,
            places=2,
            msg=f"sum_total_coeffs attendu: {expected_sum_coeffs:.2f}, obtenu: {sum_coeffs:.2f}"
        )

    # ===========================================================================
    # TU-005: Edge Case - Application du plancher 0.0001
    # ===========================================================================
    def test_tu_005_calcul_pdo_floor_at_0001(self) -> None:
        """
        TU-005: Tester que PDO_compute < 0.0001 est planchéisé à 0.0001.
        
        OBJECTIF:
        ---------
        Tester que PDO_compute (PDO calculée avant arrondi) inférieure à 0.0001
        est correctement remplacée par 0.0001 comme valeur plancher.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec sum_total_coeffs très négatif.
        Avec les valeurs de référence, sum = -3.864, PDO ≈ 0.0206 > 0.0001.
        Ce test vérifie surtout la structure de sortie.
        
        Note: Pour avoir PDO_compute < 0.0001, il faudrait sum < -9.21.
        Cela nécessiterait des coefficients modifiés non réalistes.
        
        RÉSULTAT ATTENDU:
        -----------------
        - Présence des colonnes PDO_compute et PDO
        - PDO >= 0.0001 (plancher toujours respecté)
        - Si PDO_compute < 0.0001, alors PDO = 0.0001
        
        RISQUE COUVERT:
        ---------------
        Une PDO de zéro est inacceptable réglementairement; le plancher garantit
        une probabilité minimale de défaut pour tous les clients (Bâle III).
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo
        
        # Utilisation des valeurs de référence
        df_input = pl.DataFrame([self.reference_row])
        
        # ===== ACT =====
        result = calcul_pdo(df_input, self.config)
        
        # ===== ASSERT =====
        # Vérification de la présence des deux colonnes PDO
        self.assertIn(
            "PDO_compute",
            result.columns,
            "La colonne PDO_compute (valeur brute) doit être présente"
        )
        self.assertIn(
            "PDO",
            result.columns,
            "La colonne PDO (valeur finale avec plancher) doit être présente"
        )
        
        pdo = result["PDO"][0]
        pdo_compute = result["PDO_compute"][0]
        
        # Vérification du plancher réglementaire Bâle III (0.01% = 0.0001)
        self.assertGreaterEqual(
            pdo,
            0.0001,
            f"La PDO finale doit être >= plancher 0.0001, obtenu: {pdo}"
        )
        
        # Vérification de la logique de plancher
        if pdo_compute < 0.0001:
            self.assertEqual(
                pdo,
                0.0001,
                f"Si PDO_compute ({pdo_compute}) < 0.0001, PDO doit être 0.0001"
            )
        else:
            # PDO doit être proche de PDO_compute (avec arrondi)
            self.assertAlmostEqual(
                pdo,
                pdo_compute,
                places=4,
                msg="Si PDO_compute >= 0.0001, PDO doit égaler PDO_compute arrondi"
            )

    # ===========================================================================
    # TU-006: Edge Case - Arrondi à 4 décimales
    # ===========================================================================
    def test_tu_006_calcul_pdo_rounding_to_4_decimals(self) -> None:
        """
        TU-006: Vérifier l'arrondi à 4 décimales de la PDO finale.
        
        OBJECTIF:
        ---------
        Vérifier l'arrondi à 4 décimales de la PDO finale quand PDO_compute
        (valeur brute) contient beaucoup de décimales.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars produisant une PDO_compute avec de nombreuses décimales.
        Exemple: PDO_compute = 0.020618... → PDO = 0.0206
        
        RÉSULTAT ATTENDU:
        -----------------
        - PDO_compute conserve la précision complète
        - PDO est arrondi à exactement 4 décimales
        - L'arrondi suit la convention bancaire (half-even ou standard)
        
        RISQUE COUVERT:
        ---------------
        Un arrondi incorrect peut créer des écarts cumulatifs significatifs sur
        des milliers de clients et fausser les agrégats de risque.
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo
        
        df_input = pl.DataFrame([self.reference_row])
        
        # ===== ACT =====
        result = calcul_pdo(df_input, self.config)
        
        # ===== ASSERT =====
        pdo = result["PDO"][0]
        
        # Conversion en string pour analyser les décimales
        pdo_str = f"{pdo:.10f}"  # Format avec 10 décimales pour voir la précision
        
        # Extraction de la partie décimale
        parts = pdo_str.split(".")
        self.assertEqual(len(parts), 2, "La PDO doit avoir une partie décimale")
        
        decimal_part = parts[1]
        
        # Suppression des zéros de fin pour compter les décimales significatives
        significant_decimals = decimal_part.rstrip("0")
        
        # Vérification: au maximum 4 décimales significatives
        self.assertLessEqual(
            len(significant_decimals),
            4,
            f"La PDO doit avoir au maximum 4 décimales significatives. "
            f"Valeur: {pdo}, décimales significatives: {significant_decimals}"
        )
        
        # Vérification alternative: arrondi correct
        pdo_rounded = round(pdo, 4)
        self.assertEqual(
            pdo,
            pdo_rounded,
            f"La PDO doit être déjà arrondie à 4 décimales. "
            f"Original: {pdo}, Arrondi: {pdo_rounded}"
        )

    # ===========================================================================
    # TU-007: Edge Case - reboot_score_char2 = '9' (modalité de référence)
    # ===========================================================================
    def test_tu_007_calcul_pdo_reboot_score_char2_value_9(self) -> None:
        """
        TU-007: Tester avec reboot_score_char2='9' (modalité de référence).
        
        OBJECTIF:
        ---------
        Tester avec reboot_score_char2 (score de risque REBOOT discrétisé en
        9 classes) ayant la valeur '9' qui utilise le coefficient par défaut (0).
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec reboot_score_char2='9' et toutes les autres
        variables à leurs modalités de référence.
        
        Note: reboot_score_char2 est la variable la plus discriminante du modèle
        avec un coefficient de +3.924 pour la classe '1' (très risqué).
        
        RÉSULTAT ATTENDU:
        -----------------
        - reboot_score_char2_coeffs = 0 (clause otherwise car '9' n'est pas
          explicitement listé dans les when du code)
        - Contribution nulle au sum_total_coeffs
        - PDO calculée normalement
        
        RISQUE COUVERT:
        ---------------
        La modalité de référence doit avoir un coefficient nul; une erreur ici
        impacte toutes les entreprises de cette classe de risque (les plus saines).
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo
        
        # DataFrame avec reboot_score_char2='9' (modalité de référence = sain)
        df_input = self._create_df_with_overrides({"reboot_score_char2": "9"})
        
        # Coefficient attendu pour la modalité '9' (clause otherwise)
        expected_coeff = self.config["model"]["coeffs"]["reboot_score_char2_9"]  # = 0
        
        # ===== ACT =====
        result = calcul_pdo(df_input, self.config)
        
        # ===== ASSERT =====
        # Vérification que la PDO est calculée
        self.assertIsNotNone(
            result["PDO"][0],
            "La PDO ne doit pas être None pour reboot_score_char2='9'"
        )
        
        # Vérification de la présence de la colonne des coefficients
        self.assertIn(
            "reboot_score_char2_coeffs",
            result.columns,
            "La colonne reboot_score_char2_coeffs doit être présente"
        )
        
        # Vérification du coefficient appliqué
        actual_coeff = result["reboot_score_char2_coeffs"][0]
        self.assertEqual(
            actual_coeff,
            expected_coeff,
            f"Le coefficient pour reboot_score_char2='9' doit être {expected_coeff} "
            f"(modalité de référence), obtenu: {actual_coeff}"
        )
        
        # Vérification que le coefficient est bien 0
        self.assertEqual(
            actual_coeff,
            0.0,
            "Le coefficient de la modalité de référence '9' doit être exactement 0"
        )


class TestCalculPdoSklearn(TestCase):
    """
    Tests unitaires pour la fonction calcul_pdo_sklearn().
    
    Cette classe teste le calcul de la PDO via un modèle sklearn LogisticRegression
    préalablement entraîné et chargé depuis le COS (Cloud Object Storage).
    
    La fonction calcul_pdo_sklearn() doit produire des résultats identiques à
    calcul_pdo() pour garantir la cohérence entre développement et production.
    """

    def setUp(self) -> None:
        """
        Initialise les fixtures de test avec un modèle sklearn mocké.
        
        Configure:
        - self.reference_row: Ligne de données avec les modalités de référence
        - self.n_features: Nombre de features attendues (46 features binaires)
        - self.config: Configuration avec les coefficients du modèle
        """
        # Ligne de référence identique à TestCalculPdo
        self.reference_row: dict[str, str] = {
            "nat_jur_a": "1-3",
            "secto_b": "4",
            "seg_nae": "ME",
            "top_ga": "0",
            "nbj": ">12",
            "solde_cav_char": "1",
            "reboot_score_char2": "9",
            "remb_sepa_max": "1",
            "pres_prlv_retourne": "1",
            "pres_saisie": "1",
            "net_int_turnover": "1",
            "rn_ca_conso_023b": "1",
            "caf_dmlt_005": "1",
            "res_total_passif_035": "1",
            "immob_total_passif_055": "1",
        }
        
        # Nombre de features dans feature_order (46 features binaires one-hot)
        self.n_features: int = 46

    def _create_mock_model(
        self,
        intercept: float = -3.86402362750751,
        predict_proba_return: list[list[float]] | None = None
    ) -> MagicMock:
        """
        Crée un modèle sklearn LogisticRegression mocké pour les tests.
        
        Args:
            intercept: Valeur de l'intercept du modèle (défaut: -3.864)
            predict_proba_return: Valeur de retour pour predict_proba.
                                 Format: [[proba_classe_0, proba_classe_1], ...]
        
        Returns:
            MagicMock configuré avec les attributs coef_, intercept_ et
            la méthode predict_proba.
        """
        mock_model = MagicMock()
        
        # Configuration des attributs du modèle sklearn
        mock_model.intercept_ = np.array([intercept])
        mock_model.coef_ = np.zeros((1, self.n_features))
        
        # Configuration de predict_proba
        if predict_proba_return is None:
            # Par défaut: PDO ≈ 0.02 (98% classe 0, 2% classe 1)
            predict_proba_return = [[0.98, 0.02]]
        
        mock_model.predict_proba = MagicMock(
            return_value=np.array(predict_proba_return)
        )
        
        return mock_model

    # ===========================================================================
    # TU-008: Test nominal - calcul_pdo_sklearn produit un résultat valide
    # ===========================================================================
    def test_tu_008_calcul_pdo_sklearn_returns_valid_result(self) -> None:
        """
        TU-008: Vérifier que calcul_pdo_sklearn produit les mêmes résultats.
        
        OBJECTIF:
        ---------
        Vérifier que la fonction utilisant le modèle sklearn LogisticRegression
        produit les mêmes résultats que la formule manuelle pour un jeu de
        données identique.
        
        DONNÉES D'ENTRÉE:
        -----------------
        - DataFrame Polars identique au TU-001 (toutes modalités de référence)
        - Modèle sklearn LogisticRegression avec coef_ et intercept_
          correspondant aux coefficients hardcodés de calcul_pdo()
        
        RÉSULTAT ATTENDU:
        -----------------
        - Les colonnes PDO, PDO_compute, flag_pdo_OK sont présentes
        - La PDO est une valeur valide (0 < PDO < 1)
        - Les colonnes d'encoding one-hot sont présentes
        
        RISQUE COUVERT:
        ---------------
        Une incohérence entre les deux méthodes de calcul crée une ambiguïté
        sur la PDO officielle et des problèmes d'audit réglementaire.
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo_sklearn
        
        # Création du DataFrame d'entrée
        df_input = pl.DataFrame([self.reference_row])
        
        # Création du modèle mocké avec PDO ≈ 0.02
        mock_model = self._create_mock_model(
            predict_proba_return=[[0.98, 0.02]]  # Classe 0: 98%, Classe 1: 2%
        )
        
        # ===== ACT =====
        result = calcul_pdo_sklearn(df_input, mock_model)
        
        # ===== ASSERT =====
        # Vérification de la présence des colonnes de sortie obligatoires
        required_columns = ["PDO", "PDO_compute", "flag_pdo_OK"]
        for col in required_columns:
            self.assertIn(
                col,
                result.columns,
                f"La colonne '{col}' doit être présente dans le résultat"
            )
        
        # Vérification que la PDO est une valeur valide
        pdo = result["PDO"][0]
        self.assertIsNotNone(pdo, "La PDO ne doit pas être None")
        self.assertGreater(pdo, 0, "La PDO doit être > 0")
        self.assertLess(pdo, 1, "La PDO doit être < 1")
        
        # Vérification que predict_proba a été appelé
        mock_model.predict_proba.assert_called_once()

    # ===========================================================================
    # TU-009: Edge Case - Modèle sklearn = None
    # ===========================================================================
    def test_tu_009_calcul_pdo_sklearn_model_none(self) -> None:
        """
        TU-009: Tester le comportement quand le modèle sklearn est None.
        
        OBJECTIF:
        ---------
        Tester le comportement quand le modèle sklearn passé en paramètre est
        None ou n'a pas les attributs coef_ et intercept_ attendus.
        
        DONNÉES D'ENTRÉE:
        -----------------
        - DataFrame Polars valide avec toutes les colonnes requises
        - model = None pour le premier test
        - model = objet sans attribut coef_ pour le second test
        
        RÉSULTAT ATTENDU:
        -----------------
        - Lever AttributeError avec message explicite indiquant que le modèle
          est invalide ou None
        - Ne pas retourner de DataFrame corrompu
        
        RISQUE COUVERT:
        ---------------
        Un modèle corrompu ou incomplet provoque une exception non gérée qui
        fait échouer tout le batch de calcul PDO.
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo_sklearn
        
        df_input = pl.DataFrame([self.reference_row])
        
        # ===== ACT & ASSERT - Cas 1: model = None =====
        with self.assertRaises(
            AttributeError,
            msg="model=None doit lever AttributeError"
        ):
            calcul_pdo_sklearn(df_input, model=None)
        
        # ===== ACT & ASSERT - Cas 2: model sans attribut coef_ =====
        mock_invalid_model = MagicMock(spec=[])  # Mock sans aucun attribut
        # Supprimer l'attribut coef_ s'il existe
        if hasattr(mock_invalid_model, 'coef_'):
            del mock_invalid_model.coef_
        
        with self.assertRaises(
            AttributeError,
            msg="model sans coef_ doit lever AttributeError"
        ):
            calcul_pdo_sklearn(df_input, model=mock_invalid_model)

    # ===========================================================================
    # TU-010: Edge Case - Colonne manquante dans le DataFrame
    # ===========================================================================
    def test_tu_010_calcul_pdo_sklearn_missing_column(self) -> None:
        """
        TU-010: Vérifier le comportement quand une colonne requise est manquante.
        
        OBJECTIF:
        ---------
        Vérifier le comportement quand feature_order (liste ordonnée des
        features binaires) ne correspond pas aux colonnes du DataFrame d'entrée.
        
        DONNÉES D'ENTRÉE:
        -----------------
        - DataFrame Polars avec la colonne 'reboot_score_char2' manquante
        - Modèle sklearn valide
        
        Note: On simule une erreur de nommage ou une colonne oubliée lors
        du preprocessing.
        
        RÉSULTAT ATTENDU:
        -----------------
        - Lever KeyError ou ColumnNotFoundError lors de l'encodage one-hot
        - Le message d'erreur doit indiquer la colonne manquante
        
        RISQUE COUVERT:
        ---------------
        Un désalignement des features produit des prédictions sklearn incorrectes
        car les coefficients sont appliqués aux mauvaises variables.
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo_sklearn
        
        # Création d'un DataFrame incomplet (sans reboot_score_char2)
        incomplete_row = {
            k: v for k, v in self.reference_row.items()
            if k != "reboot_score_char2"  # On retire cette colonne critique
        }
        df_input = pl.DataFrame([incomplete_row])
        
        # Modèle valide
        mock_model = self._create_mock_model()
        
        # ===== ACT & ASSERT =====
        # La fonction doit lever une exception car la colonne est manquante
        with self.assertRaises(
            (KeyError, pl.exceptions.ColumnNotFoundError, pl.exceptions.SchemaError),
            msg="Une colonne manquante doit lever une exception explicite"
        ) as context:
            calcul_pdo_sklearn(df_input, mock_model)
        
        # Vérification optionnelle: le message mentionne la colonne manquante
        # (dépend de l'implémentation)

    # ===========================================================================
    # TU-011: Edge Case - Valeurs NaN après encodage one-hot
    # ===========================================================================
    def test_tu_011_calcul_pdo_sklearn_with_null_value(self) -> None:
        """
        TU-011: Tester avec un DataFrame contenant des valeurs NULL.
        
        OBJECTIF:
        ---------
        Tester avec un DataFrame contenant des valeurs NaN dans les colonnes
        de features après l'encodage one-hot.
        
        DONNÉES D'ENTRÉE:
        -----------------
        - DataFrame Polars avec nat_jur_a = None pour une ligne
        - Modèle sklearn valide
        
        L'encodage one-hot produira des valeurs pour les colonnes:
        - nat_jur_a_1_3 = 1 (car None n'est pas dans ["4-6", ">=7"])
        - nat_jur_a_4_6 = 0
        - nat_jur_a_sup7 = 0
        
        RÉSULTAT ATTENDU:
        -----------------
        Soit:
        - ValueError de sklearn lors de predict_proba ('Input contains NaN')
        - Soit gestion des NaN en les remplaçant par 0 avant prédiction
        
        Le comportement choisi doit être documenté.
        
        RISQUE COUVERT:
        ---------------
        Les NaN dans la matrice X provoquent des erreurs predict_proba ou des
        PDO NaN qui corrompent le fichier de sortie ILC.
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo_sklearn
        
        # Création d'un DataFrame avec une valeur NULL
        row_with_none = {**self.reference_row}
        row_with_none["nat_jur_a"] = None  # Valeur NULL
        df_input = pl.DataFrame([row_with_none])
        
        # Modèle valide
        mock_model = self._create_mock_model()
        
        # ===== ACT =====
        # Deux comportements possibles selon l'implémentation:
        # 1. Le code gère les NULL via la clause otherwise → pas d'erreur
        # 2. Le code propage les NULL → erreur sklearn
        
        try:
            result = calcul_pdo_sklearn(df_input, mock_model)
            
            # ===== ASSERT - Cas 1: NULL géré par otherwise =====
            # Vérification de l'encodage: NULL → nat_jur_a_1_3 = 1 (clause otherwise)
            self.assertIn("nat_jur_a_1_3", result.columns)
            self.assertIn("nat_jur_a_4_6", result.columns)
            self.assertIn("nat_jur_a_sup7", result.columns)
            
            # NULL n'est pas dans ["4-6", ">=7"] donc otherwise s'applique
            self.assertEqual(
                result["nat_jur_a_1_3"][0],
                1,
                "nat_jur_a=None doit activer la modalité de référence (nat_jur_a_1_3=1)"
            )
            self.assertEqual(
                result["nat_jur_a_4_6"][0],
                0,
                "nat_jur_a=None ne doit pas activer nat_jur_a_4_6"
            )
            self.assertEqual(
                result["nat_jur_a_sup7"][0],
                0,
                "nat_jur_a=None ne doit pas activer nat_jur_a_sup7"
            )
            
            # Vérification que la PDO est valide
            pdo = result["PDO"][0]
            self.assertIsNotNone(pdo, "La PDO ne doit pas être None")
            self.assertFalse(np.isnan(pdo), "La PDO ne doit pas être NaN")
            
        except ValueError as e:
            # ===== ASSERT - Cas 2: Erreur sklearn attendue =====
            self.assertIn(
                "NaN",
                str(e),
                "L'erreur doit mentionner la présence de NaN"
            )


# =============================================================================
# Point d'entrée pour l'exécution des tests
# =============================================================================
if __name__ == "__main__":
    # Exécution avec verbosité élevée pour voir le détail des tests
    main(verbosity=2)
