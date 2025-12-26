import polars as pl
from pathlib import Path

# Fichier de debug
DEBUG_FILE = Path("/mnt/code/debug_transac_full.txt")


def write_debug(msg: str, df: pl.DataFrame = None, mode: str = "a") -> None:
    """Écrit les infos de debug dans un fichier."""
    with open(DEBUG_FILE, mode, encoding="utf-8") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"{msg}\n")
        f.write(f"{'='*80}\n")
        if df is not None:
            f.write(f"Shape: {df.shape}\n")
            f.write(f"Colonnes: {df.columns}\n")
            f.write(f"Schema: {df.schema}\n")
            f.write(f"\nSample (5 lignes):\n{df.head(5)}\n")


def add_transac_features(df_main: pl.DataFrame, donnees_transac: pl.DataFrame) -> pl.DataFrame:
    """Preprocess data for PDO prediction : encoding transaction features and add to df_main."""
    
    # Initialiser le fichier de debug
    write_debug("=== DEBUT add_transac_features ===", mode="w")
    
    # =========================================================================
    # STEP 0: Données d'entrée
    # =========================================================================
    write_debug("STEP 0: donnees_transac EN ENTREE", donnees_transac)
    
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\nTypes des colonnes numériques attendues:\n")
        for col in ["netamount", "nops_category", "min_amount", "max_amount", "nops_total"]:
            if col in donnees_transac.columns:
                f.write(f"  {col}: {donnees_transac[col].dtype}\n")
            else:
                f.write(f"  {col}: COLONNE ABSENTE!\n")
    
    # =========================================================================
    # STEP 1: Cast des colonnes numériques à l'entrée
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
    
    write_debug("STEP 1: donnees_transac APRES CAST INITIAL", donnees_transac)
    
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\nTypes APRES cast:\n")
        for col in ["netamount", "nops_category", "min_amount", "max_amount", "nops_total"]:
            if col in donnees_transac.columns:
                f.write(f"  {col}: {donnees_transac[col].dtype}\n")
    
    # =========================================================================
    # STEP 2: Aggregate categories
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
    
    write_debug("STEP 2: donnees_transac APRES agg_category", donnees_transac)
    
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\nValeurs uniques de agg_category:\n")
        f.write(f"{donnees_transac.select('agg_category').unique()}\n")
    
    # =========================================================================
    # STEP 3: Filter categories
    # =========================================================================
    categories_to_keep = ["interets__", "turnover__", "prlv_sepa_retourne__", "rembt_prlv_sepa__", "saisie__"]
    donnees_transac = donnees_transac.filter(pl.col("agg_category").is_in(categories_to_keep))
    
    write_debug("STEP 3: donnees_transac APRES FILTRE", donnees_transac)
    
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\nNombre de lignes après filtre: {donnees_transac.height}\n")
        f.write(f"Valeurs uniques de agg_category après filtre:\n")
        f.write(f"{donnees_transac.select('agg_category').unique()}\n")
    
    # =========================================================================
    # STEP 4: Group by et agrégations
    # =========================================================================
    syn_donnees_transac = donnees_transac.group_by(["i_uniq_kpi", "agg_category"]).agg(
        [
            pl.col("netamount").sum().alias("netamount"),
            pl.col("nops_category").sum().alias("nops"),
            pl.col("min_amount").sum().alias("min_amount"),
            pl.col("max_amount").sum().alias("max_amount"),
        ]
    )
    
    write_debug("STEP 4: syn_donnees_transac APRES GROUP_BY", syn_donnees_transac)
    
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\nTypes après group_by:\n")
        for col in syn_donnees_transac.columns:
            f.write(f"  {col}: {syn_donnees_transac[col].dtype}\n")
    
    # =========================================================================
    # STEP 4b: df_nops
    # =========================================================================
    df_nops = donnees_transac.group_by(["i_uniq_kpi"]).agg(
        [
            pl.col("nops_total").sum().alias("nops"),
        ]
    )
    
    write_debug("STEP 4b: df_nops", df_nops)
    
    # =========================================================================
    # STEP 5: Cast après group_by
    # =========================================================================
    syn_donnees_transac = syn_donnees_transac.cast({
        "netamount": pl.Float64,
        "nops": pl.Float64,
        "min_amount": pl.Float64,
        "max_amount": pl.Float64,
    })
    
    write_debug("STEP 5: syn_donnees_transac APRES CAST", syn_donnees_transac)
    
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\nTypes après cast explicite:\n")
        for col in syn_donnees_transac.columns:
            f.write(f"  {col}: {syn_donnees_transac[col].dtype}\n")
    
    # =========================================================================
    # STEP 6: UNPIVOT - ÉTAPE CRITIQUE
    # =========================================================================
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write("STEP 6: AVANT UNPIVOT\n")
        f.write(f"Colonnes pour unpivot 'on': ['netamount', 'nops', 'min_amount', 'max_amount']\n")
        f.write(f"Colonnes pour unpivot 'index': ['i_uniq_kpi', 'agg_category']\n")
        f.write(f"{'='*80}\n")
    
    syn_donnees_transac_pivot = syn_donnees_transac.unpivot(
        index=["i_uniq_kpi", "agg_category"],
        on=["netamount", "nops", "min_amount", "max_amount"],
        variable_name="_NAME_",
        value_name="COL1",
    )
    
    write_debug("STEP 6: syn_donnees_transac_pivot APRES UNPIVOT", syn_donnees_transac_pivot)
    
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\n*** VERIFICATION CRITIQUE ***\n")
        f.write(f"Colonnes présentes: {syn_donnees_transac_pivot.columns}\n")
        f.write(f"\nType de _NAME_: {syn_donnees_transac_pivot['_NAME_'].dtype}\n")
        f.write(f"Type de COL1: {syn_donnees_transac_pivot['COL1'].dtype}\n")
        f.write(f"\nValeurs UNIQUES de _NAME_ (devrait être netamount, nops, min_amount, max_amount):\n")
        f.write(f"{syn_donnees_transac_pivot.select('_NAME_').unique()}\n")
        f.write(f"\nSample de _NAME_ (10 premières valeurs):\n")
        f.write(f"{syn_donnees_transac_pivot.select('_NAME_').head(10)}\n")
        f.write(f"\nSample de COL1 (10 premières valeurs):\n")
        f.write(f"{syn_donnees_transac_pivot.select('COL1').head(10)}\n")
    
    # =========================================================================
    # STEP 7: Cast COL1 en Float64
    # =========================================================================
    syn_donnees_transac_pivot = syn_donnees_transac_pivot.with_columns(
        pl.col("COL1").cast(pl.Float64, strict=False)
    )
    
    write_debug("STEP 7: APRES CAST COL1", syn_donnees_transac_pivot)
    
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\nType de COL1 après cast: {syn_donnees_transac_pivot['COL1'].dtype}\n")
    
    # =========================================================================
    # STEP 8: CONCAT_STR - ÉTAPE CRITIQUE
    # =========================================================================
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write("STEP 8: AVANT CONCAT_STR\n")
        f.write(f"On va concaténer: agg_category + _NAME_\n")
        f.write(f"Exemple attendu: 'turnover__' + 'netamount' = 'turnover__netamount'\n")
        f.write(f"{'='*80}\n")
    
    syn_donnees_transac_pivot = syn_donnees_transac_pivot.with_columns(
        pl.concat_str([
            pl.col("agg_category").cast(pl.Utf8),
            pl.col("_NAME_").cast(pl.Utf8)
        ]).alias("agg_category_NAME")
    )
    
    write_debug("STEP 8: APRES CONCAT_STR", syn_donnees_transac_pivot)
    
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\n*** VERIFICATION CRITIQUE ***\n")
        f.write(f"Type de agg_category_NAME: {syn_donnees_transac_pivot['agg_category_NAME'].dtype}\n")
        f.write(f"\nValeurs UNIQUES de agg_category_NAME:\n")
        unique_names = syn_donnees_transac_pivot.select('agg_category_NAME').unique()
        f.write(f"{unique_names}\n")
        f.write(f"\nNombre de valeurs uniques: {unique_names.height}\n")
        f.write(f"\nListe des valeurs uniques:\n")
        for val in unique_names['agg_category_NAME'].to_list():
            f.write(f"  - '{val}'\n")
    
    # =========================================================================
    # STEP 9: PIVOT - ÉTAPE CRITIQUE
    # =========================================================================
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write("STEP 9: AVANT PIVOT\n")
        f.write(f"on='agg_category_NAME'\n")
        f.write(f"index='i_uniq_kpi'\n")
        f.write(f"values='COL1'\n")
        f.write(f"aggregate_function='sum'\n")
        f.write(f"{'='*80}\n")
    
    syn_donnees_transac_pivot_final = syn_donnees_transac_pivot.pivot(
        on="agg_category_NAME",
        index="i_uniq_kpi",
        values="COL1",
        aggregate_function="sum",
    )
    
    write_debug("STEP 9: syn_donnees_transac_pivot_final APRES PIVOT", syn_donnees_transac_pivot_final)
    
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\n*** COLONNES CREEES PAR LE PIVOT ***\n")
        for col in syn_donnees_transac_pivot_final.columns:
            f.write(f"  - '{col}': {syn_donnees_transac_pivot_final[col].dtype}\n")
    
    # =========================================================================
    # STEP 10: JOIN avec df_nops
    # =========================================================================
    df_transac = syn_donnees_transac_pivot_final.join(df_nops, on="i_uniq_kpi", how="left")
    
    write_debug("STEP 10: df_transac APRES JOIN", df_transac)
    
    # =========================================================================
    # STEP 11: Calcul des features
    # =========================================================================
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write("STEP 11: AVANT CALCUL FEATURES\n")
        f.write(f"Colonnes disponibles pour calcul:\n")
        for col in df_transac.columns:
            f.write(f"  - {col}\n")
        f.write(f"\nColonnes attendues:\n")
        expected_cols = [
            "rembt_prlv_sepa__max_amount",
            "prlv_sepa_retourne__nops", 
            "saisie__nops",
            "interets__netamount",
            "turnover__netamount",
            "nops"
        ]
        for col in expected_cols:
            if col in df_transac.columns:
                f.write(f"  ✓ {col} PRESENT\n")
            else:
                f.write(f"  ✗ {col} ABSENT!\n")
        f.write(f"{'='*80}\n")
    
    # remb_sepa_max
    df_transac = df_transac.with_columns(
        pl.when(pl.col("rembt_prlv_sepa__max_amount") > 3493.57007)
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("remb_sepa_max")
    )

    # pres_prlv_retourne
    df_transac = df_transac.with_columns(
        pl.when(pl.col("prlv_sepa_retourne__nops") > 0)
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("pres_prlv_retourne")
    )

    # pres_saisie
    df_transac = df_transac.with_columns(
        pl.when(pl.col("saisie__nops") > 0)
        .then(pl.lit("1"))
        .otherwise(pl.lit("2"))
        .alias("pres_saisie")
    )

    # net_interets_sur_turnover
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

    write_debug("STEP 11: df_transac APRES CALCUL FEATURES", df_transac)

    # =========================================================================
    # STEP 12: Unique et JOIN final
    # =========================================================================
    df_transac = df_transac.unique(subset=["i_uniq_kpi"], keep="first")
    df_main = df_main.join(df_transac, on="i_uniq_kpi", how="left")

    write_debug("STEP 12: df_main FINAL", df_main)
    
    with open(DEBUG_FILE, "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write("=== FIN add_transac_features ===\n")
        f.write(f"{'='*80}\n")

    return df_main.with_columns(pl.lit("OK").alias("flag_transac"))
