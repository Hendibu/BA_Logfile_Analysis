# eval_precision.py [stichprobe.tsv]
# Liest die MANUELL ausgefuellte Stichprobe und rechnet die Precision je Strategie
# sowie die haeufigsten Fehlklassifikationen. Ausgabe = reine Aggregate (NDA-sicher).
import csv, sys
from collections import Counter
IN = sys.argv[1] if len(sys.argv) > 1 else "precision_stichprobe.tsv"

per = Counter(); ok = Counter(); conf = Counter(); nicht = 0
with open(IN, newline="", encoding="utf-8") as f:
    r = csv.reader(f, delimiter="\t"); next(r)
    for row in r:
        if len(row) < 5 or row[4].strip() == "":   # noch nicht annotiert
            nicht += 1; continue
        lbl = row[1]; korrekt = row[4].strip()
        per[lbl] += 1
        if korrekt == "1":
            ok[lbl] += 1
        else:
            true = row[5].strip() if len(row) > 5 and row[5].strip() else "?"
            conf[(lbl, true)] += 1

tot = sum(per.values()); tok = sum(ok.values())
print("=== Precision je Strategie (korrekt / geprueft) ===")
for lbl in sorted(per):
    print(f"  {lbl:22} {ok[lbl]:>3}/{per[lbl]:<3} = {100*ok[lbl]/per[lbl]:5.1f}%")
if tot:
    print(f"  {'---':22}")
    print(f"  {'GESAMT':22} {tok:>3}/{tot:<3} = {100*tok/tot:5.1f}%")
if nicht: print(f"\n(noch nicht annotiert: {nicht} Zeilen)")
print("\n=== Haeufigste Fehlklassifikationen (zugewiesen -> tatsaechlich) ===")
for (a, b), n in conf.most_common(15):
    print(f"  {a:20} -> {b:20} {n}")