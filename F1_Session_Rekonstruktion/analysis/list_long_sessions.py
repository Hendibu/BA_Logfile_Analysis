# list_long_sessions.py -- listet Sessions mit >= MIN_Q Queries lesbar auf,
# getrennt fuer Kaskade und DIS22, zum manuellen Durchsehen/Auswaehlen.
# Ausgabe: cascade_long.txt und dis22_long.txt (Sessions durch Leerzeilen getrennt).
import csv, random
from collections import Counter
from datetime import datetime, timezone
random.seed(42)
csv.field_size_limit(2**31 - 1)

MIN_Q = 3
LIMIT = 400          # max. so viele Sessions je Datei (Zufallsstichprobe; hoeher = mehr)

SOURCES = [
    ("Kaskade", "../../data/cascade_full_1234_nobots.tsv",       "session_id",     "../../data/cascade_long.txt"),
    ("DIS22",   "../../data/dis22_sessions_nobots.tsv", "session_id", "../../data/dis22_long.txt"),
]

def fmt_ts(s):
    return datetime.fromtimestamp(int(s), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

for label, path, sidcol, out in SOURCES:
    sample = []; seen = 0
    def consider(sid, buf):                      # Reservoir-Sampling ueber alle >=MIN_Q Sessions
        global seen
        if len(buf) < MIN_Q: return
        seen += 1
        if len(sample) < LIMIT: sample.append((sid, buf))
        else:
            j = random.randint(0, seen - 1)
            if j < LIMIT: sample[j] = (sid, buf)
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
        i_sid, i_ts, i_q, i_uid = h.index(sidcol), h.index("ts"), h.index("query"), h.index("uid")
        cur = None; buf = []
        for row in r:                            # Sessions liegen zusammenhaengend vor
            sid = row[i_sid]
            if sid != cur:
                if cur is not None: consider(cur, buf)
                cur = sid; buf = []
            buf.append((row[i_ts], row[i_q], row[i_uid]))
        if cur is not None: consider(cur, buf)

    with open(out, "w", encoding="utf-8") as fo:
        fo.write(f"# {label}: {len(sample)} von {seen} Sessions mit >= {MIN_Q} Queries "
                 f"(Zufallsstichprobe, LIMIT={LIMIT})\n\n")
        for sid, buf in sample:
            uids = Counter(u for _, _, u in buf)
            uidstr = ", ".join(f"{u}({c})" for u, c in uids.most_common())
            fo.write(f"### {label}-Session {sid} | {len(buf)} Queries | uids: {uidstr}\n")
            for ts, q, u in buf:
                fo.write(f"    {fmt_ts(ts)}   {q}\n")
            fo.write("\n\n")
    print(f"{label}: {seen:,} Sessions mit >= {MIN_Q} Queries gefunden, "
          f"{len(sample)} in {out} geschrieben")