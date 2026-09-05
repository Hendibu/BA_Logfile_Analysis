# check_pairs.py <session_datei>
# Zaehlt Events, Sessions, konsekutive Paare (= Events - Sessions) und leere
# Query-Zeilen in einer Session-Datei. Damit laesst sich die Basis der
# Reformulierungsauswertung (218.452 Paare) gegen die Rekonstruktions-Zahlen
# abgleichen. NUR Aggregate.
import csv, sys
csv.field_size_limit(2**31 - 1)
PATH = sys.argv[1] if len(sys.argv) > 1 else "cascade_full_1234_nobots.tsv"

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

with open(PATH, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
    i_sid = h.index(sidcol)
    i_q = h.index("query") if "query" in h else None

    events = 0; sessions = 0; empty_q = 0
    cur = None; size = 0
    def close():
        global sessions
        if size > 0: sessions += 1
    for row in r:
        sid = row[i_sid] if i_sid < len(row) else ""
        if not sid:
            close(); cur = None; size = 0; continue
        events += 1
        if i_q is not None and (i_q >= len(row) or not row[i_q].strip()):
            empty_q += 1
        if sid != cur:
            close(); cur = sid; size = 1
        else:
            size += 1
    close()

pairs = events - sessions
print(f"Datei            : {PATH}  (Spalte '{sidcol}')")
print(f"Events           : {events:,}")
print(f"Sessions         : {sessions:,}")
print(f"konsekutive Paare: {pairs:,}   (= Events - Sessions)")
print(f"leere query-Zeilen: {empty_q:,}")