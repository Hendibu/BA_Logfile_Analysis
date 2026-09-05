# analyze_bot_uids.py <session_file>
# Stuft Sessions als bot-artig ein (SCHNELL und GLEICHMAESSIG getaktet), merkt sich die
# uid, misst den Overlap Bot-/Gute-uids und schreibt eine Detail-Datei mit der
# Standardabweichung der Zeitluecken je geflaggter Session. NDA-sichere Aggregate.
# Schwellen literaturgestuetzt: ~13 s mittlere SERP-Sichtung (Jiang, He & Allan 2014).
import csv, sys, statistics
from collections import defaultdict, Counter
csv.field_size_limit(2**31 - 1)

SRC          = sys.argv[1] if len(sys.argv) > 1 else "dis22_sessions.tsv"
MIN_Q        = 3      # >=3 Queries -> mind. 2 Luecken, um Gleichmaessigkeit zu beurteilen
REG_STD      = 2.0    # Standardabw. der Zeitluecken <= das  -> "gleichmaessig getaktet"
MAX_MEAN_GAP = 12     # mittlere Luecke <= das (s) -> schneller als ~13 s SERP-Sichtung
DETAIL_OUT   = "bot_sessions_detail.tsv"   # je geflaggter Session: uid, n, mean_gap, std_gap

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

sess_ts = defaultdict(list); sess_uid = {}
with open(SRC, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
    i_sid, i_ts, i_uid = h.index(sidcol), h.index("ts"), h.index("uid")
    for row in r:
        sid = row[i_sid]
        if not sid: continue
        sess_ts[sid].append(int(row[i_ts]))
        if sid not in sess_uid: sess_uid[sid] = row[i_uid]

uid_bot = defaultdict(int); uid_good = defaultdict(int)
n_multi = n_bot = 0; gap_modes = Counter(); std_buckets = Counter()
det = open(DETAIL_OUT, "w", newline="", encoding="utf-8"); dw = csv.writer(det, delimiter="\t")
dw.writerow(["session_id", "uid", "n_queries", "mean_gap_s", "std_gap_s"])

for sid, tss in sess_ts.items():
    if len(tss) < MIN_Q: continue
    tss.sort()
    gaps = [tss[i+1] - tss[i] for i in range(len(tss)-1)]
    n_multi += 1
    mean_gap = sum(gaps) / len(gaps); std_gap = statistics.pstdev(gaps)
    u = sess_uid[sid]
    if std_gap <= REG_STD and mean_gap <= MAX_MEAN_GAP:
        n_bot += 1; uid_bot[u] += 1
        gap_modes[round(mean_gap)] += 1
        std_buckets["0 (exakt gleich)" if std_gap == 0 else
                    "<=0.5" if std_gap <= 0.5 else
                    "<=1"   if std_gap <= 1.0 else "<=2"] += 1
        dw.writerow([sid, u, len(tss), f"{mean_gap:.1f}", f"{std_gap:.2f}"])
    else:
        uid_good[u] += 1
det.close()

bot_uids, good_uids = set(uid_bot), set(uid_good)
both = bot_uids & good_uids; only_bot = bot_uids - good_uids

print(f"Datei: {SRC}  (Schwellen: mean_gap<={MAX_MEAN_GAP}s, std<={REG_STD}s, >= {MIN_Q} Queries)")
print(f"Sessions mit >= {MIN_Q} Queries: {n_multi:,} | bot-artig: {n_bot:,} "
      f"({100*n_bot/max(n_multi,1):.1f}%)\n")
print("--- uid-Overlap ---")
print(f"uids mit >=1 bot-artigen Session:  {len(bot_uids):,}")
print(f"uids mit >=1 guten Session:        {len(good_uids):,}")
print(f"uids mit BEIDEM (Overlap):         {len(both):,} ({100*len(both)/max(len(bot_uids),1):.1f}% der Bot-uids)")
print(f"uids NUR bot-artig (klar Bot):     {len(only_bot):,}")
print("\n--- Gleichmaessigkeit der geflaggten Sessions (Std der Luecken) ---")
for k in ("0 (exakt gleich)", "<=0.5", "<=1", "<=2"):
    if std_buckets[k]: print(f"   Std {k}: {std_buckets[k]:,}")
print("\n--- typische Taktung (mittlere Luecke, s) ---")
for g, c in gap_modes.most_common(8):
    print(f"   ~{g}s: {c:,} Sessions")
print(f"\nDetail je geflaggter Session -> {DETAIL_OUT}")