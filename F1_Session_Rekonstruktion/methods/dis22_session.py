# dis22_session.py -- DIS22-Sessionrekonstruktion PRO uid|Tag (Eingabe dis22_uidday.tsv).
# Bei jedem uid|Tag-Wechsel harte Grenze; sonst gleiche Session nur, wenn ALLE drei
# Kriterien erfuellt sind: Zeitabstand < TD_SEC, SERP-Jaccard >= SERP_TH, Wort-Cosinus >= COS_TH.
# Eingabe: dis22_uidday.tsv | Ausgabe: dis22_sessions.tsv (+ .time)

import csv, random, time
import numpy as np
from datetime import datetime, timezone
from sklearn.feature_extraction.text import TfidfVectorizer

# Pfade sowie DIS22-Parameter (Zeitfenster, SERP- und Cosinus-Schwelle) und technische Groessen
SORTED, OUT = "../../data/dis22_uidday.tsv", "../../data/dis22_sessions.tsv"
TIME_FILE   = OUT + ".time"
MAX_ROWS    = None
TD_SEC, SERP_TH, COS_TH = 5*60, 0.01, 0.10
BATCH, SAMPLE_FIT, MAX_FEAT = 20_000, 1_000_000, 100_000

csv.field_size_limit(2**31 - 1); random.seed(42)
# Hilfsfunktionen: NUL-Bytes entfernen, SERP parsen, Jaccard, Tag- und uid|Tag-Schluessel
def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")
def parse_serp(s):
    s = s.strip().strip("[]"); return set(x.strip() for x in s.split(",") if x.strip())
def jacc(a, b):
    return 0.0 if (not a or not b) else len(a & b) / len(a | b)
def day(ts):  return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
def grp_of(uid, ts): return uid + "|" + day(ts)

# Pass 1: Wort-TF-IDF-Vokabular auf einer Zufallsstichprobe der Queries lernen (Reservoir-Sampling)
t0 = time.time()
sample = []; n = 0
with open(SORTED, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r); iq = h.index("query")
    for row in r:
        if MAX_ROWS is not None and n >= MAX_ROWS: break
        n += 1; q = row[iq]
        if len(sample) < SAMPLE_FIT: sample.append(q)
        else:
            j = random.randint(0, n - 1)
            if j < SAMPLE_FIT: sample[j] = q
vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=MAX_FEAT).fit(sample)
del sample
print(f"Pass 1: {n} Zeilen, {len(vec.vocabulary_)} Terme ({time.time()-t0:.0f}s)", flush=True)

# Ausgabedatei anlegen und Zustandsvariablen fuer die laufende Session initialisieren
sid = 0; prev_vec = prev_serp = prev_ts = prev_grp = None; batch = []; seen = 0
fo = open(OUT, "w", newline="", encoding="utf-8"); w = csv.writer(fo, delimiter="\t")
w.writerow(["session_id", "ts", "query", "serp", "search_id", "uid"])

# Einen Batch verarbeiten: je Zeile pruefen, ob sie zur laufenden Session gehoert oder eine neue beginnt
def flush():
    global sid, prev_vec, prev_serp, prev_ts, prev_grp, batch
    if not batch: return
    B = vec.transform([b[iq] for b in batch])
    # Wort-Cosinus benachbarter Zeilen im Batch vorab berechnen (Skalarprodukt der TF-IDF-Vektoren)
    within = np.asarray(B[1:].multiply(B[:-1]).sum(axis=1)).ravel() if B.shape[0] > 1 else np.array([])
    for k, b in enumerate(batch):
        ts = int(b[its]); serp = parse_serp(b[isp]); grp = grp_of(b[iu], ts)
        if prev_vec is None:
            sid = 1
        elif grp != prev_grp:                       # uid|Tag-Grenze -> neue Session
            sid += 1
        else:
            # Cosinus zum Vorgaenger (batchuebergreifend fuer k==0, sonst aus 'within')
            cos = float((B[0].multiply(prev_vec)).sum()) if k == 0 else float(within[k - 1])
            same = ((ts - prev_ts) < TD_SEC) and (jacc(serp, prev_serp) >= SERP_TH) and (cos >= COS_TH)
            if not same: sid += 1
        w.writerow([f"session{sid}", ts, b[iq], b[isp], b[isid], b[iu]])
        prev_vec = B[k]; prev_serp = serp; prev_ts = ts; prev_grp = grp
    batch = []

# Eingabe zeilenweise lesen, batchweise verarbeiten und regelmaessig Fortschritt melden
with open(SORTED, newline="", encoding="utf-8") as fin:
    r = csv.reader(strip_nul(fin), delimiter="\t"); h = next(r)
    iq, its, isp, isid, iu = (h.index("query"), h.index("ts"), h.index("serp"),
                              h.index("search_id"), h.index("uid"))
    for row in r:
        if MAX_ROWS is not None and seen >= MAX_ROWS: break
        batch.append(row); seen += 1
        if len(batch) >= BATCH:
            flush()
            if seen % 500_000 == 0:
                print(f"   {seen:,} Zeilen | {sid} Sessions | {time.time()-t0:.0f}s", flush=True)
    flush()
fo.close()
elapsed = time.time() - t0
with open(TIME_FILE, "w") as tf: tf.write(f"{elapsed:.1f}")
print(f"Fertig: {sid} Sessions, {seen:,} Zeilen, {elapsed/60:.2f} min -> {OUT}", flush=True)