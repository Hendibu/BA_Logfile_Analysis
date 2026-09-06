# check_query_events.py <rohlog>
# Prueft, wie viele Query-Events (query != '') zusaetzlich unvollstaendige
# Pflichtfelder (date/search_id leer) haben.
# Eingabe: log_files.tsv (default)

import sys

# Eingabepfad (Argument oder Standard)
PATH = sys.argv[1] if len(sys.argv) > 1 else "../../data/log_files.tsv"

with open(PATH, encoding="utf-8", errors="replace") as f:
    # Kopfzeile lesen und Spaltenindizes fuer query, date, search_id bestimmen
    h = f.readline().replace("\x00", "").rstrip("\n").split("\t")
    iq = h.index("query")     if "query"     in h else None
    idt = h.index("date")     if "date"      in h else None
    isd = h.index("search_id") if "search_id" in h else None

    # Query-Events zaehlen und je Zeile pruefen, ob date UND search_id gefuellt sind
    q_total = 0; q_ok = 0; q_missing = 0
    for line in f:
        p = line.replace("\x00", "").rstrip("\n").split("\t")
        q = p[iq].strip() if (iq is not None and iq < len(p)) else ""
        if not q:
            continue
        q_total += 1
        dt = p[idt].strip() if (idt is not None and idt < len(p)) else ""
        sd = p[isd].strip() if (isd is not None and isd < len(p)) else ""
        if dt and sd:
            q_ok += 1
        else:
            q_missing += 1

# Ergebnis ausgeben: Gesamtzahl sowie vollstaendige vs. unvollstaendige Query-Events
print(f"Query-Events (query != '')            : {q_total:,}")
print(f"  davon mit vollstaendigem date+search_id: {q_ok:,}")
print(f"  davon mit fehlendem date oder search_id: {q_missing:,}")