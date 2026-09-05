# reformulation.py -- Klassifikation von Query-Reformulierungen (Huang & Efthimiadis 2009).
# 13 Strategien in fester Prioritaetsreihenfolge; zusaetzlich "Identical" und "New".
# Stemming/Word-Substitution brauchen nltk+WordNet (optional):
#   pip install nltk --break-system-packages
#   python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
import re
from collections import Counter

try:
    from nltk.stem import PorterStemmer
    _stem = PorterStemmer().stem
    _HAS_STEM = True
except Exception:
    _HAS_STEM = False
    def _stem(w): return w
try:
    from nltk.corpus import wordnet as _wn
    _wn.synsets("test")
    _HAS_WN = True
except Exception:
    _HAS_WN = False

def _norm(q):   return q.strip().lower()
def _tokens(q): return _norm(q).split()
def _strip_ws_punct(q): return re.sub(r"[\s'\-.]", "", _norm(q))
def _levenshtein(a, b):
    if a == b: return 0
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0]*len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            cur[j] = min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + cost)
        prev = cur
    return prev[len(b)]
def _related_wn(w1, w2):
    if w1 == w2: return True
    if not _HAS_WN: return False
    s1 = _wn.synsets(w1); s2 = set(_wn.synsets(w2))
    if not s1 or not s2: return False
    for s in s1:
        rel = set(s.hypernyms() + s.hyponyms()
                  + s.part_meronyms() + s.substance_meronyms() + s.member_meronyms()
                  + s.part_holonyms() + s.substance_holonyms() + s.member_holonyms())
        rel.add(s)
        if s2 & rel: return True
    return False
def _submultiset(small, big):
    cs, cb = Counter(small), Counter(big)
    return all(cs[w] <= cb[w] for w in cs)

def r01_reorder(t1, t2, q1, q2):  return t1 != t2 and sorted(t1) == sorted(t2)
def r02_wspunct(t1, t2, q1, q2):  return q1 != q2 and _strip_ws_punct(q1) == _strip_ws_punct(q2)
def r03_remove(t1, t2, q1, q2):   return len(t2) < len(t1) and _submultiset(t2, t1)
def r04_add(t1, t2, q1, q2):      return len(t2) > len(t1) and _submultiset(t1, t2)
def r05_url(t1, t2, q1, q2):
    def s(x):
        x = _norm(x)
        for p in (".com", "www.", "http_", "http://", "https://"): x = x.replace(p, "")
        return x.strip()
    return q1 != q2 and s(q1) == s(q2)
def r06_stem(t1, t2, q1, q2):
    if not _HAS_STEM or len(t1) != len(t2): return False
    return t1 != t2 and [_stem(w) for w in t1] == [_stem(w) for w in t2]
def r07_form_acr(t1, t2, q1, q2):
    return len(t2) == 1 and len(t1) >= 2 and t2[0] == "".join(w[0] for w in t1 if w)
def r08_exp_acr(t1, t2, q1, q2):  return r07_form_acr(t2, t1, q2, q1)
def r09_substr(t1, t2, q1, q2):
    a, b = _norm(q1), _norm(q2);  return b != a and (a.startswith(b) or a.endswith(b))
def r10_superstr(t1, t2, q1, q2):
    a, b = _norm(q1), _norm(q2);  return b != a and (b.startswith(a) or b.endswith(a))
def r11_abbrev(t1, t2, q1, q2):
    if len(t1) != len(t2) or t1 == t2: return False
    return all(w1.startswith(w2) or w2.startswith(w1) for w1, w2 in zip(t1, t2))
def r12_subst(t1, t2, q1, q2):
    if not _HAS_WN or len(t1) != len(t2) or t1 == t2: return False
    return all(_related_wn(w1, w2) for w1, w2 in zip(t1, t2))
def r13_spell(t1, t2, q1, q2):
    a, b = _norm(q1), _norm(q2);  return a != b and _levenshtein(a, b) <= 2

_RULES = [
    ("Word Reorder", r01_reorder), ("Whitespace/Punctuation", r02_wspunct),
    ("Remove Words", r03_remove),  ("Add Words", r04_add),
    ("URL Stripping", r05_url),    ("Stemming", r06_stem),
    ("Form Acronym", r07_form_acr),("Expand Acronym", r08_exp_acr),
    ("Substring", r09_substr),     ("Superstring", r10_superstr),
    ("Abbreviation", r11_abbrev),  ("Word Substitution", r12_subst),
    ("Spelling Correction", r13_spell),
]

def classify(q_prev, q_curr):
    if _norm(q_prev) == _norm(q_curr): return "Identical"
    t1, t2 = _tokens(q_prev), _tokens(q_curr)
    if not t1 or not t2: return "New"
    for name, fn in _RULES:
        try:
            if fn(t1, t2, q_prev, q_curr): return name
        except Exception:
            continue
    return "New"

if __name__ == "__main__":
    print(f"Stemming aktiv: {_HAS_STEM} | WordNet aktiv: {_HAS_WN}")
    for q1, q2 in [("machine learning","machine learning"),("new york city","new york"),
                   ("recieve","receive"),("banana bread","quantum physics")]:
        print(f"  {q1!r} -> {q2!r}: {classify(q1,q2)}")