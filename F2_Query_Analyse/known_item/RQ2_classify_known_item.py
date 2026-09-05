# classify_known_item.py  [session_datei]
# Known-Item- vs Exploratory-Heuristik pro Session (Singletons bleiben drin).
# Klassen:
#   Known-Item              : Titel getippt (jede Laenge, auch n=1) ODER
#                             kurze Mehr-Query-Episode (2-3 Q, keine Verfeinerung)
#   Exploratory             : >= 4 Queries (LANGE Session; OHNE Verfeinerungspflicht)
#   Einzelquery (ohne Titel): n=1 ohne Titel-Treffer
#   Unscharf                : der Rest (2-3 Q mit Verfeinerung)
# Innerhalb Exploratory: Aufschluesselung nach lexikalischer Verfeinerung.
# Aggregate -> teilbar. Beispiele (echte Queries) -> lokale UTF-8-Datei.
import csv, sys, re
from collections import Counter, defaultdict
csv.field_size_limit(2**31 - 1)
from RQ2_reformulation import classify

SRC   = sys.argv[1] if len(sys.argv) > 1 else "cascade_full_1234_nostruct.tsv"
TITLE = "doc_titles.tsv"
OUTEX = "known_item_beispiele.txt"
SHORT_MAX = 3      # kurze Mehr-Query-Episode: 2..SHORT_MAX Queries
LONG_MIN  = 4      # explorativ ab so vielen Queries (OHNE Verfeinerungspflicht)
REFINE = {"Add Words","Remove Words","Word Substitution","Substring","Superstring"}
CLASSES = ["Known-Item","Exploratory","Einzelquery (ohne Titel)","Unscharf"]

def strip_nul(fo):
    for line in fo: yield line.replace("\x00","")
def norm(s):
    return re.sub(r"[\W_]+"," ", s.lower(), flags=re.UNICODE).strip()
def find(h,c):
    for x in c:
        if x in h: return h.index(x)
    return None

titles=set(); nt=0
try:
    with open(TITLE, newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.reader(strip_nul(f), delimiter="\t"):
            if len(row)>=2:
                t=norm(row[1])
                if t: titles.add(t); nt+=1
except FileNotFoundError:
    print(f"[WARN] {TITLE} nicht gefunden -> Titel-Signal deaktiviert.")
print(f"Titel im Index: {len(titles):,} (aus {nt:,} Zeilen)\n")

with open(SRC, newline="", encoding="utf-8", errors="replace") as f:
    h=next(csv.reader(strip_nul(f), delimiter="\t"))
i_s=find(h,["session_id","sid","session"]); i_q=find(h,["query"])
if i_s is None or i_q is None: sys.exit(f"Brauche session_id+query. Header:{h}")

labels=Counter(); ki_by=Counter(); expl_by=Counter(); title_sessions=0
examples=defaultdict(list)

def finalize(qs):
    global title_sessions
    n=len(qs)
    title_hit=any(norm(q) in titles for q in qs if q.strip())
    if title_hit: title_sessions+=1
    refine=sum(1 for k in range(1,n) if classify(qs[k-1],qs[k]) in REFINE)
    if title_hit:
        lab="Known-Item"; ki_by["Titel getippt"]+=1
    elif n==1:
        lab="Einzelquery (ohne Titel)"
    elif n>=LONG_MIN:
        lab="Exploratory"
        expl_by["mit lexikalischer Verfeinerung" if refine>=1
                else "reine Themen-Spruenge"] += 1
    elif n<=SHORT_MAX and refine==0:
        lab="Known-Item"; ki_by["kurze Session (2-3 Q)"]+=1
    else:
        lab="Unscharf"
    labels[lab]+=1
    if len(examples[lab])<3:
        examples[lab].append((n, title_hit, refine, list(qs)))

with open(SRC, newline="", encoding="utf-8", errors="replace") as f:
    r=csv.reader(strip_nul(f), delimiter="\t"); next(r)
    cur=None; qs=[]
    for row in r:
        if max(i_s,i_q)>=len(row): continue
        s=row[i_s]
        if s!=cur:
            if cur is not None: finalize(qs)
            cur=s; qs=[]
        qs.append(row[i_q])
    if cur is not None: finalize(qs)

total=sum(labels.values())
print("KLASSIFIKATION JE SESSION (Aggregate -> teilbar):")
print("-"*52)
for lab in CLASSES:
    c=labels.get(lab,0); pct=f"{100*c/total:.1f}%" if total else "-"
    print(f"   {lab:<26}{c:>12,}{pct:>9}")
print(f"   {'GESAMT':<26}{total:>12,}")
print(f"\nKnown-Item nach Ausloeser:")
for k,c in ki_by.most_common():
    print(f"   {k:<24}{c:>12,}")
print(f"\nExploratory-Unterteilung:")
et=sum(expl_by.values())
for k,c in expl_by.most_common():
    print(f"   {k:<24}{c:>12,}"+(f"  ({100*c/et:.1f}%)" if et else ""))
print(f"\nSessions mit mind. 1 Titel-Treffer: {title_sessions:,}"
      + (f"  ({100*title_sessions/total:.1f}%)" if total else ""))

with open(OUTEX,"w",encoding="utf-8") as o:
    o.write("BEISPIEL-SESSIONS je Klasse (echte Queries -> LOKAL)\n"+"="*60+"\n")
    for lab in CLASSES:
        o.write(f"\n### {lab}\n")
        for (n,th,rf,qq) in examples[lab]:
            o.write(f"  [n={n}, Titel-Treffer={th}, Refinements={rf}]\n")
            for q in qq: o.write(f"     - {q!r}\n")
print(f"\nBeispiele geschrieben nach: {OUTEX}")



# # classify_known_item.py  [session_datei]
# # Known-Item- vs Exploratory-Heuristik pro Session (Singletons bleiben drin).
# # Klassen:
# #   Known-Item              : Titel getippt (jede Laenge, auch n=1) ODER
# #                             kurze Mehr-Query-Episode (2-3 Q, keine Verfeinerung)
# #   Exploratory             : >= 4 Queries mit mind. 1 Verfeinerung
# #   Einzelquery (ohne Titel): n=1 ohne Titel-Treffer (sichtbar, aber nicht KI)
# #   Unscharf                : der Rest
# # Aggregate -> teilbar. Beispiele (echte Queries) -> lokale UTF-8-Datei.
# import csv, sys, re
# from collections import Counter, defaultdict
# csv.field_size_limit(2**31 - 1)
# from RQ2_reformulation import classify

# SRC   = sys.argv[1] if len(sys.argv) > 1 else "cascade_full_1234_nostruct.tsv"
# TITLE = "doc_titles.tsv"
# OUTEX = "known_item_beispiele.txt"
# SHORT_MAX = 3      # kurze Mehr-Query-Episode: 2..SHORT_MAX Queries
# LONG_MIN  = 4      # explorativ ab so vielen Queries (mit Verfeinerung)
# REFINE = {"Add Words","Remove Words","Word Substitution","Substring","Superstring"}
# CLASSES = ["Known-Item","Exploratory","Einzelquery (ohne Titel)","Unscharf"]

# def strip_nul(fo):
#     for line in fo: yield line.replace("\x00","")
# def norm(s):
#     return re.sub(r"[\W_]+"," ", s.lower(), flags=re.UNICODE).strip()
# def find(h,c):
#     for x in c:
#         if x in h: return h.index(x)
#     return None

# titles=set(); nt=0
# try:
#     with open(TITLE, newline="", encoding="utf-8", errors="replace") as f:
#         for row in csv.reader(strip_nul(f), delimiter="\t"):
#             if len(row)>=2:
#                 t=norm(row[1])
#                 if t: titles.add(t); nt+=1
# except FileNotFoundError:
#     print(f"[WARN] {TITLE} nicht gefunden -> Titel-Signal deaktiviert.")
# print(f"Titel im Index: {len(titles):,} (aus {nt:,} Zeilen)\n")

# with open(SRC, newline="", encoding="utf-8", errors="replace") as f:
#     h=next(csv.reader(strip_nul(f), delimiter="\t"))
# i_s=find(h,["session_id","sid","session"]); i_q=find(h,["query"])
# if i_s is None or i_q is None: sys.exit(f"Brauche session_id+query. Header:{h}")

# labels=Counter(); ki_by=Counter(); title_sessions=0
# examples=defaultdict(list)

# def finalize(qs):
#     global title_sessions
#     n=len(qs)
#     title_hit=any(norm(q) in titles for q in qs if q.strip())
#     if title_hit: title_sessions+=1
#     refine=sum(1 for k in range(1,n) if classify(qs[k-1],qs[k]) in REFINE)
#     if title_hit:
#         lab="Known-Item"; ki_by["Titel getippt"]+=1
#     elif n==1:
#         lab="Einzelquery (ohne Titel)"
#     elif n<=SHORT_MAX and refine==0:
#         lab="Known-Item"; ki_by["kurze Session (2-3 Q)"]+=1
#     elif n>=LONG_MIN and refine>=1:
#         lab="Exploratory"
#     else:
#         lab="Unscharf"
#     labels[lab]+=1
#     if len(examples[lab])<3:
#         examples[lab].append((n, title_hit, refine, list(qs)))

# with open(SRC, newline="", encoding="utf-8", errors="replace") as f:
#     r=csv.reader(strip_nul(f), delimiter="\t"); next(r)
#     cur=None; qs=[]
#     for row in r:
#         if max(i_s,i_q)>=len(row): continue
#         s=row[i_s]
#         if s!=cur:
#             if cur is not None: finalize(qs)
#             cur=s; qs=[]
#         qs.append(row[i_q])
#     if cur is not None: finalize(qs)

# total=sum(labels.values())
# print("KLASSIFIKATION JE SESSION (Aggregate -> teilbar):")
# print("-"*52)
# for lab in CLASSES:
#     c=labels.get(lab,0); pct=f"{100*c/total:.1f}%" if total else "-"
#     print(f"   {lab:<26}{c:>12,}{pct:>9}")
# print(f"   {'GESAMT':<26}{total:>12,}")
# print(f"\nKnown-Item aufgeschluesselt nach Ausloeser:")
# for k,c in ki_by.most_common():
#     print(f"   {k:<22}{c:>12,}")
# print(f"\nSessions mit mind. 1 Titel-Treffer: {title_sessions:,}"
#       + (f"  ({100*title_sessions/total:.1f}%)" if total else ""))

# with open(OUTEX,"w",encoding="utf-8") as o:
#     o.write("BEISPIEL-SESSIONS je Klasse (echte Queries -> LOKAL)\n"+"="*60+"\n")
#     for lab in CLASSES:
#         o.write(f"\n### {lab}\n")
#         for (n,th,rf,qq) in examples[lab]:
#             o.write(f"  [n={n}, Titel-Treffer={th}, Refinements={rf}]\n")
#             for q in qq: o.write(f"     - {q!r}\n")
# print(f"\nBeispiele geschrieben nach: {OUTEX}")