#!/usr/bin/env python3
"""
WM-2026-Tippspiel EV-Optimierer
================================
Berechnet den erwarteten Punktwert (EV) fuer jeden moeglichen Tipp
auf Basis von Buchmacher-Correct-Score-Quoten (The Odds API).

Punkteregeln (disjunkte Schalen, hoechste zutreffende gewinnt):
  4 Punkte: exakt richtiges Ergebnis
  3 Punkte: richtige Tordifferenz UND richtige Tendenz, aber nicht exakt
  2 Punkte: richtige Tendenz, aber falsche Tordifferenz
  0 Punkte: falsche Tendenz

Wichtig bei Remis-Tipps: Tendenz=Unentschieden impliziert Tordifferenz=0,
daher existiert die 2-Punkte-Schale fuer Remis-Tipps strukturell nicht
(nur 4, 3 oder 0 erreichbar). Das ergibt sich automatisch aus den
disjunkten Schalen ohne Sonderbehandlung.

Datenquelle: The Odds API (https://api.the-odds-api.com/v4)
API-Key via Umgebungsvariable ODDS_API_KEY.

Fallback: Wenn Correct-Score-Markt nicht verfuegbar, Poisson-Modell
aus h2h-Quoten + Over/Under-Linie.
"""

import argparse
import math
import os
import statistics
import sys
from typing import Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

API_BASE = "https://api.the-odds-api.com/v4"
OVERROUND_WARN_THRESHOLD = 1.30  # > 30% Marge -> Warnung


# ===========================================================================
# KERLOGIK: Punkte und EV
# ===========================================================================

def tendency(home: int, away: int) -> str:
    """H = Heimsieg, A = Auswaertssieg, U = Unentschieden."""
    if home > away:
        return "H"
    if away > home:
        return "A"
    return "U"


def score_points(tip: Tuple[int, int], result: Tuple[int, int]) -> int:
    """
    Berechnet die Punkte fuer (tip, result).

    Schalen sind disjunkt; hoehere Stufe hat Vorrang:
      4  exakt
      3  gleiche Tordifferenz UND gleiche Tendenz, nicht exakt
      2  gleiche Tendenz, andere Tordifferenz
      0  falsche Tendenz

    Konsequenz fuer Remis: tend(U) <=> diff=0, deshalb fuer Remis-Tipps
    niemals die 2-Punkte-Schale erreichbar — ergibt sich hier ohne
    Sonderfall automatisch aus der Disjunktheitsbedingung.
    """
    tip_h, tip_a = tip
    res_h, res_a = result

    tip_tend = tendency(tip_h, tip_a)
    tip_diff = tip_h - tip_a  # vorzeichenbehaftet

    res_tend = tendency(res_h, res_a)
    res_diff = res_h - res_a

    if tip == result:
        return 4
    if res_diff == tip_diff and res_tend == tip_tend:
        return 3
    if res_tend == tip_tend:
        return 2
    return 0


def compute_ev(
    tip: Tuple[int, int],
    probs: Dict[Tuple[int, int], float],
) -> Dict[str, float]:
    """
    EV(tip) = sum_r punkte(tip, r) * P(r).

    Gibt zusaetzlich die anteiligen Wahrscheinlichkeiten je Schale zurueck.
    """
    ev = p4 = p3 = p2 = p0 = 0.0
    for result, prob in probs.items():
        pts = score_points(tip, result)
        ev += pts * prob
        if pts == 4:
            p4 += prob
        elif pts == 3:
            p3 += prob
        elif pts == 2:
            p2 += prob
        else:
            p0 += prob
    return {"ev": ev, "p4": p4, "p3": p3, "p2": p2, "p0": p0}


def normalize_probs(
    raw_odds: Dict[Tuple[int, int], float],
) -> Tuple[Dict[Tuple[int, int], float], float]:
    """
    Margenbereinigung:
      p_raw(r) = 1 / quote(r)
      overround = sum(p_raw)
      p(r)     = p_raw(r) / overround  =>  sum(p) = 1

    Gibt (normierte_Probs, overround) zurueck.
    """
    p_raw = {r: 1.0 / o for r, o in raw_odds.items()}
    overround = sum(p_raw.values())
    p_norm = {r: p / overround for r, p in p_raw.items()}
    return p_norm, overround


# ===========================================================================
# SELBSTTEST
# ===========================================================================

SELF_TEST_ODDS: Dict[Tuple[int, int], float] = {
    (1, 0): 8.50,   (2, 0): 12.50,  (2, 1): 10.00,  (3, 0): 27.00,
    (3, 1): 21.00,  (3, 2): 30.00,  (4, 0): 75.00,  (4, 1): 65.00,
    (4, 2): 95.00,  (4, 3): 175.00, (5, 0): 250.00, (5, 1): 200.00,
    (5, 2): 300.00, (5, 3): 700.00, (6, 0): 1250.00, (6, 1): 900.00,
    (6, 2): 501.00, (7, 0): 125.00, (7, 1): 125.00,
    (0, 0): 11.00,  (1, 1): 6.00,   (2, 2): 13.50,  (3, 3): 65.00,
    (4, 4): 500.00,
    (0, 1): 11.00,  (0, 2): 19.50,  (1, 2): 13.00,  (0, 3): 50.00,
    (1, 3): 32.00,  (2, 3): 41.00,  (0, 4): 175.00, (1, 4): 110.00,
    (2, 4): 120.00, (3, 4): 250.00, (0, 5): 800.00, (1, 5): 500.00,
    (2, 5): 600.00, (3, 5): 1000.00, (0, 6): 150.00, (1, 6): 125.00,
    (2, 6): 125.00, (1, 7): 125.00,
}


def run_self_test() -> bool:
    """
    Prueft die EV-Kernlogik mit den fest verdrahteten Beispielquoten.

    Erwartetes Ergebnis:
      1. 1:0  EV ~1.13  (Top-Tipp)
      2. 2:1  EV ~1.12  (2. Platz)
      Remis 1:1 nur EV ~1.01 trotz hoechster Einzelquote 6.00.
    """
    print("=" * 62)
    print("SELBSTTEST")
    print("=" * 62)

    probs, overround = normalize_probs(SELF_TEST_ODDS)
    marge = (overround - 1) * 100

    print(f"\nOverround: {overround:.4f}  |  Marge: {marge:.1f}%")
    print(f"Anzahl Ergebnisse: {len(SELF_TEST_ODDS)}")
    print(f"Prob-Summe nach Normierung: {sum(probs.values()):.6f}  (soll 1.000000)")

    # EV fuer alle Tipps
    results = []
    for tip in SELF_TEST_ODDS:
        d = compute_ev(tip, probs)
        results.append((tip, d["ev"], d["p4"], d["p3"], d["p2"]))
    results.sort(key=lambda x: x[1], reverse=True)

    print("\nTop-5 Tipps:")
    print(f"  {'Tipp':<7} {'EV':>7} {'P(exakt)':>9} {'P(diff+tend)':>13} {'P(tend)':>8}")
    print("  " + "-" * 48)
    for tip, ev, p4, p3, p2 in results[:5]:
        print(f"  {tip[0]}:{tip[1]:<4} {ev:>7.4f} {p4:>9.4f} {p3:>13.4f} {p2:>8.4f}")

    # Lookup spezifischer Tipps
    def ev_of(t):
        return next(ev for tip, ev, *_ in results if tip == t)

    ev_10 = ev_of((1, 0))
    ev_21 = ev_of((2, 1))
    ev_11 = ev_of((1, 1))

    top1_tip = results[0][0]
    top2_tip = results[1][0]

    # Pruefe: kein 2-Punkte-Fall bei Remis-Tipps (strukturelle Eigenschaft)
    draw_tips = [r for r in SELF_TEST_ODDS if r[0] == r[1]]
    draw_has_no_2pts = True
    for tip in draw_tips:
        for result, prob in probs.items():
            if prob > 0 and score_points(tip, result) == 2:
                draw_has_no_2pts = False
                break

    print(f"\nEinzelpruefungen:")
    checks = [
        ("1:0 ist Top-Tipp (Platz 1)", top1_tip == (1, 0), f"ist {top1_tip[0]}:{top1_tip[1]}"),
        ("2:1 ist 2. Tipp  (Platz 2)", top2_tip == (2, 1), f"ist {top2_tip[0]}:{top2_tip[1]}"),
        ("EV(1:0) ∈ [1.08, 1.18]",     1.08 <= ev_10 <= 1.18, f"EV={ev_10:.4f}"),
        ("EV(2:1) ∈ [1.07, 1.17]",     1.07 <= ev_21 <= 1.17, f"EV={ev_21:.4f}"),
        ("EV(1:1) ∈ [0.95, 1.07]",     0.95 <= ev_11 <= 1.07, f"EV={ev_11:.4f}"),
        ("Kein 2-Punkte bei Remis-Tipps", draw_has_no_2pts, ""),
    ]
    all_ok = True
    for desc, ok, detail in checks:
        status = "OK  " if ok else "FEHLER"
        suffix = f"  ({detail})" if detail else ""
        print(f"  [{status}] {desc}{suffix}")
        all_ok = all_ok and ok

    print()
    if all_ok:
        print("SELBSTTEST BESTANDEN")
    else:
        print("SELBSTTEST FEHLGESCHLAGEN")
    print("=" * 62)
    return all_ok


# ===========================================================================
# THE ODDS API: Hilfsfunktionen
# ===========================================================================

def get_api_key() -> str:
    key = os.environ.get("ODDS_API_KEY", "")
    if not key:
        print("FEHLER: Umgebungsvariable ODDS_API_KEY nicht gesetzt.")
        print("  Beispiel:  export ODDS_API_KEY=dein_api_key")
        sys.exit(1)
    return key


def _get(url: str, params: dict, timeout: int = 15) -> dict | list:
    """HTTP-GET mit einheitlichem Fehlerhandling."""
    try:
        resp = requests.get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        print(f"NETZWERKFEHLER: {exc}")
        sys.exit(1)

    if resp.status_code == 401:
        print("FEHLER: Ungueltige API-Key (401 Unauthorized).")
        sys.exit(1)
    if resp.status_code == 429:
        remaining = resp.headers.get("x-requests-remaining", "?")
        print(f"FEHLER: API Rate-Limit erreicht (429). Verbleibende Anfragen: {remaining}")
        sys.exit(1)
    if not resp.ok:
        print(f"FEHLER: HTTP {resp.status_code} — {resp.text[:200]}")
        sys.exit(1)

    return resp.json()


def find_wm_sport_key(api_key: str) -> Optional[str]:
    """
    Sucht den korrekten Sport-Key fuer die FIFA WM 2026 ueber /v4/sports/.
    Ratet NICHT — verifiziert anhand der echten API-Antwort.
    """
    sports = _get(f"{API_BASE}/sports/", {"apiKey": api_key})
    wm_sports = [s for s in sports if "world_cup" in s.get("key", "").lower()]

    if not wm_sports:
        print("Kein WM-Sport in der API gefunden.")
        soccer = [s for s in sports if "soccer" in s.get("key", "").lower()]
        if soccer:
            print("Alle Soccer-Sportarten:")
            for s in soccer:
                print(f"  {s['key']}: {s.get('title', '')}")
        return None

    # Bevorzuge aktive Eintraege
    active = [s for s in wm_sports if s.get("active", False)]
    return (active or wm_sports)[0]["key"]


def get_games(api_key: str, sport_key: str) -> List[dict]:
    """Holt alle anstehenden Spiele (nur h2h fuer minimalen API-Verbrauch)."""
    return _get(
        f"{API_BASE}/sports/{sport_key}/odds/",
        {
            "apiKey": api_key,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal",
        },
    )


def get_game_odds(
    api_key: str, sport_key: str, game_id: str, markets: List[str]
) -> dict:
    """Holt Quoten fuer ein einzelnes Spiel; mehrere Maerkte in einer Anfrage."""
    data = _get(
        f"{API_BASE}/sports/{sport_key}/odds/",
        {
            "apiKey": api_key,
            "regions": "eu",
            "markets": ",".join(markets),
            "oddsFormat": "decimal",
            "eventIds": game_id,
        },
    )
    return data[0] if data else {}


# ===========================================================================
# CORRECT-SCORE-PARSING
# ===========================================================================

def parse_score_string(s: str) -> Optional[Tuple[int, int]]:
    """
    Parst Score-Strings aus The Odds API in (home, away).
    Unterstuetzte Formate: '1:0', '1-0', '1–0', 'Home 1-0', 'Draw 1:1' etc.
    """
    import re
    s = s.strip()
    s = re.sub(r"(?i)^(home|away|draw)\s+", "", s)
    m = re.search(r"(\d+)\s*[:\-–]\s*(\d+)", s)
    return (int(m.group(1)), int(m.group(2))) if m else None


def parse_correct_score_market(
    game_data: dict,
) -> Optional[Dict[Tuple[int, int], float]]:
    """
    Extrahiert Correct-Score-Quoten aus allen Bookies.
    Bei mehreren Bookies: Median der Quoten pro Ergebnis (robuster gegen Ausreisser).
    Returns None wenn der Markt nicht vorhanden ist.
    """
    all_prices: Dict[Tuple[int, int], List[float]] = {}

    for bookie in game_data.get("bookmakers", []):
        for market in bookie.get("markets", []):
            if market.get("key") != "correct_score":
                continue
            for outcome in market.get("outcomes", []):
                score = parse_score_string(outcome.get("name", ""))
                price = float(outcome.get("price", 0))
                if score is not None and price > 1.0:
                    all_prices.setdefault(score, []).append(price)

    if not all_prices:
        return None

    # Median je Ergebnis
    return {r: statistics.median(prices) for r, prices in all_prices.items()}


def list_available_markets(game_data: dict) -> List[str]:
    markets: set = set()
    for bookie in game_data.get("bookmakers", []):
        for market in bookie.get("markets", []):
            markets.add(market.get("key", ""))
    return sorted(markets)


# ===========================================================================
# POISSON-FALLBACK
# ===========================================================================

def parse_h2h_probs(game_data: dict) -> Optional[Tuple[float, float, float]]:
    """
    Extrahiert 1X2-Quoten und gibt margenbereingte (p_home, p_draw, p_away) zurueck.
    """
    home_name = game_data.get("home_team", "")
    away_name = game_data.get("away_team", "")
    raw: Dict[str, List[float]] = {"home": [], "draw": [], "away": []}

    for bookie in game_data.get("bookmakers", []):
        for market in bookie.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                name = outcome.get("name", "")
                price = float(outcome.get("price", 0))
                if price <= 1.0:
                    continue
                if name == home_name:
                    raw["home"].append(price)
                elif name == away_name:
                    raw["away"].append(price)
                else:  # Draw / Unentschieden
                    raw["draw"].append(price)

    if not raw["home"] or not raw["away"]:
        return None

    o_home = statistics.median(raw["home"])
    o_draw = statistics.median(raw["draw"]) if raw["draw"] else 0.0
    o_away = statistics.median(raw["away"])

    p_h = 1.0 / o_home
    p_d = (1.0 / o_draw) if o_draw > 0 else 0.0
    p_a = 1.0 / o_away
    total = p_h + p_d + p_a
    return p_h / total, p_d / total, p_a / total


def parse_totals_line(game_data: dict) -> Optional[float]:
    """Extrahiert die Over/Under-Linie als Proxy fuer erwartete Gesamttore."""
    lines: List[float] = []
    for bookie in game_data.get("bookmakers", []):
        for market in bookie.get("markets", []):
            if market.get("key") != "totals":
                continue
            for outcome in market.get("outcomes", []):
                pt = outcome.get("point")
                if pt is not None:
                    lines.append(float(pt))
    return statistics.median(lines) if lines else None


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def build_poisson_probs(
    lambda_home: float, lambda_away: float, max_goals: int = 7
) -> Dict[Tuple[int, int], float]:
    """
    Baut eine Wahrscheinlichkeitsverteilung ueber alle (h, a) mit
    h, a in [0, max_goals] via zwei unabhaengige Poisson-Verteilungen.
    Normiert auf 1 (restliche Wahrscheinlichkeit wird gleichmaessig verteilt).
    """
    probs: Dict[Tuple[int, int], float] = {}
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            probs[(h, a)] = _poisson_pmf(h, lambda_home) * _poisson_pmf(a, lambda_away)
    total = sum(probs.values())
    return {r: p / total for r, p in probs.items()}


def lambdas_from_probs_and_total(
    p_home: float, p_away: float, total_goals: float
) -> Tuple[float, float]:
    """
    Leitet (lambda_home, lambda_away) aus Quoten-Tendenzprobs und Total ab.

    Annahme: lambda_home / lambda_away approximiert P(Heimsieg) / P(Auswaertssieg)
    (direkter Odds-Proxy fuer Staerkeratio), kombiniert mit der Nebenbedingung
    lambda_home + lambda_away = total_goals.
    """
    ratio = (p_home / p_away) if p_away > 0 else 1.0
    lambda_away = total_goals / (1.0 + ratio)
    lambda_home = total_goals - lambda_away
    return max(0.3, lambda_home), max(0.3, lambda_away)  # Minimum 0.3 sinnvoll


# ===========================================================================
# AUSGABE
# ===========================================================================

def _format_time(iso: str) -> str:
    """Wandelt ISO-8601-String in lesbare lokale Zeit (UTC) um."""
    return iso.replace("T", "  ").replace("Z", " UTC") if iso else "?"


def print_ev_table(
    game_data: dict,
    probs: Dict[Tuple[int, int], float],
    overround: float,
    top_n: int,
    mode: str = "correct_score",
) -> None:
    """Druckt die vollstaendige EV-Auswertung fuer ein Spiel."""
    home = game_data.get("home_team", "Heim")
    away = game_data.get("away_team", "Auswaerts")
    start = _format_time(game_data.get("commence_time", ""))

    print()
    print("=" * 66)
    print(f"  {home}  vs  {away}")
    print(f"  Anstoss: {start}")
    if mode == "poisson":
        print("  [MODELLBASIERT — Poisson-Fallback, NICHT aus Correct-Score-Quoten]")
    print("=" * 66)

    if mode == "correct_score":
        marge_pct = (overround - 1) * 100
        print(f"\n  Overround: {overround:.4f}  |  Marge: {marge_pct:.1f}%")
        if overround > OVERROUND_WARN_THRESHOLD:
            print()
            print("  *** WARNUNG: Marge > 30%! ***")
            print("  Buchmacher hinterlegen oft Platzhalter-Quoten fuer")
            print("  unwahrscheinliche Ergebnisse. EV-Absolutwerte sind")
            print("  unzuverlaessig; die RANGFOLGE bleibt meist brauchbar.")

    # Tendenzmasse aus normierten Probs
    p_h = sum(p for (h, a), p in probs.items() if h > a)
    p_d = sum(p for (h, a), p in probs.items() if h == a)
    p_a = sum(p for (h, a), p in probs.items() if a > h)
    print(f"\n  Tendenzen:  P(Heimsieg)={p_h:.1%}   P(Remis)={p_d:.1%}   P(Auswaerts)={p_a:.1%}")

    # EV fuer alle Kandidaten-Tipps
    ev_rows = []
    for tip in probs:
        d = compute_ev(tip, probs)
        p_exact = probs.get(tip, 0.0)
        # Approximiere Rohquote aus normierten Probs + Overround
        approx_odds = (overround / p_exact) if p_exact > 0 else float("inf")
        ev_rows.append((tip, d["ev"], d["p4"], d["p3"], d["p2"], approx_odds))

    ev_rows.sort(key=lambda x: x[1], reverse=True)
    top = ev_rows[:top_n]

    print(f"\n  Top-{top_n} Tipps nach EV:\n")
    print(f"  {'Ergebnis':<10} {'EV':>7}  {'P(exakt)':>8}  {'P(diff)':>8}  {'P(tend)':>8}  {'Quote(~)':>9}")
    print("  " + "-" * 58)
    for tip, ev, p4, p3, p2, odds in top:
        print(
            f"  {tip[0]}:{tip[1]:<7} {ev:>7.4f}  {p4:>8.4f}  {p3:>8.4f}  {p2:>8.4f}  {odds:>9.1f}"
        )

    # Empfehlung
    best = top[0]
    print(f"\n  >>> EMPFEHLUNG: {best[0][0]}:{best[0][1]}   (EV = {best[1]:.4f})")

    # Hinweis wenn Top-2 sehr nah beieinander und verschiedene Tordifferenz
    if len(top) >= 2:
        ev_gap = top[0][1] - top[1][1]
        diff0 = top[0][0][0] - top[0][0][1]
        diff1 = top[1][0][0] - top[1][0][1]
        if ev_gap < 0.05 and diff0 != diff1:
            print()
            print(
                f"  HINWEIS: {top[0][0][0]}:{top[0][0][1]} und {top[1][0][0]}:{top[1][0][1]} liegen"
                f" nur {ev_gap:.4f} EV-Punkte auseinander"
            )
            print(
                "  und haben verschiedene Tordifferenzen — Fussballwissen und WM-Historie"
            )
            print(
                "  heranziehen! (1:0 ist historisch der haeufigste WM-Ausgang, haeufiger als 2:1)"
            )

    print()


# ===========================================================================
# CLI-KOMMANDOS
# ===========================================================================

def cmd_list(api_key: str, sport_key: str) -> None:
    games = get_games(api_key, sport_key)
    if not games:
        print("Keine anstehenden Spiele gefunden.")
        return
    print(f"\nAnstehende WM-Spiele ({sport_key}) — {len(games)} Spiele:\n")
    for i, g in enumerate(games, 1):
        print(f"  {i:3}.  {g.get('home_team', '?')}  vs  {g.get('away_team', '?')}")
        print(f"        Anstoss: {_format_time(g.get('commence_time', ''))}")


def cmd_match(
    api_key: str, sport_key: str, query: str, top_n: int
) -> None:
    games = get_games(api_key, sport_key)
    q = query.lower()
    matches = [
        g for g in games
        if q in g.get("home_team", "").lower() or q in g.get("away_team", "").lower()
    ]

    if not matches:
        print(f"Kein Spiel gefunden fuer: '{query}'")
        print("\nVerfuegbare Spiele:")
        for g in games:
            print(f"  {g.get('home_team', '?')} vs {g.get('away_team', '?')}")
        return

    if len(matches) > 1:
        print(f"Mehrere Spiele fuer '{query}' gefunden — bitte Suche verfeinern:\n")
        for g in matches:
            print(f"  {g.get('home_team')} vs {g.get('away_team')}  ({g.get('commence_time')})")
        return

    game = matches[0]
    game_id = game["id"]
    print(
        f"\nLade Quoten fuer {game['home_team']} vs {game['away_team']} ..."
    )

    # Alle relevanten Maerkte in einer Anfrage (spart API-Quota)
    game_data = get_game_odds(
        api_key, sport_key, game_id, ["correct_score", "h2h", "totals"]
    )
    if not game_data:
        print("FEHLER: Keine Daten fuer dieses Spiel erhalten.")
        return

    cs_odds = parse_correct_score_market(game_data)

    if cs_odds:
        print(f"  Correct-Score-Markt gefunden ({len(cs_odds)} Ergebnisse, Median ueber Bookies).")
        probs, overround = normalize_probs(cs_odds)
        print_ev_table(game_data, probs, overround, top_n, mode="correct_score")
        return

    # --- Fallback: Poisson ---
    available = list_available_markets(game_data)
    print("  Correct-Score-Markt NICHT verfuegbar.")
    print(f"  Verfuegbare Maerkte: {', '.join(available) if available else 'keine'}")
    print()
    print("  Aktiviere Poisson-Fallback (modellbasiert) ...")

    h2h = parse_h2h_probs(game_data)
    if h2h is None:
        print("FEHLER: Keine 1X2-Quoten verfuegbar. Poisson-Fallback nicht moeglich.")
        return

    p_home, p_draw, p_away = h2h
    total = parse_totals_line(game_data)
    if total is None:
        total = 2.5
        print("  Kein Over/Under-Markt verfuegbar — setze Total = 2.5 Tore (Standard).")
    else:
        print(f"  Over/Under-Linie: {total} Tore")

    print(
        f"  1X2 (margenbereinigte Probs): "
        f"P(H)={p_home:.2%}  P(U)={p_draw:.2%}  P(A)={p_away:.2%}"
    )

    lh, la = lambdas_from_probs_and_total(p_home, p_away, total)
    print(f"  Poisson-Lambdas: λ_Heim={lh:.3f}  λ_Auswaerts={la:.3f}")

    probs = build_poisson_probs(lh, la)
    print_ev_table(game_data, probs, overround=1.0, top_n=top_n, mode="poisson")


# ===========================================================================
# EINSTIEGSPUNKT
# ===========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="WM-2026-Tippspiel EV-Optimierer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python wm_ev.py --list
  python wm_ev.py --match "Morocco"
  python wm_ev.py --match "Germany" --top 8
  python wm_ev.py --self-test
        """,
    )
    parser.add_argument("--list", action="store_true", help="Listet anstehende WM-Spiele")
    parser.add_argument("--match", metavar="TEAM", help="Team-Name (Teilstring) fuer Spielsuche")
    parser.add_argument("--top", type=int, default=5, metavar="N", help="Anzahl Top-Tipps (default: 5)")
    parser.add_argument("--self-test", action="store_true", help="Fuehrt eingebauten Selbsttest durch")

    args = parser.parse_args()

    if args.self_test:
        ok = run_self_test()
        sys.exit(0 if ok else 1)

    if not args.list and not args.match:
        parser.print_help()
        return

    api_key = get_api_key()

    print("Ermittle FIFA-WM-2026-Sport-Key ...")
    sport_key = find_wm_sport_key(api_key)
    if not sport_key:
        print("FEHLER: Kein WM-Sport in der API gefunden.")
        sys.exit(1)
    print(f"  Sport-Key: {sport_key}")

    if args.list:
        cmd_list(api_key, sport_key)
    elif args.match:
        cmd_match(api_key, sport_key, args.match, args.top)


if __name__ == "__main__":
    main()
