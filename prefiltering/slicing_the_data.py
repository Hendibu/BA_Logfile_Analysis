from datetime import datetime, timezone

def ts(dt_str):
    return int(datetime.strptime(dt_str, "%d.%m.%Y %H:%M:%S")
               .replace(tzinfo=timezone.utc)
               .timestamp())

RANGES = {
    "../data/data_2025_03_05.log": (ts("01.03.2025 00:00:00"), ts("01.06.2025 00:00:00")),
    "../data/data_2025_06_08.log": (ts("01.06.2025 00:00:00"), ts("01.09.2025 00:00:00")),
    "../data/data_2025_09_11.log": (ts("01.09.2025 00:00:00"), ts("01.12.2025 00:00:00")),
}


import json

INPUT_FILE = "../data/search_log.log"

files = {name: open(name, "w", encoding="utf-8") for name in RANGES}

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line_number, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue

        try:
            record = json.loads(line)
            ts_value = int(record["date"])
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Skip (Row {line_number}): {e}")
            continue

        for filename, (start, end) in RANGES.items():
            if start <= ts_value < end:
                files[filename].write(line + "\n")
                break

for f in files.values():
    f.close()
