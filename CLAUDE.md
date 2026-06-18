# Johannes1 – Projektdokumentation für Claude Code

## GitHub Pages – Live-URLs

Die Apps sind unter diesen URLs erreichbar (vom Deployment-Log bestätigt):

| App | URL |
|-----|-----|
| Start (Fondsübersicht) | https://johannesmerkl1982-dotcom.github.io/Johannes1/ |
| SAA (Asset Allocation) | https://johannesmerkl1982-dotcom.github.io/Johannes1/saa/ |
| JOME (Fonds & ETFs) | https://johannesmerkl1982-dotcom.github.io/Johannes1/jome/ |
| Longevity Supplements | https://johannesmerkl1982-dotcom.github.io/Johannes1/longevity/ |
| Webapp | https://johannesmerkl1982-dotcom.github.io/Johannes1/webapp/ |

**GitHub-Account:** `johannesmerkl1982-dotcom`
**Repository:** `Johannes1`
**Pages-Branch:** `gh-pages`

## Deployment-Regeln (IMMER einhalten)

1. **Feature-Branch** → Entwicklung auf `claude/<feature>` branches
2. **Deploy** → Nur `longevity/index.html` (oder den jeweiligen Ordner) von Feature-Branch nach `gh-pages` übernehmen:
   ```bash
   git checkout gh-pages
   git checkout <feature-branch> -- <ordner>/index.html
   git commit -m "Deploy ..."
   git push origin gh-pages
   ```
3. **`.nojekyll` muss auf gh-pages vorhanden sein** – ohne diese Datei verarbeitet Jekyll die HTML-Dateien und kann `{%`-ähnliche Muster in JavaScript-Code als Template-Tags interpretieren und Seiten beschädigen oder leer ausliefern. **Nie löschen!**
4. **Build-Status prüfen** via GitHub Actions → `pages build and deployment` workflow

## Bekannte Probleme

### 404-Fehler nach Deployment
- Ursache war historisch: fehlende `.nojekyll`-Datei (Jekyll verarbeitete HTML)
- Fix: `.nojekyll` auf `gh-pages` branch (bereits vorhanden seit 2026-06-18)
- Die korrekte URL ist **immer** `https://johannesmerkl1982-dotcom.github.io/Johannes1/<app>/`
- Nach dem Push 1–2 Minuten warten bis GitHub Actions durch ist

## Projektstruktur

```
gh-pages/
├── .nojekyll          ← Jekyll deaktivieren (PFLICHT)
├── index.html         ← Hauptseite / Fondsübersicht
├── saa/index.html     ← Strategic Asset Allocation Tool
├── jome/index.html    ← Fonds & ETF Übersicht
├── longevity/index.html ← CFS & Longevity Supplement-Protokoll
└── webapp/index.html  ← Webapp

main (default branch: claude/morningstar-fund-metrics-tool-yjpaJ):
├── data/              ← Fondsdaten (JSON)
├── build_dataset.py   ← Morningstar-Datenabruf App 1
├── build_dataset2.py  ← Morningstar-Datenabruf App 2
└── ...
```

## App-Spezifika

### SAA (saa/index.html)
- Strategic Asset Allocation Optimizer
- Keine externen Dependencies

### JOME (jome/index.html)  
- Fonds & ETF Vergleichstool
- Daten aus `data/funds2.json`

### Longevity (longevity/index.html)
- CFS & Longevity Supplement-Protokoll
- 27 Supplements, filterbar nach 8 Gesundheitszielen
- Keine externen Dependencies
