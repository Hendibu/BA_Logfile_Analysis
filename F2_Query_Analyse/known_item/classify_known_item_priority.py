# classify_known_item_priority.py <session_file>
# Klassifiziert Sessions nach Prioritaetsregel:
#   Titel-Treffer            -> Known-Item-indikativ
#   sonst >= 4 Anfragen      -> explorativ-indikativ
#   sonst                    -> nicht eindeutig klassifizierbar
# Titelabgleich: normalisierte Query exakt = Titel aus doc_titles.tsv.
# Eingabe: cascade_full_1234_nostruct.tsv (default), doc_titles.tsv

import csv, sys, re
csv.field_size_limit(2**31 - 1)

# Session-Datei (Argument oder Standard), Titel-Index und Schwelle fuer "explorativ"
SESSION_FILE = sys.argv[1] if len(sys.argv) > 1 else "../../data/cascade_full_1234_nostruct.tsv"
TITLE_INDEX  = "../../data/doc_titles.tsv"
MIN_EXPL     = 4

# Hilfsfunktionen: NUL-Bytes entfernen und Text normalisieren (klein, ohne Satzzeichen, Leerraum vereinheitlicht)
def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")
_norm = re.compile(r"[^\w\s]", re.UNICODE)
def norm(s): return " ".join(_norm.sub(" ", s.lower()).split())

# Titel-Index laden: alle Titel normalisiert in ein Set (fuer den exakten Abgleich)
titles = set()
with open(TITLE_INDEX, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    it = h.index("title") if "title" in h else (1 if len(h) > 1 else 0)
    for row in r:
        if it < len(row):
            t = norm(row[it])
            if t: titles.add(t)
print(f"Titel geladen: {len(titles):,}")

# Eine fertige Session nach der Prioritaetsregel einordnen (Titel-Treffer > Laenge > unklar)
ki = expl = unklar = 0; total = 0
def flush(qs):
    global ki, expl, unklar, total
    if not qs: return
    total += 1
    if any(norm(q) in titles for q in qs): ki += 1
    elif len(qs) >= MIN_EXPL:              expl += 1
    else:                                  unklar += 1

# Session-Datei durchlaufen, Queries je zusammenhaengendem Block sammeln und klassifizieren
with open(SESSION_FILE, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
    i_sid, i_q = h.index(sidcol), h.index("query")
    cur = None; qs = []
    for row in r:
        sid = row[i_sid] if i_sid < len(row) else ""
        q   = row[i_q]   if i_q   < len(row) else ""
        if not sid: flush(qs); cur=None; qs=[]; continue
        if sid != cur: flush(qs); cur=sid; qs=[q]
        else: qs.append(q)
    flush(qs)

# Verteilung der drei Klassen ausgeben
print(f"Sessions gesamt      : {total:,}")
print(f"Known-Item-indikativ : {ki:,} ({100*ki/total:.2f} %)")
print(f"Explorativ-indikativ : {expl:,} ({100*expl/total:.2f} %)")
print(f"Nicht eindeutig      : {unklar:,} ({100*unklar/total:.2f} %)")