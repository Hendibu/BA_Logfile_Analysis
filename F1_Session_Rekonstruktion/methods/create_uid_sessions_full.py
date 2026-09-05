import polars as pl
import csv
from datetime import datetime, timezone

CLEAN             = "log_files_cleaned.tsv"
SORTED            = "cleaned_sorted.tsv"
SESSIONS_PER_FILE = 5000
OUT_PREFIX        = "uuid_sessions_part_"

# --- Phase 1: nach uid/Zeit sortieren (streamend auf die Platte) ---
print("Phase 1: sortiere nach uid/Zeit ...", flush=True)
(pl.scan_csv(CLEAN, separator="\t")
   .filter(pl.col("uid").is_not_null() & (pl.col("uid") != ""))
   .with_columns(pl.col("date").cast(pl.Int64, strict=False).alias("ts"))
   .filter(pl.col("ts").is_not_null())
   .select(["uid", "ts", "query"])
   .sort(["uid", "ts"])
   .sink_csv(SORTED, separator="\t"))
print("   ->", SORTED, flush=True)

# --- Phase 2: sortierte Datei streamend in lesbare Split-Dateien schreiben ---
print("Phase 2: schreibe lesbare Sessions ...", flush=True)
csv.field_size_limit(2**31 - 1)
def fmt_ts(s):
    return datetime.fromtimestamp(int(s), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

sess_count = in_file = file_idx = 0
cur_uid = None; prev_ts = None; fout = None

with open(SORTED, newline="", encoding="utf-8") as fin:
    reader = csv.reader(fin, delimiter="\t")
    header = next(reader)
    iu, it, iq = header.index("uid"), header.index("ts"), header.index("query")
    for row in reader:
        uid, ts, query = row[iu], int(row[it]), row[iq]
        if uid != cur_uid:                       # neue Session (uid wechselt)
            if fout is None or in_file >= SESSIONS_PER_FILE:
                if fout: fout.close()
                file_idx += 1
                fout = open(f"{OUT_PREFIX}{file_idx:03d}.txt", "w", encoding="utf-8")
                in_file = 0
            else:
                fout.write("\n\n")               # Abgrenzung zur vorigen Session
            sess_count += 1; in_file += 1
            cur_uid = uid; prev_ts = None
            fout.write("=" * 90 + "\n")
            fout.write(f"SESSION {sess_count}  (uid = {uid})\n")
            fout.write("=" * 90 + "\n")
        luecke = "" if prev_ts is None else f"(+{round((ts - prev_ts)/60)} min)"
        fout.write(f"  {fmt_ts(ts)}  {luecke:>16}   {query}\n")
        prev_ts = ts
if fout: fout.close()
print(f"Fertig: {sess_count} Sessions in {file_idx} Dateien ({OUT_PREFIX}NNN.txt)", flush=True)