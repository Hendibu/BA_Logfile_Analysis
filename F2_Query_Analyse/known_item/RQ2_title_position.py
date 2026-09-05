# title_position.py  [session_datei]
# Verteilung der Titel-Queries (Query == echter Paper-Titel):
#   (A) nach Session-Laenge (Singleton vs. Mehr-Query) + Trefferrate je Laenge
#   (B) Position der Titel-Query innerhalb der Session (erste/mittlere/letzte)
# Nur Aggregate -> teilbar. Nutzt doc_titles.tsv.
import csv, sys, re
from collections import Counter
csv.field_size_limit(2**31 - 1)

SRC   = sys.argv[1] if len(sys.argv) > 1 else "../../data/cascade_full_1234_nostruct.tsv"
TITLE = "../../data/doc_titles.tsv"

def strip_nul(fo):
    for line in fo: yield line.replace("\x00","")
def norm(s):
    return re.sub(r"[\W_]+"," ", s.lower(), flags=re.UNICODE).strip()
def find(h,c):
    for x in c:
        if x in h: return h.index(x)
    return None
def bucket(n):
    if n==1: return "1 (Singleton)"
    if n==2: return "2"
    if n==3: return "3"
    if n<=5: return "4-5"
    if n<=10:return "6-10"
    return "11+"
BUCKETS=["1 (Singleton)","2","3","4-5","6-10","11+"]

titles=set()
with open(TITLE, newline="", encoding="utf-8", errors="replace") as f:
    for row in csv.reader(strip_nul(f), delimiter="\t"):
        if len(row)>=2:
            t=norm(row[1])
            if t: titles.add(t)
print(f"Titel im Index: {len(titles):,}\n")

with open(SRC, newline="", encoding="utf-8", errors="replace") as f:
    h=next(csv.reader(strip_nul(f), delimiter="\t"))
i_s=find(h,["session_id","sid","session"]); i_q=find(h,["query"])
if i_s is None or i_q is None: sys.exit(f"Brauche session_id+query. Header:{h}")

q_total=Counter(); q_title=Counter()
sess_total=Counter(); sess_withtitle=Counter()
pos=Counter()
tq_all=0; ts_all=0

def finalize(qs):
    global tq_all, ts_all
    n=len(qs); b=bucket(n)
    sess_total[b]+=1; q_total[b]+=n
    hits=[i for i,q in enumerate(qs) if q.strip() and norm(q) in titles]
    q_title[b]+=len(hits); tq_all+=len(hits)
    if hits:
        sess_withtitle[b]+=1; ts_all+=1
        if n>=2:
            for i in hits:
                pos["erste" if i==0 else "letzte" if i==n-1 else "mittlere"]+=1

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

print("(A) TITEL-QUERIES NACH SESSION-LAENGE")
print(f"{'Laenge':<15}{'Sess ges.':>11}{'Sess m.Titel':>14}{'Titel-Q':>10}{'Rate Q':>9}{'% aller TitelQ':>16}")
print("-"*75)
for b in BUCKETS:
    st=sess_total.get(b,0); sw=sess_withtitle.get(b,0)
    qt=q_total.get(b,0); qi=q_title.get(b,0)
    rate=f"{100*qi/qt:.2f}%" if qt else "-"
    share=f"{100*qi/tq_all:.1f}%" if tq_all else "-"
    print(f"{b:<15}{st:>11,}{sw:>14,}{qi:>10,}{rate:>9}{share:>16}")
print("-"*75)
print(f"Titel-Queries gesamt: {tq_all:,} | Sessions mit >=1 Titel: {ts_all:,}")

singleton_ts=sess_withtitle.get('1 (Singleton)',0)
print(f"\nDirekte Antwort: von {ts_all:,} Titel-Sessions sind "
      f"{singleton_ts:,} Singletons"
      + (f" ({100*singleton_ts/ts_all:.1f}%)" if ts_all else "")
      + f" und {ts_all-singleton_ts:,} Mehr-Query-Sessions"
      + (f" ({100*(ts_all-singleton_ts)/ts_all:.1f}%)." if ts_all else "."))

print("\n(B) POSITION DER TITEL-QUERY (nur Mehr-Query-Sessions, n>=2)")
pt=sum(pos.values())
for k in ["erste","mittlere","letzte"]:
    c=pos.get(k,0)
    print(f"   {k:<10}{c:>10,}"+(f"  ({100*c/pt:.1f}%)" if pt else ""))