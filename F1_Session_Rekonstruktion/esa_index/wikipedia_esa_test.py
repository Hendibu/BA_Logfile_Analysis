# wikipedia_esa_test.py -- vergleicht ESA-Cosinus-Werte fuer Beispiel-Query-Paare
# bei verschiedenen TOPN-Werten, um den Einfluss der Konzeptanzahl zu pruefen.
# Eingabe: wiki_index_full (PyTerrier-Index)

import os
# Lokale Umgebung: an die eigene Installation anpassen.
# JAVA_HOME wird von PyTerrier (Java-basiert) benoetigt und muss auf ein JDK zeigen;
# ein bereits in der Umgebung gesetzter Wert wird bevorzugt.
os.environ.setdefault("JAVA_HOME", r"<Pfad zur lokalen JDK-Installation>")
import numpy as np
import pyterrier as pt

# Lokaler Pfad zum ESA-/Wikipedia-Index; BM25-Retriever auf Top-1000 begrenzen
INDEX_DIR = r"<Pfad zum wiki_index_full>"
index = pt.IndexFactory.of(INDEX_DIR)
try:
    bm25 = pt.terrier.Retriever(index, wmodel="BM25") % 1000
except AttributeError:
    bm25 = pt.BatchRetrieve(index, wmodel="BM25") % 1000

# ESA-Vektor einer Query: Top-1000 Wikipedia-Konzepte mit BM25-Score
def full_vector(query):
    res = bm25.search(query)                       # Top-1000, nach Score sortiert
    return list(zip(res["docno"], res["score"]))

# Cosinus-Aehnlichkeit zweier ESA-Vektoren, beschraenkt auf die jeweiligen Top-N Konzepte
def cosine_topn(vec1, vec2, topn):
    v1 = dict(vec1[:topn]); v2 = dict(vec2[:topn])  # nur die Top-N Konzepte
    common = set(v1) & set(v2)
    if not common:
        return 0.0
    dot = sum(v1[c]*v2[c] for c in common)
    n1 = np.sqrt(sum(s*s for s in v1.values()))
    n2 = np.sqrt(sum(s*s for s in v2.values()))
    return dot/(n1*n2) if n1 and n2 else 0.0

# Beispielpaare: je zwei verwandte und zwei unverwandte Themen als Kontrolle
pairs = [("global warming","climate change"),
         ("machine learning","artificial intelligence"),
         ("global warming","italian cuisine"),
         ("machine learning","roman empire")]

# ESA-Vektoren fuer alle vorkommenden Queries einmalig vorberechnen
vecs = {}
for a,b in pairs:
    for q in (a,b):
        if q not in vecs:
            vecs[q] = full_vector(q)

# Fuer verschiedene TOPN die Cosinus-Werte aller Paare ausgeben
for topn in (100, 300, 500, 1000):
    print(f"--- TOPN = {topn} ---")
    for a,b in pairs:
        print(f"  {a!r:26} <-> {b!r:24}: {cosine_topn(vecs[a], vecs[b], topn):.3f}")