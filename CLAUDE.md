# Projektnotizen für Claude

## Apps & Live-Deployment (WICHTIG)

Dieses Repo hostet mehrere statische Web-Apps über **GitHub Pages**. Pages wird aus
dem Branch **`gh-pages`** ausgeliefert (NICHT aus `main` — `main` ist nur ein leerer
Baseline-Commit). Jede App liegt in einem eigenen Unterordner = eigene URL:

| App | Ordner | Live-URL |
|-----|--------|----------|
| Union & Quoniam | `index.html` (root) | `https://johannesmerkl1982-dotcom.github.io/Johannes1/` |
| JoMe – Fonds & ETF | `jome/` | `https://johannesmerkl1982-dotcom.github.io/Johannes1/jome/` |
| SAA-Optimierungsmodell | `saa/` | `https://johannesmerkl1982-dotcom.github.io/Johannes1/saa/` |

### So macht man eine App live (bewährter Ablauf)
1. Quellcode auf dem Arbeits-/Feature-Branch bearbeiten und committen.
2. Auf den Live-Branch wechseln und **nur** den betroffenen App-Ordner übernehmen
   (die anderen Apps NICHT anfassen):
   ```bash
   git fetch origin gh-pages
   git checkout -B gh-pages origin/gh-pages
   git checkout <feature-branch> -- saa/index.html   # nur diesen Ordner
   git commit -m "Deploy ... nach gh-pages (/saa/)"
   git push origin gh-pages
   ```
3. GitHub baut automatisch (Workflow „pages build and deployment"). Status prüfbar via
   GitHub-MCP `actions_list` (Filter branch=gh-pages) → muss „completed/success" für
   den neuen Commit-SHA zeigen.

### Link-/404-Lektion (NICHT vergessen!)
- Aus der Remote-Sandbox sind `*.github.io`-URLs **nicht erreichbar** (alle Pfade geben
  403 zurück, auch funktionierende Apps). **Live-Status NIE aus der Sandbox per curl
  „bestätigen"** — das geht nicht. Stattdessen verifizieren über: (a) Datei liegt auf
  `gh-pages`, (b) Pages-Build-Workflow „success" für den Commit.
- Dem Nutzer **keinen Link als „live" versprechen**, bevor der Pages-Build durch ist.
- Ein **404 direkt nach dem Deploy ist meist Browser-/CDN-Cache** (URL wurde aufgerufen,
  bevor der Build fertig war). Fix: URL mit Cache-Buster `?neu=1` oder Inkognito-Tab.
  Schreibweise ist case-sensitive (großes `J` in `Johannes1`, kleines `saa`).

## SAA-Optimierungsmodell (`saa/index.html`)

Bildet das Excel-Modell „Modernes Optimierungsmodell SAA V2" 1:1 im Browser ab.
Eigenständige Single-File-HTML-App (kein Build, kein Server).

- **Zielfunktion:** erwartete Rendite maximieren (refined arithmetic mean / 100).
- **Nebenbedingungen:** Σ Gewichte = 1; CVaR ≤ Ziel; quadr. Abweichung von der
  Risk-Parity-Benchmark ≤ Regularisierungsparameter; RTF-/RWA-/Illiquiditäts-Obergrenze;
  LCR-HQLA (1a/1b, 2a, 2b mit 60 %/15 %); Min/Max je Assetklasse.
- **CVaR-Formel:** `√(wᵀΣw) · ((wᵀ(CVaR-Cutoff+μ)/wᵀσ)·Tail-Dämpfung) − E[r]`.
- **Benchmark:** inverse Vola, Liquiditätsanteil = Ist-Liquidität/Volumen.
- **Solver (im Browser):** Augmented Lagrangian + Simplex-Projektion, zentrale Differenzen,
  **100 Multistart-Punkte** (asynchron mit Fortschrittsanzeige, harte Zeitobergrenze ~22 s).
  Reproduziert die Excel-Lösung (E[r]≈4,42 %, CVaR=0,10, reg=0,05).
- **Auto-Lockerung der Regularisierung:** Ist beim vom Nutzer gesetzten Reg-Parameter wegen
  anderer Nebenbedingungen (z. B. max. RWA) keine Lösung möglich, wird der Parameter
  automatisch **so wenig wie nötig** erhöht (geometrisch + Bisektion auf das Minimum). Eine
  Lösung scheitert nur, wenn CVaR + übrige Bedingungen selbst ohne Reg-Bindung unvereinbar
  sind (dann feasible=false, ehrliche Meldung). Günstige Proben (`BUD_FAST`) für die Suche,
  genau EINE teure 100-Start-Lösung (`BUD_STRICT`) am Ende.
- **NaN-Schutz:** `cvar()` fängt Division durch ~0 ab (große endliche Strafe statt NaN),
  sonst degenerieren Gewichte (Σ≠1) und der Solver hängt. Bei Solver-Änderungen IMMER
  mit extremem CVaR-Ziel (z. B. 0,5 %) gegentesten.
- **Eingabe-Einheiten:** „Zielwert CVaR" und „Maximaler Anteil illiquider Assetklassen"
  werden in **% eingegeben** (intern ÷100). Übrige Min/Max je Klasse sind Anteile 0–1.
- Modellkonstanten (Mittelwerte, Std-Abw., CVaR-Cutoffs, Korrelationsmatrix, RTF-/RWA-
  Gewichte, LCR-Einstufung, Illiquiditäts-Flags) sind im `<script>` fest hinterlegt und
  entsprechen exakt dem Excel.

### Verifikation bei Änderungen
JS-Kern in Node testen (Excel-Referenzlösung muss reproduziert werden):
```bash
node -e 'const fs=require("fs");let h=fs.readFileSync("saa/index.html","utf8");
let js=h.split("<script>")[1].split("</script>")[0].split("/* ===================== UI")[0];
js+="\nmodule.exports={optimize,benchmarkWeights,expReturn,cvar,regDev,NAMES};";
fs.writeFileSync("/tmp/core.js",js);const M=require("/tmp/core.js");/* ... */'
```
Referenz (Standardeingaben): E1=0.044242, CVaR=0.100000, reg=0.050000, und Gewichte
≈ [0.1862, 0.0089, 0.0975, 0, 0.1295, 0.1089, 0.1482, 0.3208].
