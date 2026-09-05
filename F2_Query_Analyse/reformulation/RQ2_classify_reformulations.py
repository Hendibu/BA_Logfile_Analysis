# classify_reformulations.py <session_file>
# RQ2 (4.5): Verteilung der Reformulierungs-Strategien in EINER Session-Datei.
import csv, sys
from collections import Counter
from RQ2_reformulation import classify
csv.field_size_limit(2**31 - 1)

SESSION_FILE = sys.argv[1] if len(sys.argv) > 1 else "cascade_full_1234_nostruct.tsv"
DETAIL_OUT   = None      # z.B. "reform_detail.tsv" (LOKAL, echte Queries)
ORDER = ["Identical","Word Reorder","Whitespace/Punctuation","Remove Words","Add Words",
         "URL Stripping","Stemming","Form Acronym","Expand Acronym","Substring","Superstring",
         "Abbreviation","Word Substitution","Spelling Correction","New"]

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

counts = Counter(); pairs = 0; sessions = 0
dw = None
if DETAIL_OUT:
    _d = open(DETAIL_OUT, "w", newline="", encoding="utf-8"); dw = csv.writer(_d, delimiter="\t")
    dw.writerow(["session_id","ts","q_prev","q_curr","strategy"])
with open(SESSION_FILE, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"   # autom. erkannt
    i_sid, i_ts, i_q = h.index(sidcol), h.index("ts"), h.index("query")
    cur = None; prev = None
    for row in r:
        sid = row[i_sid]
        if not sid: cur = None; prev = None; continue
        if sid != cur: cur = sid; prev = row[i_q]; sessions += 1; continue
        lbl = classify(prev, row[i_q]); counts[lbl] += 1; pairs += 1
        if dw: dw.writerow([sid, row[i_ts], prev, row[i_q], lbl])
        prev = row[i_q]

print(f"Datei: {SESSION_FILE}  (Spalte '{sidcol}')  {sessions:,} Sessions, {pairs:,} Paare\n")
for s in ORDER:
    if counts[s]: print(f"  {s:24} {counts[s]:>10,}  ({100*counts[s]/pairs:.2f}%)")