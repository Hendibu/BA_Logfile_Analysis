# filter_bot_sessions.py <session_file>
# Entfernt GANZE Sessions, die entweder
#   (A) NUR aus strukturierten Filter-Queries bestehen UND kleine Zeitspanne haben
#       (Bot-Sweeps ueber die Jahreszahl), ODER
#   (B) mehr als 1 Query haben und aus der EXAKT selben Query bestehen (Wiederholung).
# Exposé 4.3: Session-Level-Bot-Filter NACH der Rekonstruktion. sidcol autom. erkannt.
import csv, sys, re
csv.field_size_limit(2**31 - 1)

SRC = sys.argv[1] if len(sys.argv) > 1 else "../../data/dis22_sessions.tsv"
MAX_SPAN_SEC = 120     # (A) Bot-Sweep, wenn alle Queries strukturiert UND Spanne <= das
PAT = re.compile(r'yearPublished|(<=|>=|<|>)\s*\d|\bAND\s*\(|\bOR\s*\(', re.IGNORECASE)

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

# Pass 1: pro Session -> [count, all_struct, min_ts, max_ts, first_hash, all_same]
agg = {}
with open(SRC, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
    i_sid, i_ts, i_q = h.index(sidcol), h.index("ts"), h.index("query")
    for row in r:
        sid = row[i_sid]
        if not sid: continue
        ts = int(row[i_ts]); q = row[i_q]
        m = bool(PAT.search(q)); qh = hash(q); e = agg.get(sid)
        if e is None: agg[sid] = [1, m, ts, ts, qh, True]
        else:
            e[0] += 1; e[1] = e[1] and m
            if ts < e[2]: e[2] = ts
            if ts > e[3]: e[3] = ts
            if qh != e[4]: e[5] = False          # andere Query gesehen -> nicht alle gleich

sweep = set(); dup = set()
for sid, (c, allm, mn, mx, qh, allsame) in agg.items():
    if allm and (mx - mn) <= MAX_SPAN_SEC: sweep.add(sid)     # (A)
    if c >= 2 and allsame:                    dup.add(sid)     # (B)
bot = sweep | dup
print(f"{len(agg):,} Sessions | Bot-Sweeps (A): {len(sweep):,} | "
      f"reine Wiederholungen (B): {len(dup):,} | entfernt gesamt: {len(bot):,}")

# Pass 2: Sessions in 'bot' komplett rauswerfen
OUT = SRC.replace(".tsv", "_nobots.tsv")
kept = dropped = 0
with open(SRC, newline="", encoding="utf-8") as f, open(OUT, "w", newline="", encoding="utf-8") as o:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    w = csv.writer(o, delimiter="\t"); w.writerow(h)
    i_sid = h.index(sidcol)
    for row in r:
        if row[i_sid] in bot: dropped += 1
        else: w.writerow(row); kept += 1
print(f"Events behalten {kept:,} | entfernt {dropped:,} -> {OUT}")