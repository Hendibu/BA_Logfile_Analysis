# transition_matrix.py <session_file>
# Analysiert die ABFOLGE von Reformulierungsstrategien INNERHALB von Sessions:
# fuer aufeinanderfolgende Reformulierungs-Labels (l_i -> l_{i+1}) wird eine
# Uebergangsmatrix gebildet. Struktur-/Bot-Paare werden wie in 6.4 uebersprungen
# und unterbrechen die Abfolge. NUR Aggregate (NDA-sicher).
import csv, sys, re
from collections import Counter
from RQ2_reformulation import classify
csv.field_size_limit(2**31 - 1)

SESSION_FILE = sys.argv[1] if len(sys.argv) > 1 else "../../data/cascade_full_1234_nostruct.tsv"
STRUCT = re.compile(r'year\s*:|yearpublished|(<=|>=|<|>)\s*\d|\bAND\s*\(|\bOR\s*\(', re.IGNORECASE)
ORDER = ["Identical","Word Reorder","Whitespace/Punctuation","Remove Words","Add Words",
         "URL Stripping","Stemming","Form Acronym","Expand Acronym","Substring","Superstring",
         "Abbreviation","Word Substitution","Spelling Correction","New"]

def strip_nul(fo):
    for line in fo: yield line.replace("\x00","")

trans = Counter(); cur_total = Counter(); n_labels = 0; n_trans = 0
with open(SESSION_FILE, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
    i_sid, i_q = h.index(sidcol), h.index("query")
    cur_sid=None; prev_q=None; prev_lab=None
    for row in r:
        sid = row[i_sid] if i_sid < len(row) else ""
        q   = row[i_q]   if i_q   < len(row) else ""
        if not sid: cur_sid=None; prev_q=None; prev_lab=None; continue
        if sid != cur_sid: cur_sid=sid; prev_q=q; prev_lab=None; continue
        if STRUCT.search(prev_q) or STRUCT.search(q):       # Bot-Paar -> Abfolge unterbrechen
            prev_q=q; prev_lab=None; continue
        lab = classify(prev_q, q); n_labels += 1
        if prev_lab is not None:
            trans[(prev_lab, lab)] += 1; cur_total[prev_lab] += 1; n_trans += 1
        prev_lab = lab; prev_q = q

print(f"Reformulierungs-Labels: {n_labels:,} | Uebergaenge (l_i -> l_i+1): {n_trans:,}\n")
print("=== Bedingte Uebergaenge P(naechste | aktuelle) fuer haeufige Ausgangs-Strategien ===")
for cur in ORDER:
    tot = cur_total[cur]
    if tot < 50: continue
    nxts = sorted(((trans[(cur,n)], n) for n in ORDER if trans[(cur,n)]>0), reverse=True)[:3]
    parts = ", ".join(f"{n} {100*c/tot:.0f}%" for c,n in nxts)
    print(f"  {cur:20} (n={tot:,}): {parts}")
print("\n=== Haeufigste Uebergaenge insgesamt ===")
for (a,b),c in trans.most_common(15):
    print(f"  {a:18} -> {b:18} {c:,} ({100*c/n_trans:.1f}%)")