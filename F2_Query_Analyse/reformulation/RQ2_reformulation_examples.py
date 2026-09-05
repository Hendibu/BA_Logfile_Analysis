# reformulation_examples.py  [session_datei]
# Verteilung + bis zu 2 Beispiele je Reformulierungs-Klassifikation.
# NEU: strukturierte Rest-Bot-Queries (Jahr-Sweeps etc.) werden aus der
# Auswertung ausgeschlossen, damit Identical/Spelling nicht verzerrt werden.
# Beispiele -> lokale UTF-8-Datei (echte Queries). Zaehler -> Konsole (teilbar).
import csv, sys, re
from collections import Counter, defaultdict
csv.field_size_limit(2**31 - 1)
try:
    from RQ2_reformulation import classify, _HAS_STEM, _HAS_WN
except Exception as e:
    sys.exit(f"reformulation.py muss im selben Ordner liegen. Fehler: {e}")

SRC = sys.argv[1] if len(sys.argv) > 1 else "../../data/cascade_full_1234_nostruct.tsv"
OUT = "../../data/RQ2_reformulation_beispiele.txt"
PER = 2
# strukturierte / automatisierte Query-Muster, die uebersprungen werden:
STRUCT = re.compile(r'year\s*:|yearpublished|(<=|>=|<|>)\s*\d|\bAND\s*\(|\bOR\s*\(', re.IGNORECASE)

LABELS = ["Identical","Word Reorder","Whitespace/Punctuation","Remove Words",
          "Add Words","URL Stripping","Stemming","Form Acronym","Expand Acronym",
          "Substring","Superstring","Abbreviation","Word Substitution",
          "Spelling Correction","New"]

def strip_nul(fo):
    for line in fo: yield line.replace("\x00","")
def find(h,c):
    for x in c:
        if x in h: return h.index(x)
    return None

with open(SRC, newline="", encoding="utf-8", errors="replace") as f:
    header = next(csv.reader(strip_nul(f), delimiter="\t"))
i_sess = find(header, ["session_id","sid","session"]); i_q = find(header, ["query"])
if i_sess is None or i_q is None: sys.exit(f"Brauche session_id+query. Header:{header}")

counts=Counter(); examples=defaultdict(list); skipped=0

with open(SRC, newline="", encoding="utf-8", errors="replace") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); next(r)
    prev_q=None; prev_sess=None
    for row in r:
        if max(i_sess,i_q)>=len(row): prev_q=None; prev_sess=None; continue
        sess=row[i_sess]; q=row[i_q]
        if prev_q is not None and sess==prev_sess and q.strip() and prev_q.strip():
            if STRUCT.search(prev_q) or STRUCT.search(q):
                skipped += 1                      # strukturiertes Bot-Paar -> raus
            else:
                lbl=classify(prev_q,q); counts[lbl]+=1
                if len(examples[lbl])<PER: examples[lbl].append((prev_q,q))
        prev_q=q; prev_sess=sess

total=sum(counts.values())
with open(OUT,"w",encoding="utf-8") as o:
    o.write(f"Quelle: {SRC}\n")
    o.write(f"nltk-Stemming: {_HAS_STEM} | WordNet: {_HAS_WN}\n")
    o.write(f"ausgeschlossene strukturierte Paare: {skipped}\n"+"="*66+"\n")
    for lbl in LABELS:
        c=counts.get(lbl,0); pct=f"{100*c/total:.2f}%" if total else "-"
        o.write(f"\n### {lbl}   (Haeufigkeit: {c:,}, {pct})\n")
        if not examples[lbl]: o.write("   (kein Beispiel)\n")
        for j,(a,b) in enumerate(examples[lbl],1):
            o.write(f"   {j}. {a!r}\n      -> {b!r}\n")

print(f"Quelle: {SRC}")
print(f"WordNet aktiv: {_HAS_WN} | ausgeschlossene strukturierte Paare: {skipped:,}")
print(f"verbleibende Paare: {total:,}\n")
print("HAEUFIGKEITEN JE KLASSIFIKATION (Aggregate -> teilbar):")
print("-"*46)
for lbl in LABELS:
    c=counts.get(lbl,0); pct=f"{100*c/total:.2f}%" if total else "-"
    print(f"   {lbl:<24}{c:>10,}{pct:>9}")
print("-"*46)
print(f"   {'GESAMT':<24}{total:>10,}")
print(f"\nBeispiele -> {OUT}")





# # reformulation_examples.py  [session_datei]
# # --------------------------------------------------------------------------
# # Gibt fuer JEDE Reformulierungs-Klassifikation bis zu 2 Beispiele aus.
# # Geht die aufeinanderfolgenden Query-Paare innerhalb jeder Session durch
# # (session_id + ts-Reihenfolge) und klassifiziert sie mit reformulation.classify.
# #
# # ACHTUNG: die Beispiele enthalten ECHTE Query-Texte -> Ausgabe bleibt LOKAL.
# # Die Haeufigkeits-Zaehler am Ende sind Aggregate (teilbar).
# # --------------------------------------------------------------------------
# import csv, sys
# from collections import Counter, defaultdict
# csv.field_size_limit(2**31 - 1)

# try:
#     from RQ2_reformulation import classify, _HAS_STEM, _HAS_WN
# except Exception as e:
#     sys.exit(f"reformulation.py muss im selben Ordner liegen. Fehler: {e}")

# SRC = sys.argv[1] if len(sys.argv) > 1 else "cascade_full_1234_nostruct.tsv"
# PER = 2   # Beispiele je Kategorie

# # Anzeige-Reihenfolge (Prioritaet wie im Klassifizierer)
# LABELS = ["Identical", "Word Reorder", "Whitespace/Punctuation", "Remove Words",
#           "Add Words", "URL Stripping", "Stemming", "Form Acronym",
#           "Expand Acronym", "Substring", "Superstring", "Abbreviation",
#           "Word Substitution", "Spelling Correction", "New"]

# def strip_nul(fo):
#     for line in fo:
#         yield line.replace("\x00", "")

# def find(h, cands):
#     for c in cands:
#         if c in h: return h.index(c)
#     return None

# with open(SRC, newline="", encoding="utf-8", errors="replace") as f:
#     header = next(csv.reader(strip_nul(f), delimiter="\t"))
# i_sess = find(header, ["session_id","sid","session"])
# i_q    = find(header, ["query"])
# i_ts   = find(header, ["ts"])
# if i_sess is None or i_q is None:
#     sys.exit(f"Brauche session_id und query. Header: {header}")

# counts   = Counter()
# examples = defaultdict(list)   # label -> Liste von (q_prev, q_curr)

# with open(SRC, newline="", encoding="utf-8", errors="replace") as f:
#     r = csv.reader(strip_nul(f), delimiter="\t"); next(r)
#     prev_q = None; prev_sess = None
#     for row in r:
#         if max(i_sess, i_q) >= len(row):
#             prev_q = None; prev_sess = None; continue
#         sess = row[i_sess]
#         q = row[i_q]
#         if prev_q is not None and sess == prev_sess and q.strip() and prev_q.strip():
#             lbl = classify(prev_q, q)
#             counts[lbl] += 1
#             if len(examples[lbl]) < PER:
#                 examples[lbl].append((prev_q, q))
#         prev_q = q; prev_sess = sess

# # Ausgabe
# print(f"Quelle: {SRC}")
# print(f"nltk-Stemming aktiv: {_HAS_STEM} | WordNet (Word Substitution) aktiv: {_HAS_WN}")
# print("(ohne nltk koennen 'Stemming' und 'Word Substitution' nicht auftreten)\n")
# print("=" * 70)
# print("BEISPIELE JE KLASSIFIKATION   [echte Queries -> LOKAL behalten]")
# print("=" * 70)
# total = sum(counts.values())
# for lbl in LABELS:
#     c = counts.get(lbl, 0)
#     pct = f"{100*c/total:.2f}%" if total else "-"
#     print(f"\n### {lbl}   (Haeufigkeit: {c:,}, {pct})")
#     if not examples[lbl]:
#         print("   (kein Beispiel gefunden)")
#     for j, (a, b) in enumerate(examples[lbl], 1):
#         print(f"   {j}. {a!r}")
#         print(f"      -> {b!r}")

# extra = [l for l in counts if l not in LABELS]
# if extra:
#     print("\n[Hinweis] Weitere Labels:", ", ".join(extra))

# print("\n" + "=" * 70)
# print("NUR ZAEHLER (Aggregate -> teilbar):")
# for lbl in LABELS:
#     print(f"   {lbl:<24}{counts.get(lbl,0):>12,}")
# print(f"   {'GESAMT':<24}{total:>12,}")