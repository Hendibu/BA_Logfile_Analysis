# check_interaction_match.py <session_file>
# Prueft je Interaktionstyp, wie viele merge_keys auf die search_ids der Session-Datei
# passen -> zeigt, ob get-pdf (anders als author/works/data-provider) nicht matcht.
# Gibt ausserdem ein paar Beispiel-IDs zum Augenschein aus.
# Eingabe: cascade_full_1234_nostruct.tsv (default), interactions.tsv

import csv, sys
from collections import Counter
csv.field_size_limit(2**31 - 1)

# Session-Datei (Argument oder Standard) und Interaktionsdatei
SESSION = sys.argv[1] if len(sys.argv) > 1 else "../../data/cascade_full_1234_nostruct.tsv"
INTER   = "../../data/interactions.tsv"

# Hilfsfunktion: entfernt NUL-Bytes, damit der CSV-Reader nicht abbricht
def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

# Alle search_ids der Session-Datei einsammeln
sids = set()
with open(SESSION, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r); i = h.index("search_id")
    for row in r:
        if row[i]: sids.add(row[i])
print(f"{len(sids):,} search_ids in {SESSION}\n")

# Interaktionen durchlaufen: je Typ gesamt zaehlen und wie viele merge_keys eine search_id treffen
tot = Counter(); match = Counter(); ex_mk = {}
with open(INTER, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    imk, ity, itr = h.index("merge_key"), h.index("type"), h.index("trackId")
    for row in r:
        t = row[ity]; tot[t] += 1
        if row[imk] in sids: match[t] += 1
        if t not in ex_mk: ex_mk[t] = (row[imk], row[itr])   # erstes Beispiel je Typ merken

# Trefferquote je Typ und ein paar Beispiel-IDs ausgeben
print(f"{'type':16} {'interactions':>13} {'auf search_id':>14}")
for t in tot:
    print(f"  {t:14} {tot[t]:>13,} {match[t]:>11,} ({100*match[t]/max(tot[t],1):.2f}%)")
print("\nBeispiel merge_key | trackId je Typ:")
for t, (mk, tr) in ex_mk.items():
    print(f"  {t:14} merge_key={mk[:24]}…  trackId={tr[:40]}…")
print("\n3 Session-search_ids zum Vergleich:", [s[:24] for s in list(sids)[:3]])