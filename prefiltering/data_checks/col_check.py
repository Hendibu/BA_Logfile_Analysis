import polars as pl
lf = pl.scan_csv("../../data/log_files.tsv", separator="\t", quote_char=None, infer_schema_length=0)
COLS = ["date","search_id","serp","query","trackId","type","uid"]
lf = lf.with_columns([pl.when(pl.col(c) == "").then(None).otherwise(pl.col(c)).alias(c) for c in COLS])

res = lf.select(
    pl.len().alias("total"),
    pl.col("trackId").is_not_null().sum().alias("nn_trackId"),
    pl.col("type").is_not_null().sum().alias("nn_type"),
    pl.col("uid").is_not_null().sum().alias("nn_uid"),
    (pl.col("query").is_not_null() & pl.col("uid").is_not_null()).sum().alias("query_UND_uid"),
).collect(streaming=True)
with pl.Config(tbl_cols=-1):
    print(res)