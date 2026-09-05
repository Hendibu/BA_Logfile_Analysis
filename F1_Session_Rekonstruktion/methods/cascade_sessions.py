# ============================================================================
# cascade_sessions.py -- Kaskade Stufe 1+2+3+4, jetzt PRO uid|Tag.
# Eingabe dis22_uidday.tsv (nach uid,ts sortiert). Bei jedem uid|Tag-Wechsel
# wird eine harte Session-Grenze gesetzt (stage="grp"), kein Vergleich darueber.
#   start=erste Zeile | grp=uid|Tag-Grenze | gap=>90min | s1..s4=Stufen | boundary=keine
# ============================================================================
import os, csv, re, random, time
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sklearn.feature_extraction.text import TfidfVectorizer

os.environ["JAVA_HOME"] = r"C:\Users\hebus\AppData\Local\Programs\Eclipse Adoptium\jdk-21.0.11.10-hotspot"
import pyterrier as pt

SORTED    = "dis22_uidday.tsv"                 # <-- Eingabe jetzt uid|Tag-sortiert
OUT       = "cascade_full_1234.tsv"
TIME_FILE = OUT + ".time"
INDEX_DIR = r"C:\Bachelorarbeit\Wikipedia\wiki_index"
MAX_ROWS  = None

WINDOW_SEC = 90 * 60
TOKEN_TH   = 0.50
SIM_TH     = 0.30
CHAR_NGRAM = (2, 4)
ESA_TH     = 0.30
TOPN       = 1000
SERP_TH    = 0.10

SAMPLE_FIT = 1_000_000
MAX_FEAT   = 200_000
CHUNK_ROWS = 50_000
ESA_BATCH  = 2_000

OUTCOLS = ["session_id", "ts", "query", "serp", "search_id", "esa_cos", "stage", "uid"]
csv.field_size_limit(2**31 - 1); random.seed(42)

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")
def toks(q): return set(q.lower().split())
def day(ts): return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
def grp_of(uid, ts): return uid + "|" + day(ts)          # <-- Gruppen-Schluessel uid|Tag
def stage1_same(qa, ta, qb, tb):
    if qa == qb: return True
    if ta and tb and (ta <= tb or tb <= ta): return True
    if ta and tb and len(ta & tb) / len(ta | tb) >= TOKEN_TH: return True
    return False
def parse_serp(s):
    s = s.strip().strip("[]"); return set(x.strip() for x in s.split(",") if x.strip())
def jacc(a, b):
    return 0.0 if (not a or not b) else len(a & b) / len(a | b)

index = pt.IndexFactory.of(INDEX_DIR)
try:
    bm25 = pt.terrier.Retriever(index, wmodel="BM25") % TOPN
except AttributeError:
    bm25 = pt.BatchRetrieve(index, wmodel="BM25") % TOPN

_san = re.compile(r"[^0-9a-zA-Z]+")
def sanitize(q): return _san.sub(" ", q).strip()

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

def esa_cos(va, vb):
    if not va or not vb: return 0.0
    if len(va) > len(vb): va, vb = vb, va
    return float(sum(s * vb[d] for d, s in va.items() if d in vb))

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
    fo.close(); print("Bereits fertig.", flush=True); raise SystemExit

# ---- Pass 2: Kaskade -------------------------------------------------------
print("Pass 2: Sessions bilden ...", flush=True)
t0 = time.time(); seen_rows = rows_done
cnt = {"start":0,"grp":0,"gap":0,"s1":0,"s2":0,"s3":0,"s4":0,"boundary":0}   # <-- "grp" ergaenzt

def total_elapsed():
    return prev_elapsed + (time.time() - t0)
def write_time():
    tmp = TIME_FILE + ".tmp"
    with open(tmp, "w") as tf: tf.write(f"{total_elapsed():.1f}")
    os.replace(tmp, TIME_FILE)

def process_chunk(chunk):
    global sid, prev_q, prev_t, prev_ts, prev_vec, prev_serp, prev_exists, prev_grp
    qs = [row[iq] for row in chunk]; ts_list = [int(row[its]) for row in chunk]
    tk = [toks(q) for q in qs]; sp_list = [parse_serp(row[isp]) for row in chunk]
    uid_list = [row[iu] for row in chunk]
    grp_list = [grp_of(uid_list[k], ts_list[k]) for k in range(len(chunk))]   # <-- uid|Tag je Zeile
    B = vec.transform(qs)

    lab = [None] * len(chunk); needed = set()
    for k in range(len(chunk)):
        if k == 0: pq, pt_, pts, pvec, pex, pg = prev_q, prev_t, prev_ts, prev_vec, prev_exists, prev_grp
        else:      pq, pt_, pts, pvec, pex, pg = qs[k-1], tk[k-1], ts_list[k-1], B[k-1], True, grp_list[k-1]
        if not pex: lab[k] = "start"; continue
        if grp_list[k] != pg: lab[k] = "grp"                 # <-- uid|Tag-Grenze -> neue Session
        elif ts_list[k] - pts > WINDOW_SEC: lab[k] = "gap"
        elif stage1_same(pq, pt_, qs[k], tk[k]): lab[k] = "s1"
        elif float(B[k].multiply(pvec).sum()) >= SIM_TH: lab[k] = "s2"
        else:
            lab[k] = "undecided"; needed.add(pq); needed.add(qs[k])

    esa = esa_vectors_for(needed) if needed else {}

    buf = []
    for k in range(len(chunk)):
        l = lab[k]; ecos_out = ""
        if l == "start": sid = 1
        elif l == "grp": sid += 1                            # <-- Gruppengrenze
        elif l == "gap": sid += 1
        elif l in ("s1", "s2"): pass
        else:
            pq   = prev_q    if k == 0 else qs[k-1]
            psrp = prev_serp if k == 0 else sp_list[k-1]
            ecos = esa_cos(esa.get(qs[k]), esa.get(pq)); ecos_out = f"{ecos:.4f}"
            if ecos >= ESA_TH:                       l = "s3"
            elif jacc(sp_list[k], psrp) >= SERP_TH:  l = "s4"
            else:                                    l = "boundary"; sid += 1
        cnt[l] += 1
        buf.append([f"session{sid}", ts_list[k], qs[k], chunk[k][isp],
                    chunk[k][isid], ecos_out, l, uid_list[k]])
        prev_q, prev_t, prev_ts = qs[k], tk[k], ts_list[k]
        prev_vec, prev_serp, prev_exists = B[k], sp_list[k], True
        prev_grp = grp_list[k]                               # <-- prev_grp mitfuehren
    w.writerows(buf); fo.flush(); os.fsync(fo.fileno())
    write_time()

with open(SORTED, newline="", encoding="utf-8") as fin:
    r = csv.reader(strip_nul(fin), delimiter="\t"); h = next(r)
    iq, its, isp, isid, iu = (h.index("query"), h.index("ts"), h.index("serp"),
                              h.index("search_id"), h.index("uid"))
    for _ in range(rows_done): next(r, None)
    chunk = []
    for row in r:
        if MAX_ROWS is not None and seen_rows >= MAX_ROWS: break
        chunk.append(row); seen_rows += 1
        if len(chunk) >= CHUNK_ROWS:
            process_chunk(chunk); chunk = []
            done = seen_rows - rows_done; rate = done / max(time.time() - t0, 1e-9)
            eta_h = (TOTAL - seen_rows) / rate / 3600 if rate > 0 else float("inf")
            print(f"   {seen_rows:,}/{TOTAL:,} | {sid} Sess | "
                  f"s1={cnt['s1']:,} s2={cnt['s2']:,} s3={cnt['s3']:,} s4={cnt['s4']:,} "
                  f"grenzen={cnt['gap']+cnt['boundary']+cnt['grp']:,} | {rate:.0f} Z/s | "
                  f"ETA {eta_h:.1f} h | ges {total_elapsed()/3600:.1f} h", flush=True)
    if chunk: process_chunk(chunk)
fo.close(); write_time()
print(f"Fertig: {sid} Sessions, {seen_rows:,} Zeilen -> {OUT}", flush=True)
print(f"   Gesamtzeit (kumuliert): {total_elapsed()/3600:.2f} h", flush=True)
print(f"   (dieser Lauf) {cnt}", flush=True)






# ============================================================================
# cascade_sessions.py  -- Kaskade Stufe 1+2+3+4, mit Stufen-Protokollierung
# Neue Ausgabespalte "stage": welche Stufe hat die Entscheidung getroffen?
#   start  = allererste Zeile (Session-Start)
#   gap    = Grenze wegen >90 Min Abstand
#   s1     = gleiche Session via Stufe 1 (lexikalisch)
#   s2     = gleiche Session via Stufe 2 (Zeichen-n-Gramm-Cosinus)
#   s3     = gleiche Session via Stufe 3 (ESA)
#   s4     = gleiche Session via Stufe 4 (SERP-Overlap)
#   boundary = Grenze, keine Stufe hat gegriffen
# ============================================================================
# ============================================================================
# cascade_full.py  -- Kaskade Stufe 1+2+3+4, mit Stufen-Protokollierung
#                     und KUMULIERTER Zeitmessung ueber Resumes hinweg.
# ============================================================================
# import os, csv, re, random, time
# import numpy as np
# import pandas as pd
# from sklearn.feature_extraction.text import TfidfVectorizer

# os.environ["JAVA_HOME"] = r"C:\Users\hebus\AppData\Local\Programs\Eclipse Adoptium\jdk-21.0.11.10-hotspot"
# import pyterrier as pt

# #SORTED    = "dis22_sorted.tsv"
# SORTED    = "dis22_sorted_noburst.tsv"
# OUT       = "cascade_full_1234.tsv"
# TIME_FILE = OUT + ".time"
# INDEX_DIR = r"C:\Bachelorarbeit\Wikipedia\wiki_index"
# MAX_ROWS  = None                      # <-- auf 5 Mio gesetzt

# WINDOW_SEC = 90 * 60
# TOKEN_TH   = 0.50
# SIM_TH     = 0.30
# CHAR_NGRAM = (2, 4)
# ESA_TH     = 0.30
# TOPN       = 1000
# SERP_TH    = 0.10

# SAMPLE_FIT = 1_000_000
# MAX_FEAT   = 200_000
# CHUNK_ROWS = 50_000
# ESA_BATCH  = 2_000

# OUTCOLS = ["session_id", "ts", "query", "serp", "search_id", "esa_cos", "stage", "uid"]   # <-- uid ergaenzt
# csv.field_size_limit(2**31 - 1); random.seed(42)

# def strip_nul(fo):
#     for line in fo: yield line.replace("\x00", "")
# def toks(q): return set(q.lower().split())
# def stage1_same(qa, ta, qb, tb):
#     if qa == qb: return True
#     if ta and tb and (ta <= tb or tb <= ta): return True
#     if ta and tb and len(ta & tb) / len(ta | tb) >= TOKEN_TH: return True
#     return False
# def parse_serp(s):
#     s = s.strip().strip("[]"); return set(x.strip() for x in s.split(",") if x.strip())
# def jacc(a, b):
#     return 0.0 if (not a or not b) else len(a & b) / len(a | b)

# index = pt.IndexFactory.of(INDEX_DIR)
# try:
#     bm25 = pt.terrier.Retriever(index, wmodel="BM25") % TOPN
# except AttributeError:
#     bm25 = pt.BatchRetrieve(index, wmodel="BM25") % TOPN

# _san = re.compile(r"[^0-9a-zA-Z]+")
# def sanitize(q): return _san.sub(" ", q).strip()

# def _retrieve_batch(sub):
#     df = pd.DataFrame({"qid": [str(j) for j in range(len(sub))],
#                        "query": [sanitize(q) for q in sub]})
#     df = df[df["query"].str.len() > 0]; res_map = {}
#     if not df.empty:
#         res = bm25.transform(df)
#         for qid, g in res.groupby("qid"):
#             scores = g["score"].to_numpy(dtype=np.float64)
#             nrm = np.sqrt((scores * scores).sum())
#             if nrm > 0:
#                 res_map[int(qid)] = dict(zip(g["docno"].tolist(), scores / nrm))
#     return res_map

# def esa_vectors_for(query_set):
#     qlist = list(query_set); out = {}
#     for start in range(0, len(qlist), ESA_BATCH):
#         sub = qlist[start:start + ESA_BATCH]
#         try:
#             got = _retrieve_batch(sub)
#         except Exception as e:
#             print(f"   [WARN] Batch fehlgeschlagen ({e}); einzeln ...", flush=True)
#             got = {}
#             for j, q in enumerate(sub):
#                 try:
#                     g = _retrieve_batch([q])
#                     if 0 in g: got[j] = g[0]
#                 except Exception: pass
#         for j, q in enumerate(sub): out[q] = got.get(j, {})
#     return out

# def esa_cos(va, vb):
#     if not va or not vb: return 0.0
#     if len(va) > len(vb): va, vb = vb, va
#     return float(sum(s * vb[d] for d, s in va.items() if d in vb))

# def recover_state(out_path):
#     if not os.path.exists(out_path): return None
#     tmp = out_path + ".tmp"; rows_done = 0; last = None
#     with open(out_path, newline="", encoding="utf-8") as fin, \
#          open(tmp, "w", newline="", encoding="utf-8") as fout:
#         r = csv.reader(strip_nul(fin), delimiter="\t"); w = csv.writer(fout, delimiter="\t")
#         try: next(r)
#         except StopIteration: os.remove(tmp); return None
#         w.writerow(OUTCOLS)
#         for row in r:
#             if len(row) != len(OUTCOLS): continue
#             w.writerow(row); rows_done += 1; last = row
#     os.replace(tmp, out_path)
#     if rows_done == 0 or last is None: return None
#     return rows_done, int(last[0].replace("session", "")), last[2], int(last[1]), last[3]

# # ---- Pass 1: Vokabular -----------------------------------------------------
# print("Pass 1: Zeichen-n-Gramm-Vokabular lernen ...", flush=True)
# t_fit = time.time(); sample = []; n = 0
# with open(SORTED, newline="", encoding="utf-8") as f:
#     r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r); iq = h.index("query")
#     for row in r:
#         if MAX_ROWS is not None and n >= MAX_ROWS: break
#         n += 1; q = row[iq]
#         if len(sample) < SAMPLE_FIT: sample.append(q)
#         else:
#             j = random.randint(0, n - 1)
#             if j < SAMPLE_FIT: sample[j] = q
# vec = TfidfVectorizer(analyzer="char_wb", ngram_range=CHAR_NGRAM, max_features=MAX_FEAT).fit(sample)
# del sample; TOTAL = n
# print(f"   {n} Zeilen (Ziel), {len(vec.vocabulary_)} n-Gramme ({time.time()-t_fit:.0f}s)", flush=True)

# # ---- Zustand + kumulierte Zeit ---------------------------------------------
# st = recover_state(OUT)
# if st:
#     rows_done, sid, prev_q, prev_ts, prev_serp_raw = st
#     prev_t = toks(prev_q); prev_vec = vec.transform([prev_q])[0]
#     prev_serp = parse_serp(prev_serp_raw); prev_exists = True
#     fo = open(OUT, "a", newline="", encoding="utf-8"); w = csv.writer(fo, delimiter="\t")
#     prev_elapsed = 0.0
#     if os.path.exists(TIME_FILE):
#         try: prev_elapsed = float(open(TIME_FILE).read().strip())
#         except Exception: prev_elapsed = 0.0
#     print(f"RESUME: weiter bei Zeile {rows_done:,} ({sid} Sessions, "
#           f"bisher {prev_elapsed/3600:.1f} h).", flush=True)
# else:
#     rows_done = 0; sid = 0
#     prev_q = prev_t = prev_ts = prev_vec = prev_serp = None; prev_exists = False
#     fo = open(OUT, "w", newline="", encoding="utf-8"); w = csv.writer(fo, delimiter="\t")
#     w.writerow(OUTCOLS)
#     prev_elapsed = 0.0
#     print("Neuer Lauf.", flush=True)
# if MAX_ROWS is not None and rows_done >= MAX_ROWS:
#     fo.close(); print("Bereits fertig.", flush=True); raise SystemExit

# # ---- Pass 2: Kaskade -------------------------------------------------------
# print("Pass 2: Sessions bilden ...", flush=True)
# t0 = time.time(); seen_rows = rows_done
# cnt = {"start":0,"gap":0,"s1":0,"s2":0,"s3":0,"s4":0,"boundary":0}

# def total_elapsed():
#     return prev_elapsed + (time.time() - t0)

# def write_time():
#     tmp = TIME_FILE + ".tmp"
#     with open(tmp, "w") as tf: tf.write(f"{total_elapsed():.1f}")
#     os.replace(tmp, TIME_FILE)

# def process_chunk(chunk):
#     global sid, prev_q, prev_t, prev_ts, prev_vec, prev_serp, prev_exists
#     qs = [row[iq] for row in chunk]; ts_list = [int(row[its]) for row in chunk]
#     tk = [toks(q) for q in qs]; sp_list = [parse_serp(row[isp]) for row in chunk]
#     uid_list = [row[iu] for row in chunk]                      # <-- NEU: uid je Zeile
#     B = vec.transform(qs)

#     lab = [None] * len(chunk); needed = set()
#     for k in range(len(chunk)):
#         if k == 0: pq, pt_, pts, pvec, pex = prev_q, prev_t, prev_ts, prev_vec, prev_exists
#         else:      pq, pt_, pts, pvec, pex = qs[k-1], tk[k-1], ts_list[k-1], B[k-1], True
#         if not pex: lab[k] = "start"; continue
#         if ts_list[k] - pts > WINDOW_SEC: lab[k] = "gap"
#         elif stage1_same(pq, pt_, qs[k], tk[k]): lab[k] = "s1"
#         elif float(B[k].multiply(pvec).sum()) >= SIM_TH: lab[k] = "s2"
#         else:
#             lab[k] = "undecided"; needed.add(pq); needed.add(qs[k])

#     esa = esa_vectors_for(needed) if needed else {}

#     buf = []
#     for k in range(len(chunk)):
#         l = lab[k]; ecos_out = ""
#         if l == "start": sid = 1
#         elif l == "gap": sid += 1
#         elif l in ("s1", "s2"): pass
#         else:
#             pq   = prev_q    if k == 0 else qs[k-1]
#             psrp = prev_serp if k == 0 else sp_list[k-1]
#             ecos = esa_cos(esa.get(qs[k]), esa.get(pq)); ecos_out = f"{ecos:.4f}"
#             if ecos >= ESA_TH:                       l = "s3"
#             elif jacc(sp_list[k], psrp) >= SERP_TH:  l = "s4"
#             else:                                    l = "boundary"; sid += 1
#         cnt[l] += 1
#         buf.append([f"session{sid}", ts_list[k], qs[k], chunk[k][isp],
#                     chunk[k][isid], ecos_out, l, uid_list[k]])    # <-- NEU: uid angehaengt
#         prev_q, prev_t, prev_ts = qs[k], tk[k], ts_list[k]
#         prev_vec, prev_serp, prev_exists = B[k], sp_list[k], True
#     w.writerows(buf); fo.flush(); os.fsync(fo.fileno())
#     write_time()

# with open(SORTED, newline="", encoding="utf-8") as fin:
#     r = csv.reader(strip_nul(fin), delimiter="\t"); h = next(r)
#     iq, its, isp, isid, iu = (h.index("query"), h.index("ts"), h.index("serp"),
#                               h.index("search_id"), h.index("uid"))   # <-- NEU: iu
#     for _ in range(rows_done): next(r, None)
#     chunk = []
#     for row in r:
#         if MAX_ROWS is not None and seen_rows >= MAX_ROWS: break
#         chunk.append(row); seen_rows += 1
#         if len(chunk) >= CHUNK_ROWS:
#             process_chunk(chunk); chunk = []
#             done = seen_rows - rows_done; rate = done / max(time.time() - t0, 1e-9)
#             eta_h = (TOTAL - seen_rows) / rate / 3600 if rate > 0 else float("inf")
#             print(f"   {seen_rows:,}/{TOTAL:,} | {sid} Sess | "
#                   f"s1={cnt['s1']:,} s2={cnt['s2']:,} s3={cnt['s3']:,} s4={cnt['s4']:,} "
#                   f"grenzen={cnt['gap']+cnt['boundary']:,} | {rate:.0f} Z/s | "
#                   f"ETA {eta_h:.1f} h | ges {total_elapsed()/3600:.1f} h", flush=True)
#     if chunk: process_chunk(chunk)
# fo.close(); write_time()
# print(f"Fertig: {sid} Sessions, {seen_rows:,} Zeilen -> {OUT}", flush=True)
# print(f"   Gesamtzeit (kumuliert ueber alle Laeufe): {total_elapsed()/3600:.2f} h", flush=True)
# print(f"   (dieser Lauf) {cnt}", flush=True)