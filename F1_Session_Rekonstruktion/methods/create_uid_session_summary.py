import polars as pl

SRC = "../../data/log_files_cleaned.tsv"
OUT = "../../data/uuid_sessions_summary.tsv"

lf = pl.scan_csv(SRC, separator="\t")

# nur Zeilen mit uid; date als Unix-Sekunden interpretieren
lf = (lf
    .filter(pl.col("uid").is_not_null() & (pl.col("uid") != ""))
    .with_columns(pl.col("date").cast(pl.Int64, strict=False).alias("ts"))
    .filter(pl.col("ts").is_not_null())
)

# UUID-Session = alle Ereignisse einer uid
sessions = (
    lf.group_by("uid").agg(
        pl.len().alias("n_queries"),
        pl.col("ts").min().alias("ts_start"),
        pl.col("ts").max().alias("ts_end"),
    )
    .with_columns(((pl.col("ts_end") - pl.col("ts_start")) / 60).alias("dauer_min"))
    .collect(engine="streaming")
)

print("Anzahl UUID-Sessions (distinct uids):", sessions.height)
print("Queries pro Session -> Mittel: {:.2f} | Median: {} | Max: {}".format(
    sessions["n_queries"].mean(), sessions["n_queries"].median(), sessions["n_queries"].max()))
print("Dauer (Minuten)     -> Mittel: {:.1f} | Median: {:.1f} | Max: {:.1f}".format(
    sessions["dauer_min"].mean(), sessions["dauer_min"].median(), sessions["dauer_min"].max()))

sessions.write_csv(OUT, separator="\t")
print("gespeichert ->", OUT)