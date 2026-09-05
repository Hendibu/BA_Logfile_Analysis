# ============================================================================
# Kaskade Stufe 1-2 (nach Hagen et al. 2011, rekonstruiert aus dem Exposé)
# ----------------------------------------------------------------------------
# Fuer jedes chronologisch aufeinanderfolgende Query-Paar wird entschieden:
# Session-Fortsetzung oder Session-Grenze. Gestuft (billig zuerst):
#   - > 90 Min Abstand                     -> Grenze  (Stufe-2-Zeitfenster)
#   - Stufe 1 (lexikalisch): identisch /   -> gleiche Session
#     Generalisierung-Spezialisierung /
#     Token-Overlap
#   - Stufe 2 (geometrisch): Zeichen-n-Gramm-Cosinus >= Schwelle
#                                          -> gleiche Session, sonst Grenze
#   (Im Vollausbau gingen die "sonst"-Faelle an Stufe 3 (ESA) / 4 (Retrieval).)
# Laeuft global (ohne uid) ueber den zeitsortierten Strom, speicherkonstant.
# ============================================================================
import csv, random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# ---- Einstellungen (rekonstruierte Defaults, alle tunebar) -----------------
SORTED     = "../data/dis22_sorted.tsv"    # global zeitsortiert (ts, query, serp, search_id) - aus dem DIS22-Sort
OUT        = "../data/cascade_sessions.tsv"
WINDOW_SEC = 90 * 60      # Stufe 2: 90-Minuten-Fenster (harte Obergrenze)
TOKEN_TH   = 0.50         # Stufe 1: Schwelle fuer Token-Overlap (Jaccard)
SIM_TH     = 0.30         # Stufe 2: Schwelle fuer Zeichen-n-Gramm-Cosinus
CHAR_NGRAM = (2, 4)       # Stufe 2: Groesse der Zeichen-n-Gramme
BATCH      = 20_000       # Vektorisierungs-Batch (nur Tempo, nicht das Ergebnis)
SAMPLE_FIT = 1_000_000    # Stichprobe fuers TF-IDF-Vokabular (Speicher begrenzen)
MAX_FEAT   = 200_000

csv.field_size_limit(2**31 - 1)
random.seed(42)

def strip_nul(fileobj):                       # NUL-Bytes zeilenweise entfernen
    for line in fileobj:
        yield line.replace("\x00", "")

def toks(q):                                  # Query -> Menge kleingeschriebener Tokens
    return set(q.lower().split())

# ---- Stufe 1: lexikalische Entscheidung (True = "offensichtlich gleiche Session") ----
def stage1_same(qa, ta, qb, tb):
    if qa == qb:                                        # identische Query
        return True
    if ta and tb and (ta <= tb or tb <= ta):           # eine Query ist Token-Teilmenge der anderen
        return True                                    #   (Generalisierung / Spezialisierung)
    if ta and tb and len(ta & tb) / len(ta | tb) >= TOKEN_TH:  # genug gemeinsame Tokens
        return True
    return False

# ============================================================================
# PASS 1: Zeichen-n-Gramm-TF-IDF auf einer Zufalls-Stichprobe lernen
#   (analyzer="char_wb" = Zeichen-n-Gramme innerhalb von Wortgrenzen; L2-normiert
#    -> Cosinus zweier Vektoren = ihr Skalarprodukt)
# ============================================================================
print("Pass 1: Zeichen-n-Gramm-Vokabular lernen ...", flush=True)
sample = []; n = 0
with open(SORTED, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r); iq = h.index("query")
    for row in r:
        n += 1; q = row[iq]
        if len(sample) < SAMPLE_FIT:
            sample.append(q)
        else:                                          # Reservoir-Sampling (gleichverteilt, ein Durchlauf)
            j = random.randint(0, n - 1)
            if j < SAMPLE_FIT: sample[j] = q
vec = TfidfVectorizer(analyzer="char_wb", ngram_range=CHAR_NGRAM, max_features=MAX_FEAT).fit(sample)
del sample
print(f"   {n} Zeilen, {len(vec.vocabulary_)} n-Gramme", flush=True)

# ============================================================================
# PASS 2: streamend durch den Strom, Kaskaden-Entscheidung, session_id vergeben
# ============================================================================
print("Pass 2: Sessions bilden ...", flush=True)
sid = 0
prev_q = prev_t = prev_ts = prev_vec = None
batch = []
fo = open(OUT, "w", newline="", encoding="utf-8"); w = csv.writer(fo, delimiter="\t")
w.writerow(["session_id", "ts", "query", "serp", "search_id"])

def flush():
    global sid, prev_q, prev_t, prev_ts, prev_vec, batch
    if not batch: return
    B = vec.transform([b[iq] for b in batch])          # Zeichen-n-Gramm-Vektoren des Batches
    # Cosinus zwischen aufeinanderfolgenden Zeilen INNERHALB des Batches (vektorisiert)
    within = np.asarray(B[1:].multiply(B[:-1]).sum(axis=1)).ravel() if B.shape[0] > 1 else np.array([])
    for k, b in enumerate(batch):
        q = b[iq]; t = toks(q); ts = int(b[its])
        if prev_vec is None:                           # allererste Zeile
            sid = 1
        else:
            gap = ts - prev_ts
            if gap > WINDOW_SEC:                        # Stufe 2: zu weit weg -> Grenze
                sid += 1
            elif stage1_same(prev_q, prev_t, q, t):     # Stufe 1: offensichtlich zusammengehoerig
                pass                                    #   -> gleiche Session (sid bleibt)
            else:
                # Cosinus curr vs. vorherige Zeile (batch-uebergreifend gegen prev_vec)
                cos = float((B[0].multiply(prev_vec)).sum()) if k == 0 else float(within[k - 1])
                if cos < SIM_TH:                        # Stufe 2: nicht aehnlich genug -> Grenze
                    sid += 1                            #   (im Vollausbau -> Stufe 3/4)
        w.writerow([f"session{sid}", ts, q, b[isp], b[isid]])
        prev_q, prev_t, prev_ts, prev_vec = q, t, ts, B[k]
    batch = []

with open(SORTED, newline="", encoding="utf-8") as fin:
    r = csv.reader(strip_nul(fin), delimiter="\t"); h = next(r)
    iq, its, isp, isid = h.index("query"), h.index("ts"), h.index("serp"), h.index("search_id")
    for row in r:
        batch.append(row)
        if len(batch) >= BATCH: flush()
    flush()
fo.close()
print(f"Fertig: {sid} Sessions -> {OUT}", flush=True)