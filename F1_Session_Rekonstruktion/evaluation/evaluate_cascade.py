# ============================================================================
# evaluate_cascade.py  -- Auswertung der fertigen Kaskaden-Ausgabe
# Rechnet aus cascade_full_1234.tsv alle Kennzahlen fuer die Arbeit:
#   * Beitrag jeder Stufe (wie viele Fortsetzungen/Grenzen)
#   * Anzahl Sessions, Session-Laengen- und -Dauer-Verteilung
#   * ESA-Cosinus-Verteilung (zum spaeteren Nachjustieren von ESA_TH)
# Speicherkonstant: Sessions liegen in der Ausgabe zusammenhaengend vor.
# ============================================================================
import csv, numpy as np

INP = "cascade_full_1234.tsv"; REPORT = "cascade_eval.txt"
csv.field_size_limit(2**31 - 1)

cnt = {"start":0,"gap":0,"s1":0,"s2":0,"s3":0,"s4":0,"boundary":0}
sess_len = []; sess_dur = []; esa_vals = []
cur_id = None; cur_n = 0; cur_min = None; cur_max = None; rows = 0

def close_session():
    if cur_id is not None:
        sess_len.append(cur_n)
        sess_dur.append((cur_max - cur_min) / 60.0)   # Minuten

with open(INP, newline="", encoding="utf-8") as f:
    r = csv.reader(f, delimiter="\t"); h = next(r)
    i_sid, i_ts, i_ec, i_st = (h.index("session_id"), h.index("ts"),
                               h.index("esa_cos"), h.index("stage"))
    for row in r:
        rows += 1
        cnt[row[i_st]] = cnt.get(row[i_st], 0) + 1
        if row[i_ec]:
            esa_vals.append(float(row[i_ec]))
        sid = row[i_sid]; ts = int(row[i_ts])
        if sid != cur_id:                      # neue Session beginnt
            close_session()
            cur_id = sid; cur_n = 0; cur_min = ts; cur_max = ts
        cur_n += 1; cur_min = min(cur_min, ts); cur_max = max(cur_max, ts)
    close_session()

pairs   = rows - cnt["start"]
cont    = cnt["s1"] + cnt["s2"] + cnt["s3"] + cnt["s4"]
bound   = cnt["gap"] + cnt["boundary"]
n_sess  = len(sess_len)
L = np.array(sess_len); D = np.array(sess_dur); E = np.array(esa_vals)

def pct(x, base): return f"{x:,} ({100*x/base:.1f}%)" if base else f"{x:,}"

lines = []
lines.append("=== KASKADE — AUSWERTUNG ===")
lines.append(f"Zeilen (Queries):        {rows:,}")
lines.append(f"Aufeinanderfolg. Paare:  {pairs:,}")
lines.append(f"Sessions:                {n_sess:,}")
lines.append("")
lines.append("--- Entscheidungen pro Paar ---")
lines.append(f"Fortsetzungen gesamt:    {pct(cont, pairs)}")
lines.append(f"  Stufe 1 (lexikalisch): {pct(cnt['s1'], pairs)}")
lines.append(f"  Stufe 2 (Zeichen-Cos): {pct(cnt['s2'], pairs)}")
lines.append(f"  Stufe 3 (ESA):         {pct(cnt['s3'], pairs)}")
lines.append(f"  Stufe 4 (SERP):        {pct(cnt['s4'], pairs)}")
lines.append(f"Grenzen gesamt:          {pct(bound, pairs)}")
lines.append(f"  davon Zeit (>90 Min):  {pct(cnt['gap'], pairs)}")
lines.append(f"  davon inhaltlich:      {pct(cnt['boundary'], pairs)}")
lines.append("")
lines.append("--- Session-Laenge (Queries/Session) ---")
lines.append(f"Mittel {L.mean():.2f} | Median {int(np.median(L))} | "
             f"Min {L.min()} | Max {L.max()}")
for lo, hi, name in [(1,1,"1 (Singletons)"),(2,5,"2-5"),(6,10,"6-10"),
                     (11,50,"11-50"),(51,10**9,">50")]:
    c = int(((L >= lo) & (L <= hi)).sum())
    lines.append(f"  {name:14}: {pct(c, n_sess)}")
lines.append("")
lines.append("--- Session-Dauer (Minuten) ---")
lines.append(f"Mittel {D.mean():.1f} | Median {np.median(D):.1f} | Max {D.max():.1f}")
lines.append("")
lines.append("--- ESA-Cosinus (nur Paare, die Stufe 3 erreichten) ---")
if E.size:
    qs = np.percentile(E, [50,75,90,95,99])
    lines.append(f"Anzahl {E.size:,} | Mittel {E.mean():.4f} | "
                 f"Median {qs[0]:.4f} | 90% {qs[2]:.4f} | 95% {qs[3]:.4f} | 99% {qs[4]:.4f} | Max {E.max():.4f}")
    lines.append("Wieviele Paare hielte welcher Schwellwert fuer 'gleiche Session':")
    for th in (0.02, 0.05, 0.10, 0.15, 0.20):
        lines.append(f"  ESA_TH={th:.2f}: {pct(int((E >= th).sum()), E.size)}")
else:
    lines.append("keine ESA-Werte vorhanden.")

report = "\n".join(lines)
print(report)
with open(REPORT, "w", encoding="utf-8") as f:
    f.write(report + "\n")
print(f"\n-> gespeichert in {REPORT}")