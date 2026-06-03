#!/usr/bin/env python3
"""Tests für die Kernlogik von fund_metrics.py.

Ausführen:  python3 -m pytest test_fund_metrics.py -q
        oder python3 test_fund_metrics.py   (einfacher Selbsttest ohne pytest)
"""
from __future__ import annotations

import os
import tempfile

import fund_metrics as fm

SAMPLE_FUNDS = [
    {
        "id": "F1", "name": "Alpha Global", "branding": "Union Investment",
        "category": "EAA Fund Global Large-Cap Blend Equity",
        "metrics": {"sharpe_3y": 0.90, "sharpe_1y": 1.20, "alpha_3y": -2.5, "information_3y": -0.66},
    },
    {
        "id": "F2", "name": "Beta Global", "branding": "Union Investment",
        "category": "EAA Fund Global Large-Cap Blend Equity",
        "metrics": {"sharpe_3y": 1.05, "sharpe_1y": 1.30, "alpha_3y": 0.4},
    },
    {
        "id": "F3", "name": "Quoniam Euro Credit", "branding": "Quoniam",
        "category": "EAA Fund EUR Corporate Bond",
        "metrics": {"sharpe_3y": 0.50, "information_3y": 0.20, "information_5y": 0.18},
    },
    {
        "id": "F4", "name": "Junger Fonds", "branding": "Quoniam",
        "category": "EAA Fund EUR Corporate Bond",
        "metrics": {"sharpe_1y": 0.80},  # keine 3J-Daten
    },
]


def test_normalize_category():
    assert fm.normalize_category("EAA Fund Global Large-Cap Blend Equity") == \
        "Global Large-Cap Blend Equity"
    assert fm.normalize_category("Sonstiges") == "Sonstiges"


def test_query_sort_descending():
    rows = fm.query(SAMPLE_FUNDS, "sharpe", "3y")
    vals = [r["value"] for r in rows]
    assert vals == sorted(vals, reverse=True)
    assert rows[0]["name"] == "Beta Global"  # 1.05 > 0.90 > 0.50


def test_query_excludes_missing_values():
    # F4 hat keinen sharpe_3y -> darf nicht erscheinen
    rows = fm.query(SAMPLE_FUNDS, "sharpe", "3y")
    assert "Junger Fonds" not in [r["name"] for r in rows]
    # aber bei 1y erscheint F4
    rows1 = fm.query(SAMPLE_FUNDS, "sharpe", "1y")
    assert "Junger Fonds" in [r["name"] for r in rows1]


def test_query_category_filter():
    rows = fm.query(
        SAMPLE_FUNDS, "sharpe", "3y", category="EUR Corporate Bond"
    )
    assert {r["name"] for r in rows} == {"Quoniam Euro Credit"}


def test_query_provider_filter():
    rows = fm.query(SAMPLE_FUNDS, "sharpe", "3y", provider="quoniam")
    assert all(r["branding"] == "Quoniam" for r in rows)
    rows_u = fm.query(SAMPLE_FUNDS, "sharpe", "3y", provider="union")
    assert all(r["branding"] == "Union Investment" for r in rows_u)


def test_treynor_is_available_metric():
    # Treynor muss als Kennzahl mit 1y/3y/5y vorhanden sein
    assert "treynor" in fm.METRICS
    assert fm.METRICS["treynor"][1] == ["1y", "3y", "5y"]


def test_treynor_query_sort_and_filter():
    funds = [
        {"id": "T1", "name": "A", "branding": "Quoniam",
         "category": "EAA Fund EUR Corporate Bond", "metrics": {"treynor_3y": 5.0}},
        {"id": "T2", "name": "B", "branding": "Quoniam",
         "category": "EAA Fund EUR Corporate Bond", "metrics": {"treynor_3y": 9.0}},
        {"id": "T3", "name": "C", "branding": "Quoniam",
         "category": "EAA Fund EUR Corporate Bond", "metrics": {}},  # ohne Treynor
    ]
    rows = fm.query(funds, "treynor", "3y")
    assert [r["name"] for r in rows] == ["B", "A"]  # absteigend, C ausgelassen


def test_information_ratio_has_1y():
    # Information Ratio unterstützt jetzt 1y (Datenpunkt ZS71V).
    assert fm.METRICS["information"][1] == ["1y", "3y", "5y"]
    # darf keinen ValueError mehr werfen
    fm.query(SAMPLE_FUNDS, "information", "1y")


def test_all_metrics_support_1_3_5_except_none():
    # Jede Kennzahl deckt jetzt 1y/3y/5y ab.
    for k, (_lbl, periods, _hb) in fm.METRICS.items():
        assert periods == ["1y", "3y", "5y"], f"{k} deckt nicht 1/3/5 ab: {periods}"


def test_available_categories():
    cats = fm.available_categories(SAMPLE_FUNDS)
    assert "Global Large-Cap Blend Equity" in cats
    assert "EUR Corporate Bond" in cats
    # alphabetisch sortiert
    assert cats == sorted(cats)


def test_export_csv_roundtrip():
    rows = fm.query(SAMPLE_FUNDS, "sharpe", "3y")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "out.csv")
        fm.export_rows(rows, "sharpe", "3y", path)
        assert os.path.exists(path)
        with open(path, encoding="utf-8-sig") as fh:
            content = fh.read()
        assert "Beta Global" in content
        assert "Sharpe Ratio 3 Jahre" in content
        # Rang 1 ist der beste Fonds
        first_data_line = content.splitlines()[1]
        assert first_data_line.startswith("1;Beta Global")


def _run_without_pytest():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"  ok  {fn.__name__}")
    print(f"\n{passed} Tests bestanden.")


if __name__ == "__main__":
    _run_without_pytest()
