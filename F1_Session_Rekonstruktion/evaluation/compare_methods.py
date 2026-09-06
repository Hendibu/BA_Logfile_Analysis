# compare_methods.py  [uidday] [kaskade] [dis22]
# RQ1-Methodenvergleich auf GEMEINSAMER Event-Basis (dis22_uidday.tsv).
# Alle drei Dateien stehen in derselben Zeilenreihenfolge -> Gleichschritt-Lesen.
#   UUID    = uid|Tag (Basislinie, aus dis22_uidday: uid + ts)
#   Kaskade = session_id aus cascade_full_1234.tsv
#   DIS22   = session_id aus dis22_sessions.tsv
# Ausgabe: (1) Session-Statistik je Methode, (2) Aufteilungsfaktor ggue. uid|Tag,
#          (3) paarweise Uebereinstimmung.

import csv, sys
from collections import Counter
from datetime import datetime, timezone
csv.field_size_limit(2**31 - 1)

# Die drei Eingabedateien (Argument oder Standardpfad)
UIDDAY = sys.argv[1] if len(sys.argv) > 1 else "../../data/dis22_uidday.tsv"
CASC   = sys.argv[2] if len(sys.argv) > 2 else "../../data/cascade_full_1234.tsv"
DIS    = sys.argv[3] if len(sys.argv) > 3 else "../../data/dis22_sessions.tsv"

# Hilfsfunktionen: NUL-Bytes entfernen, Spaltenindex suchen, Zeitstempel -> Tag
def strip_nul(fo):
    for line in fo: yield line.replace("\x00","")
def find(h,c):
    for x in c:
        if x in h: return h.index(x)
    return None
def day(ts):
    return datetime.fromtimestamp(int(float(ts)), tz=timezone.utc).strftime("%Y-%m-%d")

# Datei oeffnen und Reader + Kopfzeile zurueckgeben
def opencsv(path):
    f=open(path, newline="", encoding="utf-8", errors="replace")
    r=csv.reader(strip_nul(f), delimiter="\t")
    h=next(r)
    return f, r, h

# Alle drei Dateien oeffnen und die benoetigten Spaltenindizes bestimmen (fehlt eine, Abbruch)
fu,ru,hu = opencsv(UIDDAY)
fc,rc,hc = opencsv(CASC)
fd,rd,hd = opencsv(DIS)
u_sid=find(hu,["search_id"]); u_uid=find(hu,["uid"]); u_ts=find(hu,["ts"])
c_sid=find(hc,["search_id"]); c_sess=find(hc,["session_id","sid","session"])
d_sid=find(hd,["search_id"]); d_sess=find(hd,["session_id","sid","session"])
for nm,ix,h in [("uidday",u_sid,hu),("kaskade",c_sess,hc),("dis22",d_sess,hd)]:
    if ix is None: sys.exit(f"{nm}: noetige Spalte fehlt. Header:{h}")

# Je Methode ein Laengen-Histogramm; cur/run verfolgen die laufende Session
hist={"UUID":Counter(),"Kaskade":Counter(),"DIS22":Counter()}
cur={"UUID":None,"Kaskade":None,"DIS22":None}
run={"UUID":0,"Kaskade":0,"DIS22":0}
# Session-Label fortschreiben; bei Wechsel die abgeschlossene Laenge ins Histogramm zaehlen
def step(method,label):
    if label!=cur[method]:
        if cur[method] is not None: hist[method][run[method]]+=1
        cur[method]=label; run[method]=1
    else:
        run[method]+=1

# Zaehler fuer den paarweisen Vergleich aufeinanderfolgender Events
pairs=0; within=0
agree={("UUID","Kaskade"):0,("UUID","DIS22"):0,("Kaskade","DIS22"):0}
within_cd_agree=0; within_cas_split=0; within_dis_split=0
prev={"UUID":None,"Kaskade":None,"DIS22":None}

# Alle drei Dateien im Gleichschritt lesen; je Event die Methoden-Labels bilden und vergleichen
n=0; mismatch=0
while True:
    a=next(ru,None); b=next(rc,None); c=next(rd,None)
    if a is None or b is None or c is None: break
    if max(u_sid,u_uid,u_ts)>=len(a) or c_sess>=len(b) or d_sess>=len(c): continue
    sid=a[u_sid].strip()
    # Ausrichtung pruefen: gleiche search_id in allen drei Dateien, sonst Zeile ueberspringen
    if sid!=b[c_sid].strip() or sid!=c[d_sid].strip():
        mismatch+=1
        if mismatch<=5: print(f"[WARN] Zeilen nicht ausgerichtet bei Zeile {n}: {sid} / {b[c_sid]} / {c[d_sid]}")
        continue
    n+=1
    # Session-Label je Methode fuer dieses Event (UUID = uid|Tag)
    lab={"UUID": a[u_uid].strip()+"|"+day(a[u_ts]),
         "Kaskade": b[c_sess], "DIS22": c[d_sess]}
    for m in hist: step(m, lab[m])
    # Fuer jedes Paar (Vorgaenger, aktuell): pruefen, ob die Methoden gleich entscheiden
    if prev["UUID"] is not None:
        pairs+=1
        s={m:(lab[m]==prev[m]) for m in hist}   # True = Paar bleibt in derselben Session
        agree[("UUID","Kaskade")] += (s["UUID"]==s["Kaskade"])
        agree[("UUID","DIS22")]   += (s["UUID"]==s["DIS22"])
        agree[("Kaskade","DIS22")]+= (s["Kaskade"]==s["DIS22"])
        # Nur Paare innerhalb desselben uid|Tag: wie oft trennen Kaskade/DIS22 hier?
        if s["UUID"]:
            within+=1
            within_cd_agree += (s["Kaskade"]==s["DIS22"])
            within_cas_split += (not s["Kaskade"])
            within_dis_split += (not s["DIS22"])
    prev=lab
# Letzte offene Session je Methode abschliessen und Dateien schliessen
for m in hist:
    if cur[m] is not None: hist[m][run[m]]+=1
fu.close(); fc.close(); fd.close()

# Aus einem Laengen-Histogramm Kennzahlen ableiten (Anzahl, Mittel, Median, Max, Singleton-%, >=4-Q-%)
def stats(H):
    N=sum(H.values())
    if not N: return (0,0,0,0,0,0)
    tot=sum(g*c for g,c in H.items()); mx=max(H); sing=H.get(1,0)
    ge4=sum(c for g,c in H.items() if g>=4)
    half=N/2; run2=0; med=mx
    for g in sorted(H):
        run2+=H[g]
        if run2>=half: med=g; break
    return N, tot/N, med, mx, 100*sing/N, 100*ge4/N

# (1) Session-Statistik je Methode ausgeben
print(f"Ausgerichtete Events: {n:,}" + (f"  | NICHT ausgerichtet: {mismatch:,}" if mismatch else "  | Ausrichtung OK"))
print("\n(1) SESSION-STATISTIK JE METHODE (gemeinsame Event-Basis)")
print(f"{'Methode':<10}{'Sessions':>13}{'Mittel':>9}{'Median':>8}{'Max':>8}{'Singl.%':>10}{'>=4 Q %':>10}")
print("-"*68)
for m in ["UUID","Kaskade","DIS22"]:
    N,mean,med,mx,sing,ge4=stats(hist[m])
    print(f"{m:<10}{N:>13,}{mean:>9.2f}{med:>8,}{mx:>8,}{sing:>9.1f}%{ge4:>9.1f}%")

# (2) Aufteilungsfaktor: wie viele Kaskade-/DIS22-Sessions je uid|Tag-Basislinie
nu=sum(hist["UUID"].values())
print("\n(2) AUFTEILUNG DER uid|Tag-BASISLINIE")
print(f"   uid|Tage (UUID-Sessions): {nu:,}")
for m in ["Kaskade","DIS22"]:
    nm=sum(hist[m].values())
    if nu: print(f"   {m}-Sessions je uid|Tag: {nm/nu:.2f}   (gesamt {nm:,})")

# (3) Paarweise Uebereinstimmung der Methoden ueber alle Query-Paare
print("\n(3) PAARWEISE UEBEREINSTIMMUNG (aufeinanderfolgende Query-Paare)")
print(f"   betrachtete Paare gesamt: {pairs:,}")
for k,v in agree.items():
    if pairs: print(f"   {k[0]:<8} vs {k[1]:<8}: {100*v/pairs:.1f}% gleiche Entscheidung")
print(f"\n   davon INNERHALB desselben uid|Tag: {within:,} Paare")
if within:
    print(f"     Kaskade vs DIS22 einig : {100*within_cd_agree/within:.1f}%")
    print(f"     Kaskade trennt das Paar: {100*within_cas_split/within:.1f}%")
    print(f"     DIS22 trennt das Paar  : {100*within_dis_split/within:.1f}%")