# ===========================================================================
    # TU-004: Edge Case - Profil haut risque (modalités de référence)
    # ===========================================================================
    def test_tu_004_calcul_pdo_high_risk_profile_reference_modalities(self) -> None:
        """
        TU-004: Vérifier qu'un profil haut risque produit une PDO élevée.
        
        OBJECTIF:
        ---------
        Vérifier le comportement avec un profil à HAUT RISQUE, c'est-à-dire
        une entreprise ayant toutes les MODALITÉS DE RÉFÉRENCE.
        
        CONTEXTE IMPORTANT - LOGIQUE INVERSÉE DES COEFFICIENTS:
        -------------------------------------------------------
        Le modèle de régression logistique a été calibré pour prédire
        P(NON-DÉFAUT), pas P(défaut). Cela signifie que :
        
        - Les coefficients POSITIFS augmentent P(non-défaut), donc DIMINUENT le risque
        - Les coefficients NÉGATIFS diminuent P(non-défaut), donc AUGMENTENT le risque
        - Les MODALITÉS DE RÉFÉRENCE (coefficient = 0) représentent le RISQUE ÉLEVÉ
        - L'INTERCEPT NÉGATIF (-3.864) représente la baseline risquée
        
        La formule du code : PDO = 1 - σ(z) = 1 - 1/(1+exp(-z))
        
        Avec z = sum_total_coeffs :
        - Si z est NÉGATIF (proche de l'intercept seul) → PDO ÉLEVÉE (risque)
        - Si z est POSITIF (intercept + coeffs positifs) → PDO FAIBLE (sain)
        
        Tableau de correspondance modalités / risque :
        
        | Variable         | Modalité référence (RISQUÉE) | Modalité protectrice (coeff > 0) |
        |------------------|------------------------------|----------------------------------|
        | nat_jur_a        | "1-3" (coeff=0)              | ">=7" (+1.146) ✓ plus sûr        |
        | secto_b          | "4" (coeff=0)                | "1" (+0.946) ✓ plus sûr          |
        | seg_nae          | "ME" (coeff=0)               | "autres" (+0.699) ✓ plus sûr     |
        | top_ga           | "0" (coeff=0)                | "1" (+0.382) ✓ plus sûr          |
        | nbj              | ">12" (coeff=0)              | "<=12" (+0.739) ✓ plus sûr       |
        | solde_cav_char   | "1" (coeff=0)                | "4" (+0.924) ✓ plus sûr          |
        | reboot_score_char2| "9" (coeff=0)               | "1" (+3.924) ✓ plus sûr          |
        | remb_sepa_max    | "1" (coeff=0)                | "2" (+1.346) ✓ plus sûr          |
        | pres_prlv_retourne| "1" (coeff=0)               | "2" (+0.917) ✓ plus sûr          |
        | pres_saisie      | "1" (coeff=0)                | "2" (+0.805) ✓ plus sûr          |
        | net_int_turnover | "1" (coeff=0)                | "2" (+0.479) ✓ plus sûr          |
        | rn_ca_conso_023b | "1" (coeff=0)                | "3" (+1.645) ✓ plus sûr          |
        | caf_dmlt_005     | "1" (coeff=0)                | "2" (+0.553) ✓ plus sûr          |
        | res_total_passif_035| "1" (coeff=0)             | "4" (+0.977) ✓ plus sûr          |
        | immob_total_passif_055| "1" (coeff=0)           | "3" (+0.573) ✓ plus sûr          |
        
        ATTENTION: Cette logique est CONTRE-INTUITIVE par rapport aux noms
        des modalités. Par exemple, reboot_score_char2="1" (score REBOOT le
        plus bas) a un coefficient de +3.924, ce qui le rend PROTECTEUR.
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec TOUTES les modalités de RÉFÉRENCE (coefficient = 0):
        - nat_jur_a = "1-3"
        - secto_b = "4"
        - seg_nae = "ME"
        - top_ga = "0"
        - nbj = ">12"
        - solde_cav_char = "1"
        - reboot_score_char2 = "9"
        - remb_sepa_max = "1"
        - pres_prlv_retourne = "1"
        - pres_saisie = "1"
        - net_int_turnover = "1"
        - rn_ca_conso_023b = "1"
        - caf_dmlt_005 = "1"
        - res_total_passif_035 = "1"
        - immob_total_passif_055 = "1"
        
        Somme des coefficients = intercept seul = -3.864
        
        RÉSULTAT ATTENDU:
        -----------------
        - sum_total_coeffs ≈ -3.864 (uniquement l'intercept)
        - PDO = 1 - σ(-3.864) = 1 - 1/(1+exp(3.864)) = 1 - 0.0206 ≈ 0.9794
        - PDO après arrondi = 0.9794 (≈ 98% de risque de défaut)
        
        RISQUE COUVERT:
        ---------------
        Ce test vérifie que la logique inversée des coefficients est correctement
        implémentée. Une entreprise avec toutes les modalités de référence
        (aucun facteur protecteur) doit avoir une PDO très élevée.
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo
        
        # =====================================================================
        # Profil HAUT RISQUE : toutes les modalités de RÉFÉRENCE
        # Ces modalités ont un coefficient = 0, donc seul l'intercept compte
        # =====================================================================
        high_risk_profile = {
            "nat_jur_a": "1-3",              # Référence (coeff=0) - pas de protection
            "secto_b": "4",                   # Référence (coeff=0) - pas de protection
            "seg_nae": "ME",                  # Référence (coeff=0) - pas de protection
            "top_ga": "0",                    # Référence (coeff=0) - pas de protection
            "nbj": ">12",                     # Référence (coeff=0) - pas de protection
            "solde_cav_char": "1",            # Référence (coeff=0) - pas de protection
            "reboot_score_char2": "9",        # Référence (coeff=0) - pas de protection
            "remb_sepa_max": "1",             # Référence (coeff=0) - pas de protection
            "pres_prlv_retourne": "1",        # Référence (coeff=0) - pas de protection
            "pres_saisie": "1",               # Référence (coeff=0) - pas de protection
            "net_int_turnover": "1",          # Référence (coeff=0) - pas de protection
            "rn_ca_conso_023b": "1",          # Référence (coeff=0) - pas de protection
            "caf_dmlt_005": "1",              # Référence (coeff=0) - pas de protection
            "res_total_passif_035": "1",      # Référence (coeff=0) - pas de protection
            "immob_total_passif_055": "1",    # Référence (coeff=0) - pas de protection
        }
        
        # La somme des coefficients = intercept seul (toutes les modalités = 0)
        expected_sum_coeffs = self.intercept  # -3.864
        
        # Calcul de la PDO attendue avec la formule : PDO = 1 - σ(z)
        # σ(-3.864) = 1/(1+exp(3.864)) ≈ 0.0206
        # PDO = 1 - 0.0206 ≈ 0.9794
        import math
        sigma_z = 1 / (1 + math.exp(-expected_sum_coeffs))  # σ(-3.864)
        expected_pdo = 1 - sigma_z  # ≈ 0.9794
        
        df_input = pl.DataFrame([high_risk_profile])
        
        # ===== ACT =====
        result = calcul_pdo(df_input, self.config)
        
        # ===== ASSERT =====
        pdo = result["PDO"][0]
        sum_coeffs = result["sum_total_coeffs"][0]
        
        # Vérification de l'absence d'erreurs numériques
        self.assertFalse(np.isnan(pdo), "La PDO ne doit pas être NaN")
        self.assertFalse(np.isinf(pdo), "La PDO ne doit pas être Inf")
        
        # Vérification que sum_total_coeffs ≈ intercept (≈ -3.864)
        self.assertAlmostEqual(
            sum_coeffs,
            expected_sum_coeffs,
            places=2,
            msg=f"Avec toutes les modalités de référence, sum_total_coeffs doit "
                f"être ≈ intercept ({expected_sum_coeffs}), obtenu: {sum_coeffs}"
        )
        
        # Vérification que sum_total_coeffs est NÉGATIF (profil risqué)
        self.assertLess(
            sum_coeffs,
            0,
            f"Un profil haut risque (modalités de référence) doit avoir "
            f"sum_total_coeffs < 0, obtenu: {sum_coeffs}"
        )
        
        # Vérification que la PDO est élevée (> 0.5 pour un profil risqué)
        self.assertGreater(
            pdo,
            0.5,
            f"Un profil haut risque (toutes modalités de référence) doit avoir "
            f"une PDO > 0.5, obtenu: {pdo}"
        )
        
        # Vérification que la PDO est proche de la valeur théorique (≈ 0.98)
        self.assertAlmostEqual(
            pdo,
            expected_pdo,
            places=2,
            msg=f"PDO attendue ≈ {expected_pdo:.4f}, obtenue: {pdo:.4f}"
        )
        
        # Vérification que PDO reste dans les bornes [0, 1]
        self.assertGreaterEqual(pdo, 0.0, "La PDO doit être >= 0")
        self.assertLessEqual(pdo, 1.0, "La PDO doit être <= 1")


    # ===========================================================================
    # TU-004b: Test complémentaire - Profil sain (modalités protectrices)
    # ===========================================================================
    def test_tu_004b_calcul_pdo_low_risk_profile_protective_modalities(self) -> None:
        """
        TU-004b: Vérifier qu'un profil sain produit une PDO faible.
        
        OBJECTIF:
        ---------
        Vérifier le comportement avec un profil SAIN, c'est-à-dire une
        entreprise ayant toutes les MODALITÉS PROTECTRICES (coefficients > 0).
        
        LOGIQUE DES COEFFICIENTS (RAPPEL):
        ----------------------------------
        Les coefficients sont calibrés pour P(NON-DÉFAUT):
        - Coefficient POSITIF → augmente P(non-défaut) → DIMINUE le risque
        - Plus la somme des coefficients est ÉLEVÉE, plus la PDO est FAIBLE
        
        DONNÉES D'ENTRÉE:
        -----------------
        DataFrame Polars avec TOUTES les modalités PROTECTRICES (coefficient > 0):
        - nat_jur_a = ">=7" (+1.146)
        - secto_b = "1" (+0.946)
        - seg_nae = "autres" (+0.699)
        - top_ga = "1" (+0.382)
        - nbj = "<=12" (+0.739)
        - solde_cav_char = "4" (+0.924)
        - reboot_score_char2 = "1" (+3.924)
        - remb_sepa_max = "2" (+1.346)
        - pres_prlv_retourne = "2" (+0.917)
        - pres_saisie = "2" (+0.805)
        - net_int_turnover = "2" (+0.479)
        - rn_ca_conso_023b = "3" (+1.645)
        - caf_dmlt_005 = "2" (+0.553)
        - res_total_passif_035 = "4" (+0.977)
        - immob_total_passif_055 = "3" (+0.573)
        
        Somme = -3.864 + 16.055 = +12.191
        
        RÉSULTAT ATTENDU:
        -----------------
        - sum_total_coeffs ≈ +12 (intercept + tous les coefficients positifs)
        - PDO = 1 - σ(12.191) = 1 - 0.99999... ≈ 0.0001 (floor)
        - PDO après floor = 0.0001 (très faible risque)
        
        RISQUE COUVERT:
        ---------------
        Ce test vérifie qu'une entreprise avec tous les facteurs protecteurs
        obtient bien une PDO très faible, proche du minimum.
        """
        # ===== ARRANGE =====
        from common.calcul_pdo import calcul_pdo
        
        # =====================================================================
        # Profil SAIN : toutes les modalités PROTECTRICES (coefficient > 0)
        # Ces modalités augmentent P(non-défaut), donc diminuent la PDO
        # =====================================================================
        low_risk_profile = {
            "nat_jur_a": ">=7",               # +1.146 (PROTECTEUR)
            "secto_b": "1",                    # +0.946 (PROTECTEUR)
            "seg_nae": "autres",               # +0.699 (PROTECTEUR)
            "top_ga": "1",                     # +0.382 (PROTECTEUR)
            "nbj": "<=12",                     # +0.739 (PROTECTEUR)
            "solde_cav_char": "4",             # +0.924 (PROTECTEUR)
            "reboot_score_char2": "1",         # +3.924 (PROTECTEUR - le plus fort)
            "remb_sepa_max": "2",              # +1.346 (PROTECTEUR)
            "pres_prlv_retourne": "2",         # +0.917 (PROTECTEUR)
            "pres_saisie": "2",                # +0.805 (PROTECTEUR)
            "net_int_turnover": "2",           # +0.479 (PROTECTEUR)
            "rn_ca_conso_023b": "3",           # +1.645 (PROTECTEUR)
            "caf_dmlt_005": "2",               # +0.553 (PROTECTEUR)
            "res_total_passif_035": "4",       # +0.977 (PROTECTEUR)
            "immob_total_passif_055": "3",     # +0.573 (PROTECTEUR)
        }
        
        # Calcul de la somme des coefficients
        expected_sum_coeffs = self.intercept  # -3.864
        expected_sum_coeffs += self.config["model"]["coeffs"]["nat_jur_a_sup7"]      # +1.146
        expected_sum_coeffs += self.config["model"]["coeffs"]["secto_b_1"]           # +0.946
        expected_sum_coeffs += self.config["model"]["coeffs"]["seg_nae_autres"]      # +0.699
        expected_sum_coeffs += self.config["model"]["coeffs"]["top_ga_1"]            # +0.382
        expected_sum_coeffs += self.config["model"]["coeffs"]["nbj_inf_equal_12"]    # +0.739
        expected_sum_coeffs += self.config["model"]["coeffs"]["solde_cav_char_4"]    # +0.924
        expected_sum_coeffs += self.config["model"]["coeffs"]["reboot_score_char2_1"]# +3.924
        expected_sum_coeffs += self.config["model"]["coeffs"]["remb_sepa_max_2"]     # +1.346
        expected_sum_coeffs += self.config["model"]["coeffs"]["pres_prlv_retourne_2"]# +0.917
        expected_sum_coeffs += self.config["model"]["coeffs"]["pres_saisie_2"]       # +0.805
        expected_sum_coeffs += self.config["model"]["coeffs"]["net_int_turnover_2"]  # +0.479
        expected_sum_coeffs += self.config["model"]["coeffs"]["rn_ca_conso_023b_3"]  # +1.645
        expected_sum_coeffs += self.config["model"]["coeffs"]["caf_dmlt_005_2"]      # +0.553
        expected_sum_coeffs += self.config["model"]["coeffs"]["res_total_passif_035_4"]# +0.977
        expected_sum_coeffs += self.config["model"]["coeffs"]["immob_total_passif_055_3"]# +0.573
        
        # PDO attendue avec la formule : PDO = 1 - σ(z)
        # σ(12.191) ≈ 0.99999...
        # PDO = 1 - 0.99999 ≈ 0.00001, mais floor à 0.0001
        expected_pdo_floor = 0.0001  # Floor appliqué par le code
        
        df_input = pl.DataFrame([low_risk_profile])
        
        # ===== ACT =====
        result = calcul_pdo(df_input, self.config)
        
        # ===== ASSERT =====
        pdo = result["PDO"][0]
        sum_coeffs = result["sum_total_coeffs"][0]
        
        # Vérification de l'absence d'erreurs numériques
        self.assertFalse(np.isnan(pdo), "La PDO ne doit pas être NaN")
        self.assertFalse(np.isinf(pdo), "La PDO ne doit pas être Inf")
        
        # Vérification que sum_total_coeffs est très POSITIF (profil protégé)
        self.assertGreater(
            sum_coeffs,
            10,
            f"Un profil sain (toutes modalités protectrices) doit avoir "
            f"sum_total_coeffs > 10, obtenu: {sum_coeffs}"
        )
        
        # Vérification de la somme des coefficients
        self.assertAlmostEqual(
            sum_coeffs,
            expected_sum_coeffs,
            places=2,
            msg=f"sum_total_coeffs attendu ≈ {expected_sum_coeffs:.2f}, obtenu: {sum_coeffs:.2f}"
        )
        
        # Vérification que la PDO est très faible (profil protégé)
        self.assertLess(
            pdo,
            0.01,
            f"Un profil sain (toutes modalités protectrices) doit avoir "
            f"une PDO très faible (< 0.01), obtenu: {pdo}"
        )
        
        # Vérification que la PDO est au floor (0.0001)
        self.assertEqual(
            pdo,
            expected_pdo_floor,
            f"La PDO doit être au floor ({expected_pdo_floor}), obtenu: {pdo}"
        )
