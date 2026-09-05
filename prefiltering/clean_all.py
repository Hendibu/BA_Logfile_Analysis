import os
os.environ["POLARS_MAX_THREADS"] = "4"
import polars as pl

def drop_track_ids(df):                   # behaelt uid/trackId/type, nur Null-Zeilen raus
    return df.drop_nulls(subset=['date', 'search_id', 'query'])

def drop_doi_queries(df):
    return df.filter(~pl.col("query").str.contains(r'10\.\d{4,}/'))
def drop_id_queries(df):
    return df.filter(~pl.col("query").str.contains(r'id:\d{9}'))
def drop_rows_with_languages(df, text_column):
    japanese  = r'[\u3040-\u30FF\u4E00-\u9FFF]'
    arabic    = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]'
    cyrillic  = r'[\u0400-\u04FF]'
    latin_acc = r'[\u00C0-\u024F]'          # á í ó ú ñ ã õ ä ö ü ß ... (Spanisch, Port., Deutsch, Tuerkisch, Polnisch ...)
    punct     = r'[\u00A1\u00BF]'           # ¡ ¿
    combined  = f"({japanese}|{arabic}|{cyrillic}|{latin_acc}|{punct})"
    return df.filter(~pl.col(text_column).str.contains(combined, literal=False))
def drop_title_queries(df):
    return df.filter(~pl.col("query").str.contains(r'title:"'))
def drop_update_date_queries(df):
    return df.filter(~pl.col("query").str.contains(
        r'^updatedDate\s*>=\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{6}\+\d{2}:\d{2}|Z)\s+AND\s+updatedDate\s*<\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{6}\+\d{2}:\d{2}|Z)$'))
def drop_number_only_queries(df):
    return df.filter(~pl.col("query").str.contains(r'^\d{10}$'))
def drop_cell_capture_queries(df):
    return df.filter(~pl.col('query').str.contains(r'^(?:"|)cell capture AND.*'))

# NEU: feldbasierte Queries (abstract:, authors:, doi:, title: ... ) entfernen
_FIELDS = [
    "abstract","acceptedDate","arxivId","authors","citationCount","contributors",
    "createdDate","dataProviders","depositedDate","documentType","doi","downloadUrl",
    "fieldOfStudy","fullText","identifiers","journals","links","magId","oaiIds",
    "outputs","publishedDate","publisher","pubmedId","references","sourceFulltextUrls",
    "title","updatedDate","yearPublished","language","_exists_","id","yearpublished","updateddate"
]
# Feldname am Wortanfang (Start oder nach einem Nicht-alphanumerischen Zeichen), gefolgt von ":"
_FIELD_PATTERN = r'(^|[^a-zA-Z0-9])(' + '|'.join(_FIELDS) + r'):'
def drop_special_field_queries(df):
    return df.filter(~pl.col("query").str.contains(_FIELD_PATTERN))

def drop_duplicate_search_ids(df):
    return df.unique(subset="search_id", keep="first")

def drop_high_frequency_queries(df, limit):     # Anti-Join = leichter
    high = (df.group_by("query").agg(pl.len().alias("c"))
              .filter(pl.col("c") >= limit).select("query"))
    return df.join(high, on="query", how="anti")

def limit_high_frequency_queries(df, limit):    # No-Op (Pass-through)
    return df

SRC = "log_files.tsv"
OUT = "log_files_cleaned.tsv"
COLS = ["date","search_id","serp","query","trackId","type","uid"]

lf = pl.scan_csv(SRC, separator="\t", quote_char=None, infer_schema_length=0)
lf = lf.with_columns([pl.when(pl.col(c) == "").then(None).otherwise(pl.col(c)).alias(c) for c in COLS])

lf_cleaned = (
    lf.pipe(drop_track_ids)
      # billige Query-Filter ZUERST -> verkleinern die Daten
      .pipe(drop_doi_queries)
      .pipe(drop_id_queries)
      .pipe(drop_rows_with_languages, "query")
      .pipe(drop_title_queries)
      .pipe(drop_update_date_queries)
      .pipe(drop_number_only_queries)
      .pipe(drop_cell_capture_queries)
      .pipe(drop_special_field_queries)        # NEU
      # danach erst die speicherintensiven Schritte, auf viel weniger Daten
      .pipe(drop_duplicate_search_ids)
      .pipe(drop_high_frequency_queries, 500)
      .pipe(limit_high_frequency_queries, 100)
)

lf_cleaned.sink_csv(OUT, separator="\t")
print("Fertig ->", OUT)