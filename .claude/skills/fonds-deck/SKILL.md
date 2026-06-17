---
name: fonds-deck
description: >
  Erstellt für ein fest hinterlegtes Fondsuniversum (98 ISINs, Union/Quoniam/
  iShares/Xtrackers u. a.) zu einem beliebigen, vom Nutzer genannten Stichtag
  eine professionelle PowerPoint-Analyse: Gliederung in grobe Anlageklassen
  (Aktien, Renten, Rohstoffe & Gold, Wandelanleihen, Immobilien, Geldmarkt) und
  je Klasse ein fundierter Vergleich (Ranglisten + Risiko-Rendite-Streudiagramm)
  sowie ein Kompaktprofil je Fonds (Stammdaten, Morningstar-Ratings, Rendite-/
  Risikokennzahlen, optional Portfolio-X-Ray). Daten live über den Morningstar-
  MCP-Konnektor. Nutzen, wenn der Nutzer „die Fondsanalyse / das Fonds-Deck /
  die Fonds-PowerPoint" zu einem Stichtag will. Dies ist die DRITTE App und ist
  unabhängig von App 1 (index.html) und App 2 (jome/).
---

# Fonds-Analyse-PowerPoint (App 3)

Erzeugt aus dem fest hinterlegten Universum (`data/raw3/universe.json`, 98 in
Morningstar verfügbare Fonds; 14 ISINs nicht verfügbar, siehe `not_found`) eine
fertige `.pptx` für einen beliebigen Stichtag. Tokensparsam: die großen
`data-tool`-Antworten werden vom Harness **in Dateien gespeichert** und per
Skript geparst – die Zahlen fließen nicht Wert für Wert durch den Chat.

## Ablauf

### 1. Stichtag erfragen
Frage den gewünschten **Stichtag** ab (Format `YYYY-MM-DD`, sinnvoll ein
Monatsultimo, z. B. `2026-05-31`). Quantitative Kennzahlen beziehen sich auf den
Stichtag, soweit Morningstar Historie liefert; Portfolio-Zusammensetzungen
entsprechen dem aktuellsten verfügbaren Stand.

### 2. Kennzahlen abrufen (5 Batches, `morningstar-data-tool`)
Für **jeden** der 5 Investment-Batches die **46 Datenpunkt-IDs** mit
`start_date = end_date = <Stichtag>` abrufen. Die Antworten sind groß und landen
automatisch in einer Datei („Output has been saved to …"). Batches und
Datenpunkte stehen in `data/raw3/datapoints.txt`. Investment-Batches neu
erzeugen mit:
```bash
python3 -c "import json;inv=list(json.load(open('data/raw3/universe.json'))['investments']);[print(','.join(inv[k:k+20])) for k in range(0,len(inv),20)]"
```
Bei einem 502/Bad-Gateway den betroffenen Batch einfach erneut abrufen.

### 3. Parsen
```bash
python3 parse_tool_result3.py "<datei_batch1>" data/raw3/metrics/b1.json <Stichtag>
# … b2 … b5 analog (Stichtag als 3. Argument: wählt bei Zeitreihen den Wert zum Stichtag)
```

### 4. (Optional) Portfolio-X-Ray je Fonds
Für tiefere Profile (Asset-Allokation, Sektoren, Top-Positionen) je Fonds:
- `morningstar-portfolio-analysis-tool` mit `fund_id=<FID>`, `analysis_type` aus
  `asset_allocation`, `equity_sectors`, ggf. `fixed_income_sectors`.
- `morningstar-fund-holdings-tool` mit `investment_ids=[<FID>]`, `num_holdings=15`.
Die (kleinen) Antworten in **eine** Sammeldatei im Schema
`{ "<FID>": {"asset_allocation":…, "equity_sectors":…, "holdings":…} }` schreiben
und normalisieren:
```bash
python3 parse_portfolio3.py <sammeldatei.json>   # schreibt data/raw3/portfolio|holdings/<FID>.json
```
Hinweis: 4 Aufrufe je Fonds × 98 = teuer. Standardmäßig **ohne** X-Ray bauen
(die quantitative Auswertung ist bereits umfassend); X-Ray nur auf Wunsch oder
für eine Teilmenge ergänzen.

### 5. Datensatz & PowerPoint bauen
```bash
python3 build_deck_dataset.py <Stichtag>          # -> data/funds3.json
python3 make_fund_deck.py --out "/tmp/Fondsanalyse_<Stichtag>.pptx"
```
`build_deck_dataset.py` klassifiziert anhand der Morningstar-Kategorie in grobe
Anlageklassen und bindet vorhandene Portfolio-/Holdings-Dateien automatisch ein.

### 6. Liefern
Die `.pptx` mit **SendUserFile** an den Nutzer senden und kurz zusammenfassen
(Stichtag, Fondszahl je Klasse, Auffälligkeiten). Danach anbieten, mit einem
anderen Stichtag direkt erneut zu bauen.

## Voraussetzungen
`pip install python-pptx -q` (falls Import fehlschlägt).

## Universe pflegen
Neue/zu entfernende ISINs in `data/raw3/universe.json` ändern. Neue ISIN →
Morningstar-ID via `morningstar-id-lookup-tool` (fund-level `F…`-ID nehmen, nicht
die Börsen-Listings `0P…`). Nicht auffindbare ISINs in `not_found` eintragen.

## Wichtig
- Dies ist **App 3**. App 1 (`index.html`, `webapp/`, `build_*.py`,
  `data/funds.json`) und App 2 (`jome/`, `*2.py`, `data/funds2.json`) **nicht**
  anfassen. Eigene Dateien: `*_deck*.py`/`*3.py`, `data/raw3/`, `data/funds3.json`.
- Stichtag erscheint auf jeder Folie. Zahlenformat ist deutsch (Komma, Tsd.-Punkt).
