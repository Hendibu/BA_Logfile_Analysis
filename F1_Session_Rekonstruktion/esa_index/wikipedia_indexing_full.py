import os, json, time
os.environ["JAVA_HOME"] = r"C:\Users\hebus\AppData\Local\Programs\Eclipse Adoptium\jdk-21.0.11.10-hotspot"
import pyterrier as pt

ARTICLES  = r"C:\Bachelorarbeit\Wikipedia\wiki_articles_full.jsonl"
INDEX_DIR = r"C:\Bachelorarbeit\Wikipedia\wiki_index_full"

t0 = time.time()

# Artikel als Strom liefern + alle 100.000 den Fortschritt melden
def article_iter(path):
    n = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            n += 1
            if n % 100000 == 0:
                print(f"{n:,} Artikel eingelesen | {(time.time()-t0)/60:.0f} min", flush=True)
            yield {"docno": obj["docno"], "text": obj["text"]}

indexer = pt.IterDictIndexer(INDEX_DIR, overwrite=True, meta={"docno": 20})
index_ref = indexer.index(article_iter(ARTICLES))

index = pt.IndexFactory.of(index_ref)
print("Fertig. Dokumente im Index:", index.getCollectionStatistics().getNumberOfDocuments())