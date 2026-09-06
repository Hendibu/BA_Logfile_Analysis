# prepare_sorted_events.py -- filtert das bereinigte Log auf Zeilen mit query und serp und
# sortiert sie zeitlich; behaelt alle fuer die Sessionrekonstruktion noetigen Spalten.
# Eingabe: log_files_cleaned.tsv | Ausgabe: dis22_sorted.tsv

import polars as pl

# Log lazy einlesen, auf gueltige query+serp filtern, date als ts, nach ts sortieren und wegschreiben
(pl.scan_csv("../../data/log_files_cleaned.tsv", separator="\t")
   .filter(pl.col("query").is_not_null() & (pl.col("query") != ""))
   .filter(pl.col("serp").is_not_null()  & (pl.col("serp")  != ""))
   .with_columns(pl.col("date").cast(pl.Int64, strict=False).alias("ts"))
   .filter(pl.col("ts").is_not_null())
   .select(["ts", "query", "serp", "search_id", "trackId", "type", "uid"])  # alle Spalten
   .sort("ts")
   .sink_csv("../../data/dis22_sorted.tsv", separator="\t"))
print("Stage 1 fertig -> ../../data/dis22_sorted.tsv (mit allen Spalten)")