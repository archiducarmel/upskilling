# Voir la distribution de c_profl_immbr
print(df_main.select("c_profl_immbr").describe())
print(df_main.group_by("c_profl_immbr").len().sort("len", descending=True))

# Compter NULL vs non-NULL
null_count = df_main.filter(pl.col("c_profl_immbr").is_null()).height
not_null_count = df_main.filter(pl.col("c_profl_immbr").is_not_null()).height
print(f"NULL: {null_count:,}")
print(f"NOT NULL: {not_null_count:,}")
