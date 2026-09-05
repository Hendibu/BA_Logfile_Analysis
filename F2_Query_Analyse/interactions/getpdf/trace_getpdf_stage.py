# trace_getpdf_stage.py  <datei1> <datei2> ...
# --------------------------------------------------------------------------
# Verfolgt die get-pdf-Such-Nummern (search_id) durch die Pipeline-Stufen.
# Fuer jede uebergebene Datei wird gezaehlt, wie viele der ~94k get-pdf-
# search_ids darin noch als search_id vorkommen. So sieht man, an WELCHER
# Stufe die Download-Suchen verschwinden.
# Nur Aggregate -> NDA-sicher. Bleibt lokal.
# --------------------------------------------------------------------------
import csv, sys, os
csv.field_size_limit(2**31 - 1)

INTER = "interactions.tsv"
files = sys.argv[1:]
if not files:
    sys.exit("Bitte die zu pruefenden Dateien in Pipeline-Reihenfolge uebergeben.")

def strip_nul(fo):
    for line in fo:
        yield line.replace("\x00", "")

# 1) get-pdf search_ids sammeln (klein)
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
total = len(keys)
print(f"distinct get-pdf search_ids: {total:,}")
print("")

# 2) je Datei zaehlen, wie viele davon als search_id vorkommen
def count_in(path):
    if not os.path.exists(path):
        return None
    found = set()
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(strip_nul(f), delimiter="\t")
        h = next(r, None)
        if not h or "search_id" not in h:
            return -1
        isid = h.index("search_id")
        for row in r:
            if isid >= len(row):
                continue
            sid = row[isid].strip()
            if sid and sid in keys:
                found.add(sid)
    return len(found)

print(f"{'Datei':<40}{'gefunden':>12}{'Anteil':>10}")
print("-" * 62)
for p in files:
    c = count_in(p)
    if c is None:
        print(f"{p:<40}{'FEHLT':>12}")
    elif c == -1:
        print(f"{p:<40}{'keine search_id-Spalte':>22}")
    else:
        pct = 100 * c / total if total else 0
        print(f"{os.path.basename(p):<40}{c:>12,}{pct:>9.1f}%")
print("-" * 62)
print("Dort, wo der Anteil zusammenbricht, verschwinden die Download-Suchen.")