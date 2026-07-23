#!/usr/bin/env python3
"""Wandelt eine gespeicherte morningstar-data-tool Antwort (rich JSON) in das
kompakte Rohformat {fid: {datapointId: value}} um und legt sie unter
data/raw2/metrics/ ab. Wird sowohl beim Erstaufbau als auch beim monatlichen
Update verwendet (spart Tokens: Daten laufen per Skript, nicht per Abtippen).

Aufruf:  python3 parse_tool_result2.py <tool_result_datei> <ausgabe.json>
"""
import json, sys

def main(src, dst):
    d = json.load(open(src, encoding="utf-8"))
    res = d.get("result", d) if isinstance(d, dict) else {}
    compact = {}
    for fid, body in res.items():
        if not isinstance(body, dict):
            continue
        vals = {}
        for it in body.get("values", []) or []:
            dp = it.get("datapointId"); v = it.get("value")
            if dp is not None and v is not None and v != "":
                vals[dp] = v
        if vals:
            compact[fid] = vals
    json.dump(compact, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(compact)} Wertpapiere -> {dst}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
