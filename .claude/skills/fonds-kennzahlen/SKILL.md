---
name: fonds-kennzahlen
description: >-
  Interaktiver Generator für Kennzahlen von Union- & Quoniam-Investmentfonds
  (Datenquelle Morningstar, Snapshot in data/funds.json). Fragt Kennzahl,
  Laufzeit, Anbieter und Morningstar-Fondskategorie ab und erzeugt daraus eine
  PowerPoint (.pptx) – auf Wunsch zusätzlich CSV/Excel – mit der gerankten
  Ergebnistabelle und liefert die Datei. Nutzen, wenn der Nutzer eine
  Auswertung, Rangliste, Tabelle oder PowerPoint zu Union-/Quoniam-Fonds will
  bzw. "den Generator" startet.
---

# Fonds-Kennzahlen-Generator (PowerPoint/CSV/Excel)

Ablauf, wenn diese Skill aufgerufen wird:

## 1. Eingaben erfragen
Frage die folgenden vier Punkte ab – am besten gebündelt mit **AskUserQuestion**
(wenn der Nutzer Werte schon im Text genannt hat, diese übernehmen und nur
fehlende erfragen):

- **Kennzahl**: `performance` (absolute Rendite), `sharpe` (Sharpe Ratio),
  `sortino` (Sortino Ratio), `information` (Information Ratio), `treynor`
  (Treynor Ratio, berechnet), `alpha` (Jensens Alpha), `volatility`
  (Volatilität/Std.-Abw., niedriger=besser), `beta`, `trackingerror`
  (Tracking Error, nur 3y/5y, niedriger=besser).
- **Laufzeit**: `1y`, `3y`, `5y` für alle Kennzahlen; zusätzlich `1m`, `3m`, `6m`
  **nur** für `performance`. `trackingerror` gibt es erst ab `3y`. Welche
  Laufzeiten je Kennzahl gültig sind, steht in `fund_metrics.METRICS`.
- **Anbieter**: `all` (Union + Quoniam), `union`, `quoniam`.
- **Kategorie**: eine Morningstar-Kategorie (ohne „EAA Fund“-Präfix) oder „Alle
  Kategorien“. Wenn der Nutzer die Liste sehen will, vorher ausgeben mit:
  `python3 fund_metrics.py --list-categories` (bei Bedarf mit `--provider`).

Optional: gewünschtes Ausgabeformat (PowerPoint = Standard; zusätzlich CSV/Excel
möglich) und ob nur die Top-N gezeigt werden sollen.

## 2. Voraussetzungen sicherstellen
- Im Projektverzeichnis arbeiten (dort liegen `make_pptx.py`, `fund_metrics.py`,
  `data/funds.json`).
- Für PowerPoint wird `python-pptx` benötigt. Falls Import fehlschlägt:
  `pip install python-pptx -q` (für Excel analog `openpyxl`).

## 3. Datei erzeugen
PowerPoint:
```bash
python3 make_pptx.py --metric <KENNZAHL> --period <LAUFZEIT> \
    --provider <ANBIETER> [--category "<KATEGORIE>"] [--top <N>] \
    --out "/tmp/<sprechender_name>.pptx"
```
Optional zusätzlich CSV/Excel:
```bash
python3 fund_metrics.py --metric <KENNZAHL> --period <LAUFZEIT> \
    --provider <ANBIETER> [--category "<KATEGORIE>"] [--top <N>] \
    --export "/tmp/<name>.csv"   # oder .xlsx
```
- `--category` nur setzen, wenn eine konkrete Kategorie gewählt wurde (sonst
  weglassen = alle Kategorien).
- Dateinamen sprechend wählen (Kennzahl/Laufzeit/Anbieter/Kategorie).

## 4. Ergebnis liefern
- Die erzeugte Datei mit **SendUserFile** an den Nutzer senden.
- Kurze Zusammenfassung dazugeben: Auswahl, Anzahl Fonds, Top 3 mit Werten.

## Hinweise
- Höhere Werte sind besser (Sortierung absteigend) – außer bei `volatility` und
  `trackingerror`, wo niedrigere Werte besser sind (aufsteigend, kleinster Wert =
  Rang 1). Fonds ohne Wert für die konkrete Kennzahl/Laufzeit werden ausgelassen.
- Treynor ist berechnet (`Sharpe × StdAbw ÷ Beta`); ohne Beta kein Wert.
- Datengrundlage ist ein Snapshot (`data/funds.json`); Stand steht im Feld
  `meta.as_of` und erscheint auf der Titelfolie.
- Nach einer Ausgabe anbieten, mit einer neuen Auswahl direkt die nächste Datei
  zu erzeugen.
