# sample_precision.py <session_datei> [K]
# Zieht eine GESCHICHTETE Stichprobe klassifizierter Reformulierungs-Paare
# (bis zu K je Strategie) fuer die manuelle Precision-Pruefung.
# Eingabe: cascade_full_1234_nostruct.tsv (default) | Ausgabe: precision_stichprobe.tsv

import csv, sys, re, random
from collections import defaultdict, Counter
import os
# Reformulierungs-Klassifikator aus dem Nachbarordner importierbar machen
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "reformulation"))
from RQ2_reformulation import classify
csv.field_size_limit(2**31 - 1)

# Session-Datei, Stichprobengroesse je Strategie und Ausgabedatei
SESSION_FILE = sys.argv[1] if len(sys.argv) > 1 else "../../data/cascade_full_1234_nostruct.tsv"
K   = int(sys.argv[2]) if len(sys.argv) > 2 else 25          # Stichprobengroesse je Strategie
OUT = "../../data/precision_stichprobe.tsv"
# gleicher Struktur-Filter wie in der Auswertung, damit dieselbe Basis geprueft wird
STRUCT = re.compile(r'year\s*:|yearpublished|(<=|>=|<|>)\s*\d|\bAND\s*\(|\bOR\s*\(', re.IGNORECASE)
rng = random.Random(42)                                       # feste Seed = reproduzierbar

# Hilfsfunktion: entfernt NUL-Bytes, damit der CSV-Reader nicht abbricht
def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

# Je Strategie ein Reservoir (bis K Beispiele) und die Gesamtzahl gesehener Paare
reservoir = defaultdict(list)   # Label -> Liste von (prev, curr)
seen = Counter()                # wie viele Paare je Label insgesamt gesehen

# Session-Datei paarweise durchgehen, Struktur-Paare ausschliessen und je Strategie per Reservoir sampeln
with open(SESSION_FILE, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
    i_sid, i_q = h.index(sidcol), h.index("query")
    cur = None; prev = None
    for row in r:
        sid = row[i_sid]
        if not sid: cur = None; prev = None; continue
        if sid != cur: cur = sid; prev = row[i_q]; continue
        q = row[i_q]
        if STRUCT.search(prev) or STRUCT.search(q): prev = q; continue   # Bot-Paare raus
        lbl = classify(prev, q)
        seen[lbl] += 1
        buf = reservoir[lbl]
        if len(buf) < K:                       # Reservoir-Sampling je Label
            buf.append((prev, q))
        else:
            j = rng.randint(0, seen[lbl] - 1)
            if j < K: buf[j] = (prev, q)
        prev = q

# Stichprobe als TSV schreiben (mit leeren Spalten fuer die manuelle Annotation)
with open(OUT, "w", newline="", encoding="utf-8") as o:
    w = csv.writer(o, delimiter="\t")
    w.writerow(["idx", "strategie", "prev_query", "curr_query",
                "korrekt(1/0)", "richtige_klasse_falls_falsch"])
    idx = 0
    for lbl in sorted(reservoir):
        for (p, c) in reservoir[lbl]:
            idx += 1
            w.writerow([idx, lbl, p, c, "", ""])

# Ueberblick ausgeben: je Strategie Gesamtzahl und wie viele in die Stichprobe kamen
print("Stichprobe geschrieben ->", OUT)
print(f"{'Strategie':22}{'gesamt':>10}{'Stichprobe':>12}")
for lbl in sorted(seen):
    print(f"{lbl:22}{seen[lbl]:>10,}{len(reservoir[lbl]):>12}")