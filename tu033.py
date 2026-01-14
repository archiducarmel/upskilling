# ===========================================================================
    # TU-033: Nominal - Déduplication déterministe (score le plus récent)
    # ===========================================================================
    def test_tu_033_add_reboot_features_deduplication_most_recent(self) -> None:
        """
        TU-033: Vérifier la déduplication déterministe avec conservation du score le plus récent.
        
        OBJECTIF:
        ---------
        Vérifier que lorsque plusieurs scores REBOOT existent pour la même
        entreprise, le score le plus RÉCENT (basé sur d_histo) est conservé.
        
        CONTEXTE DE LA CORRECTION:
        --------------------------
        Avant correction, le code utilisait `unique(keep='first')` sans tri
        préalable. L'ordre des lignes après `group_by().agg()` n'étant pas
        garanti en Polars, le comportement était NON DÉTERMINISTE :
        - Deux exécutions du batch pouvaient donner des résultats différents
        - Le score conservé était aléatoire parmi les scores disponibles
        
        La correction implémentée ajoute un tri explicite par d_histo (date
        historique) en ordre décroissant AVANT l'appel à `unique()` :
```python
        # AVANT (non déterministe):
        df_score_reboot = df_score_reboot.unique(subset=["i_uniq_kpi"], keep="first")
        
        # APRÈS (déterministe - score le plus récent):
        df_score_reboot = df_score_reboot.sort("d_histo", descending=True)
        df_score_reboot = df_score_reboot.unique(subset=["i_uniq_kpi"], keep="first")
```
        
        JUSTIFICATION MÉTIER:
        ---------------------
        Conserver le score REBOOT le plus récent est pertinent car :
        - Le score REBOOT est recalculé périodiquement (mensuel ou trimestriel)
        - Un score plus récent reflète mieux la situation actuelle de l'entreprise
        - Les anciennes notations peuvent être obsolètes suite à des événements
          (restructuration, changement d'activité, etc.)
        
        DONNÉES D'ENTRÉE:
        -----------------
        3 scores REBOOT pour la même entreprise (i_uniq_kpi='E001') avec des
        dates différentes (d_histo) :
        - Score 1.0 du 2024-01-01 (le plus ancien)
        - Score 2.0 du 2024-01-15 (intermédiaire)
        - Score 3.0 du 2024-01-31 (le plus récent) ← DOIT ÊTRE CONSERVÉ
        
        RÉSULTAT ATTENDU:
        -----------------
        Après tri par d_histo décroissant puis déduplication :
        - L'entreprise E001 doit avoir UN SEUL score
        - Ce score doit être 3.0 (celui du 2024-01-31, le plus récent)
        - Le comportement est DÉTERMINISTE (reproductible)
        
        RISQUE COUVERT:
        ---------------
        - Garantit la reproductibilité des résultats entre exécutions
        - Assure que le score le plus à jour est utilisé pour le calcul PDO
        - Évite d'utiliser des scores obsolètes qui fausseraient l'évaluation
        """
        # ===== ARRANGE =====
        from common.preprocessing.preprocessing_reboot import add_reboot_features
        
        # DataFrame principal avec 1 entreprise
        df_main = self._create_df_main(["E001"])
        
        # =====================================================================
        # Tableau REBOOT avec 3 scores pour la MÊME entreprise
        # Les colonnes de groupement (autres que d_histo) sont DIFFÉRENTES
        # pour éviter la sommation et forcer la déduplication
        # =====================================================================
        reboot_data = [
            {
                "i_uniq_kpi": "E001",
                "q_score": "1,0",              # Score le plus ANCIEN (à ignorer)
                "d_histo": "2024-01-01",       # Date la plus ancienne
                "c_int_modele": "011",
                "d_rev_notation": "2024-01-01",
                "c_not": "A",
                "c_type_prsne": "PM",
                "b_bddf_gestionnaire": "N",
            },
            {
                "i_uniq_kpi": "E001",
                "q_score": "2,0",              # Score INTERMÉDIAIRE (à ignorer)
                "d_histo": "2024-01-15",       # Date intermédiaire
                "c_int_modele": "011",
                "d_rev_notation": "2024-01-15",
                "c_not": "B",                  # Notation différente
                "c_type_prsne": "PM",
                "b_bddf_gestionnaire": "N",
            },
            {
                "i_uniq_kpi": "E001",
                "q_score": "3,0",              # Score le plus RÉCENT (À CONSERVER)
                "d_histo": "2024-01-31",       # Date la plus récente ✓
                "c_int_modele": "011",
                "d_rev_notation": "2024-01-31",
                "c_not": "C",                  # Notation différente
                "c_type_prsne": "PM",
                "b_bddf_gestionnaire": "N",
            },
        ]
        reboot = self._create_reboot(reboot_data, default_values={})
        
        # Le score attendu est celui de la date la plus récente (2024-01-31)
        expected_score = 3.0
        expected_date = "2024-01-31"
        
        # ===== ACT =====
        result = add_reboot_features(df_main, reboot)
        
        # ===== ASSERT =====
        # Vérification qu'il n'y a qu'une seule ligne pour E001
        self.assertEqual(
            len(result),
            1,
            "L'entreprise E001 doit apparaître exactement 1 fois après déduplication"
        )
        
        # Vérification que le score conservé est le plus RÉCENT (3.0)
        actual_score = result["reboot_score"][0]
        
        self.assertAlmostEqual(
            actual_score,
            expected_score,
            places=4,
            msg=f"Le score conservé doit être le plus récent ({expected_score}, "
                f"date {expected_date}). Obtenu: {actual_score}"
        )
        
        # Vérification que ce n'est PAS un des anciens scores
        self.assertNotAlmostEqual(
            actual_score,
            1.0,
            places=4,
            msg="Le score 1.0 (2024-01-01) ne doit PAS être conservé (trop ancien)"
        )
        self.assertNotAlmostEqual(
            actual_score,
            2.0,
            places=4,
            msg="Le score 2.0 (2024-01-15) ne doit PAS être conservé (pas le plus récent)"
        )
        
        # Vérification de la colonne d_histo (doit être la date la plus récente)
        if "d_histo" in result.columns:
            actual_date = result["d_histo"][0]
            self.assertEqual(
                actual_date,
                expected_date,
                f"La date conservée doit être la plus récente ({expected_date}). "
                f"Obtenu: {actual_date}"
            )

    # ===========================================================================
    # TU-033b: Test complémentaire - Reproductibilité (déterminisme)
    # ===========================================================================
    def test_tu_033b_add_reboot_features_deduplication_deterministic(self) -> None:
        """
        TU-033b: Vérifier que la déduplication est DÉTERMINISTE (reproductible).
        
        OBJECTIF:
        ---------
        Vérifier que plusieurs exécutions de la fonction avec les mêmes données
        produisent TOUJOURS le même résultat.
        
        Ce test est important car avant la correction, l'ordre après group_by()
        n'était pas garanti, rendant le résultat aléatoire.
        
        DONNÉES D'ENTRÉE:
        -----------------
        Mêmes données que TU-033, exécutées 5 fois de suite.
        
        RÉSULTAT ATTENDU:
        -----------------
        Les 5 exécutions doivent produire EXACTEMENT le même score (3.0).
        
        RISQUE COUVERT:
        ---------------
        Un comportement non déterministe peut :
        - Rendre le debugging impossible
        - Fausser les comparaisons entre versions
        - Créer des incohérences dans les rapports réglementaires
        """
        # ===== ARRANGE =====
        from common.preprocessing.preprocessing_reboot import add_reboot_features
        
        df_main = self._create_df_main(["E001"])
        
        reboot_data = [
            {"i_uniq_kpi": "E001", "q_score": "1,0", "d_histo": "2024-01-01"},
            {"i_uniq_kpi": "E001", "q_score": "2,0", "d_histo": "2024-01-15"},
            {"i_uniq_kpi": "E001", "q_score": "3,0", "d_histo": "2024-01-31"},
        ]
        reboot = self._create_reboot(reboot_data)
        
        expected_score = 3.0
        n_executions = 5
        
        # ===== ACT & ASSERT =====
        results = []
        for i in range(n_executions):
            result = add_reboot_features(df_main, reboot)
            actual_score = result["reboot_score"][0]
            results.append(actual_score)
            
            with self.subTest(execution=i + 1):
                self.assertAlmostEqual(
                    actual_score,
                    expected_score,
                    places=4,
                    msg=f"Exécution {i + 1}/{n_executions}: le score doit être "
                        f"{expected_score}, obtenu: {actual_score}"
                )
        
        # Vérification que tous les résultats sont identiques
        self.assertTrue(
            all(r == results[0] for r in results),
            f"Toutes les exécutions doivent produire le même résultat. "
            f"Résultats obtenus: {results}"
        )

    # ===========================================================================
    # TU-033c: Test complémentaire - Même date, scores différents
    # ===========================================================================
    def test_tu_033c_add_reboot_features_same_date_different_scores(self) -> None:
        """
        TU-033c: Vérifier le comportement quand plusieurs scores ont la MÊME date.
        
        OBJECTIF:
        ---------
        Vérifier le comportement de la déduplication quand plusieurs scores
        ont exactement la même date d_histo. Dans ce cas, le tri par date
        ne permet pas de départager et le comportement dépend de l'ordre
        initial des données (ou d'un critère secondaire si implémenté).
        
        DONNÉES D'ENTRÉE:
        -----------------
        3 scores REBOOT pour E001 avec la MÊME date :
        - Score 1.0 du 2024-01-15
        - Score 2.0 du 2024-01-15
        - Score 3.0 du 2024-01-15
        
        RÉSULTAT ATTENDU:
        -----------------
        Un seul score est conservé. Avec le comportement actuel (tri stable
        de Polars), le premier score dans l'ordre d'entrée après le group_by
        sera conservé.
        
        ATTENTION: Ce cas edge nécessite peut-être un critère de tri secondaire
        pour garantir un comportement parfaitement déterministe.
        
        RISQUE COUVERT:
        ---------------
        Identifier les cas limites où le tri par date seul ne suffit pas.
        """
        # ===== ARRANGE =====
        from common.preprocessing.preprocessing_reboot import add_reboot_features
        
        df_main = self._create_df_main(["E001"])
        
        # Tous les scores ont la MÊME date
        same_date = "2024-01-15"
        reboot_data = [
            {"i_uniq_kpi": "E001", "q_score": "1,0", "d_histo": same_date,
             "c_not": "A"},  # Différencier par c_not pour éviter la sommation
            {"i_uniq_kpi": "E001", "q_score": "2,0", "d_histo": same_date,
             "c_not": "B"},
            {"i_uniq_kpi": "E001", "q_score": "3,0", "d_histo": same_date,
             "c_not": "C"},
        ]
        reboot = self._create_reboot(reboot_data)
        
        # ===== ACT =====
        result = add_reboot_features(df_main, reboot)
        
        # ===== ASSERT =====
        # Vérification qu'il n'y a qu'une seule ligne
        self.assertEqual(
            len(result),
            1,
            "Une seule ligne doit être conservée après déduplication"
        )
        
        # Le score doit être l'un des trois (comportement déterministe mais
        # dépendant de l'implémentation interne de Polars pour les égalités)
        actual_score = result["reboot_score"][0]
        valid_scores = {1.0, 2.0, 3.0}
        
        self.assertIn(
            actual_score,
            valid_scores,
            f"Le score doit être l'un des scores d'entrée {valid_scores}. "
            f"Obtenu: {actual_score}"
        )
        
        # ===== DOCUMENTATION =====
        # Si ce test échoue de manière non déterministe, il faudra ajouter
        # un critère de tri secondaire, par exemple:
        #
        # df_score_reboot = df_score_reboot.sort(
        #     ["d_histo", "q_score"],  # Tri secondaire par score
        #     descending=[True, True]   # Plus récent, puis plus élevé
        # )
        #
        # Ou utiliser une colonne de timestamp plus précise si disponible.

    # ===========================================================================
    # TU-033d: Test complémentaire - Sommation ET déduplication
    # ===========================================================================
    def test_tu_033d_add_reboot_features_sum_then_dedup_most_recent(self) -> None:
        """
        TU-033d: Vérifier le comportement combiné sommation + déduplication.
        
        OBJECTIF:
        ---------
        Vérifier le comportement quand :
        1. Plusieurs lignes ont les MÊMES colonnes de groupement → SOMMATION
        2. Après sommation, plusieurs groupes existent pour la même entreprise
           → DÉDUPLICATION (score le plus récent)
        
        Ce test vérifie l'interaction entre les deux mécanismes.
        
        DONNÉES D'ENTRÉE:
        -----------------
        5 scores REBOOT pour E001 :
        - Groupe 1 (2024-01-01, notation A): scores 1.0 et 2.0 → somme = 3.0
        - Groupe 2 (2024-01-15, notation B): score 4.0 → somme = 4.0
        - Groupe 3 (2024-01-31, notation C): scores 5.0 et 6.0 → somme = 11.0 ← PLUS RÉCENT
        
        RÉSULTAT ATTENDU:
        -----------------
        - Le groupe le plus récent (2024-01-31) est conservé
        - Le score final est la SOMME de ce groupe: 5.0 + 6.0 = 11.0
        """
        # ===== ARRANGE =====
        from common.preprocessing.preprocessing_reboot import add_reboot_features
        
        df_main = self._create_df_main(["E001"])
        
        # Définition des groupes avec colonnes de groupement identiques
        # au sein de chaque groupe (pour déclencher la sommation)
        group1_base = {
            "i_uniq_kpi": "E001",
            "d_histo": "2024-01-01",
            "c_int_modele": "011",
            "d_rev_notation": "2024-01-01",
            "c_not": "A",
            "c_type_prsne": "PM",
            "b_bddf_gestionnaire": "N",
        }
        group2_base = {
            "i_uniq_kpi": "E001",
            "d_histo": "2024-01-15",
            "c_int_modele": "011",
            "d_rev_notation": "2024-01-15",
            "c_not": "B",  # Différent → nouveau groupe
            "c_type_prsne": "PM",
            "b_bddf_gestionnaire": "N",
        }
        group3_base = {
            "i_uniq_kpi": "E001",
            "d_histo": "2024-01-31",  # Plus récent
            "c_int_modele": "011",
            "d_rev_notation": "2024-01-31",
            "c_not": "C",  # Différent → nouveau groupe
            "c_type_prsne": "PM",
            "b_bddf_gestionnaire": "N",
        }
        
        reboot_data = [
            # Groupe 1: sera sommé (1.0 + 2.0 = 3.0)
            {**group1_base, "q_score": "1,0"},
            {**group1_base, "q_score": "2,0"},
            # Groupe 2: score unique (4.0)
            {**group2_base, "q_score": "4,0"},
            # Groupe 3 (plus récent): sera sommé (5.0 + 6.0 = 11.0) ← CONSERVÉ
            {**group3_base, "q_score": "5,0"},
            {**group3_base, "q_score": "6,0"},
        ]
        reboot = self._create_reboot(reboot_data, default_values={})
        
        # Le score attendu est la somme du groupe le plus récent
        expected_score = 5.0 + 6.0  # = 11.0
        
        # ===== ACT =====
        result = add_reboot_features(df_main, reboot)
        
        # ===== ASSERT =====
        self.assertEqual(
            len(result),
            1,
            "Une seule ligne doit être conservée pour E001"
        )
        
        actual_score = result["reboot_score"][0]
        
        self.assertAlmostEqual(
            actual_score,
            expected_score,
            places=4,
            msg=f"Le score doit être la somme du groupe le plus récent "
                f"({expected_score}). Obtenu: {actual_score}"
        )
        
        # Vérification que ce n'est pas un autre groupe
        self.assertNotAlmostEqual(
            actual_score,
            3.0,  # Groupe 1 (sommé mais pas le plus récent)
            places=4,
            msg="Le groupe du 2024-01-01 (somme=3.0) ne doit PAS être conservé"
        )
        self.assertNotAlmostEqual(
            actual_score,
            4.0,  # Groupe 2 (pas le plus récent)
            places=4,
            msg="Le groupe du 2024-01-15 (score=4.0) ne doit PAS être conservé"
        )
