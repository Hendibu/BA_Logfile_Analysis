# interaction_dwell.py <session_file>
# Berechnet je (relevanter) Interaktion die Verweildauer = Zeit bis zum naechsten
# Event derselben uid (aus dem ROHEN Log) und markiert plausibel (>= THRESHOLD s)
# vs. zu kurz. Ausgabe: interactions_dwell.tsv
import csv, re, bisect, os, sys
from collections import defaultdict
from datetime import datetime, timezone
csv.field_size_limit(2**31 - 1)

RAW           = "../../data/log_files.tsv"
INTERACTIONS  = "../../data/interactions.tsv"
OUT           = "../../data/RQ2_interactions_dwell.tsv"
SESSION_FILE  = sys.argv[1] if len(sys.argv) > 1 else "../../data/cascade_full_1234_nostruct.tsv"
THRESHOLD     = 30    # Sekunden: darunter = "zu kurz". ~120 Woerter bei 238 WpM.

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")
def to_epoch(s):
    s = s.strip()
    if not s: return None
    if re.fullmatch(r"\d+(\.\d+)?", s):
        v = float(s); return int(v/1000.0 if v > 1e12 else v)
    for fmt in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M:%S.%f","%Y-%m-%d %H:%M:%S.%f"):
        try: return int(datetime.strptime(s[:26], fmt).replace(tzinfo=timezone.utc).timestamp())
        except ValueError: continue
    return None

def target_sids(session_file):
    s = set()
    if not os.path.exists(session_file): return s
    with open(session_file, newline="", encoding="utf-8") as f:
        r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r); i = h.index("search_id")
        for row in r:
            if row[i]: s.add(row[i])
    return s

def relevant_interactions(path, tsids):
    rel = []; uids = set()
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
        iu, its, ity, imk = h.index("uid"), h.index("ts"), h.index("type"), h.index("merge_key")
        for row in r:
            if row[imk] in tsids:
                rel.append((row[iu], int(row[its]), row[ity], row[imk])); uids.add(row[iu])
    return rel, uids

def build_timeline(raw, uids):
    tl = defaultdict(list)                      # uid -> sortierte Liste aller Event-ts
    with open(raw, newline="", encoding="utf-8") as f:
        r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
        idate, iu = h.index("date"), h.index("uid")
        for row in r:
            if iu >= len(row) or idate >= len(row):   # unvollstaendige Zeile -> ueberspringen
                continue
            u = row[iu]
            if u in uids:
                ts = to_epoch(row[idate])
                if ts is not None: tl[u].append(ts)
    for u in tl: tl[u].sort()
    return tl

def run(raw=RAW, interactions=INTERACTIONS, out=OUT, session_file=SESSION_FILE, threshold=THRESHOLD):
    tsids = target_sids(session_file)
    rel, uids = relevant_interactions(interactions, tsids)
    tl = build_timeline(raw, uids)
    n_pl = n_sh = n_un = 0
    with open(out, "w", newline="", encoding="utf-8") as o:
        w = csv.writer(o, delimiter="\t"); w.writerow(["ts","uid","type","merge_key","dwell","plausible"])
        for u, ts, ty, mk in rel:
            arr = tl.get(u, [])
            j = bisect.bisect_right(arr, ts)    # erstes Event mit ts STRIKT groesser
            if j < len(arr):
                dwell = arr[j] - ts; pl = 1 if dwell >= threshold else 0
            else:
                dwell = -1; pl = 1              # kein Folge-Event -> kein schnelles Weitersuchen
            n_un += (dwell < 0); n_pl += (dwell >= 0 and pl); n_sh += (dwell >= 0 and not pl)
            w.writerow([ts, u, ty, mk, dwell, pl])
    print(f"{len(rel):,} relevante Interaktionen | plausibel {n_pl:,} | zu kurz {n_sh:,} | kein Folge-Event {n_un:,} -> {out}")

if __name__ == "__main__":
    run()