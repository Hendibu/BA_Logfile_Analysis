# drop_bursts.py -- entfernt automatisierte BURST-EVENTS (NICHT ganze uids!).
# Eine (uid, Sekunde)-Gruppe mit >= BURST_MIN Queries gilt als Bot-Dump und wird
# entfernt; alle uebrigen Events derselben uid (auch von echten Menschen, die die
# uid zu anderer Zeit hatten) bleiben erhalten.
# Eingabe: dis22_sorted.tsv | Ausgabe: dis22_sorted_noburst.tsv

import csv
from collections import defaultdict
csv.field_size_limit(2**31 - 1)

# Ein-/Ausgabe und Schwelle: ab so vielen Queries einer uid in EINER Sekunde -> Burst
INPUT     = "../../data/dis22_sorted.tsv"          # volle, nach ts sortierte Daten
OUTPUT    = "../../data/dis22_sorted_noburst.tsv"
BURST_MIN = 2      # ab so vielen Queries derselben uid in EINER Sekunde -> entfernen

# Hilfsfunktion: entfernt NUL-Bytes, damit der CSV-Reader nicht abbricht
def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

kept = dropped = 0

# Einen Sekunden-Block auswerten: pro uid zaehlen und Burst-Events verwerfen, den Rest schreiben
def flush_block(block, w):
    # block = Liste von (uid, row) fuer EINE Sekunde
    global kept, dropped
    by_uid = defaultdict(int)
    for u, _ in block: by_uid[u] += 1          # zaehlen, wie oft jede uid in dieser Sekunde vorkommt
    for u, row in block:
        if by_uid[u] >= BURST_MIN:
            dropped += 1                        # Teil eines Bursts -> raus
        else:
            w.writerow(row); kept += 1          # Einzel-/Doppelquery -> behalten

# Sortierte Datei durchlaufen und die Events je Sekunde blockweise pruefen
with open(INPUT, newline="", encoding="utf-8") as f, \
     open(OUTPUT, "w", newline="", encoding="utf-8") as out:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    w = csv.writer(out, delimiter="\t"); w.writerow(h)   # Kopfzeile uebernehmen
    it = h.index("ts"); iu = h.index("uid")
    cur = None; block = []
    for row in r:
        ts = row[it]
        if ts != cur:                           # neue Sekunde -> alten Block schreiben
            if block: flush_block(block, w)
            cur = ts; block = []
        block.append((row[iu], row))
    if block: flush_block(block, w)             # letzten Block nicht vergessen

print(f"behalten: {kept:,} | entfernt: {dropped:,} "
      f"({100*dropped/(kept+dropped):.1f}%)  ->  {OUTPUT}", flush=True)