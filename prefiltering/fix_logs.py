import json
import os
import time

files = [
    "../Datasets/search_logs_fe01_051235/search_log_1.log",
    "../Datasets/search_logs_fe02_051235/search_log_2.log",
    "../Datasets/search_logs_fe03_051235/search_log_3.log",
]

output_file = "../data/log_files.tsv"
bad_lines_file = "../data/bad_lines.log"
fields_cache = "../data/fieldnames.json"

PROGRESS_EVERY = 1_000_000   # alle 1 Mio. Zeilen eine Statusmeldung


def clean_value(v):
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False)
    else:
        v = str(v)
    return v.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def iter_json_lines(files):
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError:
                    obj = None
                yield file, i, stripped, obj


def get_fieldnames(files):
    """Pass 1 (gecacht): alle Spaltennamen sammeln."""
    if os.path.exists(fields_cache):
        with open(fields_cache, encoding="utf-8") as f:
            names = json.load(f)
        print(f"Spalten aus Cache '{fields_cache}' geladen: {names}", flush=True)
        return names

    t0 = time.time()
    fieldnames, seen = [], set()
    total = bad = 0
    for file, i, raw, obj in iter_json_lines(files):
        total += 1
        if obj is None:
            bad += 1
            continue
        for key in obj.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
        if total % 10_000_000 == 0:
            print(f"  Pass 1: {total:,} Zeilen gescannt...", flush=True)

    with open(fields_cache, "w", encoding="utf-8") as f:
        json.dump(fieldnames, f, ensure_ascii=False)
    print(
        f"Pass 1 fertig ({time.time()-t0:.0f}s): {total:,} Zeilen, "
        f"{len(fieldnames)} Spalten, {bad} fehlerhaft. Spalten: {fieldnames}",
        flush=True,
    )
    return fieldnames


def main():
    t0 = time.time()
    fieldnames = get_fieldnames(files)

    tmp_output = output_file + ".part"   # erst am Ende in output_file umbenannt
    good = bad = 0
    with open(tmp_output, "w", encoding="utf-8", newline="", buffering=1024 * 1024) as out_f, \
         open(bad_lines_file, "w", encoding="utf-8") as bad_f:

        out_f.write("\t".join(fieldnames) + "\n")

        for file, i, raw, obj in iter_json_lines(files):
            if obj is None:
                bad += 1
                bad_f.write(f"{file}\t{i}\t{clean_value(raw)[:300]}\n")
                continue
            out_f.write("\t".join(clean_value(obj.get(k)) for k in fieldnames) + "\n")
            good += 1
            if good % PROGRESS_EVERY == 0:
                out_f.flush()
                print(f"  Pass 2: {good:,} Zeilen geschrieben ({time.time()-t0:.0f}s)...", flush=True)

    os.replace(tmp_output, output_file)
    print(f"Fertig ({time.time()-t0:.0f}s): Geladene Zeilen {good:,}, Fehlerhafte {bad}.", flush=True)
    print(f"Ausgabe: {output_file}  |  Fehlerhafte Zeilen: {bad_lines_file}", flush=True)


if __name__ == "__main__":
    main()