# count_sessions.py <session_datei>
# Zaehlt Sessions und Events in einer Session-Datei (streamend, O(1)-Speicher).
# Nutzt, dass Zeilen derselben Session zusammenhaengend stehen. NUR Aggregate.
import csv, sys
csv.field_size_limit(2**31 - 1)
PATH = sys.argv[1] if len(sys.argv) > 1 else "dis22_sessions.tsv"

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

with open(PATH, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
    i_sid = h.index(sidcol)
    sessions = 0; events = 0; singles = 0
    cur = None; size = 0
    def close():
        global sessions, singles
        if size > 0:
            sessions += 1
            if size == 1: singles += 1
    for row in r:
        sid = row[i_sid]
        if not sid:                      # leere Session-ID = Grenze
            close(); cur=None; size=0; continue
        events += 1
        if sid != cur:
            close(); cur=sid; size=1
        else:
            size += 1
    close()

print(f"Datei      : {PATH}  (Spalte '{sidcol}')")
print(f"Events     : {events:,}")
print(f"Sessions   : {sessions:,}")
if sessions:
    print(f"Singletons : {singles:,} ({100*singles/sessions:.1f} %)")