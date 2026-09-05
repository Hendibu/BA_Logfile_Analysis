# build_title_index.py  [dokument_ordner]
# Baut aus den LongEval-Dokumenten (oeffentliches Korpus) einen Titel-Index:
#   doc_titles.tsv  mit Spalten  doc_id <TAB> title(raw)
# Erkennt Titel-/ID-Feld automatisch, verarbeitet JSON-Array, JSONL und
# {"...":[...]}-Objekte, auch einfach verschachtelt (z.B. unter "metadata").
# Oeffentliches Korpus -> Statistik/Beispiele teilbar.
import json, sys, os, glob

FOLDER = sys.argv[1] if len(sys.argv) > 1 else "."
OUT = "doc_titles.tsv"
TITLE_CANDS = ["title","dc_title","dctitle","document_title","documenttitle",
               "name","heading","titles"]
ID_CANDS    = ["id","docid","doc_id","documentid","document_id","coreid",
               "core_id","_id","docno","cord_uid","uid"]

def norm_key(k): return k.lower().replace(" ", "").replace("-", "_")

def pick(d, cands):
    keys = {norm_key(k): k for k in d}
    for c in cands:
        if c in keys: return d[keys[c]]
    for v in d.values():
        if isinstance(v, dict):
            keys2 = {norm_key(k): k for k in v}
            for c in cands:
                if c in keys2: return v[keys2[c]]
    return None

def as_text(v):
    if v is None: return ""
    if isinstance(v, list): v = v[0] if v else ""
    return str(v).replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()

def iter_records(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, list):
            yield from data; return
        if isinstance(data, dict):
            lk = next((k for k, v in data.items() if isinstance(v, list)), None)
            if lk: yield from data[lk]; return
            yield data; return
    except Exception:
        pass
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: yield json.loads(line)
            except Exception: continue

files = sorted(glob.glob(os.path.join(FOLDER, "*.json")) +
               glob.glob(os.path.join(FOLDER, "*.jsonl")))
if not files:
    sys.exit(f"Keine .json/.jsonl in {FOLDER}")

n_docs = n_titled = 0
title_field = id_field = None
samples = []
with open(OUT, "w", encoding="utf-8") as o:
    for path in files:
        for rec in iter_records(path):
            if not isinstance(rec, dict): continue
            n_docs += 1
            if title_field is None:
                for c in TITLE_CANDS:
                    if pick({k:rec[k] for k in rec}, [c]) is not None:
                        title_field = c; break
                for c in ID_CANDS:
                    if pick({k:rec[k] for k in rec}, [c]) is not None:
                        id_field = c; break
            title = as_text(pick(rec, TITLE_CANDS))
            docid = as_text(pick(rec, ID_CANDS))
            if title:
                n_titled += 1
                o.write(f"{docid}\t{title}\n")
                if len(samples) < 3: samples.append((docid, title))

print(f"Dateien verarbeitet     : {len(files)}")
print(f"Dokumente gesamt        : {n_docs:,}")
print(f"davon mit Titel         : {n_titled:,}")
print(f"erkanntes Titel-Feld    : {title_field}")
print(f"erkanntes ID-Feld       : {id_field}")
print(f"-> geschrieben          : {OUT}")
print("\nBeispiele (doc_id | title):")
for did, t in samples:
    print(f"   {did!r} | {t!r}")