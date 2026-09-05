# compare_split.py  [falsche_datei] [richtige_datei]
# --------------------------------------------------------------------------
# Vergleicht die ALTEN Sessions (globaler Strom, ohne uid-Tag-Aufteilung, oft
# mehrere uids pro Session) mit den NEUEN Sessions (pro uid-Tag rekonstruiert).
# Zeigt:
#   (A) Gesamtstatistik beider Dateien (Sessionzahl, Groessenverteilung).
#   (B) Wie sich die LANGEN alten Sessions in neue Sessions aufsplitten.
#   (C) Eine Beispiel-Session: welche Query in welche neue Session gewandert ist.
#
# Verknuepfung der Events beider Dateien ueber die search_id (eindeutig je Query).
# Events der alten Session, die in der neuen Datei fehlen, sind wegen LEERER uid
# entfernt worden (die neue Datei baut auf dis22_uidday.tsv auf).
#
# (A) und (B) sind Aggregate -> NDA-sicher / teilbar.
# (C) enthaelt echte Queries -> bleibt LOKAL, nicht an Dritte/AI weitergeben.
# --------------------------------------------------------------------------
import csv, sys, os
from collections import Counter
from datetime import datetime, timezone
csv.field_size_limit(2**31 - 1)

WRONG = sys.argv[1] if len(sys.argv) > 1 else "(WRONG)cascade_full_1234.tsv"
RIGHT = sys.argv[2] if len(sys.argv) > 2 else "cascade_full_1234.tsv"
LONG_MIN = 4          # ab wie vielen Queries eine alte Session als "lang" gilt

def strip_nul(fo):
    for line in fo:
        yield line.replace("\x00", "")

def find_col(header, candidates):
    for c in candidates:
        if c in header:
            return header.index(c)
    return None

def detect_cols(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        h = next(csv.reader(strip_nul(f), delimiter="\t"))
    isid = find_col(h, ["search_id"])
    iu   = find_col(h, ["uid"])
    its  = find_col(h, ["ts"])
    iq   = find_col(h, ["query"])
    isess= find_col(h, ["session_id","sid","session","sessionid","sess_id","label"])
    if isid is None or isess is None:
        sys.exit(f"{path}: brauche search_id und eine Session-Spalte. Header: {h}")
    return h, isid, iu, its, iq, isess

def stats_from_hist(hist):
    """hist: Counter{groesse: anzahl_sessions} -> Kennzahlen."""
    n = sum(hist.values())
    if n == 0:
        return dict(n=0, mean=0, median=0, mx=0, singleton_pct=0, ge4_pct=0)
    total = sum(g*c for g, c in hist.items())
    mx = max(hist)
    singleton = hist.get(1, 0)
    ge4 = sum(c for g, c in hist.items() if g >= 4)
    half = n / 2
    run = 0
    median = mx
    for g in sorted(hist):
        run += hist[g]
        if run >= half:
            median = g
            break
    return dict(n=n, mean=total/n, median=median, mx=mx,
                singleton_pct=100*singleton/n, ge4_pct=100*ge4/n)

def ep(ts):
    try:
        return datetime.fromtimestamp(int(float(ts)), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)

# 1) RICHTIGE Datei: search_id -> neue Session, + Groessenverteilung
rh, r_sid, r_uid, r_ts, r_q, r_sess = detect_cols(RIGHT)
right_sess_of = {}                 # search_id -> neue session_id
right_size = Counter()             # neue session_id -> Eventzahl
canon = {}                         # String-Interning fuer Session-IDs (Speicher sparen)
with open(RIGHT, newline="", encoding="utf-8", errors="replace") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); next(r)
    for row in r:
        if r_sess >= len(row) or r_sid >= len(row):
            continue
        s = canon.setdefault(row[r_sess], row[r_sess])
        right_size[s] += 1
        sq = row[r_sid].strip()
        if sq:
            right_sess_of[sq] = s

# 2) FALSCHE Datei streamen (Sessions liegen zusammenhaengend vor)
wh, w_sid, w_uid, w_ts, w_q, w_sess = detect_cols(WRONG)

wrong_size_hist = Counter()
split_hist      = Counter()
uidcount_hist   = Counter()
sum_dropped = sum_split = sum_uids = n_long = 0
best_example = None

def finalize(sid, rows):
    global sum_dropped, sum_split, sum_uids, n_long, best_example
    size = len(rows)
    wrong_size_hist[size] += 1
    if size < LONG_MIN:
        return
    n_long += 1
    new_sessions = set(); dropped = 0; uids = set()
    for (u, ts, sq, q) in rows:
        if u:                       # leere uid nicht als echten Nutzer zaehlen
            uids.add(u)
        tgt = right_sess_of.get(sq)
        if tgt is None:
            dropped += 1
        else:
            new_sessions.add(tgt)
    nsplit = len(new_sessions)
    split_hist[nsplit] += 1
    uidcount_hist[len(uids)] += 1
    sum_split += nsplit; sum_dropped += dropped; sum_uids += len(uids)
    if 5 <= size <= 20 and nsplit >= 2 and len(uids) >= 2:
        score = (nsplit, len(uids), -size)
        if best_example is None or score > best_example[0]:
            best_example = (score, sid, rows[:])

with open(WRONG, newline="", encoding="utf-8", errors="replace") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); next(r)
    cur = None; buf = []
    for row in r:
        if w_sess >= len(row) or w_sid >= len(row):
            continue
        s = row[w_sess]
        if s != cur:
            if cur is not None:
                finalize(cur, buf)
            cur = s; buf = []
        u  = row[w_uid].strip() if (w_uid is not None and w_uid < len(row)) else ""
        ts = row[w_ts]  if (w_ts  is not None and w_ts  < len(row)) else ""
        sq = row[w_sid].strip()
        q  = row[w_q]   if (w_q   is not None and w_q   < len(row)) else ""
        buf.append((u, ts, sq, q))
    if cur is not None:
        finalize(cur, buf)

# 3) Ausgabe
ws = stats_from_hist(wrong_size_hist)
rs = stats_from_hist(dict(Counter(right_size.values())))

print("=" * 70)
print("(A) GESAMTVERGLEICH   [Aggregate -> teilbar]")
print("=" * 70)
print(f"{'':28}{'ALT (global)':>18}{'NEU (uid-Tag)':>18}")
print(f"{'Sessions gesamt':28}{ws['n']:>18,}{rs['n']:>18,}")
print(f"{'Singletons (%)':28}{ws['singleton_pct']:>17.1f}%{rs['singleton_pct']:>17.1f}%")
print(f"{'Sessions mit >=4 Q (%)':28}{ws['ge4_pct']:>17.1f}%{rs['ge4_pct']:>17.1f}%")
print(f"{'mittlere Groesse':28}{ws['mean']:>18.2f}{rs['mean']:>18.2f}")
print(f"{'Median-Groesse':28}{ws['median']:>18,}{rs['median']:>18,}")
print(f"{'max. Groesse':28}{ws['mx']:>18,}{rs['mx']:>18,}")

print()
print("=" * 70)
print(f"(B) AUFSPLITTUNG DER LANGEN ALTEN SESSIONS (>= {LONG_MIN} Queries)   [teilbar]")
print("=" * 70)
if n_long:
    print(f"betrachtete lange alte Sessions      : {n_long:,}")
    print(f"-> im Schnitt distinct uids je Session: {sum_uids/n_long:.2f}")
    print(f"-> zerfallen im Schnitt in ... neue Sessions: {sum_split/n_long:.2f}")
    print(f"-> im Schnitt entfernte Events (leere uid) je Session: {sum_dropped/n_long:.2f}")
    print()
    print("Verteilung: in wie viele neue Sessions zerfaellt eine alte lange Session?")
    print(f"  {'neue Sessions':>14}{'Anzahl alter Sessions':>26}")
    for k in sorted(split_hist):
        if k >= 10:
            continue
        print(f"  {k:>14}{split_hist[k]:>26,}")
    tenplus = sum(c for g, c in split_hist.items() if g >= 10)
    if tenplus:
        print(f"  {'10+':>14}{tenplus:>26,}")
else:
    print("Keine langen alten Sessions gefunden.")

print()
print("=" * 70)
print("(C) BEISPIEL-SESSION   [enthaelt echte Queries -> LOKAL behalten]")
print("=" * 70)
if best_example is None:
    print("Kein passendes Beispiel (5-20 Queries, >=2 neue Sessions, >=2 uids) gefunden.")
else:
    _, sid, rows = best_example
    rows_sorted = sorted(rows, key=lambda x: (x[1] if x[1] else ""))
    print(f"Alte Session-ID: {sid}   ({len(rows)} Queries)")
    nummer = {}
    for (u, ts, sq, q) in rows_sorted:
        tgt = right_sess_of.get(sq)
        if tgt is not None and tgt not in nummer:
            nummer[tgt] = f"NEU-{len(nummer)+1}"
    print(f"-> zerfaellt in {len(nummer)} neue Sessions (+ ggf. Events mit leerer uid = entfernt)\n")
    print(f"  {'Zeitpunkt (UTC)':<21}{'uid':<16}{'neue Session':<14} Query")
    print("  " + "-" * 68)
    for (u, ts, sq, q) in rows_sorted:
        tgt = right_sess_of.get(sq)
        neu = nummer.get(tgt, "-(entfernt)")
        ushort = (u[:14] + "..") if len(u) > 14 else u
        print(f"  {ep(ts):<21}{ushort:<16}{neu:<14} {q}")
    print()
    print("  Lies es so: gleiche 'neue Session' = landet jetzt in derselben Session;")
    print("  verschiedene = wurde aufgetrennt; '-(entfernt)' = Event hatte keine uid.")