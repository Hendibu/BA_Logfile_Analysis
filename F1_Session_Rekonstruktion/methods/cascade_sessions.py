# cascade_sessions.py -- adaptierte Kaskade (Stufen 1-4), rekonstruiert Sessions PRO uid|Tag.
# Bei jedem uid|Tag-Wechsel wird eine harte Session-Grenze gesetzt (stage="grp"),
# darueber hinweg wird nicht verglichen. stage-Werte:
#   start=erste Zeile | grp=uid|Tag-Grenze | gap=>90min | s1..s4=Stufen | boundary=keine Stufe griff
# Eingabe: dis22_uidday.tsv (nach uid,ts sortiert) | Ausgabe: cascade_full_1234.tsv (+ .time)

import os, csv, re, random, time
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sklearn.feature_extraction.text import TfidfVectorizer

# JAVA_HOME wird von PyTerrier (Java-basiert) benoetigt; bereits gesetzter Wert wird bevorzugt
os.environ.setdefault("JAVA_HOME", r"<Pfad zur lokalen JDK-Installation>")
import pyterrier as pt

# Ein-/Ausgabepfade und lokaler Wikipedia-Index
SORTED    = "../../data/dis22_uidday.tsv"                 # <-- Eingabe jetzt uid|Tag-sortiert
OUT       = "../../data/cascade_full_1234.tsv"
TIME_FILE = OUT + ".time"
INDEX_DIR = r"C:\Bachelorarbeit\Wikipedia\wiki_index"
MAX_ROWS  = None

# Kaskaden-Parameter: Zeitfenster und Schwellwerte der einzelnen Stufen
WINDOW_SEC = 90 * 60
TOKEN_TH   = 0.50
SIM_TH     = 0.30
CHAR_NGRAM = (2, 4)
ESA_TH     = 0.30
TOPN       = 1000
SERP_TH    = 0.10

# Technische Parameter: Stichprobe fuers Vokabular, Feature-Zahl, Chunk- und ESA-Batchgroesse
SAMPLE_FIT = 1_000_000
MAX_FEAT   = 200_000
CHUNK_ROWS = 50_000
ESA_BATCH  = 2_000

OUTCOLS = ["session_id", "ts", "query", "serp", "search_id", "esa_cos", "stage", "uid"]
csv.field_size_limit(2**31 - 1); random.seed(42)

# Hilfsfunktionen: NUL-Bytes entfernen, Tokenisieren, Tag- und Gruppen-Schluessel bilden
def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")
def toks(q): return set(q.lower().split())
def day(ts): return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
def grp_of(uid, ts): return uid + "|" + day(ts)          # <-- Gruppen-Schluessel uid|Tag
# Stufe 1 (lexikalisch): identische Query, Teilmenge/Obermenge oder Token-Jaccard >= TOKEN_TH
def stage1_same(qa, ta, qb, tb):
    if qa == qb: return True
    if ta and tb and (ta <= tb or tb <= ta): return True
    if ta and tb and len(ta & tb) / len(ta | tb) >= TOKEN_TH: return True
    return False
# SERP-Feld in Menge parsen und Jaccard-Aehnlichkeit zweier Mengen berechnen
def parse_serp(s):
    s = s.strip().strip("[]"); return set(x.strip() for x in s.split(",") if x.strip())
def jacc(a, b):
    return 0.0 if (not a or not b) else len(a & b) / len(a | b)

# ESA-Retriever: BM25 ueber den Wikipedia-Index, auf die Top-N Konzepte begrenzt
index = pt.IndexFactory.of(INDEX_DIR)
try:
    bm25 = pt.terrier.Retriever(index, wmodel="BM25") % TOPN
except AttributeError:
    bm25 = pt.BatchRetrieve(index, wmodel="BM25") % TOPN

# Query fuer die Index-Suche bereinigen (nur alphanumerische Zeichen)
_san = re.compile(r"[^0-9a-zA-Z]+")
def sanitize(q): return _san.sub(" ", q).strip()

# Ein Batch Queries gegen den Index suchen -> je Query ein normierter ESA-Vektor (docno -> score)
def _retrieve_batch(sub):
    df = pd.DataFrame({"qid": [str(j) for j in range(len(sub))],
                       "query": [sanitize(q) for q in sub]})
    df = df[df["query"].str.len() > 0]; res_map = {}
    if not df.empty:
        res = bm25.transform(df)
        for qid, g in res.groupby("qid"):
            scores = g["score"].to_numpy(dtype=np.float64)
            nrm = np.sqrt((scores * scores).sum())
            if nrm > 0:
                res_map[int(qid)] = dict(zip(g["docno"].tolist(), scores / nrm))
    return res_map

# ESA-Vektoren fuer eine Menge Queries holen (batchweise, mit Einzel-Fallback bei Fehlern)
def esa_vectors_for(query_set):
    qlist = list(query_set); out = {}
    for start in range(0, len(qlist), ESA_BATCH):
        sub = qlist[start:start + ESA_BATCH]
        try:
            got = _retrieve_batch(sub)
        except Exception as e:
            print(f"   [WARN] Batch fehlgeschlagen ({e}); einzeln ...", flush=True)
            got = {}
            for j, q in enumerate(sub):
                try:
                    g = _retrieve_batch([q])
                    if 0 in g: got[j] = g[0]
                except Exception: pass
        for j, q in enumerate(sub): out[q] = got.get(j, {})
    return out

# ESA-Cosinus zweier (bereits normierter) Vektoren = Skalarprodukt der gemeinsamen Konzepte
def esa_cos(va, vb):
    if not va or not vb: return 0.0
    if len(va) > len(vb): va, vb = vb, va
    return float(sum(s * vb[d] for d, s in va.items() if d in vb))

# Resume-Unterstuetzung: bereits geschriebene Ausgabe pruefen/reparieren und letzten Stand zurueckgeben
def recover_state(out_path):
    if not os.path.exists(out_path): return None
    tmp = out_path + ".tmp"; rows_done = 0; last = None
    with open(out_path, newline="", encoding="utf-8") as fin, \
         open(tmp, "w", newline="", encoding="utf-8") as fout:
        r = csv.reader(strip_nul(fin), delimiter="\t"); w = csv.writer(fout, delimiter="\t")
        try: next(r)
        except StopIteration: os.remove(tmp); return None
        w.writerow(OUTCOLS)
        for row in r:
            if len(row) != len(OUTCOLS): continue
            w.writerow(row); rows_done += 1; last = row
    os.replace(tmp, out_path)
    if rows_done == 0 or last is None: return None
    # NEU: uid (last[7]) mit zurueckgeben, damit prev_grp beim Resume stimmt
    return rows_done, int(last[0].replace("session", "")), last[2], int(last[1]), last[3], last[7]

# ---- Pass 1: Vokabular -----------------------------------------------------
# Zeichen-n-Gramm-Vokabular auf einer Zufallsstichprobe der Queries lernen (Reservoir-Sampling)
print("Pass 1: Zeichen-n-Gramm-Vokabular lernen ...", flush=True)
t_fit = time.time(); sample = []; n = 0
with open(SORTED, newline="", encoding="utf-8") as f:
    r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r); iq = h.index("query")
    for row in r:
        if MAX_ROWS is not None and n >= MAX_ROWS: break
        n += 1; q = row[iq]
        if len(sample) < SAMPLE_FIT: sample.append(q)
        else:
            j = random.randint(0, n - 1)
            if j < SAMPLE_FIT: sample[j] = q
vec = TfidfVectorizer(analyzer="char_wb", ngram_range=CHAR_NGRAM, max_features=MAX_FEAT).fit(sample)
del sample; TOTAL = n
print(f"   {n} Zeilen (Ziel), {len(vec.vocabulary_)} n-Gramme ({time.time()-t_fit:.0f}s)", flush=True)

# ---- Zustand + kumulierte Zeit ---------------------------------------------
# Entweder an vorhandener Ausgabe fortsetzen (Resume) oder einen neuen Lauf starten
st = recover_state(OUT)
if st:
    rows_done, sid, prev_q, prev_ts, prev_serp_raw, prev_uid = st       # <-- prev_uid
    prev_t = toks(prev_q); prev_vec = vec.transform([prev_q])[0]
    prev_serp = parse_serp(prev_serp_raw); prev_exists = True
    prev_grp = grp_of(prev_uid, prev_ts)                                # <-- prev_grp rekonstruieren
    fo = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fo, delimiter="\t")
    prev_elapsed = 0.0
    if os.path.exists(TIME_FILE):
        try: prev_elapsed = float(open(TIME_FILE).read().strip())
        except Exception: prev_elapsed = 0.0
    print(f"RESUME: weiter bei Zeile {rows_done:,} ({sid} Sessions, "
          f"bisher {prev_elapsed/3600:.1f} h).", flush=True)
else:
    rows_done = 0; sid = 0
    prev_q = prev_t = prev_ts = prev_vec = prev_serp = None; prev_exists = False
    prev_grp = None                                                     # <-- NEU
    fo = open(OUT, "w", newline="", encoding="utf-8"); w = csv.writer(fo, delimiter="\t")
    w.writerow(OUTCOLS)
    prev_elapsed = 0.0
    print("Neuer Lauf.", flush=True)
if MAX_ROWS is not None and rows_done >= MAX_ROWS: