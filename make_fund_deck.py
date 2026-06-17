#!/usr/bin/env python3
"""Erzeugt aus data/funds3.json eine professionelle PowerPoint-Praesentation:
Gliederung aller Fonds in grobe Anlageklassen (Aktien, Renten, Rohstoffe ...)
und je Klasse ein fundierter Vergleich (Ranglisten-Tabellen + Risiko-Rendite-
Streudiagramm) sowie ein Kompaktprofil je Fonds (Stammdaten, Ratings, Rendite-
und Risikokennzahlen, optional Portfolio-Zusammensetzung aus der Morningstar-
X-Ray-Analyse).

Aufruf:  python3 make_fund_deck.py [--data data/funds3.json] [--out /tmp/deck.pptx]

Benoetigt: python-pptx  (pip install python-pptx)
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime

try:
    from pptx import Presentation
    from pptx.util import Pt, Inches, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.chart.data import CategoryChartData, XyChartData
    from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
except ImportError:
    sys.exit("python-pptx fehlt. Installation: pip install python-pptx")

# ---- Farbschema (professionell, dezent) -----------------------------------
NAVY   = RGBColor(0x14, 0x2A, 0x4A)   # Dunkelblau (Primaer)
ACCENT = RGBColor(0xC8, 0x10, 0x2E)   # Rot-Akzent (Union)
SLATE  = RGBColor(0x44, 0x52, 0x66)   # Grau-Blau
LIGHT  = RGBColor(0xF2, 0xF4, 0xF7)   # heller Tabellenhintergrund
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
INK    = RGBColor(0x22, 0x28, 0x33)   # Text
MUTED  = RGBColor(0x7A, 0x84, 0x92)
GOOD   = RGBColor(0x1E, 0x7A, 0x3C)
BAD    = RGBColor(0xB3, 0x26, 0x1E)

CLASS_ACCENT = {
    "Aktien": RGBColor(0x1F, 0x4E, 0x79),
    "Renten": RGBColor(0x2E, 0x6B, 0x4F),
    "Wandelanleihen": RGBColor(0x6B, 0x4E, 0x8A),
    "Rohstoffe & Gold": RGBColor(0xB5, 0x7A, 0x1E),
    "Immobilien": RGBColor(0x8A, 0x4B, 0x2E),
    "Geldmarkt & Liquidität": RGBColor(0x37, 0x6B, 0x8A),
    "Mischfonds / Multi-Asset": RGBColor(0x55, 0x55, 0x55),
    "Sonstige": RGBColor(0x66, 0x66, 0x66),
}

EMU = 914400
SW, SH = 13.333, 7.5

# ---------------------------------------------------------------------------
# Formatierungs-Helfer
# ---------------------------------------------------------------------------
def de_num(v, dec=2):
    if v is None:
        return "–"
    try:
        s = f"{float(v):,.{dec}f}"
    except (TypeError, ValueError):
        return str(v)
    return s.replace(",", "§").replace(".", ",").replace("§", ".")

def pct(v, dec=1):
    return "–" if v is None else de_num(v, dec) + " %"

def stars(v):
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return "–"
    n = max(0, min(5, n))
    return "★" * n + "☆" * (5 - n)

def money_usd(v):
    if v is None:
        return "–"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "–"
    if x >= 1e9:
        return de_num(x / 1e9, 2) + " Mrd. USD"
    if x >= 1e6:
        return de_num(x / 1e6, 1) + " Mio. USD"
    return de_num(x, 0) + " USD"

def inc_date(v):
    if not v:
        return "–"
    s = str(v)[:10]
    try:
        d = datetime.strptime(s, "%Y-%m-%d")
        return d.strftime("%d.%m.%Y")
    except ValueError:
        return s

# ---------------------------------------------------------------------------
# Low-Level Slide-Helfer
# ---------------------------------------------------------------------------
def _set_fill(shape, color):
    shape.fill.solid(); shape.fill.fore_color.rgb = color
    shape.line.fill.background()

def add_rect(slide, x, y, w, h, color):
    from pptx.enum.shapes import MSO_SHAPE
    sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    _set_fill(sp, color)
    sp.shadow.inherit = False
    return sp

def add_text(slide, txt, x, y, w, h, size=14, bold=False, color=INK,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font="Calibri", italic=False,
             line_spacing=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Pt(2); tf.margin_top = tf.margin_bottom = Pt(1)
    lines = str(txt).split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line_spacing:
            p.line_spacing = line_spacing
        r = p.add_run(); r.text = ln
        f = r.font; f.size = Pt(size); f.bold = bold; f.italic = italic
        f.name = font; f.color.rgb = color
    return tb

def title_bar(slide, title, subtitle=None, accent=NAVY):
    add_rect(slide, 0, 0, SW, 1.0, accent)
    add_rect(slide, 0, 1.0, SW, 0.06, ACCENT)
    add_text(slide, title, 0.55, 0.12, SW - 3.0, 0.8, size=26, bold=True,
             color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    if subtitle:
        add_text(slide, subtitle, SW - 4.6, 0.12, 4.05, 0.8, size=12, color=RGBColor(0xCF, 0xD8, 0xE3),
                 align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)

def footer(slide, stichtag, page=None):
    add_text(slide, f"Datenquelle: Morningstar  ·  Stichtag {de_date(stichtag)}", 0.55, SH - 0.34,
             8.0, 0.3, size=8.5, color=MUTED)
    if page is not None:
        add_text(slide, str(page), SW - 1.0, SH - 0.34, 0.45, 0.3, size=8.5, color=MUTED,
                 align=PP_ALIGN.RIGHT)

def de_date(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        return str(s)

def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])

# ---------------------------------------------------------------------------
# Tabellen-Helfer
# ---------------------------------------------------------------------------
def add_table(slide, x, y, w, headers, rows, col_w, header_color=NAVY,
              font_size=10, header_size=10, row_h=0.30, header_h=0.34,
              align=None, cell_colors=None, zebra=True):
    """rows: Liste von Zeilen; jede Zelle ist str. align: Liste je Spalte.
    cell_colors: optional dict {(r,c): RGBColor} fuer Textfarbe."""
    nrows = len(rows) + 1
    ncols = len(headers)
    total_h = header_h + len(rows) * row_h
    gtbl = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(w), Inches(total_h))
    tbl = gtbl.table
    tbl.first_row = False; tbl.horz_banding = False
    for c, cw in enumerate(col_w):
        tbl.columns[c].width = Inches(cw)
    tbl.rows[0].height = Inches(header_h)
    for r in range(len(rows)):
        tbl.rows[r + 1].height = Inches(row_h)
    align = align or [PP_ALIGN.LEFT] * ncols
    # Header
    for c, htxt in enumerate(headers):
        cell = tbl.cell(0, c)
        cell.fill.solid(); cell.fill.fore_color.rgb = header_color
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = cell.margin_right = Pt(4)
        cell.margin_top = cell.margin_bottom = Pt(1)
        p = cell.text_frame.paragraphs[0]; p.alignment = align[c]
        r = p.add_run(); r.text = htxt
        r.font.size = Pt(header_size); r.font.bold = True; r.font.color.rgb = WHITE
        r.font.name = "Calibri"
    # Body
    for ri, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = tbl.cell(ri + 1, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = LIGHT if (zebra and ri % 2 == 1) else WHITE
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = Pt(4)
            cell.margin_top = cell.margin_bottom = Pt(1)
            p = cell.text_frame.paragraphs[0]; p.alignment = align[c]
            run = p.add_run(); run.text = str(val)
            run.font.size = Pt(font_size); run.font.name = "Calibri"
            run.font.color.rgb = (cell_colors or {}).get((ri, c), INK)
    return gtbl

# ---------------------------------------------------------------------------
# Slides
# ---------------------------------------------------------------------------
def slide_title(prs, meta):
    s = blank(prs)
    add_rect(s, 0, 0, SW, SH, NAVY)
    add_rect(s, 0, 4.05, SW, 0.07, ACCENT)
    add_text(s, "Fonds-Analyse & Vergleich", 0.9, 2.4, 11.5, 1.2, size=46, bold=True, color=WHITE)
    add_text(s, "Systematische Auswertung des Fondsuniversums auf Basis von Morningstar",
             0.9, 3.45, 11.5, 0.6, size=18, color=RGBColor(0xC8, 0xD3, 0xE0))
    n = meta["fund_count"]
    classes = ", ".join(f"{k} ({v})" for k, v in meta["by_class"].items())
    add_text(s, f"Stichtag: {de_date(meta['stichtag'])}", 0.9, 4.45, 11.5, 0.5, size=18, bold=True,
             color=WHITE)
    add_text(s, f"{n} Fonds · Anlageklassen: {classes}", 0.9, 5.05, 11.5, 0.8, size=13,
             color=RGBColor(0xAE, 0xBD, 0xCE))
    add_text(s, f"Erstellt am {de_date(meta['generated'])}  ·  Datenquelle: Morningstar (MCP-Konnektor)",
             0.9, 6.7, 11.5, 0.4, size=11, color=RGBColor(0x8E, 0x9D, 0xB0))

def slide_agenda(prs, meta, funds):
    s = blank(prs)
    title_bar(s, "Inhalt & Aufbau", "Gliederung nach Anlageklassen")
    classes = [c for c in meta["class_order"] if meta["by_class"].get(c)]
    y = 1.45
    add_text(s, "Die Präsentation gliedert das Fondsuniversum in grobe Anlageklassen. "
                "Je Klasse folgen ein Vergleich aller Fonds (Ranglisten und Risiko-Rendite-Profil) "
                "sowie ein Kompaktprofil je Fonds.", 0.6, y, 12.1, 0.7, size=13, color=SLATE)
    y += 0.95
    for i, c in enumerate(classes, 1):
        add_rect(s, 0.6, y + 0.04, 0.12, 0.34, CLASS_ACCENT.get(c, NAVY))
        add_text(s, f"{i}.  {c}", 0.95, y, 7.5, 0.4, size=15, bold=True, color=INK)
        add_text(s, f"{meta['by_class'][c]} Fonds", 8.8, y, 3.5, 0.4, size=13, color=MUTED,
                 align=PP_ALIGN.RIGHT)
        y += 0.52
    footer(s, meta["stichtag"])

def slide_method(prs, meta):
    s = blank(prs)
    title_bar(s, "Methodik & Hinweise")
    bullets = [
        ("Datenquelle", "Sämtliche Kennzahlen stammen aus Morningstar (Abruf über den Morningstar-MCP-"
                         "Konnektor). Performance-/Risikokennzahlen sind Monatsultimo-Werte zum Stichtag."),
        ("Anlageklassen", "Die Zuordnung erfolgt anhand der Morningstar-Kategorie (z. B. „Global Large-Cap "
                          "Blend Equity" + " → Aktien). Innerhalb jeder Klasse dient die Morningstar-Kategorie "
                          "als feinere Vergleichsgruppe."),
        ("Performance", "Wertentwicklung in % (annualisiert ab 3 Jahren). Vergangenheitswerte sind kein "
                        "verlässlicher Indikator für die künftige Entwicklung."),
        ("Risiko/Rendite", "Volatilität = annualisierte Standardabweichung. Sharpe/Sortino/Information Ratio, "
                           "Alpha, Beta und Tracking Error gemäß Morningstar-Definition (vs. Kategorie-Index)."),
        ("Ratings", "Morningstar Sterne-Rating (quantitativ, rückblickend, 1–5★), Morningstar Medalist Rating "
                    "(qualitativ, vorausschauend: Gold/Silver/Bronze/Neutral/Negative) und Morningstar Risk Rating."),
        ("Portfolio", "Sofern verfügbar zeigt das Kompaktprofil die Portfolio-Zusammensetzung (X-Ray): "
                      "Asset-Allokation, Sektoren und Top-Positionen – jeweils aktuellster verfügbarer Stand."),
    ]
    y = 1.4
    for k, v in bullets:
        add_rect(s, 0.6, y + 0.05, 0.12, 0.5, ACCENT)
        add_text(s, k, 0.9, y, 2.3, 0.6, size=13, bold=True, color=NAVY)
        add_text(s, v, 3.3, y, 9.4, 0.8, size=11.5, color=INK, line_spacing=1.0)
        y += 0.86
    footer(s, meta["stichtag"])

def _agg(funds, key):
    vals = [f["metrics"].get(key) for f in funds if f["metrics"].get(key) is not None]
    return sum(vals) / len(vals) if vals else None

def slide_overview(prs, meta, funds):
    s = blank(prs)
    title_bar(s, "Gesamtüberblick", f"{meta['fund_count']} Fonds")
    classes = [c for c in meta["class_order"] if meta["by_class"].get(c)]
    # Balkendiagramm: Anzahl je Klasse
    cd = CategoryChartData(); cd.categories = classes
    cd.add_series("Anzahl Fonds", [meta["by_class"][c] for c in classes])
    gframe = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.4),
                                Inches(6.2), Inches(3.1), cd)
    ch = gframe.chart; ch.has_legend = False; ch.has_title = True
    ch.chart_title.text_frame.text = "Fonds je Anlageklasse"
    ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
    pl = ch.plots[0]; pl.has_data_labels = True
    pl.data_labels.font.size = Pt(10); pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    ser = ch.series[0]
    ser.format.fill.solid(); ser.format.fill.fore_color.rgb = NAVY
    for ax in (ch.category_axis, ch.value_axis):
        ax.tick_labels.font.size = Pt(9)
    # Kennzahlen-Tabelle je Klasse (Durchschnitte)
    headers = ["Anlageklasse", "Fonds", "Ø Perf 1J", "Ø Perf 3J", "Ø Vola 3J", "Ø Sharpe 3J"]
    rows = []
    for c in classes:
        fc = [f for f in funds if f["asset_class"] == c]
        rows.append([c, str(len(fc)), pct(_agg(fc, "performance_1y")), pct(_agg(fc, "performance_3y")),
                     pct(_agg(fc, "volatility_3y")), de_num(_agg(fc, "sharpe_3y"), 2)])
    add_table(s, 7.05, 1.5, 5.7, headers, rows,
              [2.0, 0.7, 0.85, 0.85, 0.85, 0.95],
              align=[PP_ALIGN.LEFT, PP_ALIGN.CENTER] + [PP_ALIGN.RIGHT] * 4,
              font_size=9.5, header_size=9, row_h=0.34)
    add_text(s, "Ø = ungewichteter Durchschnitt der Fonds mit verfügbarem Wert.",
             7.05, 1.5 + 0.34 + len(rows) * 0.34 + 0.1, 5.7, 0.3, size=9, italic=True, color=MUTED)
    # Universe-Hinweis
    nf = meta.get("not_found", [])
    add_text(s, f"Nicht in Morningstar verfügbar: {len(nf)} ISIN(s)." +
             (" " + ", ".join(nf) if nf else ""),
             0.6, 4.75, 12.1, 0.9, size=9.5, color=MUTED)
    footer(s, meta["stichtag"])

def slide_class_divider(prs, c, n, meta):
    s = blank(prs)
    accent = CLASS_ACCENT.get(c, NAVY)
    add_rect(s, 0, 0, SW, SH, accent)
    add_rect(s, 0, 3.55, SW, 0.06, WHITE)
    add_text(s, "Anlageklasse", 0.9, 2.55, 11, 0.5, size=18, color=RGBColor(0xDD, 0xE4, 0xEC))
    add_text(s, c, 0.9, 3.0, 11.5, 1.0, size=44, bold=True, color=WHITE)
    add_text(s, f"{n} Fonds  ·  Vergleich und Kompaktprofile", 0.9, 4.7, 11.5, 0.5, size=16,
             color=RGBColor(0xE6, 0xEB, 0xF1))

CMP_HEADERS = ["#", "Fonds", "Kategorie", "1J", "3J", "5J", "Vola 3J", "Sharpe 3J", "★", "Risiko"]
CMP_ALIGN = [PP_ALIGN.CENTER, PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT,
             PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.CENTER, PP_ALIGN.CENTER]
CMP_COLW = [0.4, 3.55, 2.85, 0.78, 0.78, 0.78, 0.92, 0.95, 0.78, 1.0]
ROWS_PER_CMP = 15

def slide_compare(prs, c, funds, meta):
    accent = CLASS_ACCENT.get(c, NAVY)
    # Sortierung: nach 3J-Performance (fallback 1J), absteigend
    def sk(f):
        m = f["metrics"]
        return (m.get("performance_3y") if m.get("performance_3y") is not None
                else (m.get("performance_1y") if m.get("performance_1y") is not None else -1e9))
    fs = sorted(funds, key=sk, reverse=True)
    pages = [fs[i:i + ROWS_PER_CMP] for i in range(0, len(fs), ROWS_PER_CMP)]
    for pi, page in enumerate(pages):
        s = blank(prs)
        ttl = f"{c} – Vergleich" + (f" ({pi+1}/{len(pages)})" if len(pages) > 1 else "")
        title_bar(s, ttl, f"sortiert nach 3-Jahres-Performance", accent=accent)
        rows, colors = [], {}
        for idx, f in enumerate(page):
            rank = pi * ROWS_PER_CMP + idx + 1
            m = f["metrics"]
            rows.append([str(rank), f["name"][:40], f["category"][:32],
                         pct(m.get("performance_1y")), pct(m.get("performance_3y")),
                         pct(m.get("performance_5y")), pct(m.get("volatility_3y")),
                         de_num(m.get("sharpe_3y"), 2), stars(f["star_rating"]),
                         f["risk_rating"] or "–"])
            for col, key in ((3, "performance_1y"), (4, "performance_3y"), (5, "performance_5y")):
                v = m.get(key)
                if v is not None:
                    colors[(idx, col)] = GOOD if v >= 0 else BAD
        add_table(s, 0.45, 1.3, 12.45, CMP_HEADERS, rows, CMP_COLW, header_color=accent,
                  align=CMP_ALIGN, font_size=9.5, header_size=9.5, row_h=0.345)
        footer(s, meta["stichtag"])

def slide_scatter(prs, c, funds, meta):
    accent = CLASS_ACCENT.get(c, NAVY)
    pts = [(f, f["metrics"].get("volatility_3y"), f["metrics"].get("performance_3y"))
           for f in funds]
    pts = [(f, x, y) for f, x, y in pts if x is not None and y is not None]
    if len(pts) < 2:
        return
    s = blank(prs)
    title_bar(s, f"{c} – Risiko/Rendite (3 Jahre)", "Volatilität vs. annualisierte Rendite", accent=accent)
    cd = XyChartData()
    ser = cd.add_series("Fonds")
    for f, x, y in pts:
        ser.add_data_point(x, y)
    gframe = s.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER, Inches(0.6), Inches(1.35),
                                Inches(8.4), Inches(5.4), cd)
    ch = gframe.chart; ch.has_legend = False
    plot = ch.plots[0]
    sr = ch.series[0]
    sr.marker.style = 8  # circle
    sr.marker.size = 7
    sr.format.line.fill.background()
    ch.category_axis.axis_title.text_frame.text = "Volatilität 3J (%)"
    ch.value_axis.axis_title.text_frame.text = "Rendite 3J p.a. (%)"
    for ax in (ch.category_axis, ch.value_axis):
        ax.tick_labels.font.size = Pt(9)
        ax.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(10)
    # Legende rechts: nummerierte Fondsliste (nach Rendite sortiert)
    pts_sorted = sorted(pts, key=lambda t: t[2], reverse=True)
    lines = []
    for i, (f, x, y) in enumerate(pts_sorted, 1):
        lines.append(f"{f['name'][:30]}  ·  {de_num(y,1)} % / {de_num(x,1)} %")
    add_text(s, "Fonds (Rendite p.a. / Vola):", 9.15, 1.45, 3.9, 0.3, size=10, bold=True, color=NAVY)
    add_text(s, "\n".join(lines), 9.15, 1.8, 3.95, 5.0, size=8.6, color=INK, line_spacing=1.05)
    footer(s, meta["stichtag"])

RET_PERIODS = [("1m", "1 Monat"), ("3m", "3 Monate"), ("6m", "6 Monate"), ("1y", "1 Jahr"),
               ("3y", "3 Jahre p.a."), ("5y", "5 Jahre p.a."), ("10y", "10 Jahre p.a."),
               ("incep", "seit Auflage p.a.")]
RISK_PERIODS = [("1y", "1 J"), ("3y", "3 J"), ("5y", "5 J"), ("10y", "10 J")]
RISK_ROWS = [("volatility", "Volatilität (%)"), ("sharpe", "Sharpe Ratio"),
             ("sortino", "Sortino Ratio"), ("alpha", "Alpha"), ("beta", "Beta"),
             ("information", "Information Ratio"), ("trackingerror", "Tracking Error")]

def slide_profile(prs, f, meta):
    c = f["asset_class"]; accent = CLASS_ACCENT.get(c, NAVY)
    s = blank(prs)
    title_bar(s, f["name"][:52], c, accent=accent)
    m = f["metrics"]
    # ---- Stammdaten (links) ----
    info = [
        ("ISIN", f["isin"] or "–"),
        ("Kategorie", f["category"]),
        ("Anbieter", f["branding"] or "–"),
        ("Auflage", inc_date(f["inception"])),
        ("Fondsvolumen", money_usd(f["fund_size_usd"])),
        ("Laufende Kosten", pct(f["cost"], 2) if f["cost"] is not None else "–"),
        ("Ausschütt.-Rendite", pct(f["yield"], 2) if f["yield"] is not None else "–"),
    ]
    add_rect(s, 0.45, 1.3, 3.85, 0.32, accent)
    add_text(s, "Stammdaten", 0.55, 1.31, 3.7, 0.3, size=11, bold=True, color=WHITE,
             anchor=MSO_ANCHOR.MIDDLE)
    y = 1.72
    for k, v in info:
        add_text(s, k, 0.5, y, 1.6, 0.3, size=9.5, color=MUTED)
        add_text(s, str(v), 2.05, y, 2.25, 0.32, size=9.5, bold=True, color=INK)
        y += 0.305
    # Ratings
    add_rect(s, 0.45, y + 0.05, 3.85, 0.32, NAVY)
    add_text(s, "Morningstar Ratings", 0.55, y + 0.06, 3.7, 0.3, size=11, bold=True, color=WHITE,
             anchor=MSO_ANCHOR.MIDDLE)
    y += 0.47
    add_text(s, "Sterne-Rating", 0.5, y, 1.6, 0.3, size=9.5, color=MUTED)
    add_text(s, stars(f["star_rating"]), 2.05, y, 2.25, 0.3, size=12, bold=True, color=RGBColor(0xC8,0x9B,0x10))
    y += 0.34
    add_text(s, "Medalist Rating", 0.5, y, 1.6, 0.3, size=9.5, color=MUTED)
    add_text(s, f["medalist"] or "–", 2.05, y, 2.25, 0.3, size=10.5, bold=True, color=INK)
    y += 0.32
    add_text(s, "Risk Rating", 0.5, y, 1.6, 0.3, size=9.5, color=MUTED)
    add_text(s, f["risk_rating"] or "–", 2.05, y, 2.25, 0.3, size=10.5, bold=True, color=INK)
    # ---- Rendite-Tabelle (Mitte) ----
    rrows, rcolors = [], {}
    for i, (p, lab) in enumerate(RET_PERIODS):
        v = m.get(f"performance_{p}")
        rrows.append([lab, pct(v)])
        if v is not None:
            rcolors[(i, 1)] = GOOD if v >= 0 else BAD
    add_table(s, 4.55, 1.3, 3.0, ["Wertentwicklung", "Rendite"], rrows, [1.9, 1.1],
              header_color=accent, align=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT], font_size=10,
              header_size=10, row_h=0.345, cell_colors=rcolors)
    # ---- Risiko-Tabelle (rechts) ----
    headers = ["Kennzahl"] + [lab for _, lab in RISK_PERIODS]
    krows = []
    for key, lab in RISK_ROWS:
        row = [lab]
        for p, _ in RISK_PERIODS:
            v = m.get(f"{key}_{p}")
            row.append(pct(v) if key in ("volatility",) else de_num(v, 2))
        krows.append(row)
    add_table(s, 7.75, 1.3, 5.1, headers, krows, [1.9, 0.8, 0.8, 0.8, 0.8],
              header_color=NAVY, align=[PP_ALIGN.LEFT] + [PP_ALIGN.RIGHT] * 4, font_size=9.5,
              header_size=9.5, row_h=0.345)
    # ---- Portfolio (unten, falls vorhanden) ----
    yb = 4.55
    pf = f.get("portfolio") or {}
    holds = f.get("holdings") or []
    if pf or holds:
        add_rect(s, 0.45, yb, 12.45, 0.32, SLATE)
        add_text(s, "Portfolio (Morningstar X-Ray)", 0.55, yb + 0.01, 8, 0.3, size=11, bold=True,
                 color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
        yb += 0.45
        # Asset-Allokation
        aa = pf.get("asset_allocation")
        if aa:
            seg = [("Aktien", aa.get("equity")), ("Anleihen", aa.get("bonds")),
                   ("Cash", aa.get("cash")), ("Sonstige", aa.get("other"))]
            txt = "   ".join(f"{k}: {de_num(v,1)} %" for k, v in seg if v is not None)
            add_text(s, "Allokation:  " + txt, 0.5, yb, 12.3, 0.3, size=10, color=INK)
            yb += 0.35
        sec = pf.get("sectors")
        if sec:
            top = sorted(sec.items(), key=lambda kv: kv[1], reverse=True)[:5]
            txt = "   ".join(f"{k}: {de_num(v,1)} %" for k, v in top)
            add_text(s, "Top-Sektoren:  " + txt, 0.5, yb, 12.3, 0.3, size=10, color=INK)
            yb += 0.35
        if holds:
            top = holds[:8]
            txt = "   ·   ".join(f"{h.get('name','')[:24]} {de_num(h.get('weight'),1)} %" for h in top)
            add_text(s, "Top-Positionen:  " + txt, 0.5, yb, 12.3, 0.6, size=9.5, color=INK)
    else:
        add_text(s, "Performance-Werte sind Monatsultimo-Werte zum Stichtag; annualisiert ab 3 Jahren. "
                    "Vergangene Wertentwicklung ist kein verlässlicher Indikator für die Zukunft.",
                 0.5, 6.55, 12.3, 0.6, size=9, italic=True, color=MUTED)
    footer(s, meta["stichtag"])

def slide_disclaimer(prs, meta):
    s = blank(prs)
    title_bar(s, "Wichtige Hinweise")
    txt = (
        "Diese Präsentation wurde automatisiert auf Basis von Morningstar-Daten erstellt und dient "
        "ausschließlich Informationszwecken. Sie stellt keine Anlageberatung, Anlageempfehlung oder "
        "ein Angebot zum Kauf oder Verkauf von Finanzinstrumenten dar.\n\n"
        "Alle Kennzahlen wurden über den Morningstar-MCP-Konnektor zum angegebenen Stichtag abgerufen. "
        "Quantitative Kennzahlen (Rendite, Risiko, Ratings) beziehen sich auf den Stichtag, soweit "
        "Morningstar entsprechende Historie bereitstellt; Portfolio-Zusammensetzungen entsprechen dem "
        "jeweils aktuellsten von Morningstar verfügbaren Stand.\n\n"
        "Die frühere Wertentwicklung ist kein verlässlicher Indikator für künftige Ergebnisse. "
        "Investitionen in Investmentfonds unterliegen Kursschwankungen und dem Risiko von Kapitalverlusten. "
        "Für die Richtigkeit und Vollständigkeit der Daten wird keine Gewähr übernommen.\n\n"
        f"Datenquelle: Morningstar  ·  Stichtag: {de_date(meta['stichtag'])}  ·  "
        f"Erstellt am: {de_date(meta['generated'])}  ·  {meta['fund_count']} Fonds"
    )
    add_text(s, txt, 0.6, 1.5, 12.1, 5.5, size=12.5, color=INK, line_spacing=1.15)
    footer(s, meta["stichtag"])

# ---------------------------------------------------------------------------
def build(data, out):
    meta = data["meta"]; funds = data["funds"]
    prs = Presentation()
    prs.slide_width = Inches(SW); prs.slide_height = Inches(SH)
    slide_title(prs, meta)
    slide_agenda(prs, meta, funds)
    slide_method(prs, meta)
    slide_overview(prs, meta, funds)
    for c in meta["class_order"]:
        cf = [f for f in funds if f["asset_class"] == c]
        if not cf:
            continue
        slide_class_divider(prs, c, len(cf), meta)
        slide_compare(prs, c, cf, meta)
        slide_scatter(prs, c, cf, meta)
        # Kompaktprofile (nach 3J-Performance sortiert)
        cf_sorted = sorted(cf, key=lambda f: (f["metrics"].get("performance_3y")
                           if f["metrics"].get("performance_3y") is not None else -1e9), reverse=True)
        for f in cf_sorted:
            slide_profile(prs, f, meta)
    slide_disclaimer(prs, meta)
    prs.save(out)
    return len(prs.slides._sldIdLst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/funds3.json")
    ap.add_argument("--out", default="/tmp/Fondsanalyse.pptx")
    a = ap.parse_args()
    data = json.load(open(a.data, encoding="utf-8"))
    n = build(data, a.out)
    print(f"OK: {n} Folien -> {a.out}  (Stichtag {data['meta']['stichtag']}, "
          f"{data['meta']['fund_count']} Fonds)")


if __name__ == "__main__":
    main()
