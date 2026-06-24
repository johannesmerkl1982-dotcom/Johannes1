# WM-2026-Tippspiel EV-Optimierer

Berechnet den erwarteten Punktwert (EV) fuer jeden moeglichen Tipp auf Basis
von Buchmacher-Quoten aus [The Odds API](https://the-odds-api.com/).

## Voraussetzungen

```bash
pip install requests
```

Python 3.9+ wird benoetigt.

## API-Key setzen

Kostenloser API-Key unter https://the-odds-api.com/ registrieren, dann:

```bash
export ODDS_API_KEY=dein_api_key_hier
```

Dauerhaft (z. B. in `~/.bashrc` oder `~/.zshrc`):
```bash
echo 'export ODDS_API_KEY=dein_api_key_hier' >> ~/.bashrc
```

## Benutzung

```bash
# Anstehende WM-Spiele auflisten
python wm_ev.py --list

# EV-Optimierung fuer ein Spiel (Team-Teilstring genuegt)
python wm_ev.py --match "Morocco"
python wm_ev.py --match "Germany"

# Top-8 statt Top-5 anzeigen
python wm_ev.py --match "Brazil" --top 8

# Eingebauten Selbsttest ausfuehren (kein API-Key noetig)
python wm_ev.py --self-test
```

## Punkteregeln

| Punkte | Bedingung |
|--------|-----------|
| **4** | Exakt richtiges Ergebnis |
| **3** | Richtige Tordifferenz + richtige Tendenz, aber nicht exakt |
| **2** | Richtige Tendenz (Sieger/Remis), aber falsche Tordifferenz |
| **0** | Falsche Tendenz |

**Remis-Tipps:** Bei einem getippten Unentschieden ist Tendenz=Remis identisch
mit Tordifferenz=0. Deshalb gibt es fuer Remis-Tipps keine 2-Punkte-Stufe
(nur 4, 3 oder 0 erreichbar). Das Tool bildet das korrekt ab.

## Datenquelle und Markt-Verfuegbarkeit

Das Tool versucht zuerst den `correct_score`-Markt. Ob dieser auf dem eigenen
API-Tier verfuegbar ist, haengt vom Abonnement ab — kostenlose Tiers bieten
oft nur `h2h`, `spreads` und `totals`.

### Pfad A: Correct-Score verfuegbar

- Quoten werden aus allen verfuegbaren Bookies geladen
- Bei mehreren Bookies: **Median der Quoten** pro Ergebnis (robust gegen Ausreisser)
- Margenbereinigung: `p(r) = (1/quote(r)) / Overround`
- EV-Berechnung ueber alle angebotenen Ergebnisse
- Ausgabe: Overround/Marge, Tendenzmasse, Top-N-Tabelle, Empfehlung

### Pfad B: Poisson-Fallback (wenn Correct Score nicht verfuegbar)

Das Tool wechselt automatisch in den Modell-Modus:
1. Laedt `h2h`-Quoten → berechnet margenbereingte P(Heim), P(Remis), P(Auswaerts)
2. Laedt `totals`-Linie → erwartete Gesamttore λ_H + λ_A
3. Leitet Einzellambdas ab: Ratio P(Heimsieg)/P(Auswaerts) als Proxy fuer
   λ_H / λ_A, Summe = Totals-Linie
4. Berechnet alle Ergebniswahrscheinlichkeiten via unabhaengige Poisson-Verteilungen

**Ausgabe ist klar als "MODELLBASIERT" gekennzeichnet.**

### Auf echten Correct-Score-Pfad umschalten

Wenn du spaeter auf einen hoeheren API-Tier upgradesd, ist nichts zu aendern —
das Tool prueft bei jedem Aufruf, ob `correct_score` vorhanden ist, und benutzt
ihn automatisch.

## Overround-Warnung

Liegt der Overround ueber 30 % (haeufig bei seltenen Ergebnissen mit
Platzhalterquoten), gibt das Tool eine deutliche Warnung aus:
- EV-Absolutwerte sind dann unzuverlaessig
- Die Rangfolge der Tipps bleibt meist brauchbar

## Selbsttest

```bash
python wm_ev.py --self-test
```

Prueft die EV-Kernlogik mit fest verdrahteten Beispielquoten:
- `1:0` ist Top-Tipp (EV ca. 1.13) vor `2:1` (EV ca. 1.12)
- `1:1` trotz guenstigster Einzelquote (6.00) nur EV ca. 1.01
- Keine 2-Punkte-Schale fuer Remis-Tipps (strukturelle Eigenschaft)

Wenn der Selbsttest gruen ist, ist die Kernlogik korrekt implementiert.
