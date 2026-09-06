# extract_interactions.py -- Interaktions-Events aus der ROHEN Logdatei ziehen.
# merge_key = Teil des trackId VOR dem ersten '-'  == search_id der Query
# (Verknuepfung: session.search_id == trackId.split('-')[0]).
# Eingabe: log_files.tsv | Ausgabe: interactions.tsv

import csv, re
from collections import Counter
from datetime import datetime, timezone
csv.field_size_limit(2**31 - 1)

# Pfade und die Interaktionstypen, die behalten werden
SRC  = "../../data/log_files.tsv"
OUT  = "../../data/interactions.tsv"
KEEP = {"get-pdf", "data-provider", "author", "works"}

# Hilfsfunktion: entfernt NUL-Bytes, damit der CSV-Reader nicht abbricht
def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")
# Zeitstempel zu Unix-Sekunden: akzeptiert Zahl (Sekunden oder Millisekunden) und mehrere Datumsformate
def to_epoch(s):
    s = s.strip()
    if not s: return None
    if re.fullmatch(r"\d+(\.\d+)?", s):
        v = float(s); return int(v/1000.0 if v > 1e12 else v)   # >1e12 = Millisekunden
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f"):
        try: return int(datetime.strptime(s[:26], fmt).replace(tzinfo=timezone.utc).timestamp())
        except ValueError: continue
    return None

# Rohlog durchlaufen: nur behaltene Interaktionstypen mit gueltigem Zeitstempel schreiben
n = kept = 0; byt = Counter()
with open(SRC, newline="", encoding="utf-8") as f, open(OUT, "w", newline="", encoding="utf-8") as o:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    idate, it, itr, iu = h.index("date"), h.index("type"), h.index("trackId"), h.index("uid")
    w = csv.writer(o, delimiter="\t"); w.writerow(["ts", "uid", "type", "trackId", "merge_key"])
    for row in r:
        n += 1
        t = row[it].strip() if it < len(row) else ""
        if t in KEEP:
            ts = to_epoch(row[idate]); tr = row[itr]
            if ts is None: continue
            # merge_key = trackId vor dem ersten '-' (= zugehoerige search_id)
            w.writerow([ts, row[iu], t, tr, tr.split('-')[0]]); kept += 1; byt[t] += 1

# Gesamtzahl und Aufschluesselung je Interaktionstyp ausgeben
print(f"{n:,} Zeilen, {kept:,} Interaktionen -> {OUT}")
for t, c in byt.most_common(): print(f"  {t:16} {c:,}")