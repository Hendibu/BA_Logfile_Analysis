# stage_vs_dis22.py  [kaskade_datei] [dis22_datei]
# Kreuzt die "stage"-Spalte der Kaskade (s1..s4/grp/gap/boundary/start) mit DIS22:
# fuer jede Kaskaden-Verkettung (stage s1..s4) wird geprueft, ob DIS22 dieselben
# zwei aufeinanderfolgenden Queries ebenfalls zusammenhaelt oder trennt.
# Ausgabe je Stufe: Verkettungen gesamt, davon DIS22 haelt vs. DIS22 trennt
# (= Extra-Verkettung); zusaetzlich Zeitabstands-Verteilung der Extra-Verkettungen
# (Effekt des 90-min-Fensters ggue. DIS22' 5-min-Grenze). Verknuepfung ueber search_id.

import csv, sys
from collections import Counter, defaultdict
csv.field_size_limit(2**31 - 1)

# Eingaben (Argument oder Standard) und die stage-Werte, die eine Verkettung bedeuten
CASC = sys.argv[1] if len(sys.argv) > 1 else "../../data/cascade_full_1234.tsv"
DIS  = sys.argv[2] if len(sys.argv) > 2 else "../../data/dis22_sessions.tsv"
MERGE_STAGES = {"s1", "s2", "s3", "s4"}

# Hilfsfunktion: entfernt NUL-Bytes, damit der CSV-Reader nicht abbricht
def strip_nul(fo):
    for line in fo:
        yield line.replace("\x00", "")

# Ersten passenden Spaltenindex aus einer Kandidatenliste finden
def find(h, cands):
    for c in cands:
        if c in h: return h.index(c)
    return None

# Kopfzeile lesen und die benoetigten Spaltenindizes bestimmen (fehlt eine, Abbruch)
def cols(path, need):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        h = next(csv.reader(strip_nul(f), delimiter="\t"))
    idx = {}
    for key, cands in need.items():
        i = find(h, cands)
        if i is None:
            sys.exit(f"{path}: Spalte '{key}' nicht gefunden. Header: {h}")
        idx[key] = i
    return idx

# 1) DIS22: search_id -> session (Nachschlagetabelle, welche DIS22-Session eine Query hat)
di = cols(DIS, {"sid": ["search_id"], "sess": ["session_id","sid","session"]})
dis_of = {}
with open(DIS, newline="", encoding="utf-8", errors="replace") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); next(r)
    for row in r:
        if max(di["sid"], di["sess"]) >= len(row): continue
        sq = row[di["sid"]].strip()
        if sq: dis_of[sq] = row[di["sess"]]

# 2) Kaskade streamen: stage-Spalte + search_id + ts
ci = cols(CASC, {"sid": ["search_id"], "sess": ["session_id","sid","session"],
                 "stage": ["stage"], "ts": ["ts"]})

# Zaehler je Stufe: gesamt, von DIS22 getrennt, von DIS22 gehalten, unbekannt; + Zeitabstands-Buckets
stage_total = Counter()
stage_split = Counter()
stage_keep  = Counter()
stage_unk   = Counter()
gap_bucket  = defaultdict(Counter)

# Zeitabstand eines Paares in eine grobe Klasse einordnen
def bucket(g):
    if g < 300:  return "< 5 min"
    if g < 600:  return "5-10 min"
    if g < 1800: return "10-30 min"
    if g <= 5400:return "30-90 min"
    return "> 90 min"

# Kaskade zeilenweise lesen; bei jeder Verkettung (s1..s4) das Vorgaenger-Paar in DIS22 nachschlagen
with open(CASC, newline="", encoding="utf-8", errors="replace") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); next(r)
    prev_sid = None; prev_ts = None
    for row in r:
        if max(ci.values()) >= len(row):
            prev_sid = None; continue
        st  = row[ci["stage"]].strip()
        sq  = row[ci["sid"]].strip()
        ts  = row[ci["ts"]].strip()
        stage_total[st] += 1
        # Nur Verkettungen pruefen: haelt DIS22 dasselbe Paar zusammen (keep) oder trennt es (split)?
        if st in MERGE_STAGES and prev_sid is not None:
            a = dis_of.get(prev_sid); b = dis_of.get(sq)
            if a is None or b is None:
                stage_unk[st] += 1
            elif a == b:
                stage_keep[st] += 1
            else:
                # Extra-Verkettung: nur die Kaskade verbindet -> Zeitabstand in Bucket zaehlen
                stage_split[st] += 1
                try:
                    g = int(float(ts)) - int(float(prev_ts)); g = max(g, 0)
                    gap_bucket[st][bucket(g)] += 1
                except (ValueError, TypeError):
                    pass
        prev_sid = sq; prev_ts = ts

# 3) Ausgabe
print("=" * 72)
print("WELCHE KASKADEN-STUFE MACHT DIE SESSIONS LAENGER?  (stage x DIS22)")
print("=" * 72)
print(f"Kaskade: {CASC}")
print(f"DIS22  : {DIS}\n")

# Haeufigkeit aller stage-Werte
print("Haeufigkeit aller stage-Werte in der Kaskade:")
for st, c in stage_total.most_common():
    print(f"   {st:<10}{c:>14,}")
print()

# Gesamtbilanz: wie viele Verkettungen macht die Kaskade zusaetzlich zu DIS22
merges = sum(stage_total[s] for s in MERGE_STAGES)
extra  = sum(stage_split.values())
print(f"Kaskaden-Verkettungen gesamt (s1..s4)        : {merges:,}")
if merges:
    print(f"davon von DIS22 GETRENNT (Extra-Verkettungen): {extra:,}  ({100*extra/merges:.1f}%)")
print()

# Aufschluesselung je Stufe (verkettet / DIS22 trennt / DIS22 haelt / unbekannt / Extra-Anteil)
print(f"{'Stufe':<8}{'verkettet':>14}{'DIS22 trennt':>16}{'DIS22 haelt':>14}{'unbek.':>10}{'Extra-%':>10}")
print("-" * 72)
for st in ["s1", "s2", "s3", "s4"]:
    tot = stage_total.get(st, 0)
    sp, kp, un = stage_split.get(st,0), stage_keep.get(st,0), stage_unk.get(st,0)
    base = sp + kp
    pct = f"{100*sp/base:.1f}%" if base else "-"
    print(f"{st:<8}{tot:>14,}{sp:>16,}{kp:>14,}{un:>10,}{pct:>10}")
print("-" * 72)
print("'DIS22 trennt' = diese Verkettung macht NUR die Kaskade -> verlaengert.")
print()

# Zeitabstands-Verteilung der Extra-Verkettungen je Stufe
print("Zeitabstand der Extra-Verkettungen je Stufe")
print("(zeigt den Effekt des 90-min-Fensters ggue. DIS22' 5-min-Grenze):")
order = ["< 5 min","5-10 min","10-30 min","30-90 min","> 90 min"]
for st in ["s1", "s2", "s3", "s4"]:
    if not gap_bucket[st]: continue
    tot = sum(gap_bucket[st].values())
    parts = "  ".join(f"{k}:{100*gap_bucket[st][k]/tot:.0f}%"
                      for k in order if gap_bucket[st].get(k))
    print(f"   {st}: {parts}")