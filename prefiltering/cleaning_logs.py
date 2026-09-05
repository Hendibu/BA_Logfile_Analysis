import pandas as pd
import json
import re
import hashlib
import csv
from datetime import datetime
import os
import numpy as np 
from functions.clean_data import (
    drop_doi_queries, 
    drop_track_ids, 
    drop_title_queries, 
    drop_high_frequency_queries, 
    limit_high_frequency_queries,
    drop_high_frequency_uids,
    drop_undefined_track_ids,
    drop_nan_uids,
    drop_null_string_uids,
    keep_public_uids,
    drop_boolean_queries,
    drop_special_field_queries
)

INPUT_FILE = '../data/data_2025_03_05.log'

FINAL_LOG_FILE = '../data/data_2025_03_05_filtered_2.log'

def safe_serp_parse(serp_raw):
    """Versucht, die SERP-String in eine Liste von IDs zu parsen."""
    if not isinstance(serp_raw, str):
        return []
    if serp_raw.lower() in ('nan', 'none', ''):
        return []
        
    try:
        return [int(x.strip()) for x in serp_raw.split(",") if x.strip().isdigit()]
    except Exception:
        return []

print(f"1. Starte direkte zeilenweise Verarbeitung der Datei: {INPUT_FILE}")

data = []

with open(INPUT_FILE, 'r', encoding='utf-8') as infile: 
    for line_number, line in enumerate(infile, start=1):
        
        try:
            data.append(json.loads(line.strip()))
        except json.JSONDecodeError as e:
            print(f"   [FEHLER] Zeile {line_number}: Konnte nicht als JSON geparst werden: {e}")
            continue
df = pd.DataFrame(data)


subset_cols = [col for col in df.columns if col not in ['serp', 'serp_ids']]
df.drop_duplicates(subset=subset_cols, inplace=True, ignore_index=True)

if "query" in df.columns:
    df = df[df['query'].notna() & (df['query'] != "")]

df = (
    df.pipe(drop_track_ids)
      .pipe(drop_boolean_queries)
      .pipe(drop_special_field_queries)
      .pipe(drop_doi_queries)
      .pipe(drop_title_queries)
      .pipe(drop_high_frequency_queries, 100)
      .pipe(limit_high_frequency_queries, 50)
      #.pipe(drop_high_frequency_uids, 500)
      .pipe(drop_undefined_track_ids)
      .pipe(drop_nan_uids)
      .pipe(drop_null_string_uids)
      .pipe(keep_public_uids)
)


df['serp_ids'] = df['serp'].apply(safe_serp_parse)

with open(FINAL_LOG_FILE, 'w', encoding='utf-8') as logfile:
    total_rows_written = 0
    for _, row in df.iterrows():
        log_entry = {
            "date": row.get('date'),
            "search_id": row.get('search_id'),
            "serp": row.get('serp_ids', []), 
            "query": row.get('query'),
            "uid": row.get('uid')
        }
        if log_entry["date"] and log_entry["search_id"] and log_entry["query"]:
            logfile.write(json.dumps(log_entry, default=str) + '\n')
            total_rows_written += 1

print(f"Verarbeitung abgeschlossen. Finale Logdatei ({FINAL_LOG_FILE}) erstellt.")
print(f"Gesamtzahl bereinigter Zeilen: {total_rows_written}")
