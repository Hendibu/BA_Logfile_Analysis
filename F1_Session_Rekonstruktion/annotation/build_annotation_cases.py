# build_annotation_cases.py
# -----------------------------------------------------------------------------
# Baut aus deiner manuell gewaehlten Anker-Liste die Annotationsfaelle.
# Pro Anker-Session:
#   1) dominante uid der Anker-Session bestimmen (haeufigste uid ihrer Events),
#   2) drei GEMATCHTE Sessions bilden -- eine je Methode, verbunden ueber die uid:
#        - Anker-Methode: die Anker-Session selbst (deine Handauswahl bleibt erhalten),
#        - andere Methode: die Session, in der diese uid am HAEUFIGSTEN vorkommt,
#        - UUID: alle Events dieser uid (= die UUID-Session).
# Jede der drei Sessions wird mit ALLEN ihren Events gezeigt (auch Events anderer
# uids, falls die Methode sie mit reingruppiert hat) -> ehrliche Kohaerenz-Bewertung.
#
# Eingabe : cascade_full_1234.tsv, dis22_sessions_extended.tsv (ZEILENGLEICH), chosen.txt
# Ausgabe : annotation_cases.json  (BLEIBT LOKAL -- echte Queries, NDA!)
#
# chosen.txt: am einfachsten die "### ..."-Kopfzeilen aus cascade_long.txt /
#   dis22_long.txt hierher kopieren. Alternativ [Kaskade]/[DIS22]-Sektionen mit
#   je einer ID pro Zeile, oder "cascade <id>" / "dis22 <id>" pro Zeile.
# -----------------------------------------------------------------------------
import csv, json, re
from collections import Counter, defaultdict
from datetime import datetime, timezone

CASCADE = "cascade_full_1234.tsv"
DIS22   = "dis22_sessions_extended.tsv"
CHOSEN  = "chosen.txt"
OUT     = "annotation_cases.json"
UUID_WARN = 60            # nur Warnung, falls die UUID-Session sehr gross ist
csv.field_size_limit(2**31 - 1)

def fmt_ts(s):
    return datetime.fromtimestamp(int(s), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

# ---- gemeinsamer, zeilengleicher Reader ueber beide Dateien ------------------
def iter_rows(need_tq=False):
    with open(CASCADE, newline="", encoding="utf-8") as fc, \
         open(DIS22, newline="", encoding="utf-8") as fd:
        rc = csv.reader(fc, delimiter="\t"); rd = csv.reader(fd, delimiter="\t")
        hc = next(rc); hd = next(rd)
        ic_sid, ic_uid = hc.index("session_id"), hc.index("uid")
        ic_ts, ic_q    = hc.index("ts"), hc.index("query")
        id_sid         = hd.index("ext_session_id")
        for a, b in zip(rc, rd):
            if need_tq:
                yield a[ic_uid], a[ic_sid], b[id_sid], int(a[ic_ts]), a[ic_q]
            else:
                yield a[ic_uid], a[ic_sid], b[id_sid]

# ---- chosen.txt einlesen -----------------------------------------------------
def parse_chosen(path):
    chosen = []; section = None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line: continue
            if line.startswith("###"):                 # Kopfzeile aus *_long.txt
                m = "cascade" if "Kaskade" in line else ("dis22" if "DIS22" in line else None)
                mt = re.search(r"-Session\s+(\S+)", line)
                if m and mt: chosen.append((m, mt.group(1)))
                else:        print(f"  ! Kopfzeile nicht erkannt: {line}")
                continue
            if line.startswith("#"): continue           # normaler Kommentar
            if line.startswith("[") and line.endswith("]"):
                s = line[1:-1].lower()
                section = "cascade" if s.startswith(("kask","casc")) else \
                          ("dis22" if s.startswith("dis") else None)
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0].lower() in ("cascade","kaskade","dis22"):
                chosen.append(("cascade" if parts[0].lower() in ("cascade","kaskade") else "dis22", parts[1]))
            elif section: chosen.append((section, parts[0]))
            else:         print(f"  ! Zeile ohne Methode ignoriert: {line}")
    return chosen

chosen = parse_chosen(CHOSEN)
want_c = {sid for m, sid in chosen if m == "cascade"}
want_d = {sid for m, sid in chosen if m == "dis22"}
print(f"Auswahl: {len(want_c)} Kaskade- + {len(want_d)} DIS22-Anker gelesen", flush=True)

# ---- Pass 1: dominante uid je gewaehltem Anker -------------------------------
# (Nur die gewaehlten Sessions werden mitgezaehlt -> sehr wenig Speicher.)
c_uids = defaultdict(Counter); d_uids = defaultdict(Counter)
for uid, csid, dsid in iter_rows():
    if csid in want_c: c_uids[csid][uid] += 1
    if dsid in want_d: d_uids[dsid][uid] += 1
for sid in want_c - set(c_uids): print(f"  ! Kaskade-Anker nicht gefunden: {sid}")
for sid in want_d - set(d_uids): print(f"  ! DIS22-Anker nicht gefunden: {sid}")

anchors = []                                     # (methode, anker_sid, dominante_uid)
for sid, cnt in c_uids.items():
    u = cnt.most_common(1)[0][0]
    if u: anchors.append(("cascade", sid, u))
    else: print(f"  ! Kaskade-Anker {sid} ohne uid -> uebersprungen")
for sid, cnt in d_uids.items():
    u = cnt.most_common(1)[0][0]
    if u: anchors.append(("dis22", sid, u))
    else: print(f"  ! DIS22-Anker {sid} ohne uid -> uebersprungen")

# Hinweis bei gleicher dominanter uid (Faelle wuerden sich stark aehneln) -----
uid_seen = defaultdict(list)
for method, sid, u in anchors: uid_seen[u].append(sid)
for u, sids in uid_seen.items():
    if len(sids) > 1: print(f"  ! Achtung: uid {u} ist dominant in {len(sids)} Ankern: {sids}")

target_uids = {u for _, _, u in anchors}
print(f"{len(anchors)} Anker -> {len(target_uids)} dominante uids", flush=True)

# ---- Pass 2: je Ziel-uid zaehlen, in welchen Sessions sie wie oft vorkommt ---
c_by_uid = defaultdict(Counter); d_by_uid = defaultdict(Counter)
for uid, csid, dsid in iter_rows():
    if uid in target_uids:
        c_by_uid[uid][csid] += 1
        d_by_uid[uid][dsid] += 1

def best_session(cnt_by_sid):
    # haeufigste Session zuerst; Gleichstand -> kleinste ID (deterministisch)
    return sorted(cnt_by_sid.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

# ---- gematchte Session-IDs je Fall festlegen --------------------------------
specs = []                                       # (case_id, methode, uid, v_casc, v_dis)
for method, sid, u in sorted(anchors, key=lambda a: (a[0], a[1])):
    if method == "dis22":
        v_dis  = sid                             # Handauswahl bleibt erhalten
        v_casc = best_session(c_by_uid[u])       # Kaskade-Session mit meister uid
    else:
        v_casc = sid
        v_dis  = best_session(d_by_uid[u])
    specs.append((method, sid, u, v_casc, v_dis))

MC = {s[3] for s in specs}                        # zu sammelnde Kaskade-Sessions
MD = {s[4] for s in specs}                        # zu sammelnde DIS22-Sessions

# ---- Pass 3: alle Member-Events der gematchten Sessions + UUID-Events --------
c_events = defaultdict(list); d_events = defaultdict(list); u_events = defaultdict(list)
for uid, csid, dsid, ts, q in iter_rows(need_tq=True):
    if csid in MC: c_events[csid].append((ts, q, uid))
    if dsid in MD: d_events[dsid].append((ts, q, uid))
    if uid in target_uids: u_events[uid].append((ts, q, uid))

def variant(method, sid, evs):
    evs = sorted(evs, key=lambda x: x[0])
    return {"method": method, "session_id": sid, "n_events": len(evs),
            # uid pro Event nur fuer deinen Review -- die Website blendet sie aus:
            "events": [{"t": fmt_ts(ts), "query": q, "uid": uu} for ts, q, uu in evs]}

cases = []
for cid, (method, sid, u, v_casc, v_dis) in enumerate(specs, start=1):
    uuid_ev = u_events[u]
    if len(uuid_ev) > UUID_WARN:
        print(f"  ! Fall {cid}: UUID-Session (uid {u}) hat {len(uuid_ev)} Events -> sehr gross")
    cases.append({
        "case_id": cid,
        "anchor_method": method,             # nur fuer deinen Review
        "anchor_session_id": sid,            # nur fuer deinen Review
        "uid": u,                            # dominante uid -- NICHT dem Annotator zeigen
        # Reihenfolge hier fix; das Blenden + Shuffeln macht spaeter die Website:
        "variants": [
            variant("cascade", v_casc, c_events[v_casc]),
            variant("dis22",   v_dis,  d_events[v_dis]),
            variant("uuid",    "uuid_" + u, uuid_ev),
        ],
    })

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(cases, f, ensure_ascii=False, indent=1)

print(f"\n{len(cases)} Faelle -> {OUT}", flush=True)
for c in cases:                                   # Kontroll-Uebersicht (Groessen je Variante)
    sz = {v["method"]: v["n_events"] for v in c["variants"]}
    print(f"  Fall {c['case_id']:>2} [{c['anchor_method']:<7}] uid={c['uid']:<12} "
          f"Kaskade {sz['cascade']} / DIS22 {sz['dis22']} / UUID {sz['uuid']} Events")