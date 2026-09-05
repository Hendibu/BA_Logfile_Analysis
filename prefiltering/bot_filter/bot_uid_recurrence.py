# bot_uid_recurrence.py <session_file>
# Zeigt, ob/wie stark Bot-uids wiederverwendet werden: Verteilung der Bot-Sessions
# je Bot-uid, Konzentration, und ob die Top-Bot-uids rein oder geteilt (VPN) sind.
import csv, sys, statistics
from collections import defaultdict, Counter
csv.field_size_limit(2**31 - 1)

SRC = sys.argv[1] if len(sys.argv) > 1 else "cascade_full_1234.tsv"
MIN_TIMING_Q, MAX_MEAN_GAP, REG_STD = 3, 12, 2.0

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

ts_by = defaultdict(list); uid_by = {}
with open(SRC, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
    i_sid, i_ts, i_uid = h.index(sidcol), h.index("ts"), h.index("uid")
    for row in r:
        sid = row[i_sid]
        if not sid: continue
        ts_by[sid].append(int(row[i_ts])); uid_by.setdefault(sid, row[i_uid])

uid_bot = Counter(); uid_good = Counter()
for sid, tss in ts_by.items():
    c = len(tss)
    if c < MIN_TIMING_Q: continue
    tss.sort(); gaps = [tss[i+1]-tss[i] for i in range(c-1)]
    mg = sum(gaps)/len(gaps); sd = statistics.pstdev(gaps)
    u = uid_by[sid]
    if mg <= MAX_MEAN_GAP and sd <= REG_STD: uid_bot[u] += 1
    else:                                    uid_good[u] += 1

counts = sorted(uid_bot.values(), reverse=True)
total = sum(counts); n = len(counts)
print(f"{n:,} Bot-uids | {total:,} Bot-Sessions | Schnitt {total/max(n,1):.1f} Bot-Sessions/uid")
if counts:
    p = lambda q: counts[min(n-1, int(q*n))]
    print(f"Bot-Sessions je Bot-uid: Median {statistics.median(counts)}, "
          f"90-Perz {p(0.10)}, 99-Perz {p(0.01)}, max {counts[0]:,}")
    recurring = sum(1 for c in counts if c >= 2)
    print(f"Wiederverwendet (>=2 Bot-Sessions): {recurring:,} ({100*recurring/n:.1f}% der Bot-uids)")
    top10 = sum(counts[:10])
    print(f"Konzentration: die 10 aktivsten Bot-uids = {top10:,} Bot-Sessions "
          f"({100*top10/total:.1f}% aller Bot-Sessions)")
    print("\nTop-Bot-uids (Bot-Sessions / gute Sessions):")
    for u, cbot in uid_bot.most_common(10):
        tag = "REIN Bot" if uid_good.get(u, 0) == 0 else "geteilt (auch gut)"
        print(f"   {u[:16]}… : {cbot:>5} Bot / {uid_good.get(u,0):>4} gut   [{tag}]")