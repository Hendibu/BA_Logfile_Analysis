# check_getpdf_in_log.py
# Testet, ob die merge_keys der get-pdf-Events ueberhaupt als search_id im ROHEN Log vorkommen.
#   - kommen sie vor   -> echte Such-Nummern, die nur im gefilterten Session-File fehlen
#   - kommen sie NICHT -> get-pdf traegt einen anderen Hash (kein search_id), keine Verknuepfung moeglich
# Eingabe: log_files.tsv (Rohlog), interactions.tsv

import csv, sys
csv.field_size_limit(2**31 - 1)

# Rohlog und Interaktionsdatei
RAW   = "../../../data/log_files.tsv"
INTER = "../../../data/interactions.tsv"

# Hilfsfunktion: entfernt NUL-Bytes, damit der CSV-Reader nicht abbricht
def strip_nul(fo):
    for line in fo:
        yield line.replace("\x00", "")

# 1) get-pdf merge_keys sammeln (nur dieser eine Typ -> speicherschonend)
keys = set()
with open(INTER, newline="", encoding="utf-8", errors="replace") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    ity, imk = h.index("type"), h.index("merge_key")
    for row in r:
        if len(row) <= max(ity, imk):
            continue
        if row[ity] == "get-pdf":
            mk = row[imk].strip()
            if mk and mk != "undefined":
                keys.add(mk)
print(f"distinct get-pdf merge_keys (echt): {len(keys):,}")

# 2) Roh-Log streamen und schauen, welche dieser Keys als search_id vorkommen
hit = set()
n_query_rows = 0
with open(RAW, newline="", encoding="utf-8", errors="replace") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    if "search_id" not in h:
        sys.exit(f"Roh-Log hat keine search_id-Spalte. Header: {h}")
    isid = h.index("search_id")
    for row in r:
        if isid >= len(row):
            continue
        sid = row[isid].strip()
        if not sid:
            continue
        n_query_rows += 1
        if sid in keys:
            hit.add(sid)

# Trefferquote berechnen und daraus die Schlussfolgerung ableiten
pct = 100 * len(hit) / len(keys) if keys else 0
print(f"Zeilen mit search_id im Log : {n_query_rows:,}")
print(f"get-pdf merge_keys, die als search_id im Log vorkommen: {len(hit):,} von {len(keys):,} ({pct:.1f}%)")
if pct < 1:
    print(">> get-pdf-Praefix ist KEIN search_id -> Verknuepfung ueber search_id nicht moeglich.")
else:
    print(">> get-pdf-Praefix IST ein search_id -> Treffer nur im gefilterten Session-File entfernt.")