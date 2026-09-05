# compare_sessions.py -- RQ1-Gegenueberstellung + Effekt der DIS22-Extension.
import csv, os, numpy as np
csv.field_size_limit(2**31 - 1)

# (Anzeigename, Datei, Session-Spalte, [Zeit-Dateien zum Aufsummieren])
METHODS = [
    ("Kaskade",       "cascade_full_1234.tsv",       "session_id",     ["cascade_full_1234.tsv.time"]),
    ("DIS22 Bildung", "dis22_sessions.tsv",          "session_id",     ["dis22_sessions.tsv.time"]),
    ("DIS22 +Ext",    "dis22_sessions_extended.tsv", "ext_session_id", ["dis22_sessions.tsv.time","dis22_sessions_extended.tsv.time"]),
    ("UUID_days",          "uuid_day_sessions.tsv",           "session_id",     ["uuid_day_sessions.tsv.time"]),
]

def analyze(path, sidcol, timefiles):
    if not os.path.exists(path): return None
    sess = {}; rows = 0; no_sess = 0
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f, delimiter="\t"); h = next(r)
        i_sid, i_ts = h.index(sidcol), h.index("ts")
        for row in r:
            rows += 1; sid = row[i_sid]
            if not sid: no_sess += 1; continue
            ts = int(row[i_ts]); e = sess.get(sid)
            if e is None: sess[sid] = [1, ts, ts]
            else:
                e[0] += 1
                if ts < e[1]: e[1] = ts
                if ts > e[2]: e[2] = ts
    L = np.array([v[0] for v in sess.values()])
    D = np.array([(v[2]-v[1])/60.0 for v in sess.values()])
    rt = 0.0; have = False
    for tf in timefiles:
        if os.path.exists(tf):
            try: rt += float(open(tf).read().strip()); have = True
            except Exception: pass
    return dict(rows=rows, no_sess=no_sess, n=len(sess), L=L, D=D, rt=(rt if have else None))

def fmt_rt(sec):
    if sec is None: return "?"
    return f"{sec/3600:.2f} h" if sec >= 3600 else f"{sec/60:.2f} min"

res = [(name, analyze(p, sc, tf)) for name, p, sc, tf in METHODS]
def col(r):
    if r is None: return ["--"]*9
    L, D = r["L"], r["D"]; single = int((L == 1).sum())
    return [fmt_rt(r["rt"]), f"{r['rows']:,}", f"{r['n']:,}",
            f"{L.mean():.2f}", f"{int(np.median(L))}", f"{L.max()}",
            f"{100*single/len(L):.1f}%", f"{D.mean():.1f}", f"{np.median(D):.1f}"]

labels = ["Laufzeit","Events","Sessions","O-Laenge","Med-Laenge","Max-Laenge",
          "Singleton","O-Dauer(min)","Med-Dauer(min)"]
cols = [col(r) for _, r in res]
header = [""] + [n for n, _ in res]
table = [header] + [[labels[i]] + [cols[m][i] for m in range(len(res))] for i in range(len(labels))]
wd = [max(len(str(table[row][c])) for row in range(len(table))) for c in range(len(header))]
print("\n=== RQ1: Vergleich der Session-Erstellungsmethoden ===\n")
for row in table:
    print("  " + "  ".join(str(row[c]).ljust(wd[c]) for c in range(len(row))))
u = next((r for n, r in res if n == "UUID"), None)
if u: print(f"\n  UUID: {u['no_sess']:,} Events ohne uid (nicht gruppierbar).")
b = next((r for n, r in res if n == "DIS22 Bildung"), None)
e = next((r for n, r in res if n == "DIS22 +Ext"), None)
if b and e:
    print(f"\n  Effekt der Extension: {b['n']:,} -> {e['n']:,} Sessions "
          f"({100*(b['n']-e['n'])/b['n']:.1f}% weniger), "
          f"O-Laenge {b['L'].mean():.2f} -> {e['L'].mean():.2f}.")