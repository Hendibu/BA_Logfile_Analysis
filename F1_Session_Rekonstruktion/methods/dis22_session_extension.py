# DIS22 Session-EXTENSION -- mergt NUR innerhalb desselben uid|Tag (Fenster bei Gruppenwechsel geleert).
import csv, random, time
import numpy as np
from datetime import datetime, timezone
from sklearn.feature_extraction.text import TfidfVectorizer

IN_SESSIONS = "../../data/dis22_sessions.tsv"
OUT         = "../../data/dis22_sessions_extended.tsv"
TIME_FILE   = OUT + ".time"
WINDOW_SEC  = 30 * 60
MAX_SPAN    = 60 * 60
COS_TH      = 0.10
SERP_TH     = 0.01
SAMPLE_FIT  = 1_000_000
MAX_FEAT    = 100_000
MAX_ACTIVE  = 5_000

csv.field_size_limit(2**31 - 1); random.seed(42)
def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")
def parse_serp(s):
    s = s.strip().strip("[]"); return set(x.strip() for x in s.split(",") if x.strip())
def jacc(a, b):
    return 0.0 if (not a or not b) else len(a & b) / len(a | b)
def day(ts):  return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
def grp_of(uid, ts): return uid + "|" + day(ts)

class UnionFind:
    def __init__(self, t_start, t_end):
        n = len(t_start)
        self.parent = list(range(n)); self.gmin = list(t_start); self.gmax = list(t_end)
    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]; x = self.parent[x]
        return x
    def try_union(self, a, b, max_span):
        ra, rb = self.find(a), self.find(b)
        if ra == rb: return
        nmin = min(self.gmin[ra], self.gmin[rb]); nmax = max(self.gmax[ra], self.gmax[rb])
        if nmax - nmin > max_span: return
        root, other = (ra, rb) if ra < rb else (rb, ra)
        self.parent[other] = root; self.gmin[root] = nmin; self.gmax[root] = nmax

t0 = time.time()
sid_to_idx = {}; rep_query = []; rep_serp = []; t_start = []; t_end = []; rep_grp = []
with open(IN_SESSIONS, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
    i_sid, i_ts, i_q, i_sp, i_uid = (h.index("session_id"), h.index("ts"),
                                     h.index("query"), h.index("serp"), h.index("uid"))
    for row in r:
        sid, ts = row[i_sid], int(row[i_ts])
        if sid not in sid_to_idx:
            sid_to_idx[sid] = len(rep_query)
            rep_query.append(row[i_q]); rep_serp.append(parse_serp(row[i_sp]))
            t_start.append(ts); t_end.append(ts)
            rep_grp.append(grp_of(row[i_uid], ts))       # uid|Tag der Session
        else:
            t_end[sid_to_idx[sid]] = ts
n = len(rep_query)
print(f"Pass A: {n} Sessions eingelesen ({time.time()-t0:.0f}s)", flush=True)

sample = rep_query if n <= SAMPLE_FIT else random.sample(rep_query, SAMPLE_FIT)
vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=MAX_FEAT).fit(sample)
M = vec.transform(rep_query)

uf = UnionFind(t_start, t_end); active = []; cur_grp = None
for i in range(n):
    if rep_grp[i] != cur_grp:               # neue uid|Tag-Gruppe -> Fenster zuruecksetzen
        active = []; cur_grp = rep_grp[i]
    cutoff = t_start[i] - WINDOW_SEC
    active = [j for j in active if t_end[j] >= cutoff]
    if len(active) > MAX_ACTIVE: active = active[-MAX_ACTIVE:]
    if active:
        sims = np.asarray(M[active].dot(M[i].T).todense()).ravel()
        for pos, j in enumerate(active):
            if sims[pos] >= COS_TH and jacc(rep_serp[i], rep_serp[j]) >= SERP_TH:
                uf.try_union(i, j, MAX_SPAN)
    active.append(i)
print(f"Pass B: Merging fertig ({time.time()-t0:.0f}s)", flush=True)

root_to_newid = {}
def new_id(idx):
    root = uf.find(idx)
    if root not in root_to_newid: root_to_newid[root] = len(root_to_newid) + 1
    return root_to_newid[root]
with open(IN_SESSIONS, newline="", encoding="utf-8") as fin, \
     open(OUT, "w", newline="", encoding="utf-8") as fo:
    r = csv.reader(strip_nul(fin), delimiter="\t"); h = next(r)
    i_sid = h.index("session_id"); w = csv.writer(fo, delimiter="\t")
    w.writerow(h + ["ext_session_id"])
    for row in r:
        row.append(f"session{new_id(sid_to_idx[row[i_sid]])}"); w.writerow(row)
elapsed = time.time() - t0
with open(TIME_FILE, "w") as tf: tf.write(f"{elapsed:.1f}")
print(f"Fertig: {n} -> {len(root_to_newid)} Sessions nach Extension, {elapsed/60:.2f} min -> {OUT}", flush=True)



# # ============================================================================
# # Stage 3: Session-Extension - fragmentierte DIS22-Sessions wieder zusammenfuehren
# # ----------------------------------------------------------------------------
# # Zwei Sessions werden verschmolzen, wenn ihre Repraesentanten (jeweils erste
# # Query + erste SERP) sich aehneln UND sie zeitlich nah beieinander liegen:
# #   - Query-Aehnlichkeit:  Cosinus (TF-IDF) >= COS_TH
# #   - SERP-Ueberlappung:   Jaccard        >= SERP_TH
# #   - zeitliche Naehe:     Abstand         <  WINDOW_SEC
# # Schutz gegen Ketten-Explosion: eine zusammengefuehrte Session darf nie laenger
# # als MAX_SPAN werden (sonst wuerde sich ueber wiederkehrende Queries eine
# # einzige Riesen-Session ueber den ganzen Zeitraum bilden).
# # ============================================================================
# import csv, random
# import numpy as np
# from sklearn.feature_extraction.text import TfidfVectorizer

# # ---- Einstellungen ----------------------------------------------------------
# IN_SESSIONS = "dis22_sessions.tsv"            # Eingabe: Ergebnis aus Stage 2
# OUT         = "dis22_sessions_extended.tsv"   # Ausgabe: mit zusaetzlicher Spalte ext_session_id
# WINDOW_SEC  = 30 * 60      # max. zeitlicher Abstand, damit 2 Sessions ueberhaupt verglichen werden
# MAX_SPAN    = 60 * 60      # max. Gesamtdauer einer zusammengefuehrten Session (gegen Ketten-Explosion)
# COS_TH      = 0.10         # Cosinus-Schwelle; 0,1 ist locker -> bei zu viel Merging erhoehen (0.3-0.5)
# SERP_TH     = 0.01         # SERP-Jaccard-Schwelle (wie bei der Erstellung)
# SAMPLE_FIT  = 1_000_000    # Stichprobe fuers TF-IDF-Vokabular (begrenzt den Speicher)
# MAX_FEAT    = 100_000      # max. Anzahl TF-IDF-Merkmale
# MAX_ACTIVE  = 5_000        # Sicherheitsdeckel: max. Sessions gleichzeitig im Fenster

# csv.field_size_limit(2**31 - 1)
# random.seed(42)

# # ---- Hilfsfunktionen --------------------------------------------------------
# def strip_nul(fileobj):                        # NUL-Bytes zeilenweise entfernen
#     for line in fileobj:
#         yield line.replace("\x00", "")

# def parse_serp(s):                             # SERP-String "[1, 2, 3]" -> Menge {"1","2","3"}
#     s = s.strip().strip("[]")
#     return set(x.strip() for x in s.split(",") if x.strip())

# def jacc(a, b):                                # Jaccard-Ueberlappung (0, wenn eine Menge leer ist)
#     return 0.0 if (not a or not b) else len(a & b) / len(a | b)

# # ---- Union-Find MIT Zeitspannen-Deckel -------------------------------------
# # Verwaltet, welche Sessions zu einer gemeinsamen Gruppe gehoeren, und merkt
# # sich pro Gruppe die fruehste Start- und spaeteste Endzeit, um Merges abzulehnen,
# # die die Gruppe zeitlich zu lang machen wuerden.
# class UnionFind:
#     def __init__(self, t_start, t_end):
#         n = len(t_start)
#         self.parent = list(range(n))           # jede Session ist zuerst ihre eigene Gruppe
#         self.gmin   = list(t_start)            # fruehste Startzeit der Gruppe
#         self.gmax   = list(t_end)              # spaeteste Endzeit der Gruppe
#     def find(self, x):                         # Wurzel (= Gruppen-ID) von x
#         while self.parent[x] != x:
#             self.parent[x] = self.parent[self.parent[x]]   # Pfad verkuerzen (Speed)
#             x = self.parent[x]
#         return x
#     def try_union(self, a, b, max_span):       # verschmelzen, falls die Session nicht zu lang wird
#         ra, rb = self.find(a), self.find(b)
#         if ra == rb:
#             return
#         nmin = min(self.gmin[ra], self.gmin[rb])   # kombinierte Zeitspanne
#         nmax = max(self.gmax[ra], self.gmax[rb])
#         if nmax - nmin > max_span:             # wuerde die Session zu lang machen -> NICHT mergen
#             return
#         root, other = (ra, rb) if ra < rb else (rb, ra)
#         self.parent[other] = root              # kleinere Wurzel wird gemeinsame ID
#         self.gmin[root] = nmin                 # neue Zeitspanne merken
#         self.gmax[root] = nmax

# # ============================================================================
# # PASS A: pro Session Repraesentant (erste Query + erste SERP) + Zeitspanne
# #   Die Stage-2-Datei ist zeitsortiert und die session_id waechst nur monoton,
# #   d.h. alle Ereignisse einer Session stehen als zusammenhaengender Block.
# # ============================================================================
# print("Pass A: Repraesentanten je Session bilden ...", flush=True)
# sid_to_idx = {}     # "session123" -> laufender Index 0,1,2,... (= Zeitreihenfolge der Sessions)
# rep_query  = []     # erste Query je Session
# rep_serp   = []     # erste SERP je Session (als Menge von IDs)
# t_start    = []     # Startzeit je Session
# t_end      = []     # Endzeit je Session

# with open(IN_SESSIONS, newline="", encoding="utf-8") as f:
#     r = csv.reader(strip_nul(f), delimiter="\t")
#     h = next(r)
#     i_sid, i_ts, i_q, i_sp = h.index("session_id"), h.index("ts"), h.index("query"), h.index("serp")
#     for row in r:
#         sid, ts, q = row[i_sid], int(row[i_ts]), row[i_q]
#         if sid not in sid_to_idx:              # erste Zeile einer neuen Session
#             sid_to_idx[sid] = len(rep_query)
#             rep_query.append(q)                # -> Repraesentant: erste Query
#             rep_serp.append(parse_serp(row[i_sp]))  # -> Repraesentant: erste SERP
#             t_start.append(ts)
#             t_end.append(ts)
#         else:                                  # weiteres Ereignis derselben Session
#             t_end[sid_to_idx[sid]] = ts        # Endzeit fortschreiben (Datei ist zeitsortiert)

# n = len(rep_query)
# print(f"   {n} Sessions eingelesen", flush=True)

# # ============================================================================
# # TF-IDF der Repraesentanten-Queries
# #   Vokabular/IDF auf einer Stichprobe lernen (Speicher begrenzen), dann alle
# #   Repraesentanten in eine L2-normalisierte Matrix -> Cosinus = Skalarprodukt.
# # ============================================================================
# print("TF-IDF der Repraesentanten ...", flush=True)
# sample = rep_query if n <= SAMPLE_FIT else random.sample(rep_query, SAMPLE_FIT)
# vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=MAX_FEAT).fit(sample)
# M = vec.transform(rep_query)                   # n x Vokabular, sparse, normiert

# # ============================================================================
# # PASS B: gleitendes Zeitfenster + Union-Find (Cosinus UND SERP, mit Deckel)
# # ============================================================================
# print("Pass B: Sessions im Zeitfenster zusammenfuehren ...", flush=True)
# uf = UnionFind(t_start, t_end)
# active = []                                    # Indizes der Sessions, die aktuell im Fenster liegen

# for i in range(n):
#     cutoff = t_start[i] - WINDOW_SEC
#     # 1) Sessions rauswerfen, deren Ende zu lange her ist
#     active = [j for j in active if t_end[j] >= cutoff]
#     # 2) Sicherheitsdeckel gegen extrem dichte Fenster
#     if len(active) > MAX_ACTIVE:
#         active = active[-MAX_ACTIVE:]
#     # 3) Session i in EINEM vektorisierten Schritt gegen alle aktiven vergleichen (Cosinus)
#     if active:
#         sims = np.asarray(M[active].dot(M[i].T).todense()).ravel()   # Cosinus i vs. jede aktive
#         for pos, j in enumerate(active):
#             # nur mergen, wenn Query aehnlich genug UND SERP ueberlappt
#             if sims[pos] >= COS_TH and jacc(rep_serp[i], rep_serp[j]) >= SERP_TH:
#                 uf.try_union(i, j, MAX_SPAN)    # (der Deckel verhindert zu lange Sessions)
#     # 4) Session i selbst kommt ins Fenster
#     active.append(i)

# # ============================================================================
# # PASS C: Ergebnis mit zusammengefuehrter ext_session_id neu schreiben
# # ============================================================================
# print("Pass C: Ergebnis schreiben ...", flush=True)
# root_to_newid = {}                             # Wurzel-Index -> kompakte, fortlaufende neue ID
# def new_id(idx):
#     root = uf.find(idx)
#     if root not in root_to_newid:
#         root_to_newid[root] = len(root_to_newid) + 1
#     return root_to_newid[root]

# with open(IN_SESSIONS, newline="", encoding="utf-8") as fin, \
#      open(OUT, "w", newline="", encoding="utf-8") as fo:
#     r = csv.reader(strip_nul(fin), delimiter="\t")
#     h = next(r)
#     i_sid = h.index("session_id")
#     w = csv.writer(fo, delimiter="\t")
#     w.writerow(h + ["ext_session_id"])         # neue Spalte anhaengen
#     for row in r:
#         row.append(f"session{new_id(sid_to_idx[row[i_sid]])}")
#         w.writerow(row)

# print(f"Fertig: {n} -> {len(root_to_newid)} Sessions nach Extension  ({OUT})", flush=True)
# DIS22 Session-EXTENSION: fragmentierte Sessions ueber ein gleitendes Zeit-
# fenster wieder zusammenfuehren (Cosinus UND SERP-Overlap, mit Zeitspannen-
# Deckel gegen Ketten-Explosion). uid bleibt erhalten, ext_session_id angehaengt.
# import csv, random, time
# import numpy as np
# from sklearn.feature_extraction.text import TfidfVectorizer

# IN_SESSIONS = "dis22_sessions.tsv"
# OUT         = "dis22_sessions_extended.tsv"
# TIME_FILE   = OUT + ".time"
# WINDOW_SEC  = 30 * 60      # max. Abstand, damit 2 Sessions verglichen werden
# MAX_SPAN    = 60 * 60      # max. Gesamtdauer einer zusammengefuehrten Session
# COS_TH      = 0.10         # Query-Cosinus-Schwelle (bei zu viel Merging erhoehen)
# SERP_TH     = 0.01         # SERP-Jaccard-Schwelle
# SAMPLE_FIT  = 1_000_000
# MAX_FEAT    = 100_000
# MAX_ACTIVE  = 5_000

# csv.field_size_limit(2**31 - 1); random.seed(42)
# def strip_nul(fo):
#     for line in fo: yield line.replace("\x00", "")
# def parse_serp(s):
#     s = s.strip().strip("[]"); return set(x.strip() for x in s.split(",") if x.strip())
# def jacc(a, b):
#     return 0.0 if (not a or not b) else len(a & b) / len(a | b)

# class UnionFind:
#     def __init__(self, t_start, t_end):
#         n = len(t_start)
#         self.parent = list(range(n)); self.gmin = list(t_start); self.gmax = list(t_end)
#     def find(self, x):
#         while self.parent[x] != x:
#             self.parent[x] = self.parent[self.parent[x]]; x = self.parent[x]
#         return x
#     def try_union(self, a, b, max_span):
#         ra, rb = self.find(a), self.find(b)
#         if ra == rb: return
#         nmin = min(self.gmin[ra], self.gmin[rb]); nmax = max(self.gmax[ra], self.gmax[rb])
#         if nmax - nmin > max_span: return           # wuerde Session zu lang machen
#         root, other = (ra, rb) if ra < rb else (rb, ra)
#         self.parent[other] = root; self.gmin[root] = nmin; self.gmax[root] = nmax

# t0 = time.time()
# # PASS A: Repraesentant (erste Query + erste SERP) + Zeitspanne je Session
# sid_to_idx = {}; rep_query = []; rep_serp = []; t_start = []; t_end = []
# with open(IN_SESSIONS, newline="", encoding="utf-8") as f:
#     r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
#     i_sid, i_ts, i_q, i_sp = h.index("session_id"), h.index("ts"), h.index("query"), h.index("serp")
#     for row in r:
#         sid, ts = row[i_sid], int(row[i_ts])
#         if sid not in sid_to_idx:
#             sid_to_idx[sid] = len(rep_query)
#             rep_query.append(row[i_q]); rep_serp.append(parse_serp(row[i_sp]))
#             t_start.append(ts); t_end.append(ts)
#         else:
#             t_end[sid_to_idx[sid]] = ts
# n = len(rep_query)
# print(f"Pass A: {n} Sessions eingelesen ({time.time()-t0:.0f}s)", flush=True)

# # TF-IDF der Repraesentanten (Vokabular auf Stichprobe, dann alle transformieren)
# sample = rep_query if n <= SAMPLE_FIT else random.sample(rep_query, SAMPLE_FIT)
# vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=MAX_FEAT).fit(sample)
# M = vec.transform(rep_query)

# # PASS B: gleitendes Zeitfenster + Union-Find (Cosinus UND SERP, mit Deckel)
# uf = UnionFind(t_start, t_end); active = []
# for i in range(n):
#     cutoff = t_start[i] - WINDOW_SEC
#     active = [j for j in active if t_end[j] >= cutoff]
#     if len(active) > MAX_ACTIVE: active = active[-MAX_ACTIVE:]
#     if active:
#         sims = np.asarray(M[active].dot(M[i].T).todense()).ravel()
#         for pos, j in enumerate(active):
#             if sims[pos] >= COS_TH and jacc(rep_serp[i], rep_serp[j]) >= SERP_TH:
#                 uf.try_union(i, j, MAX_SPAN)
#     active.append(i)
# print(f"Pass B: Merging fertig ({time.time()-t0:.0f}s)", flush=True)

# # PASS C: Ergebnis mit ext_session_id schreiben (alle Spalten inkl. uid bleiben)
# root_to_newid = {}
# def new_id(idx):
#     root = uf.find(idx)
#     if root not in root_to_newid: root_to_newid[root] = len(root_to_newid) + 1
#     return root_to_newid[root]
# with open(IN_SESSIONS, newline="", encoding="utf-8") as fin, \
#      open(OUT, "w", newline="", encoding="utf-8") as fo:
#     r = csv.reader(strip_nul(fin), delimiter="\t"); h = next(r)
#     i_sid = h.index("session_id"); w = csv.writer(fo, delimiter="\t")
#     w.writerow(h + ["ext_session_id"])
#     for row in r:
#         row.append(f"session{new_id(sid_to_idx[row[i_sid]])}"); w.writerow(row)
# elapsed = time.time() - t0
# with open(TIME_FILE, "w") as tf: tf.write(f"{elapsed:.1f}")
# print(f"Fertig: {n} -> {len(root_to_newid)} Sessions nach Extension, "
#       f"{elapsed/60:.2f} min -> {OUT}", flush=True)