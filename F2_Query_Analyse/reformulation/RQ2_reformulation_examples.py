# reformulation_examples.py  [session_datei]
# Verteilung + bis zu 2 Beispiele je Reformulierungs-Klassifikation.
# Strukturierte Rest-Bot-Queries (Jahr-Sweeps etc.) werden aus der Auswertung
# ausgeschlossen, damit Identical/Spelling nicht verzerrt werden.
# Eingabe: cascade_full_1234_nostruct.tsv (default) | Ausgabe: RQ2_reformulation_beispiele.txt

import csv, sys, re
from collections import Counter, defaultdict
csv.field_size_limit(2**31 - 1)
# Klassifikator + Verfuegbarkeitsflags (Stemming/WordNet) importieren
try:
    from RQ2_reformulation import classify, _HAS_STEM, _HAS_WN
except Exception as e:
    sys.exit(f"reformulation.py muss im selben Ordner liegen. Fehler: {e}")

# Ein-/Ausgabe, Beispiele je Klasse und das Muster fuer strukturierte Bot-Queries
SRC = sys.argv[1] if len(sys.argv) > 1 else "../../data/cascade_full_1234_nostruct.tsv"
OUT = "../../data/RQ2_reformulation_beispiele.txt"
PER = 2
STRUCT = re.compile(r'year\s*:|yearpublished|(<=|>=|<|>)\s*\d|\bAND\s*\(|\bOR\s*\(', re.IGNORECASE)

# Anzeige-Reihenfolge der Reformulierungsklassen
LABELS = ["Identical","Word Reorder","Whitespace/Punctuation","Remove Words",
          "Add Words","URL Stripping","Stemming","Form Acronym","Expand Acronym",
          "Substring","Superstring","Abbreviation","Word Substitution",
          "Spelling Correction","New"]

# Hilfsfunktionen: NUL-Bytes entfernen und ersten passenden Spaltenindex finden
def strip_nul(fo):
    for line in fo: yield line.replace("\x00","")
def find(h,c):
    for x in c:
        if x in h: return h.index(x)
    return None

# Kopfzeile lesen und Spalten session_id + query bestimmen
with open(SRC, newline="", encoding="utf-8", errors="replace") as f:
    header = next(csv.reader(strip_nul(f), delimiter="\t"))
i_sess = find(header, ["session_id","sid","session"]); i_q = find(header, ["query"])
if i_sess is None or i_q is None: sys.exit(f"Brauche session_id+query. Header:{header}")

counts=Counter(); examples=defaultdict(list); skipped=0

# Session-Datei paarweise durchgehen: Struktur-Paare ausschliessen, Rest klassifizieren + Beispiele sammeln
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

# Beispiele je Klasse (mit Haeufigkeit) in die Ausgabedatei schreiben
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

# Haeufigkeiten je Klasse auf der Konsole ausgeben
print(f"Quelle: {SRC}")
print(f"WordNet aktiv: {_HAS_WN} | ausgeschlossene strukturierte Paare: {skipped:,}")
print(f"verbleibende Paare: {total:,}\n")
print("HAEUFIGKEITEN JE KLASSIFIKATION:")
print("-"*46)
for lbl in LABELS:
    c=counts.get(lbl,0); pct=f"{100*c/total:.2f}%" if total else "-"
    print(f"   {lbl:<24}{c:>10,}{pct:>9}")
print("-"*46)
print(f"   {'GESAMT':<24}{total:>10,}")
print(f"\nBeispiele -> {OUT}")