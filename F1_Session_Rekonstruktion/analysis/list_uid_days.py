# list_uid_days.py -- zeigt uids, deren Aktivitaet sich beim Tages-Split in
# MEHRERE Sessions (Tage) aufteilt. Ohne Mindest-Query-Filter: jeder Tag ist
# eine Session. Lesbar, mit Leerzeilen getrennt (Vorschlag des Dozenten).
import csv, random
from collections import defaultdict
from datetime import datetime, timezone
random.seed(42)
csv.field_size_limit(2**31 - 1)

SORTED   = "dis22_window.tsv"
OUT      = "uid_days.txt"
MIN_DAYS = 2       # uid muss ueber >= so viele Tage aktiv sein (sonst kein Split)
LIMIT    = 100     # max. so viele uids in die Datei (Zufallsstichprobe)

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")
def day(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
def fmt_ts(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

# ---- Pass 1: pro uid die Menge der Tage bestimmen -> Multi-Tages-uids finden ----
per_uid_days = defaultdict(set)     # uid -> set(tage)
with open(SORTED, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    its, iu = h.index("ts"), h.index("uid")
    for row in r:
        u = row[iu]
        if u: per_uid_days[u].add(day(row[its]))

interesting = [u for u, ds in per_uid_days.items() if len(ds) >= MIN_DAYS]
random.shuffle(interesting)
chosen = set(interesting[:LIMIT])
print(f"{len(interesting):,} uids ueber >= {MIN_DAYS} Tage aktiv, "
      f"{len(chosen)} in {OUT}", flush=True)

# ---- Pass 2: Events der gewaehlten uids sammeln ----
ev = defaultdict(list)   # uid -> [(ts, query)]
with open(SORTED, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    its, iq, iu = h.index("ts"), h.index("query"), h.index("uid")
    for row in r:
        u = row[iu]
        if u in chosen: ev[u].append((int(row[its]), row[iq]))

# ---- schreiben: pro uid die Tage als eigene Session-Bloecke, mit Leerzeilen ----
with open(OUT, "w", encoding="utf-8") as fo:
    fo.write(f"# UID-Tages-Ansicht: {len(interesting)} uids ueber >= {MIN_DAYS} Tage, "
             f"Stichprobe {len(chosen)}\n\n")
    for u in sorted(ev):
        events = sorted(ev[u], key=lambda x: x[0])
        by_day = defaultdict(list)
        for ts, q in events: by_day[day(ts)].append((ts, q))
        fo.write("=" * 74 + "\n")
        fo.write(f"UID {u} | {len(events)} Queries | {len(by_day)} Tage (= {len(by_day)} Sessions)\n")
        fo.write("=" * 74 + "\n")
        for d in sorted(by_day):
            evs = by_day[d]
            fo.write(f"\n  --- Tag {d}  ({len(evs)} Queries) ---\n")
            for ts, q in evs:
                fo.write(f"      {fmt_ts(ts)}   {q}\n")
        fo.write("\n\n")
print("fertig", flush=True)