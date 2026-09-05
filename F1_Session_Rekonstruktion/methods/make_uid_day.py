# make_uidday.py -- bereitet die Pro-uid-Tag-Rekonstruktion vor:
# leere uid entfernen, nach (uid, ts) sortieren, Spalte grp = uid|Tag anhaengen.
import os
os.environ["POLARS_MAX_THREADS"] = "4"
import polars as pl

SRC = "dis22_sorted_noburst.tsv"
OUT = "dis22_uidday.tsv"

df = (
    pl.scan_csv(SRC, separator="\t", infer_schema_length=0)            # alles als String lesen
      .filter(pl.col("uid").is_not_null() & (pl.col("uid").str.strip_chars() != ""))
      .with_columns(pl.col("ts").cast(pl.Int64).alias("_ts"))
      .with_columns(
          (pl.col("uid") + pl.lit("|")
           + pl.from_epoch(pl.col("_ts"), time_unit="s").dt.strftime("%Y-%m-%d")).alias("grp"))
      .sort(["uid", "_ts"])                                            # nach Nutzer, dann Zeit
      .drop("_ts")
      .collect(engine="streaming")
)
df.write_csv(OUT, separator="\t")
print(f"{df.height:,} Zeilen (mit uid), sortiert nach uid,ts, Spalte 'grp'=uid|Tag -> {OUT}")