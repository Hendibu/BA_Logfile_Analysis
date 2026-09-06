# wikipedia_extraction.py -- extrahiert aus dem Simple-English-Wikipedia-XML-Dump
# den Fliesstext aller Artikel (Namespace 0, keine Redirects) als JSONL.
# Eingabe: simplewiki-latest-pages-articles.xml.bz2 | Ausgabe: wiki_articles.jsonl

import bz2, io, os, json, time
import mwxml
import mwparserfromhell

# Lokale Pfade: Eingabe-Dump (.bz2) und Ausgabedatei (JSONL)
DUMP = r"C:\Bachelorarbeit\Wikipedia\simplewiki-latest-pages-articles.xml.bz2"
OUT  = r"C:\Bachelorarbeit\Wikipedia\wiki_articles.jsonl"

# --- Fortschritts-Wrapper: zaehlt die gelesenen (komprimierten) Bytes der .bz2 ---
class CountingRaw:
    def __init__(self, path):
        self._f = open(path, "rb")
        self.total = os.path.getsize(path)   # Gesamtgroesse des komprimierten Dumps
        self.count = 0                        # bisher gelesene Bytes
    def read(self, size=-1):
        b = self._f.read(size)
        self.count += len(b)
        return b
    def readable(self): return True
    def seekable(self): return False
    def close(self): self._f.close()

# Dump beim Lesen dekomprimieren und dabei den Byte-Fortschritt mitzaehlen
raw    = CountingRaw(DUMP)
stream = io.TextIOWrapper(bz2.BZ2File(raw), encoding="utf-8")   # dekomprimiert + zaehlt

t0   = time.time()
n    = 0     # extrahierte Artikel
seen = 0     # gescannte Seiten (inkl. uebersprungene)

# Dump streamen, echte Artikel herausfiltern und als JSONL (docno, title, text) schreiben
with open(OUT, "w", encoding="utf-8") as out:
    for page in mwxml.Dump.from_file(stream):     # streamt durch den Dump
        seen += 1

        # --- alle 50.000 Seiten: Fortschritt melden ---
        if seen % 50000 == 0:
            pct     = raw.count / raw.total * 100
            elapsed = time.time() - t0
            eta     = elapsed / pct * (100 - pct) if pct > 0 else 0
            print(f"{pct:5.1f}% des Dumps | {seen:,} Seiten | {n:,} Artikel | "
                  f"{elapsed/60:.0f} min gelaufen | ~{eta/60:.0f} min uebrig", flush=True)

        if page.namespace != 0 or page.redirect:   # nur echte Artikel
            continue
        text = ""
        for revision in page:                       # aktuelle Revision
            text = revision.text or ""
            break
        plain = mwparserfromhell.parse(text).strip_code()   # Wikitext -> Fliesstext
        if len(plain) < 50:                          # sehr kurze Stubs ueberspringen
            continue
        out.write(json.dumps({"docno": str(page.id), "title": page.title, "text": plain}) + "\n")
        n += 1

# Streams schliessen und Endstatistik ausgeben
stream.close(); raw.close()
print(f"Fertig: {n:,} Artikel aus {seen:,} Seiten -> {OUT}  ({(time.time()-t0)/60:.0f} min)", flush=True)