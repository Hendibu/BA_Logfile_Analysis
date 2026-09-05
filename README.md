# Bachelorarbeit – Analyseskripte

Dieses Repository enthält die Python-Skripte der Analyse-Pipeline für die Bachelorarbeit.
Es umfasst **ausschließlich Code** – keine Rohdaten, keine rekonstruierten Sitzungen,
keine Annotations-/Precision-Dateien und keinen Wikipedia-Suchindex.

## Datenschutz-Hinweis

Die zugrunde liegenden Suchmaschinen-Logfiles enthalten reale, teils personenbeziehbare
Suchanfragen von Nutzer:innen. Aus Datenschutz- und NDA-Gründen ist die Datenbasis
**nicht** Teil dieses Repositories – weder als Rohdaten noch als daraus abgeleitete
Zwischenergebnisse (Sessions, Interaktionslisten, Annotationen, Stichproben, Indizes).
Alle hier enthaltenen Skripte gehen von lokal vorliegenden, nicht versionierten
Eingabedateien aus (siehe `.gitignore`).

## Pipeline-Übersicht

Die Pipeline gliedert sich in eine gemeinsame Vorverarbeitung sowie zwei
Forschungsfrage-Stränge (F1, F2).

### `prefiltering/` – Vorverarbeitung der Logfiles

Reinigung und Aufbereitung der rohen Suchlogs, bevor Sessions gebildet oder
Anfragen analysiert werden.

- Top-Level: `cleaning_logs.py`, `slicing_the_data.py`, `fix_logs.py`, `clean_all.py`, `clean_pipe.py`
- `functions/` – gemeinsame Hilfsfunktionen (`clean_data.py`, `create_features.py`)
- `bot_filter/` – Erkennung und Ausschluss von Bot-/Struktur-Traffic
  (`drop_bursts.py`, `filter_bot_sessions.py`, `filter_struct_sessions.py`,
  `analyze_bot_uids.py`, `bot_uid_recurrence.py`, `check_bot_samples.py`)
- `data_checks/` – Konsistenz- und Sanity-Checks auf den Logdaten
  (`date_range.py`, `count_types.py`, `check_query_events.py`,
  `check_timestamps.py`, `col_check.py`)

### `F1_Session_Rekonstruktion/` – Forschungsfrage F1

Rekonstruktion von Nutzersitzungen aus den Logs sowie deren Bewertung.

- `methods/` – verschiedene Session-Rekonstruktionsverfahren
  (`make_uid_day.py`, `cascade_sessions.py`, `dis22_session.py`,
  `dis22_session_extension.py`, `dis22_sort.py`, `uuid_sessions.py`,
  `uid_day_sessions.py`, `create_uid_sessions_full.py`, `create_uid_session_summary.py`)
- `esa_index/` – Aufbau eines Wikipedia-basierten Ähnlichkeitsindex (Explicit
  Semantic Analysis) als Hilfsmittel für die Session-Grenzenbestimmung
  (`wikipedia_extraction.py`, `wikipedia_indexing.py`, `wikipedia_indexing_full.py`,
  `wikipedia_esa_test.py`, `inspect_esa_pairs.py`)
- `evaluation/` – Vergleich und Bewertung der Rekonstruktionsverfahren
  (`evaluate_cascade.py`, `compare_methods.py`, `compare_sessions.py`,
  `compare_split.py`, `stage_vs_dis22.py`)
- `annotation/` – Aufbereitung von Fällen für manuelle Annotation
  (`build_annotation_cases.py`, `match_annotation.py`)
- `analysis/` – deskriptive Auswertung der rekonstruierten Sessions
  (`count_sessions.py`, `check_pairs.py`, `list_uid_days.py`, `list_long_sessions.py`)

### `F2_Query_Analyse/` – Forschungsfrage F2

Analyse des Suchverhaltens innerhalb der rekonstruierten Sessions.

- `reformulation/` – Klassifikation und Analyse von Anfrage-Umformulierungen
  (`RQ2_reformulation.py`, `RQ2_classify_reformulations.py`,
  `RQ2_reformulation_examples.py`, `RQ2_transition_matrix.py`)
- `interactions/` – Nutzerinteraktionen mit Suchergebnissen
  (`RQ2_extract_interactions.py`, `RQ2_attribute_interactions.py`,
  `RQ2_interaction_dwell.py`, `check_interaction_match.py`)
  - `getpdf/` – Spezialfall PDF-Downloads
    (`check_getpdf_count.py`, `check_getpdf_in_log.py`,
    `check_getpdf_uid.py`, `trace_getpdf_stage.py`)
- `known_item/` – Erkennung von Known-Item-Suchen
  (`build_title_index.py`, `RQ2_classify_known_item.py`,
  `classify_known_item_priority.py`, `RQ2_title_position.py`)
- `precision/` – Precision-Bewertung der Suchergebnisse
  (`RQ2_sample_precision.py`, `RQ2_eval_precision.py`)

### `legacy/`

Ältere, nicht mehr aktiv genutzte Skriptversionen – nur zur Nachvollziehbarkeit
der Methodenentwicklung enthalten (`kaskade_sessions_old.py`).

## Setup

```bash
pip install -r requirements.txt
```

Für `nltk` können je nach Skript zusätzliche Ressourcen-Downloads
(`nltk.download(...)`) erforderlich sein. `python-terrier` benötigt eine
lokale Java-Installation (JDK).
