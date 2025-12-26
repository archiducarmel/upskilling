import polars as pl


def add_transac_features(df_main: pl.DataFrame, donnees_transac: pl.DataFrame) -> pl.DataFrame:
    """Preprocess data for PDO prediction : encoding transaction features and add to df_main."""
    
    # === CORRECTION: Cast explicite des colonnes numériques dès l'entrée ===
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
    
    # Aggregate some categories
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

    # Keep only categories used by the model
    donnees_transac = donnees_transac.filter(
        pl.col("agg_category").is_in(
            ["interets__", "turnover__", "prlv_sepa_retourne__", "rembt_prlv_sepa__", "saisie__"]
        )
    )

    # Calculation amount/number of operations based on aggregated categories
    syn_donnees_transac = donnees_transac.group_by(["i_uniq_kpi", "agg_category"]).agg(
        [
            pl.col("netamount").sum().alias("netamount"),
            pl.col("nops_category").sum().alias("nops"),
            pl.col("min_amount").sum().alias("min_amount"),
            pl.col("max_amount").sum().alias("max_amount"),
        ]
    )

    df_nops = donnees_transac.group_by(["i_uniq_kpi"]).agg(
        [
            pl.col("nops_total").sum().alias("nops"),
        ]
    )

    # === CORRECTION: Cast explicite après group_by pour garantir les types ===
    syn_donnees_transac = syn_donnees_transac.cast({
        "netamount": pl.Float64,
        "nops": pl.Float64,
        "min_amount": pl.Float64,
        "max_amount": pl.Float64,
    })

    # Create df_transac via unpivot
    syn_donnees_transac_pivot = syn_donnees_transac.unpivot(
        index=["i_uniq_kpi", "agg_category"],
        on=["netamount", "nops", "min_amount", "max_amount"],
        variable_name="_NAME_",
        value_name="COL1",
    )
    
    # === CORRECTION: Cast COL1 en Float64 après unpivot ===
    syn_donnees_transac_pivot = syn_donnees_transac_pivot.with_columns(
        pl.col("COL1").cast(pl.Float64, strict=False)
    )
    
    # === CORRECTION: Utiliser concat_str au lieu de l'opérateur + ===
    syn_donnees_transac_pivot = syn_donnees_transac_pivot.with_columns(
        pl.concat_str([
            pl.col("agg_category").cast(pl.Utf8),
            pl.col("_NAME_").cast(pl.Utf8)
        ]).alias("agg_category_NAME")
    )
    
    # Pivot avec aggregate_function="sum" (maintenant COL1 est bien numérique)
    syn_donnees_transac_pivot_final = syn_donnees_transac_pivot.pivot(
        on="agg_category_NAME",
        index="i_uniq_kpi",
        values="COL1",
        aggregate_function="sum",
    )
    df_transac = syn_donnees_transac_pivot_final.join(df_nops, on="i_uniq_kpi", how="left")

    # remb_sepa_max : montant max remboursement prélèvement SEPA
    df_transac = df_transac.with_columns(
        pl.when(pl.col("rembt_prlv_sepa__max_amount") > 3493.57007)
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("remb_sepa_max")
    )

    # pres_prlv_retourne : présence prélèvement SEPA retourné
    df_transac = df_transac.with_columns(
        pl.when(pl.col("prlv_sepa_retourne__nops") > 0)
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("pres_prlv_retourne")
    )

    # pres_saisie : Présence saisie arrêt ou ATD
    df_transac = df_transac.with_columns(
        pl.when(pl.col("saisie__nops") > 0).then(pl.lit("1")).otherwise(pl.lit("2")).alias("pres_saisie")
    )

    # net_int_turnover : Somme intérêts débiteurs/ turnover
    df_transac = df_transac.with_columns(
        [
            pl.when(pl.col("interets__netamount").is_null())
            .then(pl.lit("0"))
            .when(pl.col("interets__netamount") == 0)
            .then(pl.lit("0"))
            .when(pl.col("turnover__netamount").is_null())
            .then(pl.lit("0"))
            .when(pl.col("turnover__netamount") == 0)
            .then(pl.lit("0"))
            .otherwise(pl.col("interets__netamount").cast(pl.Float64) / pl.col("turnover__netamount").cast(pl.Float64))
            .alias("net_interets_sur_turnover"),
        ]
    )
    df_transac = df_transac.cast({"net_interets_sur_turnover": pl.Float64})
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

    df_transac = df_transac.unique(subset=["i_uniq_kpi"], keep="first")
    df_main = df_main.join(df_transac, on="i_uniq_kpi", how="left")

    return df_main.with_columns(pl.lit("OK").alias("flag_transac"))
