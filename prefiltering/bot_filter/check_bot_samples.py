# check_bot_samples.py <session_file>
# Gegenprobe: zeigt K geflaggte (metronomartige) und K behaltene Sessions im Klartext,
# mit Zeitabstaenden zwischen den Queries. Ausgabe bleibt LOKAL (echte Queries, NDA).
import csv, sys, random, statistics
from collections import defaultdict
from datetime import datetime, timezone
csv.field_size_limit(2**31 - 1)

SRC = sys.argv[1] if len(sys.argv) > 1 else "../../data/dis22_sessions.tsv"
K = 15
MIN_TIMING_Q, MAX_MEAN_GAP, REG_STD = 3, 12, 2.0
OUT = "../../data/bot_check_samples.txt"
rnd = random.Random(42)

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")
def fmt(ts): return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

ts_by = defaultdict(list); uid_by = {}
with open(SRC, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
    i_sid, i_ts, i_uid = h.index(sidcol), h.index("ts"), h.index("uid")
    for row in r:
        sid = row[i_sid]
        if not sid: continue
        ts_by[sid].append(int(row[i_ts])); uid_by.setdefault(sid, row[i_uid])

flag = []; good = []
for sid, tss in ts_by.items():
    c = len(tss)
    if c < MIN_TIMING_Q: continue
    tss.sort(); gaps = [tss[i+1]-tss[i] for i in range(c-1)]
    mg = sum(gaps)/len(gaps); sd = statistics.pstdev(gaps)
    (flag if (mg <= MAX_MEAN_GAP and sd <= REG_STD) else good).append((sid, mg, sd))
rnd.shuffle(flag); rnd.shuffle(good)
sel = flag[:K] + good[:K]
info = {s[0]: (s[1], s[2]) for s in sel}; want = set(info)

ev = defaultdict(list)
with open(SRC, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    i_sid, i_ts, i_q = h.index(sidcol), h.index("ts"), h.index("query")
    for row in r:
        if row[i_sid] in want: ev[row[i_sid]].append((int(row[i_ts]), row[i_q]))

with open(OUT, "w", encoding="utf-8") as fo:
    def block(title, sids):
        fo.write(f"\n########## {title} ##########\n")
        for sid in sids:
            rows = sorted(ev[sid]); mg, sd = info[sid]
            fo.write(f"\n### {sid} | uid {uid_by[sid]} | {len(rows)} Queries | "
                     f"mean_gap {mg:.1f}s | std {sd:.2f}s\n")
            prev = None
            for ts, q in rows:
                gap = f"+{ts-prev}s" if prev is not None else "start"
                fo.write(f"    {fmt(ts)}  {gap:>7}  {q}\n"); prev = ts
    block("BOT-ARTIG (geflaggt) -- sollten metronomartig/automatisiert wirken", [s[0] for s in flag[:K]])
    block("GUT (behalten) -- sollten menschlich wirken", [s[0] for s in good[:K]])
print(f"{len(flag[:K])} geflaggte + {len(good[:K])} gute Beispiel-Sessions -> {OUT}")
print("(Datei enthaelt echte Queries -> bleibt lokal, NDA)")