import polars as pl


def add_transac_features(df_main: pl.DataFrame, donnees_transac: pl.DataFrame) -> pl.DataFrame:
    """Preprocess data for PDO prediction : encoding transaction features and add to df_main.
    
    VERSION OPTIMISÉE : Un seul scan avec agrégations conditionnelles.
    Gain de performance estimé : ~75%
    """
    
    # =========================================================================
    # STEP 1: Cast des colonnes numériques (INCHANGÉ)
    # =========================================================================
    numeric_cols_to_cast = {
        "netamount": pl.Float64,
        "nops_category": pl.Float64,
        "min_amount": pl.Float64,
        "max_amount": pl.Float64,
        "nops_total": pl.Float64,
    }
    for col, dtype in numeric_cols_to_cast.items():
        if col in donnees_transac.columns:
            donnees_transac = donnees_transac.with_columns(pl.col(col).cast(dtype, strict=False))

    # =========================================================================
    # STEP 2: Création de agg_category (INCHANGÉ)
    # =========================================================================
    donnees_transac = donnees_transac.with_columns(
        pl.when(pl.col("category") == "interets")
        .then(pl.lit("interets__"))
        .when(pl.col("category") == "turnover")
        .then(pl.lit("turnover__"))
        .when(pl.col("category").is_in(["prlv_sepa_retourne"]))
        .then(pl.lit("prlv_sepa_retourne__"))
        .when(pl.col("category").is_in(["rembt_prlv_sepa"]))
        .then(pl.lit("rembt_prlv_sepa__"))
        .when(pl.col("category").is_in(["attri_blocage", "atd_tres_pub"]))
        .then(pl.lit("saisie__"))
        .otherwise(pl.col("category"))
        .alias("agg_category")
    )

    # =========================================================================
    # STEP 3: Filtrer uniquement les catégories utilisées (INCHANGÉ)
    # =========================================================================
    categories_to_keep = ["interets__", "turnover__", "prlv_sepa_retourne__", "rembt_prlv_sepa__", "saisie__"]
    donnees_transac_filtered = donnees_transac.filter(pl.col("agg_category").is_in(categories_to_keep))

    # =========================================================================
    # STEP 4-5-6-7 FUSIONNÉS : UN SEUL GROUP_BY AVEC AGRÉGATIONS CONDITIONNELLES ✅
    # =========================================================================
    
    # Liste des catégories à agréger
    categories = ["interets__", "turnover__", "prlv_sepa_retourne__", "rembt_prlv_sepa__", "saisie__"]
    
    # Construction dynamique des expressions d'agrégation
    agg_expressions = []
    
    # Pour chaque catégorie, on crée 4 agrégations conditionnelles
    for cat in categories:
        # Filtre : ne prendre que les lignes où agg_category == cat
        cat_filter = pl.col("agg_category") == cat
        
        # Agrégations avec filtre intégré
        agg_expressions.extend([
            # Somme des montants nets pour cette catégorie uniquement
            pl.col("netamount").filter(cat_filter).sum().alias(f"{cat}netamount"),
            # Somme du nombre d'opérations pour cette catégorie
            pl.col("nops_category").filter(cat_filter).sum().alias(f"{cat}nops"),
            # Somme des min (pour compatibilité avec l'ancien code)
            pl.col("min_amount").filter(cat_filter).sum().alias(f"{cat}min_amount"),
            # Somme des max (pour compatibilité avec l'ancien code)
            pl.col("max_amount").filter(cat_filter).sum().alias(f"{cat}max_amount"),
        ])
    
    # Ajouter nops total (toutes catégories confondues)
    agg_expressions.append(pl.col("nops_total").sum().alias("nops"))
    
    # ✅ UN SEUL SCAN, UN SEUL GROUP_BY, ZÉRO JOINTURE
    df_transac = (
        donnees_transac_filtered
        .group_by("i_uniq_kpi")
        .agg(agg_expressions)
    )

    # =========================================================================
    # STEP 8: Calcul des features métier (LÉGÈREMENT OPTIMISÉ - regroupé)
    # =========================================================================
    df_transac = df_transac.with_columns([
        # remb_sepa_max : montant max remboursement > seuil
        pl.when(pl.col("rembt_prlv_sepa__max_amount") > 3493.57007)
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("remb_sepa_max_enc"),
        
        # pres_prlv_retourne : présence de prélèvement retourné
        pl.when(pl.col("prlv_sepa_retourne__nops") > 0)
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("pres_prlv_retourne_enc"),
        
        # pres_saisie : présence de saisie
        pl.when(pl.col("saisie__nops") > 0)
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("pres_saisie_enc"),
        
        # net_interets_sur_turnover : ratio intérêts / turnover
        pl.when(pl.col("interets__netamount").is_null())
        .then(pl.lit(0.0))
        .when(pl.col("interets__netamount") == 0)
        .then(pl.lit(0.0))
        .when(pl.col("turnover__netamount").is_null())
        .then(pl.lit(0.0))
        .when(pl.col("turnover__netamount") == 0)
        .then(pl.lit(0.0))
        .otherwise(pl.col("interets__netamount").cast(pl.Float64) / pl.col("turnover__netamount").cast(pl.Float64))
        .alias("net_interets_sur_turnover"),
    ])

    # net_int_turnover_enc dépend de net_interets_sur_turnover, donc séparé
    df_transac = df_transac.with_columns(
        pl.when(
            (pl.col("nops") >= 60)
            & (pl.col("net_interets_sur_turnover").is_not_null())
            & (pl.col("net_interets_sur_turnover") < -0.00143675995)
        )
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("net_int_turnover_enc")
    )

    # =========================================================================
    # STEP 9: Dédoublonnage et jointure finale (INCHANGÉ)
    # =========================================================================
    df_transac = df_transac.unique(subset=["i_uniq_kpi"], keep="first")
    df_main = df_main.join(df_transac, on="i_uniq_kpi", how="left")

    return df_main.with_columns(pl.lit("flag_transac_OK").alias("check"))
```

### ✅ Ce qui change dans le code APRÈS
```
donnees_transac_filtered (1M lignes)
         │
         └── group_by("i_uniq_kpi").agg([
                 netamount.filter(cat=="interets__").sum(),
                 netamount.filter(cat=="turnover__").sum(),
                 netamount.filter(cat=="prlv_sepa...").sum(),
                 ...
             ])
             
             → UN SEUL SCAN de 1M lignes
             → Résultat direct avec toutes les colonnes
             → ZÉRO jointure nécessaire
