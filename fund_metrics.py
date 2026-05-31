#!/usr/bin/env python3
"""Union- & Quoniam-Fonds-Kennzahlen-Tool (Datenquelle: Morningstar-Konnektor).

Das Tool zeigt für Union- und Quoniam-Investmentfonds risikoadjustierte
Kennzahlen an. Der/die Nutzer:in wählt:

  * Kennzahl   – Sharpe, Sortino, Information Ratio, Treynor, Jensens Alpha
  * Laufzeit   – 1 Jahr, 3 Jahre, 5 Jahre
  * Kategorie  – Morningstar-Fondskategorie (z. B. "Global Large-Cap Blend Equity")

Hinweise zu den Kennzahlen
--------------------------
* Treynor Ratio liefert der Konnektor nicht direkt; sie wird exakt berechnet als
  Sharpe x Standardabweichung / Beta (gleiche Excess-Return-Basis). Ohne
  verfügbares Beta (oder bei |Beta| ~ 0) gibt es keinen Treynor-Wert.
* Information Ratio liefert Morningstar nur für 3 und 5 Jahre (kein 1-Jahres-Wert).
* Calmar Ratio ist nicht enthalten: Sie bräuchte den Maximum Drawdown, den der
  Konnektor nicht bereitstellt.

Verwendung
----------
Interaktiv:
    python3 fund_metrics.py

Direkt (nicht-interaktiv, eignet sich für Skripte/Tests):
    python3 fund_metrics.py --metric sharpe --period 3y \
        --category "Global Large-Cap Blend Equity" --provider all --top 20
    python3 fund_metrics.py --metric alpha --period 5y --export ergebnis.csv
    python3 fund_metrics.py --list-categories
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "funds.json")

# Kennzahl -> (Anzeigename, erlaubte Laufzeiten, höher-ist-besser?)
METRICS = {
    "sharpe": ("Sharpe Ratio", ["1y", "3y", "5y"], True),
    "sortino": ("Sortino Ratio", ["1y", "3y", "5y"], True),
    "information": ("Information Ratio", ["3y", "5y"], True),
    "treynor": ("Treynor Ratio", ["1y", "3y", "5y"], True),
    "alpha": ("Jensens Alpha", ["1y", "3y", "5y"], True),
}

PERIOD_LABELS = {"1y": "1 Jahr", "3y": "3 Jahre", "5y": "5 Jahre"}


# --------------------------------------------------------------------------- #
# Daten laden
# --------------------------------------------------------------------------- #
def load_data(path: str = DATA_FILE) -> dict:
    if not os.path.exists(path):
        sys.exit(
            f"Datendatei nicht gefunden: {path}\n"
            "Bitte zuerst 'python3 build_dataset.py' ausführen."
        )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# Kernlogik (rein, gut testbar)
# --------------------------------------------------------------------------- #
def normalize_category(cat: str) -> str:
    """Entfernt das Morningstar-Präfix 'EAA Fund ' für Anzeige & Vergleich."""
    cat = cat.strip()
    prefix = "EAA Fund "
    return cat[len(prefix):] if cat.startswith(prefix) else cat


def available_categories(funds: list[dict], provider: str = "all") -> list[str]:
    cats = {
        normalize_category(f["category"])
        for f in funds
        if provider == "all" or f["branding"].lower().startswith(provider.lower())
    }
    return sorted(cats)


def metric_key(metric: str, period: str) -> str:
    return f"{metric}_{period}"


def query(
    funds: list[dict],
    metric: str,
    period: str,
    category: str | None = None,
    provider: str = "all",
) -> list[dict]:
    """Filtert und sortiert Fonds nach der gewählten Kennzahl/Laufzeit.

    * category=None  -> alle Kategorien
    * provider       -> 'all', 'union' oder 'quoniam'
    Es werden nur Fonds zurückgegeben, die für genau diese Kennzahl/Laufzeit
    einen Wert besitzen. Sortierung: bester Wert zuerst.
    """
    if metric not in METRICS:
        raise ValueError(f"Unbekannte Kennzahl: {metric}")
    label, periods, higher_better = METRICS[metric]
    if period not in periods:
        raise ValueError(
            f"Laufzeit '{period}' für {label} nicht verfügbar "
            f"(erlaubt: {', '.join(periods)})."
        )

    key = metric_key(metric, period)
    rows = []
    for f in funds:
        if provider != "all" and not f["branding"].lower().startswith(provider.lower()):
            continue
        if category is not None and normalize_category(f["category"]) != category:
            continue
        val = f.get("metrics", {}).get(key)
        if val is None:
            continue
        rows.append(
            {
                "name": f["name"],
                "branding": f["branding"],
                "category": normalize_category(f["category"]),
                "id": f["id"],
                "value": val,
            }
        )
    rows.sort(key=lambda r: r["value"], reverse=higher_better)
    return rows


# --------------------------------------------------------------------------- #
# Ausgabe / Export
# --------------------------------------------------------------------------- #
def print_table(rows: list[dict], metric: str, period: str, top: int | None = None) -> None:
    label = METRICS[metric][0]
    shown = rows[:top] if top else rows
    header_metric = f"{label} ({PERIOD_LABELS[period]})"
    if not shown:
        print("\nKeine Fonds mit Werten für diese Auswahl gefunden.\n")
        return

    name_w = max(len("Fonds"), *(len(r["name"]) for r in shown))
    prov_w = max(len("Anbieter"), *(len(r["branding"]) for r in shown))
    name_w = min(name_w, 48)

    print()
    print(f"  {'#':>3}  {'Fonds':<{name_w}}  {'Anbieter':<{prov_w}}  {header_metric:>22}")
    print("  " + "-" * (5 + name_w + prov_w + 26))
    for i, r in enumerate(shown, 1):
        name = r["name"] if len(r["name"]) <= name_w else r["name"][: name_w - 1] + "…"
        print(f"  {i:>3}  {name:<{name_w}}  {r['branding']:<{prov_w}}  {r['value']:>22.3f}")
    print(f"\n  {len(shown)} von {len(rows)} Fonds angezeigt.\n")


def export_rows(rows: list[dict], metric: str, period: str, path: str) -> str:
    label = METRICS[metric][0]
    col = f"{label} {PERIOD_LABELS[period]}"
    ext = os.path.splitext(path)[1].lower()

    if ext in (".xlsx", ".xls"):
        try:
            from openpyxl import Workbook
        except ImportError:
            alt = os.path.splitext(path)[0] + ".csv"
            print(
                "Hinweis: 'openpyxl' ist nicht installiert – exportiere stattdessen "
                f"CSV: {alt}\n(Installation: pip install openpyxl)"
            )
            return export_rows(rows, metric, period, alt)
        wb = Workbook()
        ws = wb.active
        ws.title = "Kennzahlen"
        ws.append(["Rang", "Fonds", "Anbieter", "Kategorie", "Morningstar-ID", col])
        for i, r in enumerate(rows, 1):
            ws.append([i, r["name"], r["branding"], r["category"], r["id"], r["value"]])
        wb.save(path)
        return path

    # Standard: CSV (Semikolon, Excel-/DE-freundlich, UTF-8 BOM)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(["Rang", "Fonds", "Anbieter", "Kategorie", "Morningstar-ID", col])
        for i, r in enumerate(rows, 1):
            writer.writerow([i, r["name"], r["branding"], r["category"], r["id"], r["value"]])
    return path


# --------------------------------------------------------------------------- #
# Interaktiver Modus
# --------------------------------------------------------------------------- #
def _choose(title: str, options: list[str]) -> int | None:
    print(f"\n{title}")
    for i, opt in enumerate(options, 1):
        print(f"  {i:>3}) {opt}")
    while True:
        raw = input("Auswahl (Nummer, q = beenden): ").strip().lower()
        if raw in ("q", "quit", "exit"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print("  Ungültige Eingabe, bitte erneut.")


def interactive(data: dict) -> None:
    funds = data["funds"]
    meta = data.get("meta", {})
    print("=" * 64)
    print(" Union- & Quoniam-Fonds – Kennzahlen (Quelle: Morningstar)")
    print(f" Stand: {meta.get('as_of', '?')}   Fonds im Datensatz: {meta.get('fund_count', len(funds))}")
    print("=" * 64)

    while True:
        # 1) Anbieter
        prov_idx = _choose(
            "Anbieter wählen:",
            ["Alle (Union + Quoniam)", "Union Investment", "Quoniam"],
        )
        if prov_idx is None:
            break
        provider = {0: "all", 1: "union", 2: "quoniam"}[prov_idx]

        # 2) Kennzahl
        metric_keys = list(METRICS.keys())
        m_idx = _choose(
            "Kennzahl wählen:",
            [f"{METRICS[k][0]}  (Laufzeiten: {', '.join(METRICS[k][1])})" for k in metric_keys],
        )
        if m_idx is None:
            break
        metric = metric_keys[m_idx]

        # 3) Laufzeit
        periods = METRICS[metric][1]
        p_idx = _choose("Laufzeit wählen:", [PERIOD_LABELS[p] for p in periods])
        if p_idx is None:
            break
        period = periods[p_idx]

        # 4) Kategorie
        cats = available_categories(funds, provider)
        cat_options = ["Alle Kategorien"] + cats
        c_idx = _choose("Morningstar-Fondskategorie wählen:", cat_options)
        if c_idx is None:
            break
        category = None if c_idx == 0 else cat_options[c_idx]

        rows = query(funds, metric, period, category, provider)
        print_table(rows, metric, period, top=None)

        # 5) Export?
        ans = input("Diese Ergebnisliste exportieren? (Dateiname .csv/.xlsx, leer = nein): ").strip()
        if ans:
            out = export_rows(rows, metric, period, ans)
            print(f"  Exportiert nach: {out}")

        again = input("\nNeue Abfrage? (Enter = ja, q = beenden): ").strip().lower()
        if again in ("q", "quit", "exit"):
            break
    print("\nAuf Wiedersehen.")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Kennzahlen für Union- & Quoniam-Fonds (Morningstar).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--metric", choices=list(METRICS.keys()), help="Kennzahl")
    p.add_argument("--period", choices=["1y", "3y", "5y"], help="Laufzeit")
    p.add_argument("--category", help="Morningstar-Kategorie (ohne 'EAA Fund'-Präfix)")
    p.add_argument(
        "--provider", choices=["all", "union", "quoniam"], default="all", help="Anbieterfilter"
    )
    p.add_argument("--top", type=int, default=None, help="Nur die Top-N Fonds anzeigen")
    p.add_argument("--export", metavar="DATEI", help="Ergebnis als .csv oder .xlsx exportieren")
    p.add_argument("--list-categories", action="store_true", help="Verfügbare Kategorien auflisten")
    p.add_argument("--data", default=DATA_FILE, help="Pfad zur funds.json")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data = load_data(args.data)
    funds = data["funds"]

    if args.list_categories:
        for c in available_categories(funds, args.provider):
            print(c)
        return 0

    # Nicht-interaktiv, wenn Kennzahl & Laufzeit gesetzt sind.
    if args.metric and args.period:
        try:
            rows = query(funds, args.metric, args.period, args.category, args.provider)
        except ValueError as exc:
            print(f"Fehler: {exc}", file=sys.stderr)
            return 2
        print_table(rows, args.metric, args.period, top=args.top)
        if args.export:
            out = export_rows(rows, args.metric, args.period, args.export)
            print(f"Exportiert nach: {out}")
        return 0

    if args.metric or args.period:
        print("Bitte --metric UND --period angeben (oder ohne Argumente interaktiv starten).",
              file=sys.stderr)
        return 2

    interactive(data)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BrokenPipeError, KeyboardInterrupt):
        # Sauberes Beenden bei abgebrochener Pipe (z. B. | head) oder Ctrl-C.
        try:
            sys.stdout.close()
        except Exception:
            pass
        raise SystemExit(0)
