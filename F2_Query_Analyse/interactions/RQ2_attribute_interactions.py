# attribute_interactions.py <session_file>
# RQ2 (4.6): fuer EINE Session-Datei zwei Tabellen (plausibel gelesen / zu kurz).
import csv, sys, re                          # re NEU: fuer den Struktur-Filter
from collections import Counter, defaultdict
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "reformulation"))
from RQ2_reformulation import classify
csv.field_size_limit(2**31 - 1)

SESSION_FILE = sys.argv[1] if len(sys.argv) > 1 else "../../data/cascade_full_1234_nostruct.tsv"
DWELL = "../../data/RQ2_interactions_dwell.tsv"

# get-pdf entfernt: Downloads haben keine uid -> strukturell 0,00 %, siehe Befund.
TYPES = ["author", "works", "data-provider"]
TBIT  = {t: i for i, t in enumerate(TYPES)}

# STRUCT NEU: erkennt strukturierte/Bot-Anfragen (Jahr-Sweeps, Range-Filter,
# boolesche Operatoren). Solche Paare sind keine menschlichen Reformulierungen
# und werden aus der Auswertung ausgeschlossen -- identisch zum Filter in
# reformulation_examples.py, damit 6.3 und 6.4 auf DERSELBEN Basis stehen.
STRUCT = re.compile(r'year\s*:|yearpublished|(<=|>=|<|>)\s*\d|\bAND\s*\(|\bOR\s*\(',
                    re.IGNORECASE)

ORDER = ["Identical","Word Reorder","Whitespace/Punctuation","Remove Words","Add Words",
         "URL Stripping","Stemming","Form Acronym","Expand Acronym","Substring","Superstring",
         "Abbreviation","Word Substitution","Spelling Correction","New"]

def strip_nul(fo):
    for line in fo: yield line.replace("\x00", "")

def target_sids(path):
    s = set()
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r); i = h.index("search_id")
        for row in r:
            if row[i]: s.add(row[i])
    return s

def load_masks(target, path=DWELL):
    pl = {}; sh = {}
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
        imk, ity, ipl = h.index("merge_key"), h.index("type"), h.index("plausible")
        for row in r:
            mk = row[imk]
            if mk in target and row[ity] in TBIT:
                bit = 1 << TBIT[row[ity]]
                if row[ipl] == "1": pl[mk] = pl.get(mk, 0) | bit
                else:               sh[mk] = sh.get(mk, 0) | bit
    return pl, sh

def analyze(path, pl, sh):
    tot = Counter()
    hp = defaultdict(lambda: [0]*(len(TYPES)+1)); hs = defaultdict(lambda: [0]*(len(TYPES)+1))
    pairs = 0; skipped = 0                    # skipped NEU: ausgeschlossene Struktur-Paare
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
        sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
        i_sid, i_q, i_s = h.index(sidcol), h.index("query"), h.index("search_id")
        cur = None; prev = None
        for row in r:
            sid = row[i_sid]
            if not sid: cur = None; prev = None; continue
            if sid != cur: cur = sid; prev = row[i_q]; continue
            # NEU: strukturierte/Bot-Paare ueberspringen (aber prev fortschreiben)
            if STRUCT.search(prev) or STRUCT.search(row[i_q]):
                skipped += 1; prev = row[i_q]; continue
            lbl = classify(prev, row[i_q]); tot[lbl] += 1; pairs += 1
            mp = pl.get(row[i_s], 0); ms = sh.get(row[i_s], 0); a = hp[lbl]; b = hs[lbl]
            for i in range(len(TYPES)):
                if mp >> i & 1: a[i] += 1
                if ms >> i & 1: b[i] += 1
            if mp: a[-1] += 1
            if ms: b[-1] += 1
            prev = row[i_q]
    return tot, hp, hs, pairs, sidcol, skipped

def table(title, tot, hh):
    cols = TYPES + ["Irgendeine"]
    print(f"\n  [{title}]")
    print("  " + f"{'Strategie':22}" + f"{'Paare':>9}" + "".join(f"{c[:13]:>14}" for c in cols))
    for s in ORDER:
        if tot[s] == 0: continue
        h = hh.get(s, [0]*len(cols))
        print("  " + f"{s:22}{tot[s]:>9,}" + "".join(f"{100*h[i]/tot[s]:>13.2f}%" for i in range(len(cols))))

if __name__ == "__main__":
    target = target_sids(SESSION_FILE)
    pl, sh = load_masks(target)
    tot, hp, hs, pairs, sidcol, skipped = analyze(SESSION_FILE, pl, sh)
    print(f"=== {SESSION_FILE} (Spalte '{sidcol}'): {pairs:,} Reformulierungs-Paare "
          f"| ausgeschlossene strukturierte Paare: {skipped:,} ===")
    table("Plausibel gelesen (Verweildauer >= Schwelle)", tot, hp)
    table("Zu kurz (< Schwelle -> vorsichtig werten)", tot, hs)







# # attribute_interactions.py <session_file>
# # RQ2 (4.6): fuer EINE Session-Datei zwei Tabellen (plausibel gelesen / zu kurz).
# import csv, sys
# from collections import Counter, defaultdict
# from RQ2_reformulation import classify
# csv.field_size_limit(2**31 - 1)

# SESSION_FILE = sys.argv[1] if len(sys.argv) > 1 else "cascade_full_1234_nostruct.tsv"
# DWELL = "RQ2_interactions_dwell.tsv"
# TYPES = ["get-pdf", "author", "works", "data-provider"]
# TBIT  = {t: i for i, t in enumerate(TYPES)}
# ORDER = ["Identical","Word Reorder","Whitespace/Punctuation","Remove Words","Add Words",
#          "URL Stripping","Stemming","Form Acronym","Expand Acronym","Substring","Superstring",
#          "Abbreviation","Word Substitution","Spelling Correction","New"]

# def strip_nul(fo):
#     for line in fo: yield line.replace("\x00", "")

# def target_sids(path):
#     s = set()
#     with open(path, newline="", encoding="utf-8") as f:
#         r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r); i = h.index("search_id")
#         for row in r:
#             if row[i]: s.add(row[i])
#     return s

# def load_masks(target, path=DWELL):
#     pl = {}; sh = {}
#     with open(path, newline="", encoding="utf-8") as f:
#         r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
#         imk, ity, ipl = h.index("merge_key"), h.index("type"), h.index("plausible")
#         for row in r:
#             mk = row[imk]
#             if mk in target and row[ity] in TBIT:
#                 bit = 1 << TBIT[row[ity]]
#                 if row[ipl] == "1": pl[mk] = pl.get(mk, 0) | bit
#                 else:               sh[mk] = sh.get(mk, 0) | bit
#     return pl, sh

# def analyze(path, pl, sh):
#     tot = Counter()
#     hp = defaultdict(lambda: [0]*(len(TYPES)+1)); hs = defaultdict(lambda: [0]*(len(TYPES)+1)); pairs = 0
#     with open(path, newline="", encoding="utf-8") as f:
#         r = csv.reader(strip_nul(f), delimiter="\t"); h = next(r)
#         sidcol = "ext_session_id" if "ext_session_id" in h else "session_id"
#         i_sid, i_q, i_s = h.index(sidcol), h.index("query"), h.index("search_id")
#         cur = None; prev = None
#         for row in r:
#             sid = row[i_sid]
#             if not sid: cur = None; prev = None; continue
#             if sid != cur: cur = sid; prev = row[i_q]; continue
#             lbl = classify(prev, row[i_q]); tot[lbl] += 1; pairs += 1
#             mp = pl.get(row[i_s], 0); ms = sh.get(row[i_s], 0); a = hp[lbl]; b = hs[lbl]
#             for i in range(len(TYPES)):
#                 if mp >> i & 1: a[i] += 1
#                 if ms >> i & 1: b[i] += 1
#             if mp: a[-1] += 1
#             if ms: b[-1] += 1
#             prev = row[i_q]
#     return tot, hp, hs, pairs, sidcol

# def table(title, tot, hh):
#     cols = TYPES + ["Irgendeine"]
#     print(f"\n  [{title}]")
#     print("  " + f"{'Strategie':22}" + f"{'Paare':>9}" + "".join(f"{c[:13]:>14}" for c in cols))
#     for s in ORDER:
#         if tot[s] == 0: continue
#         h = hh.get(s, [0]*len(cols))
#         print("  " + f"{s:22}{tot[s]:>9,}" + "".join(f"{100*h[i]/tot[s]:>13.2f}%" for i in range(len(cols))))

# if __name__ == "__main__":
#     target = target_sids(SESSION_FILE)
#     pl, sh = load_masks(target)
#     tot, hp, hs, pairs, sidcol = analyze(SESSION_FILE, pl, sh)
#     print(f"=== {SESSION_FILE} (Spalte '{sidcol}'): {pairs:,} Reformulierungs-Paare ===")
#     table("Plausibel gelesen (Verweildauer >= Schwelle)", tot, hp)
#     table("Zu kurz (< Schwelle -> vorsichtig werten)", tot, hs)