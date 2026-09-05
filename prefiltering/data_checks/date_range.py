# date_range.py <logfile> [date_spalte]
# Findet frueheste und spaeteste Zeit im (grossen) Rohlog, streamend, O(1)-Speicher.
# Erkennt automatisch ISO-Strings (z. B. 2025-08-11 23:04:30) oder Epoch-Zahlen
# (Sekunden oder Millisekunden). Gibt nur min/max aus (NDA-sicher).
import sys, re
from datetime import datetime, timezone

PATH = sys.argv[1] if len(sys.argv) > 1 else "log_files.tsv"
COL  = sys.argv[2] if len(sys.argv) > 2 else "date"

def is_epoch(s):
    return bool(re.fullmatch(r"\d{9,}(\.\d+)?", s))

with open(PATH, encoding="utf-8", errors="replace") as f:
    header = f.readline().replace("\x00", "").rstrip("\n").split("\t")
    if COL in header:
        idx = header.index(COL)
    elif "ts" in header:
        idx = header.index("ts"); COL = "ts"
    else:
        idx = 0; COL = header[0]

    lo = hi = None; n = 0; epoch = None
    for line in f:
        parts = line.replace("\x00", "").rstrip("\n").split("\t")
        if idx >= len(parts): continue
        v = parts[idx].strip()
        if not v: continue
        if epoch is None:
            epoch = is_epoch(v)
        n += 1
        if epoch:
            try: x = float(v)
            except ValueError: continue
        else:
            x = v
        if lo is None or x < lo: lo = x
        if hi is None or x > hi: hi = x

print(f"Spalte           : {COL}")
print(f"gelesene Werte   : {n:,}")
if lo is None:
    print("keine Werte gefunden"); sys.exit()
if epoch:
    def fmt(x):
        s = x/1000 if x > 1e12 else x          # ms -> s falls noetig
        return datetime.fromtimestamp(s, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"frueheste (min)  : {lo}  ->  {fmt(lo)}")
    print(f"spaeteste (max)  : {hi}  ->  {fmt(hi)}")
else:
    print(f"frueheste (min)  : {lo}")
    print(f"spaeteste (max)  : {hi}")