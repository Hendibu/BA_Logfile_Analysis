# filter_struct_sessions.py <session_file>
# Entfernt GANZE Sessions, die
#   (A) strukturierte Filter-/Bot-Queries enthalten (yearPublished>=…, Vergleichs-
#       operatoren, boolesche AND()/OR()) -- Anteil > MIN_STRUCT_FRAC, ODER
#   (B) mehr als 1 Query haben und aus der EXAKT selben Query bestehen (Wiederholung).
# Ausgabe: <name>_nostruct.tsv . Schnell, kein Neu-Rechnen noetig.
import csv, sys, re
from collections import defaultdict
csv.field_size_limit(2**31 - 1)

SRC = sys.argv[1] if len(sys.argv) > 1 else "../../data/dis22_sessions.tsv"
MIN_STRUCT_FRAC = 0.6     # (A) Session raus, wenn Anteil strukturierter Queries > diesem Wert
PAT = re.compile(r'yearPublished|(<=|>=|<|>)\s*\d|\bAND\s*\(|\bOR\s*\(', re.IGNORECASE)

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

# Pass 1: pro Session Gesamt-/Struktur-Zahl + "alle Queries gleich?"
tot = defaultdict(int); struct = defaultdict(int); firsthash = {}; allsame = {}
with open(SRC, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
    i_sid, i_q = h.index(sidcol), h.index("query")
    for row in r:
        sid = row[i_sid]
        if not sid: continue
        q = row[i_q]; qh = hash(q); tot[sid] += 1
        if PAT.search(q): struct[sid] += 1
        if sid not in firsthash: firsthash[sid] = qh; allsame[sid] = True
        elif qh != firsthash[sid]: allsame[sid] = False

struct_drop = {sid for sid in tot if struct[sid] > 0 and struct[sid]/tot[sid] > MIN_STRUCT_FRAC}  # (A)
dup_drop    = {sid for sid in tot if tot[sid] >= 2 and allsame[sid]}                              # (B)
drop = struct_drop | dup_drop
print(f"{len(tot):,} Sessions | (A) strukturiert: {len(struct_drop):,} | "
      f"(B) reine Wiederholungen: {len(dup_drop):,} | entfernt gesamt: {len(drop):,}")

# Pass 2: Sessions in 'drop' komplett rauswerfen
OUT = SRC.replace(".tsv", "_nostruct.tsv")
kept = dropped = 0
with open(SRC, newline="", encoding="utf-8") as f, open(OUT, "w", newline="", encoding="utf-8") as o:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    w = csv.writer(o, delimiter="\t"); w.writerow(h)
    i_sid = h.index(sidcol)
    for row in r:
        if row[i_sid] in drop: dropped += 1
        else: w.writerow(row); kept += 1
print(f"Events behalten {kept:,} | entfernt {dropped:,}  ->  {OUT}")