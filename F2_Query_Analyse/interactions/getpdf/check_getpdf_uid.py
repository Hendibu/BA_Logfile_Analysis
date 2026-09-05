# check_getpdf_uid.py  [datei]
# --------------------------------------------------------------------------
# Bestaetigt, dass die get-pdf-Download-Suchen wegen LEERER uid entfernt werden.
# Nimmt die Query-Zeilen aus <datei> (default: dis22_sorted_noburst.tsv), deren
# search_id zu einem get-pdf-Event gehoert, und zaehlt leere vs. gefuellte uid.
# Nur Aggregate -> NDA-sicher. Bleibt lokal.
# --------------------------------------------------------------------------
import csv, sys
csv.field_size_limit(2**31 - 1)

INTER = "interactions.tsv"
SRC   = sys.argv[1] if len(sys.argv) > 1 else "dis22_sorted_noburst.tsv"

def strip_nul(fo):
    for line in fo:
        yield line.replace("\x00", "")

# 1) get-pdf search_ids sammeln
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

# 2) In SRC die zugehoerigen Query-Zeilen finden und uid pruefen
n_rows = n_empty = n_filled = 0
seen = set()
with open(SRC, newline="", encoding="utf-8", errors="replace") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    isid = h.index("search_id"); iu = h.index("uid")
    for row in r:
        if isid >= len(row):
            continue
        sid = row[isid].strip()
        if sid not in keys:
            continue
        n_rows += 1
        uid = row[iu].strip() if iu < len(row) else ""
        if uid == "":
            n_empty += 1
        else:
            n_filled += 1
        seen.add(sid)

print(f"Quelle: {SRC}")
print(f"Download-Query-Zeilen gefunden : {n_rows:,}  (distinct search_ids: {len(seen):,})")
print(f"  davon uid LEER   : {n_empty:,}" + (f"  ({100*n_empty/n_rows:.1f}%)" if n_rows else ""))
print(f"  davon uid gefuellt: {n_filled:,}" + (f"  ({100*n_filled/n_rows:.1f}%)" if n_rows else ""))