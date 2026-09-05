# stage_vs_dis22.py  [kaskade_datei] [dis22_datei]
# --------------------------------------------------------------------------
# Nutzt die vorhandene "stage"-Spalte der Kaskade (s1..s4/grp/gap/boundary/start)
# und kreuzt sie mit DIS22: Fuer jede Kaskaden-VERKETTUNG (stage in s1..s4, also
# "gleiche Session wie Vorgaenger") wird geprueft, ob DIS22 dieselben zwei
# aufeinanderfolgenden Queries ebenfalls in einer Session hat -- oder trennt.
#
# Ergebnis pro Stufe:
#   - wie oft die Stufe verkettet hat (gesamt)
#   - davon: DIS22 haelt ebenfalls zusammen  vs.  DIS22 TRENNT (= Extra-Verkettung)
# Die Stufe mit den meisten Extra-Verkettungen macht die Kaskade laenger.
#
# Zusaetzlich: Zeitabstands-Verteilung der Extra-Verkettungen (zeigt den Effekt
# des 90-min-Fensters gegenueber DIS22' 5-min-Grenze).
#
# Nur Aggregate -> NDA-sicher. Verknuepfung ueber search_id.
# --------------------------------------------------------------------------
import csv, sys
from collections import Counter, defaultdict
csv.field_size_limit(2**31 - 1)

CASC = sys.argv[1] if len(sys.argv) > 1 else "cascade_full_1234.tsv"
DIS  = sys.argv[2] if len(sys.argv) > 2 else "dis22_sessions.tsv"
MERGE_STAGES = {"s1", "s2", "s3", "s4"}

def strip_nul(fo):
    for line in fo:
        yield line.replace("\x00", "")

def find(h, cands):
    for c in cands:
        if c in h: return h.index(c)
    return None

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

# 1) DIS22: search_id -> session
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

stage_total = Counter()
stage_split = Counter()
stage_keep  = Counter()
stage_unk   = Counter()
gap_bucket  = defaultdict(Counter)

def bucket(g):
    if g < 300:  return "< 5 min"
    if g < 600:  return "5-10 min"
    if g < 1800: return "10-30 min"
    if g <= 5400:return "30-90 min"
    return "> 90 min"

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
        if st in MERGE_STAGES and prev_sid is not None:
            a = dis_of.get(prev_sid); b = dis_of.get(sq)
            if a is None or b is None:
                stage_unk[st] += 1
            elif a == b:
                stage_keep[st] += 1
            else:
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

print("Haeufigkeit aller stage-Werte in der Kaskade:")
for st, c in stage_total.most_common():
    print(f"   {st:<10}{c:>14,}")
print()

merges = sum(stage_total[s] for s in MERGE_STAGES)
extra  = sum(stage_split.values())
print(f"Kaskaden-Verkettungen gesamt (s1..s4)        : {merges:,}")
if merges:
    print(f"davon von DIS22 GETRENNT (Extra-Verkettungen): {extra:,}  ({100*extra/merges:.1f}%)")
print()

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

print("Zeitabstand der Extra-Verkettungen je Stufe")
print("(zeigt den Effekt des 90-min-Fensters ggue. DIS22' 5-min-Grenze):")
order = ["< 5 min","5-10 min","10-30 min","30-90 min","> 90 min"]
for st in ["s1", "s2", "s3", "s4"]:
    if not gap_bucket[st]: continue
    tot = sum(gap_bucket[st].values())
    parts = "  ".join(f"{k}:{100*gap_bucket[st][k]/tot:.0f}%"
                      for k in order if gap_bucket[st].get(k))
    print(f"   {st}: {parts}")