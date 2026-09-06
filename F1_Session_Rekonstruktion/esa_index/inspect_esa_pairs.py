# inspect_esa_pairs.py -- zeigt echte Query-Paare je ESA-Cosinus-Band,
# damit du ESA_TH datenbasiert festlegen kannst (laeuft lokal, NDA-sicher).
import csv, random
random.seed(42)
INP = "../../data/cascade_full_1234.tsv"
N_PER_BAND = 15
BANDS = [(0.005,0.02),(0.02,0.05),(0.05,0.10),(0.10,0.20),(0.20,0.50),(0.50,1.01)]
csv.field_size_limit(2**31 - 1)

samples = {b: [] for b in BANDS}
seen    = {b: 0  for b in BANDS}

with open(INP, newline="", encoding="utf-8") as f:
    r = csv.reader(f, delimiter="\t"); h = next(r)
    i_q, i_ec = h.index("query"), h.index("esa_cos")
    prev_q = None
    for row in r:
        ec = row[i_ec]
        if ec and prev_q is not None:            # nur Paare, die Stufe 3 erreichten
            c = float(ec)
            for lo, hi in BANDS:
                if lo <= c < hi:
                    b = (lo, hi); seen[b] += 1
                    if len(samples[b]) < N_PER_BAND:
                        samples[b].append((c, prev_q, row[i_q]))
                    else:                         # Reservoir-Sampling je Band
                        j = random.randint(0, seen[b]-1)
                        if j < N_PER_BAND: samples[b][j] = (c, prev_q, row[i_q])
                    break
        prev_q = row[i_q]

for b in BANDS:
    print(f"\n=== ESA-Cosinus {b[0]:.3f}-{b[1]:.2f}  (insgesamt {seen[b]:,} Paare) ===")
    for c, pq, q in sorted(samples[b], reverse=True):
        print(f"  {c:.4f}   {pq!r}  ->  {q!r}")