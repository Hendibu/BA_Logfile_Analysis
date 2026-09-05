import polars as pl

SRC = "log_files.parquet"
OUT = "data_filtered.ndjson"

FREQ_DROP, FREQ_CAP = 100, 50
SPECIAL_FIELDS = [
    "abstract","acceptedDate","arxivId","authors","citationCount","contributors",
    "createdDate","dataProviders","depositedDate","documentType","doi","downloadUrl",
    "fieldOfStudy","fullText","identifiers","journals","links","magId","oaiIds",
    "outputs","publishedDate","publisher","pubmedId","references","sourceFulltextUrls",
    "title","updatedDate","yearPublished","language","_exists_","id","yearpublished","updateddate",
]
field_pattern = r"(^|\s|[^a-zA-Z0-9])(" + "|".join(SPECIAL_FIELDS) + r"):"

lf = pl.scan_parquet(SRC)

# --- streaming-sicher ---
lf = lf.filter(pl.col("query").is_not_null())                          # query vorhanden/nicht leer
lf = lf.unique(subset=["date","search_id","query","trackId","type","uid"], keep="first")  # drop_duplicates
rest = ["date","search_id","serp","query","trackId","uid"]
lf = lf.drop("type").filter(                                            # drop_track_ids (type weg + thresh=2)
    pl.sum_horizontal([pl.col(c).is_not_null() for c in rest]) >= 2)
lf = lf.filter(~pl.col("query").str.contains(r"\b(?:AND|OR|NOT)\b"))    # boolean
lf = lf.filter(~pl.col("query").str.contains(field_pattern))           # special fields
lf = lf.filter(~pl.col("query").str.contains(r"10\.\d{4,}/"))          # doi
lf = lf.filter(~pl.col("query").str.contains(r'title:"'))              # title
qtot = lf.group_by("query").agg(pl.len().alias("_qtotal"))             # drop_high_frequency_queries(100)
lf = lf.join(qtot, on="query", how="left").filter(pl.col("_qtotal") < FREQ_DROP).drop("_qtotal")

# --- EINZIGER Window-Schritt: hier RAM beobachten ---
lf = lf.with_columns(pl.int_range(pl.len()).over("query").alias("_rn"))  # limit(50)
lf = lf.filter(pl.col("_rn") < FREQ_CAP).drop("_rn")

# --- wieder streaming-sicher ---
lf = lf.filter(~pl.col("trackId").cast(pl.Utf8).str.starts_with("undefined"))
lf = lf.filter(pl.col("uid").is_not_null())
lf = lf.filter(~pl.col("uid").is_in(["null","NaN"]))
lf = lf.filter(pl.col("uid").cast(pl.Utf8).str.starts_with("public"))

# serp -> Liste von IDs + finale Spalten + Pflichtfelder
lf = lf.with_columns(
    pl.col("serp").str.extract_all(r"\d+").list.eval(pl.element().cast(pl.Int64)).alias("serp"))
lf = lf.select(["date","search_id","serp","query","uid"]).filter(
    pl.col("date").is_not_null() & pl.col("search_id").is_not_null() & pl.col("query").is_not_null())

lf.sink_ndjson(OUT)
print("Fertig ->", OUT)