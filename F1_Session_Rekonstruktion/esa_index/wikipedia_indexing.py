import os, json
os.environ["JAVA_HOME"] = r"C:\Users\hebus\AppData\Local\Programs\Eclipse Adoptium\jdk-21.0.11.10-hotspot"
import pyterrier as pt

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

index = pt.IndexFactory.of(index_ref)
print("Fertig. Dokumente im Index:", index.getCollectionStatistics().getNumberOfDocuments())