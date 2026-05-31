# Union- & Quoniam-Fonds – Kennzahlen-Tool

Ein Kommandozeilen-Tool, das für **alle Union- und Quoniam-Investmentfonds**
risikoadjustierte Kennzahlen aus **Morningstar** anzeigt. Auswählbar sind
**Kennzahl**, **Laufzeit** und **Morningstar-Fondskategorie**; Ergebnisse lassen
sich als **CSV/Excel** exportieren.

## Kennzahlen & Laufzeiten

| Kennzahl              | 1 Jahr | 3 Jahre | 5 Jahre |
|-----------------------|:------:|:-------:|:-------:|
| Sharpe Ratio          |   ✓    |    ✓    |    ✓    |
| Sortino Ratio         |   ✓    |    ✓    |    ✓    |
| Information Ratio      |   –    |    ✓    |    ✓    |
| Treynor Ratio         |   ✓    |    ✓    |    ✓    |
| Jensens Alpha (Alpha) |   ✓    |    ✓    |    ✓    |

### Treynor (berechnet) und warum kein Calmar?

* **Treynor Ratio** stellt der Morningstar-Konnektor nicht als eigenen
  Datenpunkt bereit, lässt sich aber **exakt berechnen** über die Identität
  `Treynor = Sharpe × Standardabweichung ÷ Beta`. Das gilt mathematisch exakt,
  weil Morningstars Sharpe Ratio und Beta dieselbe Excess-Return-Basis (über dem
  risikofreien Zins) verwenden. Treynor ist eine Prozentgröße (Überrendite je
  Einheit Marktrisiko/Beta). Es gibt **keinen** Treynor-Wert, wenn Morningstar
  kein Beta liefert (meist mangels passender Benchmark/Historie) oder wenn
  `|Beta| < 0.05` ist (Division durch ~0 wäre unsinnig).
* **Calmar Ratio** benötigt den *Maximum Drawdown*, den der Konnektor nicht
  bereitstellt; sie ist daher weder abrufbar noch berechenbar und nicht enthalten.
* **Information Ratio** liefert Morningstar nur für **3 und 5 Jahre**
  (kein sauberer 1-Jahres-Wert im Standarddatensatz).

## Verwendung

### Interaktiv
```bash
python3 fund_metrics.py
```
Geführte Auswahl: Anbieter → Kennzahl → Laufzeit → Kategorie → Tabelle →
optionaler Export.

### Direkt (nicht-interaktiv / skriptbar)
```bash
# Top 20 nach Sharpe Ratio 3 Jahre in einer Kategorie
python3 fund_metrics.py --metric sharpe --period 3y \
    --category "Global Large-Cap Blend Equity" --top 20

# Jensens Alpha 5 Jahre, nur Quoniam, Export nach Excel/CSV
python3 fund_metrics.py --metric alpha --period 5y --provider quoniam \
    --export ergebnis.xlsx

# Verfügbare Kategorien auflisten
python3 fund_metrics.py --list-categories
```

Optionen: `--metric {sharpe,sortino,information,treynor,alpha}`,
`--period {1y,3y,5y}`, `--category "<Name ohne 'EAA Fund'-Präfix>"`,
`--provider {all,union,quoniam}`, `--top N`, `--export DATEI.csv|.xlsx`.

CSV wird Excel-/DE-freundlich exportiert (Semikolon-getrennt, UTF-8-BOM).
Für `.xlsx` wird `openpyxl` benötigt; fehlt es, wird automatisch CSV erzeugt.

### PowerPoint-Export

`make_pptx.py` erzeugt aus derselben Auswahl eine PowerPoint (Titelfolie +
gerankte Tabelle, 16:9, paginiert). Benötigt `python-pptx`
(`pip install python-pptx`):
```bash
python3 make_pptx.py --metric treynor --period 3y --provider quoniam \
    --out treynor_quoniam_3j.pptx
python3 make_pptx.py --metric sharpe --period 5y \
    --category "Global Large-Cap Blend Equity" --top 25 --out sharpe.pptx
```

## Datenstand & Aktualisierung

Das Tool arbeitet auf einem **Daten-Snapshot** (`data/funds.json`), der über den
Morningstar-Konnektor erzeugt wurde. Stand und Quelle stehen im Feld `meta`.

> Der Morningstar-Konnektor (MCP) ist nur innerhalb einer Claude-Sitzung
> erreichbar, nicht aus einem eigenständig laufenden Programm. Zum
> **Aktualisieren** der Daten müssen daher die Rohabrufe über Claude neu
> ausgeführt und in `data/raw/` abgelegt werden; anschließend:
> ```bash
> python3 build_dataset.py
> ```

### Datenpipeline
```
data/raw/screener/*.json   Fonds-Universum (ID, Name, Kategorie, Anbieter)
data/raw/metrics/*.json    Kennzahlen je Fonds (Morningstar-Datenpunkt-IDs)
data/raw/risk/*.json       Std.-Abweichung & Beta je Fonds (für Treynor)
        │  build_dataset.py   (rechnet zusätzlich Treynor je Laufzeit aus)
        ▼
data/funds.json            bereinigter Datensatz, den das Tool liest
```

Verwendete Morningstar-Datenpunkt-IDs: Sharpe `RR010/RR011/RR012`,
Sortino `RR122/RR123/RR124`, Information Ratio `RR147/RR148`,
Alpha `RR002/RR003/RR004`. Für die Treynor-Berechnung zusätzlich:
Standardabweichung `RR014/RR015/RR016` und Beta `RR00K/RR00L/RR00M`.

## Datenumfang

* **307 Fonds** gesamt: 258 Union Investment + 49 Quoniam (alle Anteilsklassen).
* **288 Fonds** mit mindestens einer Kennzahl. Sehr junge Fonds ohne
  ausreichende Historie haben (noch) keine Werte und erscheinen bei der
  betreffenden Kennzahl/Laufzeit nicht.
* Treynor ist für rund 238 (1J) / 221 (3J) / 198 (5J) Fonds vorhanden – überall
  dort, wo Morningstar ein Beta liefert.
* Fonds ohne Wert für die konkrete Kennzahl/Laufzeit werden in der Rangliste
  ausgelassen (nicht als 0 gewertet).

## Hinweise zur Interpretation

* Höhere Werte sind bei allen fünf Kennzahlen besser; sortiert wird absteigend.
* Vereinzelt liefert Morningstar bei Fonds mit nahezu null Abwärtsabweichung
  **extrem hohe Sortino-1-Jahres-Werte** (z. B. Commodities-Fonds). Diese Werte
  werden unverändert aus der Quelle übernommen.
* Kennzahlen werden „month-end" (Mo-End) berechnet.

## Tests & Validierung

```bash
python3 test_fund_metrics.py     # Unit-Tests der Kernlogik
python3 validate_dataset.py      # Integritäts-/Plausibilitätsprüfungen
```
Die Korrektheit des Datensatzes wurde zusätzlich durch eine Stichprobe
(166 Werte über 16 Fonds) gegen frische Morningstar-Abrufe geprüft
(100 % Übereinstimmung).

## Dateien

| Datei                  | Zweck                                            |
|------------------------|--------------------------------------------------|
| `fund_metrics.py`      | Das CLI-Tool (interaktiv + Argumente + Export)   |
| `build_dataset.py`     | Baut `data/funds.json` aus den Rohdaten          |
| `validate_dataset.py`  | Integritäts- und Plausibilitätsprüfungen         |
| `test_fund_metrics.py` | Unit-Tests der Filter-/Sortier-/Exportlogik      |
| `data/funds.json`      | Bereinigter Datensatz (Snapshot)                 |
| `data/raw/`            | Rohabrufe (Screener + Kennzahlen)                |
