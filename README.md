# Bachelorarbeit: Rekonstruktion von Suchsessions und Analysen von Query-Reformulierungsstrategien in CORE-Logfiles

## Informationen

* Erstgutachter: Prof. Dr. Philipp Schaer
* Zweitgutachter: M.Sc. Andreas Kruff
* Studierender: Hendrik Buschke

Schlagwörter: Sessionrekonstruktion, Query-Reformulierung, Logfile-Analyse

## Überblick

Die Analyse ist entlang der beiden Forschungsfragen aufgebaut (F1 = Sessionrekonstruktion, F2 = Query-Analyse). Das Repository enthält die folgenden Ordner:

* **prefiltering**: Code zum Aufbau und zur Bereinigung des Rohlogs (Zusammenführen der Logdateien, Bereinigung, ereignis- und sessionbezogene Bot-Filter) sowie grundlegende Datenqualitäts-Prüfungen.
* **F1_session_rekonstruktion**: Code für die Rekonstruktionsmethoden (adaptierte Kaskade, DIS22, uid/uid-Tag), den Wikipedia-/ESA-Index für die semantische Stufe der Kaskade sowie Methodenvergleich, manuelle Annotation und Session-Kennzahlen.
* **F2_query_analyse**: Code für die Query-Analyse — Reformulierungsstrategien (Taxonomie nach Huang & Efthimiadis, Übergangsmatrix), Interaktionen (Attribute, Verweildauer), Known-Item-Klassifikation und die Precision-Prüfung des Klassifikators.
* **data**: Arbeitsverzeichnis für Eingabe- und Zwischendateien. Nicht im Repository enthalten (siehe Datenverfügbarkeit).

## Datenverfügbarkeit

Die zugrunde liegenden Suchlogs sind aus Datenschutzgründen (NDA) **nicht im Repository enthalten**. Die Skripte erwarten die entsprechenden Dateien im Ordner `data/`; die Pfade lassen sich am Anfang jedes Skripts anpassen.

* Suchlogs (CORE): Werden hier nicht weitergegeben.
* Dokumentkorpus (Titel / Known-Item): die öffentliche LongEval-CORE-Dokumentkollektion.
* Semantischer Index (Kaskaden-Stufe s3): aufgebaut aus dem öffentlichen Simple-English-Wikipedia-Dump (`simplewiki-latest-pages-articles.xml.bz2`).

## Voraussetzungen

* Python 3.10+
* Pakete: `pandas`, `polars`, `numpy`, `scikit-learn`, `nltk` (mit WordNet), `python-terrier`, `mwxml`, `mwparserfromhell`
* Für PyTerrier (Kaskaden-Stufe s3) wird ein JDK benötigt; `JAVA_HOME` entsprechend setzen.

## Reproduktion (Pipeline-Reihenfolge)

1. **prefiltering**: Rohlogs zusammenführen → bereinigen → sortieren → ereignisbezogener Burst-Filter → uid|Tag-Eingabe für die Rekonstruktion bauen.
2. **F1**: Wikipedia-/ESA-Index erstellen, Rekonstruktionsmethoden ausführen (Kaskade, DIS22, uid), sessionbezogene Bot-/Struktur-Filter anwenden, danach Methodenvergleich und manuelle Annotation.
3. **F2**: Reformulierungen und deren Übergänge klassifizieren, Interaktionen und Verweildauer berechnen, Known-Item-Klassifikation durchführen; den Reformulierungs-Klassifikator über die Precision-Stichprobe prüfen.

## Hinweise

* Die semantische Stufe der Kaskade (s3) nutzt einen ESA-artigen Index, der mit PyTerrier über Simple English Wikipedia aufgebaut wird; der Indexaufbau ist ein separater, einmaliger Schritt.
* Nur zur Exploration genutzte Jupyter-Notebooks sind nicht Teil des Repositorys.
