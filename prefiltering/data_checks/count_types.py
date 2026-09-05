# count_types.py <logfile>
# Zaehlt Gesamtzeilen und schluesselt nach Ereignistyp auf (streamend, O(1)-Speicher).
# Query-Events = Zeilen mit nicht-leerem 'query'; Interaktionen = Rest (mit 'type').
# NUR Aggregate (NDA-sicher).
import sys
from collections import Counter

PATH = sys.argv[1] if len(sys.argv) > 1 else "log_files.tsv"

with open(PATH, encoding="utf-8", errors="replace") as f:
    header = f.readline().replace("\x00", "").rstrip("\n").split("\t")
    iq = header.index("query") if "query" in header else None
    it = header.index("type")  if "type"  in header else None

    total = 0; queries = 0; interactions = 0; leer = 0
    typen = Counter()
    for line in f:
        parts = line.replace("\x00", "").rstrip("\n").split("\t")
        total += 1
        q = parts[iq].strip() if (iq is not None and iq < len(parts)) else ""
        t = parts[it].strip() if (it is not None and it < len(parts)) else ""
        if q:
            queries += 1
        elif t:
            interactions += 1; typen[t] += 1
        else:
            leer += 1

print(f"Datenzeilen gesamt      : {total:,}")
print(f"  Query-Events (query!=''): {queries:,}")
print(f"  Interaktionen (type!=''): {interactions:,}")
print(f"  weder query noch type   : {leer:,}")
print("  Interaktionstypen:")
for t, n in typen.most_common():
    print(f"    {t:16} {n:,}")