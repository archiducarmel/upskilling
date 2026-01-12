"""
Tests unitaires pour le module preprocessing_df_main.py

Ce module contient les tests pour la fonction df_encoding() qui encode
les variables brutes du référentiel entreprise en variables catégorielles
utilisables par le modèle PDO.

Les tests couvrent:
- TU-012 à TU-014: Encodage de c_njur_prsne (nature juridique) → c_njur_prsne_enc
- TU-015 à TU-016: Encodage de c_sectrl_1 (code sectoriel) → c_sectrl_1_enc
- TU-017 à TU-018: Calcul de top_ga (flag groupe d'affaires)

Auteur: Équipe MLOps - Fab IA
Date: Janvier 2026
Version: 1.0.0
"""

from unittest import TestCase, main
from typing import Any
import polars as pl


class TestDfEncodingNatureJuridique(TestCase):
    """
    Tests unitaires pour l'encodage de la nature juridique (c_njur_prsne).
    
    La variable c_njur_prsne est un code à 2 chiffres représentant la forme
    juridique de l'entreprise (SARL, SAS, SA, etc.). Elle est encodée en
    3 classes pour le modèle PDO:
    
    - "1-3": Formes juridiques les plus courantes et stables (SARL, SAS, SA)
             Codes: 26, 27, 33, 30
    - "4-6": Formes juridiques intermédiaires
             Codes: 20, 21, 29, 55, 59, 64
    - "7":   Formes juridiques atypiques ou rares (plus risquées)
             Codes: 22, 25, 56, 57, 58 + toute valeur non mappée (otherwise)
    
    Impact métier: Les entreprises avec des formes juridiques atypiques ("7")
    ont un coefficient de +1.146 dans le modèle, augmentant significativement
    leur PDO.
    """

    def setUp(self) -> None:
        """
        Initialise les fixtures de test avec les mappings de référence.
        
        Configure:
        - self.codes_class_1_3: Liste des codes nature juridique → classe "1-3"
        - self.codes_class_4_6: Liste des codes nature juridique → classe "4-6"
        - self.codes_class_7: Liste des codes nature juridique → classe "7"
        """
        # =======================================================================
        # Codes nature juridique selon la documentation INSEE et le code source
        # =======================================================================
        
        # Classe "1-3": Formes juridiques courantes (SARL, SAS, SA, EURL)
        # Coefficient PDO: 0 (référence)
        self.codes_class_1_3: list[str] = ["26", "27", "33", "30"]
        
        # Classe "4-6": Formes juridiques intermédiaires
        # Coefficient PDO: +0.2428
        self.codes_class_4_6: list[str] = ["20", "21", "29", "55", "59", "64"]
        
        # Classe "7": Formes juridiques atypiques (explicitement listées)
        # Coefficient PDO: +1.1462 (risque élevé)
        self.codes_class_7_explicit: list[str] = ["22", "25", "56", "57", "58"]
        
        # Colonnes minimales requises pour df_encoding()
        self.base_columns: list[str] = [
            "c_njur_prsne",      # Nature juridique (à encoder)
            "c_sectrl_1",        # Code sectoriel (requis par la fonction)
            "i_g_affre_rmpm",    # ID groupe d'affaires (requis par la fonction)
        ]

    def _create_test_df(self, c_njur_prsne_values: list[Any]) -> pl.DataFrame:
        """
        Crée un DataFrame de test avec les valeurs c_njur_prsne spécifiées.
        
        Args:
            c_njur_prsne_values: Liste des valeurs à tester pour c_njur_prsne
        
        Returns:
            DataFrame Polars avec les colonnes minimales requises
        """
        n_rows = len(c_njur_prsne_values)
        return pl.DataFrame({
            "c_njur_prsne": c_njur_prsne_values,
            # Valeurs par défaut pour les autres colonnes requises
            "c_sectrl_1": ["010010"] * n_rows,      # Code sectoriel valide → "4"
            "i_g_affre_rmpm": [None] * n_rows,      # Pas de groupe → top_ga="0"
        })

    # ===========================================================================
    # TU-012: Test nominal - Encodage correct de c_njur_prsne en 3 classes
    # ===========================================================================
    def test_tu_012_df_encoding_njur_prsne_nominal(self) -> None:
        """
        TU-012: Vérifier l'encodage correct de c_njur_prsne en 3 classes.
        
        OBJECTIF:
        ---------
        Vérifier que c_njur_prsne (code nature juridique à 2 chiffres) est
        correctement encodé en c_njur_prsne_enc avec les 3 classes '1-3',
        '4-6', '>=7'.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec 7 lignes couvrant les 3 classes:
        - Codes 26, 27, 33, 30 pour la classe "1-3"
        - Codes 20, 21, 29, 55, 59, 64 pour la classe "4-6"
        - Codes 22, 25, 56, 57, 58 pour la classe "7"
        
        RÉSULTAT ATTENDU:
        -----------------
        - Colonne c_njur_prsne_enc ajoutée avec les valeurs correctes
        - Codes 26, 27, 33, 30 → "1-3"
        - Codes 20, 21, 29, 55, 59, 64 → "4-6"
        - Codes 22, 25, 56, 57, 58 → "7"
        - Colonne check = "flag_df_main_OK"
        
        RISQUE COUVERT:
        ---------------
        Un mauvais mapping de la nature juridique fausse le coefficient dans
        le modèle PDO. Par exemple, classer une SARL (classe "1-3") en classe
        "7" ajoute +1.146 au score, surévaluant fortement le risque.
        """
        # ===== ARRANGE =====
        from preprocessing_df_main import df_encoding
        
        # Construction du DataFrame de test avec des codes de chaque classe
        # On prend quelques codes représentatifs de chaque classe
        test_codes = [
            # Classe "1-3" - 4 codes
            "26", "27", "33", "30",
            # Classe "4-6" - 6 codes
            "20", "21", "29", "55", "59", "64",
            # Classe "7" - 5 codes explicites
            "22", "25", "56", "57", "58",
        ]
        
        # Classes attendues correspondantes
        expected_classes = (
            ["1-3"] * 4 +      # 4 codes classe "1-3"
            ["4-6"] * 6 +      # 6 codes classe "4-6"
            ["7"] * 5          # 5 codes classe "7"
        )
        
        df_input = self._create_test_df(test_codes)
        
        # ===== ACT =====
        result = df_encoding(df_input)
        
        # ===== ASSERT =====
        # Vérification de la présence de la colonne encodée
        self.assertIn(
            "c_njur_prsne_enc",
            result.columns,
            "La colonne c_njur_prsne_enc doit être créée par df_encoding()"
        )
        
        # Vérification du flag de contrôle
        self.assertIn(
            "check",
            result.columns,
            "La colonne check doit être présente"
        )
        self.assertTrue(
            all(result["check"] == "flag_df_main_OK"),
            "Toutes les valeurs de check doivent être 'flag_df_main_OK'"
        )
        
        # Vérification de chaque encodage individuellement avec subTest
        actual_classes = result["c_njur_prsne_enc"].to_list()
        
        for i, (code, expected, actual) in enumerate(zip(test_codes, expected_classes, actual_classes)):
            with self.subTest(index=i, code=code, expected=expected):
                self.assertEqual(
                    actual,
                    expected,
                    f"Code nature juridique '{code}' doit être encodé en '{expected}', "
                    f"obtenu: '{actual}'"
                )
        
        # Vérification globale: nombre de lignes préservé
        self.assertEqual(
            len(result),
            len(df_input),
            "Le nombre de lignes doit être préservé après encodage"
        )

    # ===========================================================================
    # TU-013: Edge Case - c_njur_prsne avec valeurs None ou vides
    # ===========================================================================
    def test_tu_013_df_encoding_njur_prsne_null_or_empty(self) -> None:
        """
        TU-013: Tester l'encodage quand c_njur_prsne est None ou vide.
        
        OBJECTIF:
        ---------
        Tester l'encodage quand c_njur_prsne (code nature juridique) est None
        ou une chaîne vide au lieu d'un code valide.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec 3 lignes:
        - Ligne 1: c_njur_prsne = None
        - Ligne 2: c_njur_prsne = '' (chaîne vide)
        - Ligne 3: c_njur_prsne = '  ' (espaces)
        
        RÉSULTAT ATTENDU:
        -----------------
        - c_njur_prsne_enc = "7" pour les 3 lignes (clause otherwise)
        - Pas d'exception levée
        - Le traitement continue normalement
        
        RISQUE COUVERT:
        ---------------
        Des données manquantes ou mal formatées dans le référentiel peuvent
        provoquer des erreurs silencieuses. La clause otherwise assure un
        comportement déterministe mais peut masquer des problèmes de qualité
        de données.
        """
        # ===== ARRANGE =====
        from preprocessing_df_main import df_encoding
        
        # Cas de test avec valeurs nulles ou vides
        test_cases = [
            {"value": None, "description": "None (valeur nulle)"},
            {"value": "", "description": "Chaîne vide"},
            {"value": "  ", "description": "Espaces uniquement"},
        ]
        
        # La clause otherwise renvoie "7" pour toute valeur non mappée
        expected_class = "7"
        
        # ===== ACT & ASSERT =====
        for case in test_cases:
            with self.subTest(value=case["value"], desc=case["description"]):
                # Création du DataFrame avec la valeur de test
                df_input = self._create_test_df([case["value"]])
                
                # Appel de la fonction - ne doit pas lever d'exception
                try:
                    result = df_encoding(df_input)
                except Exception as e:
                    self.fail(
                        f"df_encoding() a levé une exception pour "
                        f"c_njur_prsne={case['value']!r}: {e}"
                    )
                
                # Vérification de l'encodage (clause otherwise → "7")
                actual_class = result["c_njur_prsne_enc"][0]
                self.assertEqual(
                    actual_class,
                    expected_class,
                    f"c_njur_prsne={case['value']!r} ({case['description']}) "
                    f"doit être encodé en '{expected_class}' (clause otherwise), "
                    f"obtenu: '{actual_class}'"
                )
                
                # Vérification que le flag de contrôle est présent
                self.assertEqual(
                    result["check"][0],
                    "flag_df_main_OK",
                    "Le flag de contrôle doit être présent même pour valeurs invalides"
                )

    # ===========================================================================
    # TU-014: Edge Case - c_njur_prsne avec code inconnu
    # ===========================================================================
    def test_tu_014_df_encoding_njur_prsne_unknown_code(self) -> None:
        """
        TU-014: Vérifier l'encodage avec un code nature juridique inconnu.
        
        OBJECTIF:
        ---------
        Vérifier l'encodage avec un c_njur_prsne (code nature juridique)
        inconnu comme '99' ou 'XX' non présent dans les listes de mapping.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec 2 lignes:
        - c_njur_prsne = '99' (code numérique inconnu)
        - c_njur_prsne = 'XX' (code alphanumérique invalide)
        
        RÉSULTAT ATTENDU:
        -----------------
        - c_njur_prsne_enc = "7" pour les 2 lignes (clause otherwise)
        - Le code "7" est la valeur par défaut pour tout code non reconnu
        
        RISQUE COUVERT:
        ---------------
        De nouveaux codes nature juridique peuvent être ajoutés par l'INSEE
        sans mise à jour du code. La clause otherwise assure que ces codes
        sont traités comme "atypiques" (classe "7"), ce qui est une approche
        prudente mais peut nécessiter une revue périodique des mappings.
        """
        # ===== ARRANGE =====
        from preprocessing_df_main import df_encoding
        
        # Codes inconnus à tester
        unknown_codes = [
            {"code": "99", "description": "Code numérique non référencé"},
            {"code": "XX", "description": "Code alphanumérique invalide"},
            {"code": "00", "description": "Code zéro"},
            {"code": "123", "description": "Code à 3 chiffres (format invalide)"},
        ]
        
        # La clause otherwise renvoie "7" pour toute valeur non mappée
        expected_class = "7"
        
        # ===== ACT & ASSERT =====
        for case in unknown_codes:
            with self.subTest(code=case["code"], desc=case["description"]):
                # Création du DataFrame avec le code inconnu
                df_input = self._create_test_df([case["code"]])
                
                # Appel de la fonction
                result = df_encoding(df_input)
                
                # Vérification de l'encodage (clause otherwise → "7")
                actual_class = result["c_njur_prsne_enc"][0]
                self.assertEqual(
                    actual_class,
                    expected_class,
                    f"Code nature juridique inconnu '{case['code']}' "
                    f"({case['description']}) doit être encodé en '{expected_class}' "
                    f"(clause otherwise), obtenu: '{actual_class}'"
                )
        
        # Test supplémentaire: vérifier que '99' n'est dans aucune liste
        all_known_codes = (
            self.codes_class_1_3 + 
            self.codes_class_4_6 + 
            self.codes_class_7_explicit
        )
        self.assertNotIn(
            "99",
            all_known_codes,
            "Le code '99' ne doit pas être dans les listes de mapping connues"
        )


class TestDfEncodingCodeSectoriel(TestCase):
    """
    Tests unitaires pour l'encodage du code sectoriel (c_sectrl_1).
    
    La variable c_sectrl_1 est un code à 6 chiffres représentant le secteur
    d'activité de l'entreprise. Elle est encodée en 4 classes:
    
    - "1": Secteurs sensibles (construction, immobilier, BTP)
           Coefficient PDO: +0.946
    - "2": Secteurs intermédiaires (commerce de gros, transports)
           Coefficient PDO: +0.946
    - "3": Secteurs variés (services, industrie) + valeur par défaut
           Coefficient PDO: +0.302
    - "4": Secteurs stables (agriculture, services aux personnes)
           Coefficient PDO: 0 (référence)
    
    Note importante: La chaîne vide "" est explicitement mappée à la classe "3"
    dans le code source (ligne 183).
    """

    def setUp(self) -> None:
        """
        Initialise les fixtures de test avec quelques codes de référence.
        """
        # Exemples de codes pour chaque classe (extraits du code source)
        self.sample_codes_class_1: list[str] = ["420053", "420051", "460010"]
        self.sample_codes_class_2: list[str] = ["360120", "500030", "470030"]
        self.sample_codes_class_3: list[str] = ["380020", "380030", "450080", ""]
        self.sample_codes_class_4: list[str] = ["010010", "140020", "300010"]

    def _create_test_df(
        self, 
        c_sectrl_1_values: list[Any],
        c_njur_prsne_values: list[str] | None = None
    ) -> pl.DataFrame:
        """
        Crée un DataFrame de test avec les valeurs c_sectrl_1 spécifiées.
        """
        n_rows = len(c_sectrl_1_values)
        
        if c_njur_prsne_values is None:
            c_njur_prsne_values = ["26"] * n_rows  # Code valide → "1-3"
        
        return pl.DataFrame({
            "c_njur_prsne": c_njur_prsne_values,
            "c_sectrl_1": c_sectrl_1_values,
            "i_g_affre_rmpm": [None] * n_rows,
        })

    # ===========================================================================
    # TU-015: Test nominal - Encodage correct de c_sectrl_1 en 4 classes
    # ===========================================================================
    def test_tu_015_df_encoding_sectrl_1_nominal(self) -> None:
        """
        TU-015: Vérifier l'encodage correct de c_sectrl_1 en 4 classes.
        
        OBJECTIF:
        ---------
        Vérifier que c_sectrl_1 (code sectoriel à 6 chiffres) est correctement
        encodé en c_sectrl_1_enc avec les 4 classes '1', '2', '3', '4'.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec 4 lignes:
        - c_sectrl_1 = '420053' (classe 1 - BTP/Construction)
        - c_sectrl_1 = '360120' (classe 2 - Commerce/Transport)
        - c_sectrl_1 = '380020' (classe 3 - Services/Industrie)
        - c_sectrl_1 = '010010' (classe 4 - Agriculture/Stable)
        
        RÉSULTAT ATTENDU:
        -----------------
        - Colonne c_sectrl_1_enc ajoutée
        - '420053' → "1"
        - '360120' → "2"
        - '380020' → "3"
        - '010010' → "4"
        
        RISQUE COUVERT:
        ---------------
        Le secteur d'activité est un facteur de risque important. Un mauvais
        mapping peut affecter le coefficient de +0.946 (classes 1-2) vs +0.302
        (classe 3) vs 0 (classe 4), soit un écart de près de 1 point de log-odds.
        """
        # ===== ARRANGE =====
        from preprocessing_df_main import df_encoding
        
        # Codes sectoriels de test (un par classe)
        test_codes = ["420053", "360120", "380020", "010010"]
        expected_classes = ["1", "2", "3", "4"]
        
        df_input = self._create_test_df(test_codes)
        
        # ===== ACT =====
        result = df_encoding(df_input)
        
        # ===== ASSERT =====
        # Vérification de la présence de la colonne encodée
        self.assertIn(
            "c_sectrl_1_enc",
            result.columns,
            "La colonne c_sectrl_1_enc doit être créée par df_encoding()"
        )
        
        # Vérification de chaque encodage
        actual_classes = result["c_sectrl_1_enc"].to_list()
        
        for code, expected, actual in zip(test_codes, expected_classes, actual_classes):
            with self.subTest(code=code, expected=expected):
                self.assertEqual(
                    actual,
                    expected,
                    f"Code sectoriel '{code}' doit être encodé en classe '{expected}', "
                    f"obtenu: '{actual}'"
                )

    # ===========================================================================
    # TU-016: Edge Case - c_sectrl_1 avec chaîne vide (mappée explicitement)
    # ===========================================================================
    def test_tu_016_df_encoding_sectrl_1_empty_string(self) -> None:
        """
        TU-016: Tester l'encodage sectoriel quand c_sectrl_1 est une chaîne vide.
        
        OBJECTIF:
        ---------
        Tester l'encodage sectoriel quand c_sectrl_1 (code sectoriel) est une
        chaîne vide, ce qui est explicitement mappé à la classe '3'.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec 1 ligne: c_sectrl_1 = '' (chaîne vide)
        
        Note importante: Contrairement à c_njur_prsne où "" va dans otherwise,
        pour c_sectrl_1 la chaîne vide "" est EXPLICITEMENT listée dans les
        codes de la classe "3" (ligne 183 du code source).
        
        RÉSULTAT ATTENDU:
        -----------------
        - c_sectrl_1_enc = '3'
        - Car "" est dans la liste is_in([...,'']) de la condition classe '3'
        - Ce n'est PAS traité comme NULL ou comme otherwise
        
        RISQUE COUVERT:
        ---------------
        Des codes sectoriels manquants (chaînes vides) doivent être gérés
        de manière déterministe. Le choix de les mapper à la classe "3"
        (coefficient +0.302) est un choix métier documenté.
        """
        # ===== ARRANGE =====
        from preprocessing_df_main import df_encoding
        
        # Chaîne vide explicitement dans la liste classe "3"
        df_input = self._create_test_df([""])
        
        # ===== ACT =====
        result = df_encoding(df_input)
        
        # ===== ASSERT =====
        actual_class = result["c_sectrl_1_enc"][0]
        expected_class = "3"
        
        self.assertEqual(
            actual_class,
            expected_class,
            f"Code sectoriel vide '' doit être encodé en classe '{expected_class}' "
            f"(mapping explicite, pas otherwise), obtenu: '{actual_class}'"
        )
        
        # Vérification supplémentaire: ce n'est pas le comportement otherwise
        # Le otherwise de c_sectrl_1 renvoie aussi "3", mais ici c'est explicite
        # On vérifie que la chaîne vide est bien dans la liste de la classe 3
        # (ce test documente le comportement intentionnel)
        self.assertIsNotNone(
            actual_class,
            "Le résultat ne doit pas être None pour une chaîne vide"
        )


class TestDfEncodingTopGa(TestCase):
    """
    Tests unitaires pour le calcul du flag top_ga (appartenance groupe d'affaires).
    
    La variable top_ga indique si l'entreprise appartient à un groupe d'affaires:
    - "0": Entreprise indépendante (i_g_affre_rmpm est NULL)
           Coefficient PDO: 0 (référence)
    - "1": Appartient à un groupe (i_g_affre_rmpm est non NULL)
           Coefficient PDO: +0.382
    
    ATTENTION: Le code utilise is_null() qui ne détecte que les vraies valeurs
    NULL. Une chaîne vide "" ou des espaces "   " ne sont PAS considérés comme
    NULL et donnent top_ga="1".
    """

    def _create_test_df(self, i_g_affre_rmpm_values: list[Any]) -> pl.DataFrame:
        """
        Crée un DataFrame de test avec les valeurs i_g_affre_rmpm spécifiées.
        """
        n_rows = len(i_g_affre_rmpm_values)
        return pl.DataFrame({
            "c_njur_prsne": ["26"] * n_rows,
            "c_sectrl_1": ["010010"] * n_rows,
            "i_g_affre_rmpm": i_g_affre_rmpm_values,
        })

    # ===========================================================================
    # TU-017: Test nominal - Calcul correct de top_ga selon i_g_affre_rmpm
    # ===========================================================================
    def test_tu_017_df_encoding_top_ga_nominal(self) -> None:
        """
        TU-017: Vérifier que top_ga est correctement calculé.
        
        OBJECTIF:
        ---------
        Vérifier que top_ga (flag d'appartenance à un groupe d'affaires) est
        '1' quand i_g_affre_rmpm (identifiant groupe) est non nul et '0' sinon.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec 3 lignes:
        - Ligne 1: i_g_affre_rmpm = 'GRP001' (entreprise dans un groupe)
        - Ligne 2: i_g_affre_rmpm = None (entreprise indépendante)
        - Ligne 3: i_g_affre_rmpm = 'GRP002' (entreprise dans un autre groupe)
        
        RÉSULTAT ATTENDU:
        -----------------
        - Colonne top_ga ajoutée
        - Ligne 1: top_ga = '1' (groupe GRP001)
        - Ligne 2: top_ga = '0' (pas de groupe, NULL)
        - Ligne 3: top_ga = '1' (groupe GRP002)
        - La condition is_null() détecte correctement None
        
        RISQUE COUVERT:
        ---------------
        L'appartenance à un groupe d'affaires augmente le risque (coefficient
        +0.382). Une erreur de détection peut sous-estimer le risque des
        entreprises appartenant à des groupes fragiles.
        """
        # ===== ARRANGE =====
        from preprocessing_df_main import df_encoding
        
        # Valeurs de test
        test_values = ["GRP001", None, "GRP002"]
        expected_top_ga = ["1", "0", "1"]
        
        df_input = self._create_test_df(test_values)
        
        # ===== ACT =====
        result = df_encoding(df_input)
        
        # ===== ASSERT =====
        # Vérification de la présence de la colonne
        self.assertIn(
            "top_ga",
            result.columns,
            "La colonne top_ga doit être créée par df_encoding()"
        )
        
        # Vérification de chaque valeur
        actual_top_ga = result["top_ga"].to_list()
        
        for i, (value, expected, actual) in enumerate(zip(test_values, expected_top_ga, actual_top_ga)):
            with self.subTest(index=i, i_g_affre_rmpm=value, expected=expected):
                self.assertEqual(
                    actual,
                    expected,
                    f"Ligne {i}: i_g_affre_rmpm={value!r} doit donner top_ga='{expected}', "
                    f"obtenu: '{actual}'"
                )
        
        # Vérification spécifique du comportement NULL
        null_mask = result["top_ga"] == "0"
        self.assertEqual(
            null_mask.sum(),
            1,
            "Exactement 1 ligne doit avoir top_ga='0' (celle avec NULL)"
        )

    # ===========================================================================
    # TU-018: Edge Case - top_ga avec chaîne vide (comportement potentiellement inattendu)
    # ===========================================================================
    def test_tu_018_df_encoding_top_ga_empty_string(self) -> None:
        """
        TU-018: Tester top_ga quand i_g_affre_rmpm contient une chaîne vide.
        
        OBJECTIF:
        ---------
        Tester top_ga quand i_g_affre_rmpm (identifiant du groupe d'affaires)
        contient une chaîne vide au lieu de None.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec 2 lignes:
        - Ligne 1: i_g_affre_rmpm = '' (chaîne vide)
        - Ligne 2: i_g_affre_rmpm = '   ' (espaces uniquement)
        
        RÉSULTAT ATTENDU:
        -----------------
        - top_ga = '1' pour les 2 lignes
        - Car '' et '   ' ne sont PAS None (is_null() retourne False)
        
        ATTENTION: Comportement potentiellement non voulu!
        Une chaîne vide "" représente sémantiquement "pas de groupe", mais
        techniquement elle n'est pas NULL et donnera top_ga="1".
        
        Ce test DOCUMENTE ce comportement qui devrait être revu:
        - Soit nettoyer les données en amont (remplacer "" par NULL)
        - Soit modifier la condition: is_null() OR col == ""
        
        RISQUE COUVERT:
        ---------------
        Des chaînes vides dans i_g_affre_rmpm peuvent provenir de problèmes
        de qualité de données. Le traitement actuel considère à tort ces
        entreprises comme appartenant à un groupe, ajoutant +0.382 à leur
        score PDO de manière incorrecte.
        """
        # ===== ARRANGE =====
        from preprocessing_df_main import df_encoding
        
        # Cas de test avec chaînes vides/espaces
        test_cases = [
            {"value": "", "description": "Chaîne vide"},
            {"value": "   ", "description": "Espaces uniquement"},
        ]
        
        # Comportement ACTUEL (potentiellement incorrect):
        # Une chaîne vide n'est pas NULL, donc top_ga = "1"
        expected_top_ga = "1"
        
        # ===== ACT & ASSERT =====
        for case in test_cases:
            with self.subTest(value=case["value"], desc=case["description"]):
                df_input = self._create_test_df([case["value"]])
                
                result = df_encoding(df_input)
                
                actual_top_ga = result["top_ga"][0]
                
                # Vérification du comportement actuel
                self.assertEqual(
                    actual_top_ga,
                    expected_top_ga,
                    f"i_g_affre_rmpm={case['value']!r} ({case['description']}) "
                    f"donne top_ga='{expected_top_ga}' car is_null() retourne False. "
                    f"ATTENTION: Ce comportement peut être non voulu!"
                )
        
        # ===== DOCUMENTATION DU COMPORTEMENT =====
        # Ce test documente une incohérence potentielle:
        # - NULL → top_ga = "0" (correct: pas de groupe)
        # - ""   → top_ga = "1" (incorrect: devrait être "0")
        # 
        # Recommandation: Ajouter une condition OR ou nettoyer les données
        # Exemple de correction dans le code source:
        #   pl.when(pl.col("i_g_affre_rmpm").is_null() | (pl.col("i_g_affre_rmpm") == ""))
        #   .then(pl.lit("0"))
        #   .otherwise(pl.lit("1"))
        
        # Test de non-régression: vérifier que None donne bien "0"
        df_with_none = self._create_test_df([None])
        result_none = df_encoding(df_with_none)
        self.assertEqual(
            result_none["top_ga"][0],
            "0",
            "None doit donner top_ga='0' (comportement de référence)"
        )


class TestDfEncodingIntegration(TestCase):
    """
    Tests d'intégration pour df_encoding() vérifiant le comportement global.
    """

    def test_df_encoding_all_columns_created(self) -> None:
        """
        Vérifier que toutes les colonnes attendues sont créées par df_encoding().
        """
        # ===== ARRANGE =====
        from preprocessing_df_main import df_encoding
        
        df_input = pl.DataFrame({
            "c_njur_prsne": ["26"],
            "c_sectrl_1": ["420053"],
            "i_g_affre_rmpm": ["GRP001"],
        })
        
        # ===== ACT =====
        result = df_encoding(df_input)
        
        # ===== ASSERT =====
        expected_new_columns = [
            "c_njur_prsne_enc",  # Nature juridique encodée
            "c_sectrl_1_enc",    # Code sectoriel encodé
            "top_ga",            # Flag groupe d'affaires
            "check",             # Flag de contrôle
        ]
        
        for col in expected_new_columns:
            self.assertIn(
                col,
                result.columns,
                f"La colonne '{col}' doit être créée par df_encoding()"
            )

    def test_df_encoding_preserves_original_columns(self) -> None:
        """
        Vérifier que les colonnes originales sont préservées après encodage.
        """
        # ===== ARRANGE =====
        from preprocessing_df_main import df_encoding
        
        df_input = pl.DataFrame({
            "c_njur_prsne": ["26", "20"],
            "c_sectrl_1": ["420053", "010010"],
            "i_g_affre_rmpm": ["GRP001", None],
            "autre_colonne": ["val1", "val2"],  # Colonne supplémentaire
        })
        
        original_columns = df_input.columns
        
        # ===== ACT =====
        result = df_encoding(df_input)
        
        # ===== ASSERT =====
        for col in original_columns:
            self.assertIn(
                col,
                result.columns,
                f"La colonne originale '{col}' doit être préservée"
            )


# =============================================================================
# Point d'entrée pour l'exécution des tests
# =============================================================================
if __name__ == "__main__":
    # Exécution avec verbosité élevée pour voir le détail des tests
    main(verbosity=2)
