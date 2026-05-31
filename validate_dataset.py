#!/usr/bin/env python3
"""Integritäts- und Plausibilitätsprüfungen für data/funds.json.

Ausführen:  python3 validate_dataset.py
Exit-Code 0 = alle Prüfungen bestanden, sonst 1.
"""
from __future__ import annotations

import json
import sys

import fund_metrics as fm

ALLOWED_KEYS = {
    f"{m}_{p}" for m, (_, periods, _) in fm.METRICS.items() for p in periods
}


def main() -> int:
    data = fm.load_data()
    funds = data["funds"]
    problems: list[str] = []

    ids = [f["id"] for f in funds]
    if len(ids) != len(set(ids)):
        problems.append("Doppelte Fonds-IDs im Datensatz.")

    for f in funds:
        if not f.get("id") or not f.get("name"):
            problems.append(f"Fonds ohne ID/Name: {f}")
        if f["branding"] not in ("Union Investment", "Quoniam"):
            problems.append(f"Unerwartetes Branding bei {f['id']}: {f['branding']}")
        for key, val in f["metrics"].items():
            if key not in ALLOWED_KEYS:
                problems.append(f"{f['id']}: unerwartete Kennzahl {key}")
            if not isinstance(val, (int, float)):
                problems.append(f"{f['id']}: {key} ist kein Zahlwert ({val!r})")
            else:
                # Plausibilitätsband: die meisten risikoadjustierten Kennzahlen
                # liegen in [-50, 150] (Sortino kann bei ~0 Downside extrem groß
                # werden). Treynor ist eine Excess-Return-/Beta-Größe und kann bei
                # kleinem Beta betragsmäßig deutlich größer ausfallen.
                lo, hi = (-1000, 1000) if key.startswith("treynor") else (-50, 150)
                if not (lo <= val <= hi):
                    problems.append(f"{f['id']}: {key}={val} außerhalb Plausibilitätsband")

    # Konsistenz: identische Werte zwischen 1y-Sharpe und 1y-Sortino wären verdächtig
    # (nur ein grober Smoke-Check, keine harte Regel).

    n_with = sum(1 for f in funds if f["metrics"])
    print(f"Fonds gesamt:        {len(funds)}")
    print(f"Mit >=1 Kennzahl:    {n_with}")
    print(f"Ohne Kennzahl:       {len(funds) - n_with}")
    print(f"Kategorien (alle):   {len(fm.available_categories(funds))}")
    by_brand = {}
    for f in funds:
        by_brand[f["branding"]] = by_brand.get(f["branding"], 0) + 1
    print(f"Nach Anbieter:       {by_brand}")

    # Zähle Befüllung je Kennzahl/Laufzeit
    print("\nBefüllung je Kennzahl/Laufzeit:")
    for key in sorted(ALLOWED_KEYS):
        c = sum(1 for f in funds if key in f["metrics"])
        print(f"  {key:16s} {c:3d} Fonds")

    if problems:
        print(f"\n{len(problems)} PROBLEM(E) gefunden:")
        for p in problems[:50]:
            print(f"  - {p}")
        return 1
    print("\nAlle Integritätsprüfungen bestanden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
