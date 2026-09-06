import os
os.environ["JAVA_HOME"] = r"C:\Users\hebus\AppData\Local\Programs\Eclipse Adoptium\jdk-21.0.11.10-hotspot"
import numpy as np
import pyterrier as pt

INDEX_DIR = r"C:\Bachelorarbeit\Wikipedia\wiki_index_full"
index = pt.IndexFactory.of(INDEX_DIR)
try:
    bm25 = pt.terrier.Retriever(index, wmodel="BM25") % 1000
except AttributeError:
    bm25 = pt.BatchRetrieve(index, wmodel="BM25") % 1000

def full_vector(query):
    res = bm25.search(query)                       # Top-1000, nach Score sortiert
    return list(zip(res["docno"], res["score"]))

def cosine_topn(vec1, vec2, topn):
    v1 = dict(vec1[:topn]); v2 = dict(vec2[:topn])  # nur die Top-N Konzepte
    common = set(v1) & set(v2)
    if not common:
        return 0.0
    dot = sum(v1[c]*v2[c] for c in common)
    n1 = np.sqrt(sum(s*s for s in v1.values()))
    n2 = np.sqrt(sum(s*s for s in v2.values()))
    return dot/(n1*n2) if n1 and n2 else 0.0

pairs = [("global warming","climate change"),
         ("machine learning","artificial intelligence"),
         ("global warming","italian cuisine"),
         ("machine learning","roman empire")]

vecs = {}
for a,b in pairs:
    for q in (a,b):
        if q not in vecs:
            vecs[q] = full_vector(q)

for topn in (100, 300, 500, 1000):
    print(f"--- TOPN = {topn} ---")
    for a,b in pairs:
        print(f"  {a!r:26} <-> {b!r:24}: {cosine_topn(vecs[a], vecs[b], topn):.3f}")