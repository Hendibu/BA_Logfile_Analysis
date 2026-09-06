# clean_all.py -- bereinigt das Rohlog fuer die weitere Verarbeitung:
# entfernt Null-Zeilen, Bot-/Feld-/Fremdsprach-/Hochfrequenz-Queries und doppelte search_ids.
# Eingabe: log_files.tsv | Ausgabe: log_files_cleaned.tsv

import os
os.environ["POLARS_MAX_THREADS"] = "4"     # Threadzahl fuer Polars begrenzen
import polars as pl

# --- Filter-Funktionen: jede entfernt einen bestimmten Zeilen-/Query-Typ ---

# Zeilen mit fehlendem date/search_id/query raus (uid/trackId/type bleiben erhalten)
def drop_track_ids(df):
    return df.drop_nulls(subset=['date', 'search_id', 'query'])

# Queries, die eine DOI (10.xxxx/) enthalten
def drop_doi_queries(df):
    return df.filter(~pl.col("query").str.contains(r'10\.\d{4,}/'))

# Queries mit interner ID-Referenz (id:123456789)
def drop_id_queries(df):
    return df.filter(~pl.col("query").str.contains(r'id:\d{9}'))

# Queries mit nicht-lateinischer oder stark akzentuierter Schrift (fremdsprachige Anfragen)
def drop_rows_with_languages(df, text_column):
    japanese  = r'[\u3040-\u30FF\u4E00-\u9FFF]'
    arabic    = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]'
    cyrillic  = r'[\u0400-\u04FF]'
    latin_acc = r'[\u00C0-\u024F]'          # á í ó ú ñ ã õ ä ö ü ß ... (Spanisch, Port., Deutsch, Tuerkisch, Polnisch ...)
    punct     = r'[\u00A1\u00BF]'           # ¡ ¿
    combined  = f"({japanese}|{arabic}|{cyrillic}|{latin_acc}|{punct})"
    return df.filter(~pl.col(text_column).str.contains(combined, literal=False))

# Queries mit Titel-Feldsuche (title:"...")
def drop_title_queries(df):
    return df.filter(~pl.col("query").str.contains(r'title:"'))

# Bot-Queries mit updatedDate-Zeitfenster (>= ... AND < ...)
def drop_update_date_queries(df):
    return df.filter(~pl.col("query").str.contains(
        r'^updatedDate\s*>=\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{6}\+\d{2}:\d{2}|Z)\s+AND\s+updatedDate\s*<\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{6}\+\d{2}:\d{2}|Z)$'))

# Queries, die nur aus einer 10-stelligen Zahl bestehen
def drop_number_only_queries(df):
    return df.filter(~pl.col("query").str.contains(r'^\d{10}$'))

# Spezifische "cell capture AND ..."-Bot-Queries
def drop_cell_capture_queries(df):
    return df.filter(~pl.col('query').str.contains(r'^(?:"|)cell capture AND.*'))

# Feldbasierte Queries (abstract:, authors:, doi:, title: ...) entfernen
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

# Doppelte search_ids: nur das erste Vorkommen behalten
def drop_duplicate_search_ids(df):
    return df.unique(subset="search_id", keep="first")

# Sehr haeufige Queries (>= limit Vorkommen) per Anti-Join entfernen (leichtgewichtig)
def drop_high_frequency_queries(df, limit):
    high = (df.group_by("query").agg(pl.len().alias("c"))
              .filter(pl.col("c") >= limit).select("query"))
    return df.join(high, on="query", how="anti")

# Platzhalter (unveraendert durchreichen)
def limit_high_frequency_queries(df, limit):
    return df

# Ein-/Ausgabe und die zu behaltenden Spalten
SRC = "../data/log_files.tsv"
OUT = "../data/log_files_cleaned.tsv"
COLS = ["date","search_id","serp","query","trackId","type","uid"]

# Log lazy einlesen und leere Strings zu echten Null-Werten machen
lf = pl.scan_csv(SRC, separator="\t", quote_char=None, infer_schema_length=0)
lf = lf.with_columns([pl.when(pl.col(c) == "").then(None).otherwise(pl.col(c)).alias(c) for c in COLS])

# Filter-Pipeline: erst die billigen Query-Filter (verkleinern die Daten), dann die teuren Schritte
lf_cleaned = (
    lf.pipe(drop_track_ids)
      .pipe(drop_doi_queries)
      .pipe(drop_id_queries)
      .pipe(drop_rows_with_languages, "query")
      .pipe(drop_title_queries)
      .pipe(drop_update_date_queries)
      .pipe(drop_number_only_queries)
      .pipe(drop_cell_capture_queries)
      .pipe(drop_special_field_queries)
      # danach erst die speicherintensiven Schritte, auf viel weniger Daten
      .pipe(drop_duplicate_search_ids)
      .pipe(drop_high_frequency_queries, 500)
      .pipe(limit_high_frequency_queries, 100)
)

# Ergebnis streamend wegschreiben
lf_cleaned.sink_csv(OUT, separator="\t")
print("Fertig ->", OUT)