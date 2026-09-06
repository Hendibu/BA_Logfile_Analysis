# wikipedia_indexing.py -- baut aus den extrahierten Simple-English-Artikeln einen
# PyTerrier-Volltextindex (Grundlage fuer die ESA-Stufe der Kaskade).
# Eingabe: wiki_articles.jsonl | Ausgabe: wiki_index (PyTerrier-Index)

import os, json
# JAVA_HOME wird von PyTerrier (Java-basiert) benoetigt und muss auf ein JDK zeigen;
# ein bereits gesetzter Umgebungswert wird bevorzugt.
os.environ.setdefault("JAVA_HOME", r"<Pfad zur lokalen JDK-Installation>")
import pyterrier as pt

# Lokale Pfade: Eingabe-Artikel (JSONL) und Zielverzeichnis des Index
ARTICLES  = r"C:\Bachelorarbeit\Wikipedia\wiki_articles.jsonl"
INDEX_DIR = r"C:\Bachelorarbeit\Wikipedia\wiki_index"

# Artikel als Strom von {docno, text} liefern (speicherschonend, Zeile fuer Zeile)
def article_iter(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            yield {"docno": obj["docno"], "text": obj["text"]}

# Index bauen: 'text' wird indexiert, 'docno' als ID gespeichert
indexer = pt.IterDictIndexer(INDEX_DIR, overwrite=True, meta={"docno": 20})
index_ref = indexer.index(article_iter(ARTICLES))

# Index laden und zur Kontrolle die Anzahl indexierter Dokumente ausgeben
index = pt.IndexFactory.of(index_ref)
print("Fertig. Dokumente im Index:", index.getCollectionStatistics().getNumberOfDocuments())