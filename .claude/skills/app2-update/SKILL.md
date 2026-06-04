---
name: app2-update
description: >
  Monatliches Daten-Update für die ZWEITE App (Fonds & ETFs, app2/index.html).
  Ruft per Morningstar-Konnektor die aktuellen Monatsultimo-Kennzahlen für die
  fest hinterlegten 98 Wertpapiere ab, baut data/funds2.json + app2/index.html
  neu und committet/pusht. Tokensparsam: die Tool-Antworten werden in Dateien
  gespeichert und per Skript geparst (kein Abtippen). Nutzen, wenn der Nutzer das
  App-2-Update / den Datenstand zum Monatsende (30.06., 31.07., …) aktualisieren
  will. App 1 wird dabei NICHT angefasst.
---

# App 2 – monatliches Daten-Update (Fonds & ETFs)

Aktualisiert ausschließlich App 2. Morningstar liefert „Mo-End"-Werte automatisch
zum jeweils letzten Monatsultimo – einfach nach Monatsende ausführen.

## Warum es ein paar Tokens braucht
Der Morningstar-Konnektor ist nur in einer Claude-Sitzung erreichbar. Die Roh-
antworten sind groß, werden aber vom Harness **in Dateien gespeichert**; wir
parsen sie per Skript. Dadurch fließen die Zahlen **nicht** Wert für Wert durch
den Chat. Ein Update = 5 Tool-Aufrufe + ein paar Shell-Kommandos.

## Feste Parameter
**28 Datenpunkt-IDs** (immer alle gemeinsam abrufen):
`FC001,OF003,PM004,PM006,PM008,PM00C,PM00E,PM00G,RR141,RR142,RR010,RR011,RR012,RR122,RR123,RR124,RR147,RR148,ZS71V,RR002,RR003,RR004,RR014,RR015,RR016,RR00K,RR00L,RR00M`

**Investment-IDs in 5 Batches** (Quelle: `data/raw2/universe.json`; bei Bedarf neu
erzeugen mit `python3 -c "import json;u=json.load(open('data/raw2/universe.json'))['investments'];ids=list(u);[print(','.join(ids[k:k+20])) for k in range(0,len(ids),20)]"`):

- **Batch 1** (20): `F000002F7I,F000002F7M,F00001DKKA,F0GBR04BJP,F000010NU6,F000016S88,F00000ZYE2,F00000V3RU,F00000JY1R,F0GBR04PQF,F0GBR04BK2,F0GBR04BJZ,F0GBR04HGO,F00000V3RR,F000004580,F00000JXUB,F00000ZB3N,F000005GVD,F00000YMLB,F0GBR04BKB`
- **Batch 2** (20): `F0GBR04MIJ,F00001A20S,F0GBR04BJT,F000014J7J,F0000107Y9,F00001JXY3,F0GBR04BJV,F0GBR04BJW,F00000V7UX,F0GBR0615O,F00000V3RT,F000000GL3,F0GBR05V6L,F0GBR04PNW,F00000GV7A,F00000J4K6,F0GBR04PQE,F0GBR04J6F,F0GBR05VZU,F0GBR0573C`
- **Batch 3** (20): `F0GBR04BKA,F0GBR05V6N,F0GBR05V6O,F0GBR04BKD,F00001S9LY,F0000005RW,F000000RDC,F00000SX9U,F00000PX01,F00000V3RV,F0GBR06GPA,F0000019PX,F000002OFK,F00000Q61W,F00000VS95,F0GBR06MRQ,F00000VS97,F000010BS5,F00001PPHE,F00000Z1O1`
- **Batch 4** (20): `F00000J75J,F00000SX9T,F0GBR054RM,F00000V3RW,F00000WS4W,F00000QE2F,F00000457U,F0GBR06CHZ,F0GBR04PO1,F00000WYW3,F00000XNAF,F00000UDVM,F00000JTWF,F0GBR06MS2,F000005NQW,F00000LYLZ,F00000YJ03,F00000GWV1,F00000WTMS,F00000OO26`
- **Batch 5** (18): `F0GBR04PO2,F00001HM9W,F00000XHX4,F000000JV9,F00000NCFL,F0GBR052VJ,F0GBR04GEX,F0000100W4,F0000100W2,F00000237E,F00000LIJ7,F0000157U7,F0GBR06U04,F0GBR06BC2,F000015J9F,F00000UPJY,F0GBR0612J,F00000Q61X`

## Ablauf
1. **Branch:** auf `claude/morningstar-fund-metrics-tool-yjpaJ` arbeiten.
2. **5 Abrufe:** Für jeden Batch `mcp__…__morningstar-data-tool` mit den 28
   Datenpunkt-IDs und den Investment-IDs des Batches aufrufen. Große Antworten
   werden automatisch in eine Datei gespeichert (Pfad steht in der Fehlermeldung
   „Output has been saved to …"). Kommt eine Antwort ausnahmsweise inline (kleiner
   Batch), den Batch in zwei Hälften erneut abrufen, damit er in einer Datei landet
   – oder die Werte einmalig kompakt selbst schreiben.
3. **Parsen** (überschreibt die Rohdateien):
   ```bash
   python3 parse_tool_result2.py "<gespeicherte_datei_batch1>" data/raw2/metrics/b01.json
   python3 parse_tool_result2.py "<gespeicherte_datei_batch2>" data/raw2/metrics/b02.json
   python3 parse_tool_result2.py "<gespeicherte_datei_batch3>" data/raw2/metrics/b03.json
   python3 parse_tool_result2.py "<gespeicherte_datei_batch4>" data/raw2/metrics/b04.json
   python3 parse_tool_result2.py "<gespeicherte_datei_batch5>" data/raw2/metrics/b05.json
   ```
4. **Neu bauen & prüfen:**
   ```bash
   python3 build_dataset2.py && python3 build_webapp2.py
   ```
   `build_dataset2.py` setzt `as_of` automatisch auf das heutige Datum.
5. **Commit & Push** auf den Feature-Branch. GitHub Pages liefert App 2 unter
   `/app2/` aus dem Default-Branch-Root automatisch neu aus
   (https://johannesmerkl1982-dotcom.github.io/Johannes1/app2/).

## Wichtig
- **App 1 nicht anfassen** (eigene Dateien: `build_dataset.py`, `build_webapp.py`,
  `data/funds.json`, `webapp/`, Root-`index.html`).
- Neue/alte Wertpapiere: in `data/raw2/universe.json` ergänzen/entfernen
  (ISIN→ID via `morningstar-id-lookup-tool`), dann ab Schritt 2.
- 14 ISINs sind in Morningstar nicht auffindbar (siehe `not_found` in
  `universe.json`); diese fehlen bewusst.
