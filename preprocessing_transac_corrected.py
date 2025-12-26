import polars as pl


def add_transac_features(df_main: pl.DataFrame, donnees_transac: pl.DataFrame) -> pl.DataFrame:
    """
    Preprocess data for PDO prediction : encoding transaction features and add to df_main.
    
    VERSION CORRIGÉE : Sans unpivot/pivot pour éviter les bugs de certaines versions de Polars.
    Approche manuelle avec des agrégations séparées par catégorie.
    
    Colonnes créées:
        - interets__netamount, interets__nops, interets__min_amount, interets__max_amount
        - turnover__netamount, turnover__nops, turnover__min_amount, turnover__max_amount  
        - prlv_sepa_retourne__netamount, prlv_sepa_retourne__nops, prlv_sepa_retourne__min_amount, prlv_sepa_retourne__max_amount
        - rembt_prlv_sepa__netamount, rembt_prlv_sepa__nops, rembt_prlv_sepa__min_amount, rembt_prlv_sepa__max_amount
        - saisie__netamount, saisie__nops, saisie__min_amount, saisie__max_amount
        - nops (total)
        - remb_sepa_max, pres_prlv_retourne, pres_saisie, net_int_turnover (features métier)
    """
    
    # =========================================================================
    # STEP 1: Cast des colonnes numériques à l'entrée
    # Les données Starburst arrivent parfois en Decimal, il faut les convertir
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
            donnees_transac = donnees_transac.with_columns(
                pl.col(col).cast(dtype, strict=False)
            )
    
    # =========================================================================
    # STEP 2: Création de agg_category (regroupement de catégories)
    # Note: saisie__ regroupe attri_blocage ET atd_tres_pub
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
    # STEP 3: Filtrer uniquement les catégories utilisées par le modèle
    # =========================================================================
    categories_to_keep = [
        "interets__", 
        "turnover__", 
        "prlv_sepa_retourne__", 
        "rembt_prlv_sepa__", 
        "saisie__"
    ]
    donnees_transac_filtered = donnees_transac.filter(
        pl.col("agg_category").is_in(categories_to_keep)
    )

    # =========================================================================
    # STEP 4: Calculer nops (nombre total d'opérations) par i_uniq_kpi
    # =========================================================================
    df_nops = donnees_transac_filtered.group_by("i_uniq_kpi").agg(
        pl.col("nops_total").sum().alias("nops")
    )

    # =========================================================================
    # STEP 5: Fonction d'agrégation par catégorie
    # Reproduit exactement le comportement du code original:
    # group_by([i_uniq_kpi, agg_category]).agg([sum(netamount), sum(nops_category), sum(min_amount), sum(max_amount)])
    # =========================================================================
    def aggregate_category(df: pl.DataFrame, category: str, prefix: str) -> pl.DataFrame:
        """
        Agrège les données pour une catégorie spécifique.
        
        Args:
            df: DataFrame filtré contenant les transactions
            category: Valeur de agg_category à filtrer (ex: "interets__")
            prefix: Préfixe pour les noms de colonnes (ex: "interets__")
        
        Returns:
            DataFrame avec colonnes: i_uniq_kpi, {prefix}netamount, {prefix}nops, {prefix}min_amount, {prefix}max_amount
        """
        return (
            df.filter(pl.col("agg_category") == category)
            .group_by("i_uniq_kpi")
            .agg([
                pl.col("netamount").sum().alias(f"{prefix}netamount"),
                pl.col("nops_category").sum().alias(f"{prefix}nops"),
                pl.col("min_amount").sum().alias(f"{prefix}min_amount"),
                pl.col("max_amount").sum().alias(f"{prefix}max_amount"),
            ])
        )
    
    # =========================================================================
    # STEP 6: Agrégation pour chaque catégorie
    # =========================================================================
    df_interets = aggregate_category(donnees_transac_filtered, "interets__", "interets__")
    df_turnover = aggregate_category(donnees_transac_filtered, "turnover__", "turnover__")
    df_prlv_retourne = aggregate_category(donnees_transac_filtered, "prlv_sepa_retourne__", "prlv_sepa_retourne__")
    df_rembt_prlv = aggregate_category(donnees_transac_filtered, "rembt_prlv_sepa__", "rembt_prlv_sepa__")
    df_saisie = aggregate_category(donnees_transac_filtered, "saisie__", "saisie__")
    
    # =========================================================================
    # STEP 7: Jointure de toutes les catégories
    # On part de la liste des i_uniq_kpi uniques pour s'assurer de ne perdre personne
    # Les LEFT JOINs mettront NULL pour les catégories absentes (comportement identique au pivot)
    # =========================================================================
    df_transac = donnees_transac_filtered.select("i_uniq_kpi").unique()
    
    df_transac = df_transac.join(df_interets, on="i_uniq_kpi", how="left")
    df_transac = df_transac.join(df_turnover, on="i_uniq_kpi", how="left")
    df_transac = df_transac.join(df_prlv_retourne, on="i_uniq_kpi", how="left")
    df_transac = df_transac.join(df_rembt_prlv, on="i_uniq_kpi", how="left")
    df_transac = df_transac.join(df_saisie, on="i_uniq_kpi", how="left")
    df_transac = df_transac.join(df_nops, on="i_uniq_kpi", how="left")
    
    # =========================================================================
    # STEP 8: Calcul des features métier
    # =========================================================================
    
    # remb_sepa_max : montant max remboursement prélèvement SEPA > seuil
    df_transac = df_transac.with_columns(
        pl.when(pl.col("rembt_prlv_sepa__max_amount") > 3493.57007)
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("remb_sepa_max")
    )

    # pres_prlv_retourne : présence de prélèvement SEPA retourné
    df_transac = df_transac.with_columns(
        pl.when(pl.col("prlv_sepa_retourne__nops") > 0)
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("pres_prlv_retourne")
    )

    # pres_saisie : Présence de saisie arrêt ou ATD
    df_transac = df_transac.with_columns(
        pl.when(pl.col("saisie__nops") > 0)
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("pres_saisie")
    )

    # net_interets_sur_turnover : ratio intérêts débiteurs / turnover
    df_transac = df_transac.with_columns(
        pl.when(pl.col("interets__netamount").is_null())
        .then(pl.lit(0.0))
        .when(pl.col("interets__netamount") == 0)
        .then(pl.lit(0.0))
        .when(pl.col("turnover__netamount").is_null())
        .then(pl.lit(0.0))
        .when(pl.col("turnover__netamount") == 0)
        .then(pl.lit(0.0))
        .otherwise(
            pl.col("interets__netamount").cast(pl.Float64) / 
            pl.col("turnover__netamount").cast(pl.Float64)
        )
        .alias("net_interets_sur_turnover")
    )
    
    # net_int_turnover : indicateur binaire basé sur le ratio et le nombre d'opérations
    df_transac = df_transac.with_columns(
        pl.when(
            (pl.col("nops") >= 60)
            & (pl.col("net_interets_sur_turnover").is_not_null())
            & (pl.col("net_interets_sur_turnover") < -0.00143675995)
        )
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("net_int_turnover")
    )

    # =========================================================================
    # STEP 9: Dédoublonnage et jointure finale avec df_main
    # =========================================================================
    df_transac = df_transac.unique(subset=["i_uniq_kpi"], keep="first")
    df_main = df_main.join(df_transac, on="i_uniq_kpi", how="left")

    return df_main.with_columns(pl.lit("OK").alias("flag_transac"))
