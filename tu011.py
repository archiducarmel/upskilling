# ===========================================================================
    # TU-011: Edge Case - DataFrame avec valeurs NULL
    # ===========================================================================
    def test_tu_011_calcul_pdo_sklearn_with_null_value(self) -> None:
        """
        TU-011: Tester avec un DataFrame contenant des valeurs NULL.
        
        OBJECTIF:
        ---------
        Tester avec un DataFrame contenant des valeurs NULL dans les colonnes
        de features.
        
        DONNÉES D'ENTRÉE:
        -----------------
        - DataFrame Polars avec nat_jur_a = None pour une ligne
        - Modèle sklearn valide
        
        RÉSULTAT ATTENDU:
        -----------------
        L'encodage one-hot avec une valeur NULL produit:
        - nat_jur_a_1_3 = 0 (car None != "1-3")
        - nat_jur_a_4_6 = 0 (car None n'est pas dans ["4-6"])
        - nat_jur_a_sup7 = 0 (car None n'est pas dans [">=7"])
        
        ⚠️ ATTENTION: Toutes les colonnes one-hot sont à 0 !
        Cela signifie que le modèle ne reçoit aucune information sur
        la variable nat_jur_a, ce qui peut fausser la prédiction.
        
        Ce comportement devrait être documenté ou corrigé:
        - Option 1: Imputer la valeur NULL par la modalité la plus fréquente
        - Option 2: Exclure les lignes avec NULL du calcul
        - Option 3: Lever une erreur pour signaler les données manquantes
        
        RISQUE COUVERT:
        ---------------
        Les NULL non gérés peuvent produire des PDO incorrectes car le modèle
        n'a pas d'information sur les variables manquantes.
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
        # Le code doit gérer les NULL sans lever d'exception
        try:
            result = calcul_pdo_sklearn(df_input, mock_model)
        except Exception as e:
            self.fail(
                f"calcul_pdo_sklearn() a levé une exception avec nat_jur_a=None: {e}. "
                f"Le code devrait gérer les NULL gracieusement."
            )
        
        # ===== ASSERT =====
        # Vérification que les colonnes one-hot existent
        self.assertIn("nat_jur_a_1_3", result.columns)
        self.assertIn("nat_jur_a_4_6", result.columns)
        self.assertIn("nat_jur_a_sup7", result.columns)
        
        # =======================================================================
        # COMPORTEMENT ACTUEL: NULL → toutes les colonnes one-hot = 0
        # =======================================================================
        # 
        # Quand nat_jur_a = None:
        # - is_in(["4-6"]) → False (None n'est pas dans la liste)
        # - is_in([">=7"]) → False (None n'est pas dans la liste)
        # - La modalité de référence "1-3" est encodée par défaut (pas de colonne)
        #   mais ici elle est explicitement à 0 car None != "1-3"
        #
        # Résultat: [nat_jur_a_1_3=0, nat_jur_a_4_6=0, nat_jur_a_sup7=0]
        # C'est équivalent à "aucune modalité", ce qui est problématique.
        # =======================================================================
        
        self.assertEqual(
            result["nat_jur_a_1_3"][0],
            0,
            "nat_jur_a=None donne nat_jur_a_1_3=0 (None != '1-3')"
        )
        self.assertEqual(
            result["nat_jur_a_4_6"][0],
            0,
            "nat_jur_a=None donne nat_jur_a_4_6=0 (None n'est pas dans ['4-6'])"
        )
        self.assertEqual(
            result["nat_jur_a_sup7"][0],
            0,
            "nat_jur_a=None donne nat_jur_a_sup7=0 (None n'est pas dans ['>=7'])"
        )
        
        # Vérification que la PDO est quand même calculée (pas d'erreur)
        self.assertIn("PDO", result.columns)
        pdo = result["PDO"][0]
        
        # La PDO doit être un nombre valide
        self.assertFalse(
            np.isnan(pdo),
            "La PDO ne doit pas être NaN même avec des valeurs NULL en entrée"
        )
        
        # =======================================================================
        # DOCUMENTATION DE L'ISSUE: Gestion des NULL
        # =======================================================================
        #
        # ⚠️ PROBLÈME IDENTIFIÉ:
        # Les valeurs NULL ne sont pas correctement gérées par l'encodage one-hot.
        # Toutes les colonnes one-hot sont à 0, ce qui est équivalent à
        # "aucune modalité connue".
        #
        # IMPACT:
        # - Le modèle fait une prédiction sans information sur cette variable
        # - La PDO peut être incorrecte
        #
        # CORRECTION RECOMMANDÉE:
        # Ajouter une clause de gestion des NULL dans l'encodage:
        #
        # ```python
        # # Option 1: Imputer par la modalité de référence
        # df = df.with_columns(
        #     pl.when(pl.col("nat_jur_a").is_null())
        #     .then(pl.lit("1-3"))  # Modalité de référence par défaut
        #     .otherwise(pl.col("nat_jur_a"))
        #     .alias("nat_jur_a")
        # )
        #
        # # Option 2: Lever une erreur
        # null_count = df["nat_jur_a"].null_count()
        # if null_count > 0:
        #     raise ValueError(f"{null_count} valeurs NULL dans nat_jur_a")
        # ```
        # =======================================================================
