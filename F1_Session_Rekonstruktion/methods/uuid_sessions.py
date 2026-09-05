# UUID-Session-ERSTELLUNG: Session = die persistente uid selbst.
# Rechnerisch fast gratis (nur Label nach vorhandener id) -- genau das ist
# der interessante Kontrast zu DIS22/Kaskade. Laufzeit wird gemessen.
import csv, time
#SORTED, OUT = "dis22_sorted.tsv", "uuid_sessions.tsv"
SORTED, OUT = "dis22_sorted_noburst.tsv", "uuid_sessions.tsv"
TIME_FILE   = OUT + ".time"
MAX_ROWS    = None
csv.field_size_limit(2**31 - 1)
def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

t0 = time.time(); seen = 0; have = 0
fo = open(OUT, "w", newline="", encoding="utf-8"); w = csv.writer(fo, delimiter="\t")
w.writerow(["session_id", "ts", "query", "serp", "search_id", "uid"])
with open(SORTED, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    iq, its, isp, isid, iu = (h.index("query"), h.index("ts"), h.index("serp"),
                              h.index("search_id"), h.index("uid"))
    for row in r:
        if MAX_ROWS is not None and seen >= MAX_ROWS: break
        seen += 1; u = row[iu]
        sid = f"uuid_{u}" if u else ""           # UUID-Session = uid; leer = kein uid
        if u: have += 1
        w.writerow([sid, row[its], row[iq], row[isp], row[isid], u])
fo.close()
elapsed = time.time() - t0
with open(TIME_FILE, "w") as tf: tf.write(f"{elapsed:.1f}")
print(f"Fertig: {seen:,} Zeilen, {have:,} mit uid ({100*have/max(seen,1):.1f}%), "
      f"{elapsed/60:.2f} min -> {OUT}", flush=True)