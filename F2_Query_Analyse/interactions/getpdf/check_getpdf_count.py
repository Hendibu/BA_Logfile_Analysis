# check_getpdf_count.py
# Zaehlt je Typ: gesamt / merge_key=="undefined" / echt / leer.
# merge_key ist bereits trackId.split('-')[0].
# Eingabe: interactions.tsv

import sys, csv
from collections import Counter

# Eingabedatei (Argument oder Standardpfad)
INFILE = sys.argv[1] if len(sys.argv) > 1 else "../../../data/interactions.tsv"

# Kopfzeile lesen und die Spalten type und merge_key bestimmen (fehlt eine, Abbruch)
with open(INFILE, newline="", encoding="utf-8", errors="replace") as f:
    head = f.readline().rstrip("\r\n").split("\t")
idx = {name: i for i, name in enumerate(head)}
c_type = idx.get("type")
c_mk   = idx.get("merge_key")
if c_type is None or c_mk is None:
    sys.exit(f"Datei braucht type/merge_key, hat aber: {head}")

# Zaehler je Typ: gesamt, undefined, echt (gueltiger Wert), leer
total, undef, real, empty = Counter(), Counter(), Counter(), Counter()

# Datei durchlaufen und je Typ den merge_key-Status einordnen
with open(INFILE, newline="", encoding="utf-8", errors="replace") as f:
    r = csv.reader(f, delimiter="\t")
    next(r, None)
    for row in r:
        if len(row) <= max(c_type, c_mk):
            continue
        t  = row[c_type].strip()
        mk = row[c_mk].strip()
        total[t] += 1
        if not mk:
            empty[t] += 1
        elif mk == "undefined":
            undef[t] += 1
        else:
            real[t] += 1

# Ergebnistabelle je Typ (nach Haeufigkeit sortiert) samt Summenzeile ausgeben
print(f"Quelle: {INFILE}")
print("")
print(f"{'Typ':<16}{'gesamt':>10}{'undefined':>12}{'echt':>10}{'leer':>8}{'% undef':>10}")
print("-" * 66)
for t in sorted(total, key=lambda x: -total[x]):
    g = total[t]
    pct = 100 * undef[t] / g if g else 0
    print(f"{t:<16}{g:>10}{undef[t]:>12}{real[t]:>10}{empty[t]:>8}{pct:>9.1f}%")
print("-" * 66)
print(f"{'SUMME':<16}{sum(total.values()):>10}{sum(undef.values()):>12}{sum(real.values()):>10}{sum(empty.values()):>8}")