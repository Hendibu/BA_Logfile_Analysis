# match_annotation.py <file_A> <file_B>
# Nimmt je K Sessions mit >= MIN_Q Queries aus BEIDEN Session-Dateien und stellt
# jeder Anker-Session die passende Session der ANDEREN Methode gegenueber.
# Match ueber search_id (= gleiche Queries), NICHT ueber uid -> auch bei uids mit
# mehreren Sessions wird die inhaltlich passende getroffen.
# Ausgabe: annotation_vergleich.txt  (enthaelt echte Queries -> bleibt LOKAL, NDA).
import csv, sys, random
from collections import defaultdict
from datetime import datetime, timezone
csv.field_size_limit(2**31 - 1)
random.seed(42)

A_LABEL, A_PATH = "Kaskade", (sys.argv[1] if len(sys.argv) > 1 else "../../data/cascade_full_1234_nostruct.tsv")
B_LABEL, B_PATH = "DIS22",   (sys.argv[2] if len(sys.argv) > 2 else "../../data/dis22_sessions_nostruct.tsv")
K = 20; MIN_Q = 3
OUT = "../../data/annotation_vergleich.txt"

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")
def fmt(ts): return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

def load(path):
    ev = {}; sess = defaultdict(list)          # search_id->(sid,ts,query,uid) ; sid->[search_id]
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
        sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
        i_sid, i_ts, i_q, i_sc, i_uid = (h.index(sidcol), h.index("ts"), h.index("query"),
                                         h.index("search_id"), h.index("uid"))
        for row in r:
            sid = row[i_sid]; sc = row[i_sc]
            if not sid or not sc: continue
            ev[sc] = (sid, int(row[i_ts]), row[i_q], row[i_uid]); sess[sid].append(sc)
    return ev, sess

evA, sessA = load(A_PATH)
evB, sessB = load(B_PATH)
sc2sidB = {sc: evB[sc][0] for sc in evB}
sc2sidA = {sc: evA[sc][0] for sc in evA}

def best_match(anchor_scs, sc2other):
    cnt = defaultdict(int)
    for sc in anchor_scs:
        o = sc2other.get(sc)
        if o: cnt[o] += 1
    if not cnt: return None, 0
    b = max(cnt.items(), key=lambda x: x[1]); return b[0], b[1]

def pick(sess, k):
    cand = [sid for sid, scs in sess.items() if len(scs) >= MIN_Q]
    random.shuffle(cand); return cand[:k]

def render(fo, label, sid, scs, ev):
    rows = sorted((ev[sc][1], ev[sc][2]) for sc in scs)
    uid = ev[scs[0]][3] if scs else "?"
    fo.write(f"--- {label} | session {sid} | {len(scs)} Queries | uid {uid} ---\n")
    for ts, q in rows: fo.write(f"    {fmt(ts)}   {q}\n")

cases = []
for sid in pick(sessA, K):
    scs = sessA[sid]; msid, shared = best_match(scs, sc2sidB)
    cases.append((A_LABEL, sid, scs, evA, B_LABEL, msid, sessB.get(msid, []), evB, shared))
for sid in pick(sessB, K):
    scs = sessB[sid]; msid, shared = best_match(scs, sc2sidA)
    cases.append((B_LABEL, sid, scs, evB, A_LABEL, msid, sessA.get(msid, []), evA, shared))

with open(OUT, "w", encoding="utf-8") as fo:
    for i, (la, sida, scsa, eva, lb, sidb, scsb, evb, shared) in enumerate(cases, 1):
        fo.write("=" * 78 + "\n")
        fo.write(f"FALL {i} | Anker: {la} session {sida}  ->  gematcht: {lb} session {sidb} "
                 f"({shared}/{len(scsa)} gemeinsame Queries)\n")
        fo.write("=" * 78 + "\n")
        render(fo, la + " (Anker)", sida, scsa, eva); fo.write("\n")
        if sidb: render(fo, lb + " (gematcht)", sidb, scsb, evb)
        else:    fo.write(f"--- {lb}: keine passende Session gefunden ---\n")
        fo.write("\n\n")
print(f"{len(cases)} Faelle ({K} je Methode) -> {OUT}")
print("(enthaelt echte Queries -> bleibt lokal, NDA)")