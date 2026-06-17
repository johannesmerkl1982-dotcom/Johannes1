#!/usr/bin/env python3
"""Wandelt eine gespeicherte morningstar-data-tool Antwort in das kompakte
Rohformat {fid: {datapointId: value}} um und legt sie unter data/raw3/metrics/
ab. Behandelt sowohl direkte `value`-Felder als auch `timeSeriesData`
(z. B. Sterne-Rating). Bei Zeitreihen wird – falls vorhanden – der Eintrag zum
gewünschten Stichtag genommen, sonst der letzte verfügbare Wert.

Aufruf:  python3 parse_tool_result3.py <tool_result_datei> <ausgabe.json> [YYYY-MM-DD]
"""
import json, sys


def _pick(it, stichtag):
    v = it.get("value")
    if v not in (None, ""):
        return v
    ts = it.get("timeSeriesData") or []
    if not ts:
        return None
    if stichtag:
        for e in ts:
            if e.get("date") == stichtag and e.get("value") not in (None, ""):
                return e.get("value")
    for e in reversed(ts):
        if e.get("value") not in (None, ""):
            return e.get("value")
    return None


def main(src, dst, stichtag=None):
    d = json.load(open(src, encoding="utf-8"))
    res = d.get("result", d) if isinstance(d, dict) else {}
    compact = {}
    for fid, body in res.items():
        if not isinstance(body, dict):
            continue
        vals = {}
        for it in body.get("values", []) or []:
            dp = it.get("datapointId")
            v = _pick(it, stichtag)
            if dp is not None and v not in (None, ""):
                vals[dp] = v
        if vals:
            compact[fid] = vals
    json.dump(compact, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(compact)} Wertpapiere -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
