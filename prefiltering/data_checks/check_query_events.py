# check_query_events.py <rohlog>
# Prueft, wie viele Query-Events (query != '') zusaetzlich unvollstaendige
# Pflichtfelder (date/search_id leer) haben. Erklaert die 90.043.872 -> 89.922.834
# Differenz. NUR Aggregate.
import sys
PATH = sys.argv[1] if len(sys.argv) > 1 else "../../data/log_files.tsv"

with open(PATH, encoding="utf-8", errors="replace") as f:
    h = f.readline().replace("\x00", "").rstrip("\n").split("\t")
    iq = h.index("query")     if "query"     in h else None
    idt = h.index("date")     if "date"      in h else None
    isd = h.index("search_id") if "search_id" in h else None

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

print(f"Query-Events (query != '')            : {q_total:,}")
print(f"  davon mit vollstaendigem date+search_id: {q_ok:,}")
print(f"  davon mit fehlendem date oder search_id: {q_missing:,}")