# check_timestamps.py
# Prueft: sind die ts innerhalb einer Session WIRKLICH identisch, oder wirken sie
# nur gleich, weil die Anzeige auf Minuten kuerzt? Und wie fein ist ts ueberhaupt?
# Ausgabe ist NDA-sicher: nur Zahlen + Zeitstempel, KEINE Queries.
import csv
from datetime import datetime, timezone
csv.field_size_limit(2**31 - 1)

SOURCES = [
    ("Kaskade", "../../data/cascade_full_1234.tsv",       "session_id"),
    ("DIS22",   "../../data/dis22_sessions_extended.tsv", "ext_session_id"),
]

def s2str(ts):                                   # MIT Sekunden
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

for label, path, sidcol in SOURCES:
    sess = {}                                    # sid -> [count, min_ts, max_ts]
    n = 0; min_aligned = 0; hour_aligned = 0; tmin = None; tmax = None
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f, delimiter="\t"); h = next(r)
        i_sid, i_ts = h.index(sidcol), h.index("ts")
        for row in r:
            sid = row[i_sid]
            if not sid: continue
            ts = int(row[i_ts]); n += 1
            if ts % 60   == 0: min_aligned  += 1   # minutengenau (Sekunden = 00)?
            if ts % 3600 == 0: hour_aligned += 1   # stundengenau?
            if tmin is None or ts < tmin: tmin = ts
            if tmax is None or ts > tmax: tmax = ts
            e = sess.get(sid)
            if e is None: sess[sid] = [1, ts, ts]
            else:
                e[0] += 1
                if ts < e[1]: e[1] = ts
                if ts > e[2]: e[2] = ts

    multi = [(sid, v) for sid, v in sess.items() if v[0] >= 2]     # nur Multi-Event-Sessions
    zero  = sum(1 for _, v in multi if v[1] == v[2])               # Spanne 0 -> alle ts identisch
    sub60 = sum(1 for _, v in multi if 0 < v[2]-v[1] < 60)         # < 1 Minute
    spans = sorted(v[2]-v[1] for _, v in multi)
    med   = spans[len(spans)//2] if spans else 0

    print(f"\n=== {label} ({path}) ===")
    print(f"  Events gesamt:               {n:,}")
    print(f"  Zeitraum:                    {s2str(tmin)}  ...  {s2str(tmax)}")
    print(f"  ts teilbar durch 60 (Minute):  {100*min_aligned/n:5.1f}%   "
          f"-> {'Aufloesung ist MINUTENGENAU (keine Sekunden)' if min_aligned==n else 'es gibt Sekunden-Werte'}")
    print(f"  ts teilbar durch 3600 (Stunde): {100*hour_aligned/n:5.1f}%")
    print(f"  Sessions gesamt:             {len(sess):,}  (davon >=2 Events: {len(multi):,})")
    if multi:
        print(f"  Multi-Event-Sessions mit IDENTISCHEN ts (Spanne 0s): "
              f"{zero:,} ({100*zero/len(multi):.1f}%)")
        print(f"  ... mit Spanne < 60s:        {sub60:,} ({100*sub60/len(multi):.1f}%)")
        print(f"  Median-Spanne (Multi):       {med} s  ({med/60:.1f} min)")

    # Beispiel-Sessions mit SEKUNDEN (nur Zeitstempel -> NDA-sicher)
    ex_zero = [sid for sid, v in multi if v[1]==v[2]     and v[0]>=5][:2]
    ex_span = [sid for sid, v in multi if v[2]-v[1] > 0  and v[0]>=5][:2]
    show = set(ex_zero + ex_span)
    if show:
        buf = {sid: [] for sid in show}
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.reader(f, delimiter="\t"); h = next(r)
            i_sid, i_ts = h.index(sidcol), h.index("ts")
            for row in r:
                if row[i_sid] in show: buf[row[i_sid]].append(int(row[i_ts]))
        print("  --- Beispiel-Sessions (nur Zeitstempel, sekundengenau) ---")
        for sid in show:
            tss = sorted(buf[sid])
            print(f"    Session {sid}: {len(tss)} Events, Spanne {tss[-1]-tss[0]}s")
            for t in tss[:12]:
                print(f"        {s2str(t)}")