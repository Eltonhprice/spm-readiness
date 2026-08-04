# scripts/pptx_deck.py
"""Generate a PowerPoint SPM Readiness leadership deck from metrics.json."""
import argparse
import io
import json
import math
import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from scripts.scoring import overall_score as _overall_score

# ── Palette ────────────────────────────────────────────────────────────────────
PURPLE    = RGBColor(0xA1, 0x00, 0xFF)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
DARK      = RGBColor(0x1A, 0x1A, 0x1A)
GREY_LT   = RGBColor(0xF9, 0xF5, 0xFF)
GREY_MID  = RGBColor(0xE9, 0xD5, 0xFF)
GREY_TEXT = RGBColor(0x66, 0x66, 0x66)

RAG_RGB = {
    "green":         RGBColor(0x22, 0xC5, 0x5E),
    "amber":         RGBColor(0xF5, 0x9E, 0x0B),
    "red":           RGBColor(0xEF, 0x44, 0x44),
    "not_collected": RGBColor(0x9C, 0xA3, 0xAF),
}
RAG_HEX = {
    "green":  "#22c55e",
    "amber":  "#f59e0b",
    "red":    "#ef4444",
    "not_collected": "#9ca3af",
}

_MODULE_LABELS = {
    "demand":     "Demand Management",
    "ppm":        "Project Portfolio",
    "resource":   "Resource Mgmt",
    "financial":  "Financial Mgmt",
    "agile":      "Agile Development",
    "apm":        "APM",
    "innovation": "Innovation",
    "csdm":       "CSDM/CMDB Health",
}
_DIMS = ["activation", "data_volume", "data_completeness", "process_adoption", "integration"]
_DIM_SHORT = {
    "activation":        "Activation",
    "data_volume":       "Data Vol.",
    "data_completeness": "Completeness",
    "process_adoption":  "Adoption",
    "integration":       "Integration",
}

# ── Slide size (widescreen 13.33" × 7.5") ─────────────────────────────────────
W = Inches(13.33)
H = Inches(7.5)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _prs():
    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H
    return prs


def _blank(prs):
    blank_layout = prs.slide_layouts[6]
    return prs.slides.add_slide(blank_layout)


def _rect(slide, x, y, w, h, fill=None, line=None):
    shape = slide.shapes.add_shape(1, x, y, w, h)  # MSO_SHAPE_TYPE.RECTANGLE
    shape.line.fill.background()
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    if line:
        shape.line.color.rgb = line
        shape.line.width = Pt(0.75)
    else:
        shape.line.fill.background()
    return shape


def _txbox(slide, x, y, w, h, text, size=12, bold=False, color=None,
           align=PP_ALIGN.LEFT, italic=False, wrap=True):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    p  = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color or DARK
    return tb


def _rag_label(score):
    if score is None:
        return "not_collected"
    return "green" if score >= 70 else "amber" if score >= 40 else "red"


def _purple_bar(slide, y_top=Inches(0), height=Inches(0.08)):
    _rect(slide, 0, y_top, W, height, fill=PURPLE)


def _header_band(slide, title, subtitle=""):
    _rect(slide, 0, 0, W, Inches(1.2), fill=PURPLE)
    _txbox(slide, Inches(0.4), Inches(0.15), Inches(12.5), Inches(0.5),
           title, size=24, bold=True, color=WHITE)
    if subtitle:
        _txbox(slide, Inches(0.4), Inches(0.7), Inches(12.5), Inches(0.4),
               subtitle, size=12, color=RGBColor(0xE9, 0xD5, 0xFF))


def _footer(slide, date="", mode="rde"):
    y = H - Inches(0.35)
    _rect(slide, 0, y, W, Inches(0.35), fill=PURPLE)
    label = f"Accenture SAGE  ·  {mode.upper()}  ·  SPM Readiness Assessment  ·  {date}"
    _txbox(slide, Inches(0.4), y + Inches(0.05), Inches(12), Inches(0.25),
           label, size=9, color=RGBColor(0xE9, 0xD5, 0xFF))


# ── Radar chart (matplotlib → PNG → embed) ────────────────────────────────────
def _radar_png(labels, values, colors, size_px=480):
    n  = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    vals = [v / 100.0 for v in values]
    vals += vals[:1]

    fig, ax = plt.subplots(figsize=(size_px/96, size_px/96), dpi=96,
                           subplot_kw=dict(polar=True))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    # Grid rings
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25%", "50%", "75%", "100%"], size=7, color="#aaa")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=8, color="#333")
    ax.grid(color="#e5e7eb", linewidth=0.8)
    ax.spines["polar"].set_color("#e5e7eb")

    # Fill
    ax.fill(angles, vals, color="#A100FF", alpha=0.15)
    ax.plot(angles, vals, color="#A100FF", linewidth=2)

    # Dots per module colored by RAG
    for i, (ang, val, col) in enumerate(zip(angles[:-1], vals[:-1], colors)):
        ax.plot(ang, val, "o", color=col, markersize=6, zorder=5)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=96, bbox_inches="tight",
                transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


# ── Slides ────────────────────────────────────────────────────────────────────
def _slide_cover(prs, client, date, overall, mode):
    sl = _blank(prs)
    # Purple left accent bar
    _rect(sl, 0, 0, Inches(0.18), H, fill=PURPLE)
    # Top accent line
    _rect(sl, Inches(0.18), 0, W - Inches(0.18), Inches(0.08), fill=PURPLE)

    # Badge
    _txbox(sl, Inches(0.5), Inches(0.35), Inches(12), Inches(0.4),
           f"ACCENTURE SAGE  ·  {mode.upper()}  ·  SPM READINESS ASSESSMENT  ·  AS-IS",
           size=9, bold=True, color=PURPLE)

    # Client name
    _txbox(sl, Inches(0.5), Inches(0.8), Inches(10), Inches(1.0),
           client, size=36, bold=True, color=DARK)

    # Date
    _txbox(sl, Inches(0.5), Inches(1.8), Inches(6), Inches(0.4),
           date, size=13, color=GREY_TEXT)

    # Score label
    _txbox(sl, Inches(0.5), Inches(2.6), Inches(6), Inches(0.4),
           "OVERALL SPM READINESS SCORE", size=10, bold=True,
           color=GREY_TEXT)

    # Big score
    rag = _rag_label(overall)
    score_str = f"{overall}%" if overall is not None else "—"
    _txbox(sl, Inches(0.45), Inches(2.9), Inches(6), Inches(2.2),
           score_str, size=96, bold=True,
           color=RAG_RGB.get(rag, RGBColor(0x9C, 0xA3, 0xAF)))

    # RAG legend
    legend = "Green ≥ 70%  ·  Amber 40–69%  ·  Red < 40%"
    _txbox(sl, Inches(0.5), Inches(5.4), Inches(8), Inches(0.4),
           legend, size=10, color=GREY_TEXT)

    # Footer bar
    _footer(sl, date, mode)
    return sl


def _slide_bar(prs, scores, overall, date, mode):
    sl = _blank(prs)
    _header_band(sl, "Readiness at a Glance",
                 "Module scores  ·  Green ≥70%  ·  Amber 40–69%  ·  Red <40%  ·  Grey = not collected")

    # Layout constants
    label_x   = Inches(0.3)
    label_w   = Inches(2.3)
    bar_x     = Inches(2.75)
    bar_max_w = Inches(9.2)
    score_x   = Inches(12.1)
    score_w   = Inches(1.0)
    row_h     = Inches(0.52)
    gap       = Inches(0.06)
    y0        = Inches(1.42)

    for i, (key, label) in enumerate(_MODULE_LABELS.items()):
        ms  = scores.get(key, {}).get("module_score")
        rag = _rag_label(ms)
        col = RAG_RGB.get(rag, RGBColor(0x9C, 0xA3, 0xAF))
        y   = y0 + i * (row_h + gap)

        # Module label (right-aligned feel via wide box)
        _txbox(sl, label_x, y + Inches(0.1), label_w, Inches(0.32),
               label, size=10, color=DARK)

        # Bar track (grey background)
        _rect(sl, bar_x, y + Inches(0.1), bar_max_w, Inches(0.32),
              fill=RGBColor(0xE9, 0xE9, 0xEB))

        # Bar fill — proportional to score
        fill_w = bar_max_w * (ms / 100.0) if ms is not None else 0
        if fill_w > 0:
            _rect(sl, bar_x, y + Inches(0.1), fill_w, Inches(0.32), fill=col)

        # Score label
        score_txt = f"{ms}%" if ms is not None else "—"
        _txbox(sl, score_x, y + Inches(0.08), score_w, Inches(0.36),
               score_txt, size=11, bold=True, color=col, align=PP_ALIGN.RIGHT)

    # Overall score tile at bottom
    rag_o = _rag_label(overall)
    col_o = RAG_RGB.get(rag_o, RGBColor(0x9C, 0xA3, 0xAF))
    y_ov  = y0 + len(_MODULE_LABELS) * (row_h + gap) + Inches(0.12)
    _rect(sl, bar_x, y_ov, bar_max_w + score_w + Inches(0.15), Inches(0.55), fill=PURPLE)
    _txbox(sl, bar_x + Inches(0.2), y_ov + Inches(0.1), Inches(6), Inches(0.35),
           "OVERALL SPM READINESS", size=11, bold=True, color=WHITE)
    _txbox(sl, bar_x + bar_max_w - Inches(1.8), y_ov + Inches(0.1), Inches(2.0), Inches(0.35),
           f"{overall}%" if overall is not None else "—",
           size=13, bold=True, color=WHITE, align=PP_ALIGN.RIGHT)

    _footer(sl, date, mode)
    return sl


def _slide_scorecard(prs, scores, date, mode):
    sl = _blank(prs)
    _header_band(sl, "Module Readiness Scorecard",
                 "8 modules × 5 dimensions  ·  RAG thresholds: Green ≥70%  ·  Amber 40–69%  ·  Red <40%")

    col_w  = [Inches(2.4)] + [Inches(1.4)] * 5 + [Inches(0.85), Inches(0.9)]
    row_h  = Inches(0.48)
    x0, y0 = Inches(0.25), Inches(1.35)
    headers = ["Module"] + [_DIM_SHORT[d] for d in _DIMS] + ["Score", "RAG"]

    total_w = sum(col_w)
    rows    = 1 + len(_MODULE_LABELS)
    tbl = sl.shapes.add_table(rows, len(headers), x0, y0, total_w,
                              row_h * rows).table

    # Header row
    for ci, (hdr, cw) in enumerate(zip(headers, col_w)):
        tbl.columns[ci].width = cw
        cell = tbl.cell(0, ci)
        cell.text = hdr
        cell.fill.solid(); cell.fill.fore_color.rgb = PURPLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.runs[0] if p.runs else p.add_run()
        run.font.size = Pt(9); run.font.bold = True; run.font.color.rgb = WHITE

    for ri, (mod_key, mod_label) in enumerate(_MODULE_LABELS.items(), start=1):
        s      = scores.get(mod_key, {})
        ms     = s.get("module_score")
        mr     = s.get("rag", "not_collected")
        row_bg = GREY_LT if ri % 2 == 0 else WHITE

        tbl.rows[ri].height = row_h
        vals_row = [mod_label] + [s.get(d) for d in _DIMS] + [ms, mr.upper()]

        for ci, val in enumerate(vals_row):
            cell = tbl.cell(ri, ci)
            cell.fill.solid()

            if ci == 0:
                cell.fill.fore_color.rgb = row_bg
                cell.text = str(val)
                p = cell.text_frame.paragraphs[0]
                run = p.runs[0] if p.runs else p.add_run()
                run.font.size = Pt(9); run.font.bold = True; run.font.color.rgb = DARK
            elif ci <= 5:
                score_val = val
                rag = _rag_label(score_val) if score_val is not None else "not_collected"
                cell.fill.fore_color.rgb = RAG_RGB.get(rag, RGBColor(0x9C, 0xA3, 0xAF))
                display = f"{score_val}%" if score_val is not None else "—"
                cell.text = display
                p = cell.text_frame.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                run = p.runs[0] if p.runs else p.add_run()
                run.font.size = Pt(9); run.font.bold = True; run.font.color.rgb = WHITE
            elif ci == 6:
                cell.fill.fore_color.rgb = row_bg
                cell.text = f"{ms}%" if ms is not None else "—"
                p = cell.text_frame.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                col_ms = RAG_RGB.get(_rag_label(ms), RGBColor(0x9C, 0xA3, 0xAF))
                run = p.runs[0] if p.runs else p.add_run()
                run.font.size = Pt(10); run.font.bold = True; run.font.color.rgb = col_ms
            else:
                col_rag = RAG_RGB.get(mr, RGBColor(0x9C, 0xA3, 0xAF))
                cell.fill.fore_color.rgb = col_rag
                cell.text = mr.upper()
                p = cell.text_frame.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                run = p.runs[0] if p.runs else p.add_run()
                run.font.size = Pt(8); run.font.bold = True; run.font.color.rgb = WHITE

    _footer(sl, date, mode)
    return sl


def _slide_governance(prs, metrics, date, mode):
    sl = _blank(prs)
    _header_band(sl, "Governance & Process Adoption",
                 "Approval, timesheet, status reporting, and scoring model signals")

    gov = metrics.get("governance", {})
    ts  = gov.get("timesheets", {})
    app = gov.get("approvals", {})
    sr  = gov.get("status_reports", {})
    sm  = gov.get("scoring_models", {})
    roles = metrics.get("roles", {})

    signals = [
        ("Active Timesheet Periods",     ts.get("active_periods"),                ts.get("collected")),
        ("Timesheet Entries (total)",     ts.get("total_entries"),                 ts.get("collected")),
        ("Demands with Approvals",        app.get("demand_records_with_approvals"), app.get("collected")),
        ("Projects with Approvals",       app.get("project_records_with_approvals"),app.get("collected")),
        ("Project Status Reports",        sr.get("total"),                         sr.get("collected")),
        ("Portfolio Scoring Criteria",    sm.get("criteria_count"),                sm.get("collected")),
        ("Records with Portfolio Score",  sm.get("scored_records"),                sm.get("collected")),
    ]

    col_w = [Inches(4.5), Inches(2.2), Inches(2.5)]
    row_h = Inches(0.5)
    x0, y0 = Inches(0.5), Inches(1.4)
    tbl = sl.shapes.add_table(len(signals) + 1, 3, x0, y0,
                              sum(col_w), row_h * (len(signals) + 1)).table
    for ci, (hdr, cw) in enumerate(zip(["Signal", "Value", "Status"], col_w)):
        tbl.columns[ci].width = cw
        cell = tbl.cell(0, ci)
        cell.text = hdr
        cell.fill.solid(); cell.fill.fore_color.rgb = PURPLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.runs[0] if p.runs else p.add_run()
        run.font.size = Pt(10); run.font.bold = True; run.font.color.rgb = WHITE

    for ri, (label, val, collected) in enumerate(signals, start=1):
        bg = GREY_LT if ri % 2 == 0 else WHITE
        tbl.rows[ri].height = row_h
        for ci in range(3):
            cell = tbl.cell(ri, ci)
            cell.fill.solid(); cell.fill.fore_color.rgb = bg
        tbl.cell(ri, 0).text = label
        tbl.cell(ri, 1).text = str(val) if val is not None else "—"
        tbl.cell(ri, 1).text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        status_txt = "Collected" if collected else "Not collected"
        status_col = RAG_RGB["green"] if collected else RGBColor(0x9C, 0xA3, 0xAF)
        status_cell = tbl.cell(ri, 2)
        status_cell.fill.solid(); status_cell.fill.fore_color.rgb = status_col
        status_cell.text = status_txt
        p = status_cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.runs[0] if p.runs else p.add_run()
        run.font.size = Pt(9); run.font.bold = True; run.font.color.rgb = WHITE
        for ci in [0, 1]:
            p = tbl.cell(ri, ci).text_frame.paragraphs[0]
            run = p.runs[0] if p.runs else p.add_run()
            run.font.size = Pt(10); run.font.color.rgb = DARK

    # Role counts side panel
    x1 = Inches(7.7)
    _rect(sl, x1, Inches(1.4), Inches(5.3), Inches(5.4), fill=GREY_LT, line=GREY_MID)
    _txbox(sl, x1 + Inches(0.2), Inches(1.5), Inches(5), Inches(0.4),
           "SPM ROLE ASSIGNMENTS", size=9, bold=True, color=PURPLE)
    role_labels = {
        "portfolio_manager": "Portfolio Manager",
        "project_manager":   "Project Manager",
        "resource_manager":  "Resource Manager",
        "financial_analyst": "Financial Analyst",
        "it_demand_manager": "IT Demand Manager",
    }
    for i, (key, label) in enumerate(role_labels.items()):
        y = Inches(2.05) + i * Inches(0.7)
        count = roles.get(key)
        _txbox(sl, x1 + Inches(0.2), y, Inches(3.5), Inches(0.35),
               label, size=10, color=DARK)
        _txbox(sl, x1 + Inches(3.8), y, Inches(1.3), Inches(0.35),
               str(count) if count is not None else "—", size=13, bold=True,
               color=PURPLE, align=PP_ALIGN.RIGHT)

    _footer(sl, date, mode)
    return sl


def _slide_findings(prs, findings, date, mode):
    sl = _blank(prs)
    _header_band(sl, "Top Findings",
                 "Highest-priority signals from the readiness assessment")

    top5 = findings[:5]
    if not top5:
        _txbox(sl, Inches(0.5), Inches(2.0), Inches(12), Inches(0.5),
               "No significant findings generated from the available data.",
               size=12, color=GREY_TEXT)
    else:
        col_w = [Inches(0.9), Inches(2.3), Inches(7.3), Inches(2.4)]
        row_h = Inches(0.72)
        x0, y0 = Inches(0.25), Inches(1.35)
        tbl = sl.shapes.add_table(len(top5) + 1, 4, x0, y0,
                                  sum(col_w), row_h * (len(top5) + 1)).table
        for ci, (hdr, cw) in enumerate(zip(["ID", "Module", "Observation", "Significance"], col_w)):
            tbl.columns[ci].width = cw
            cell = tbl.cell(0, ci)
            cell.text = hdr
            cell.fill.solid(); cell.fill.fore_color.rgb = PURPLE
            p = cell.text_frame.paragraphs[0]
            run = p.runs[0] if p.runs else p.add_run()
            run.font.size = Pt(9); run.font.bold = True; run.font.color.rgb = WHITE

        for ri, f in enumerate(top5, start=1):
            rag = f.get("rag", "not_collected")
            col = RAG_RGB.get(rag, RGBColor(0x9C, 0xA3, 0xAF))
            bg  = GREY_LT if ri % 2 == 0 else WHITE
            tbl.rows[ri].height = row_h

            id_cell = tbl.cell(ri, 0)
            id_cell.fill.solid(); id_cell.fill.fore_color.rgb = col
            id_cell.text = f.get("id", "")
            p = id_cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            run = p.runs[0] if p.runs else p.add_run()
            run.font.size = Pt(9); run.font.bold = True; run.font.color.rgb = WHITE

            for ci, txt in [(1, f.get("module_label", f.get("module", ""))),
                            (2, f.get("observation", "")),
                            (3, f.get("significance", ""))]:
                cell = tbl.cell(ri, ci)
                cell.fill.solid(); cell.fill.fore_color.rgb = bg
                cell.text = txt
                p = cell.text_frame.paragraphs[0]
                run = p.runs[0] if p.runs else p.add_run()
                run.font.size = Pt(9); run.font.color.rgb = DARK

    _footer(sl, date, mode)
    return sl


def _slide_next_steps(prs, mode, findings, date):
    sl = _blank(prs)
    if mode == "fde" and findings:
        _header_band(sl, "Priority Focus Areas",
                     "FDE · Areas for Discussion  ·  Derived from top Red/Amber findings")
        priority = [f for f in findings if f.get("rag") in ("red", "amber")][:5]
        if not priority:
            priority = findings[:5]

        col_w = [Inches(0.5), Inches(2.3), Inches(7.5), Inches(2.4)]
        row_h = Inches(0.72)
        x0, y0 = Inches(0.25), Inches(1.35)
        tbl = sl.shapes.add_table(len(priority) + 1, 4, x0, y0,
                                  sum(col_w), row_h * (len(priority) + 1)).table
        for ci, (hdr, cw) in enumerate(zip(["#", "Module", "Finding", "Priority"], col_w)):
            tbl.columns[ci].width = cw
            cell = tbl.cell(0, ci)
            cell.text = hdr
            cell.fill.solid(); cell.fill.fore_color.rgb = PURPLE
            p = cell.text_frame.paragraphs[0]
            run = p.runs[0] if p.runs else p.add_run()
            run.font.size = Pt(9); run.font.bold = True; run.font.color.rgb = WHITE

        for ri, f in enumerate(priority, start=1):
            rag = f.get("rag", "not_collected")
            col = RAG_RGB.get(rag, RGBColor(0x9C, 0xA3, 0xAF))
            bg  = GREY_LT if ri % 2 == 0 else WHITE
            tbl.rows[ri].height = row_h

            num_cell = tbl.cell(ri, 0)
            num_cell.fill.solid(); num_cell.fill.fore_color.rgb = PURPLE
            num_cell.text = str(ri)
            p = num_cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            run = p.runs[0] if p.runs else p.add_run()
            run.font.size = Pt(10); run.font.bold = True; run.font.color.rgb = WHITE

            for ci, txt in [(1, f.get("module_label", f.get("module", ""))),
                            (2, f.get("observation", ""))]:
                cell = tbl.cell(ri, ci)
                cell.fill.solid(); cell.fill.fore_color.rgb = bg
                cell.text = txt
                p = cell.text_frame.paragraphs[0]
                run = p.runs[0] if p.runs else p.add_run()
                run.font.size = Pt(9); run.font.color.rgb = DARK

            pri_cell = tbl.cell(ri, 3)
            pri_cell.fill.solid(); pri_cell.fill.fore_color.rgb = col
            pri_cell.text = rag.upper()
            p = pri_cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            run = p.runs[0] if p.runs else p.add_run()
            run.font.size = Pt(9); run.font.bold = True; run.font.color.rgb = WHITE

        note = "Consultant to validate scope and sequencing with client."
        _txbox(sl, Inches(0.25), Inches(6.85), Inches(12), Inches(0.3),
               note, size=9, color=GREY_TEXT, italic=True)
    else:
        _header_band(sl, "Recommended Next Steps", "For Discussion — consultant to complete")
        _rect(sl, Inches(0.5), Inches(1.5), Inches(12.3), Inches(2.4),
              fill=GREY_LT, line=GREY_MID)
        _txbox(sl, Inches(0.7), Inches(1.65), Inches(11.8), Inches(0.4),
               "FOR DISCUSSION", size=10, bold=True, color=PURPLE)
        _txbox(sl, Inches(0.7), Inches(2.1), Inches(11.8), Inches(0.8),
               "This slide is intentionally left as a structured placeholder.\n"
               "The consultant completes this section during the FDE conversation with the client.",
               size=11, color=GREY_TEXT)

        col_w = [Inches(0.6), Inches(5.5), Inches(2.5), Inches(3.5)]
        x0, y0 = Inches(0.5), Inches(4.1)
        tbl = sl.shapes.add_table(4, 4, x0, y0, sum(col_w), Inches(2.0)).table
        for ci, (hdr, cw) in enumerate(zip(["#", "Initiative", "Module", "Priority"], col_w)):
            tbl.columns[ci].width = cw
            cell = tbl.cell(0, ci)
            cell.text = hdr
            cell.fill.solid(); cell.fill.fore_color.rgb = PURPLE
            p = cell.text_frame.paragraphs[0]
            run = p.runs[0] if p.runs else p.add_run()
            run.font.size = Pt(9); run.font.bold = True; run.font.color.rgb = WHITE
        for ri in range(1, 4):
            bg = GREY_LT if ri % 2 == 0 else WHITE
            tbl.cell(ri, 0).text = str(ri)
            for ci in range(4):
                cell = tbl.cell(ri, ci)
                cell.fill.solid(); cell.fill.fore_color.rgb = bg
                if ci > 0:
                    cell.text = "[Consultant to complete]"
                    p = cell.text_frame.paragraphs[0]
                    run = p.runs[0] if p.runs else p.add_run()
                    run.font.size = Pt(9); run.font.color.rgb = GREY_TEXT
                    run.font.italic = True

    _footer(sl, date, mode)
    return sl


def _slide_summary(prs, metrics, scores, findings, overall, date, mode):
    sl = _blank(prs)
    _header_band(sl, "Assessment Summary",
                 "Key signals from the AS-IS readiness profile")

    # ── Left panel: overall score + RAG breakdown ─────────────────────────────
    _rect(sl, Inches(0.3), Inches(1.35), Inches(3.8), Inches(5.7),
          fill=GREY_LT, line=GREY_MID)

    rag_o = _rag_label(overall)
    col_o = RAG_RGB.get(rag_o, RGBColor(0x9C, 0xA3, 0xAF))
    _txbox(sl, Inches(0.5), Inches(1.5), Inches(3.4), Inches(0.35),
           "OVERALL SCORE", size=9, bold=True, color=GREY_TEXT)
    _txbox(sl, Inches(0.45), Inches(1.8), Inches(3.8), Inches(1.4),
           f"{overall}%" if overall is not None else "—",
           size=64, bold=True, color=col_o)

    # RAG breakdown counts
    rag_counts = {"green": 0, "amber": 0, "red": 0, "not_collected": 0}
    for key in _MODULE_LABELS:
        r = scores.get(key, {}).get("rag", "not_collected")
        rag_counts[r] = rag_counts.get(r, 0) + 1

    _txbox(sl, Inches(0.5), Inches(3.1), Inches(3.4), Inches(0.3),
           "MODULE BREAKDOWN", size=9, bold=True, color=GREY_TEXT)

    breakdown = [
        ("Green",         rag_counts["green"],         RAG_RGB["green"]),
        ("Amber",         rag_counts["amber"],          RAG_RGB["amber"]),
        ("Red",           rag_counts["red"],            RAG_RGB["red"]),
        ("Not Collected", rag_counts["not_collected"],  RGBColor(0x9C, 0xA3, 0xAF)),
    ]
    for i, (label, count, col) in enumerate(breakdown):
        y = Inches(3.5) + i * Inches(0.62)
        _rect(sl, Inches(0.5), y, Inches(0.28), Inches(0.28), fill=col)
        _txbox(sl, Inches(0.9), y - Inches(0.02), Inches(1.6), Inches(0.32),
               label, size=10, color=DARK)
        _txbox(sl, Inches(2.6), y - Inches(0.02), Inches(1.2), Inches(0.32),
               str(count), size=12, bold=True, color=col, align=PP_ALIGN.RIGHT)

    # Plugin activation summary
    mods = metrics.get("modules", {})
    active = sum(1 for k in _MODULE_LABELS if mods.get(k, {}).get("plugin_active"))
    _txbox(sl, Inches(0.5), Inches(6.1), Inches(3.4), Inches(0.28),
           f"{active} of {len(_MODULE_LABELS)} modules active",
           size=9, color=GREY_TEXT, italic=True)

    # ── Right panel: top findings ──────────────────────────────────────────────
    _txbox(sl, Inches(4.4), Inches(1.35), Inches(8.6), Inches(0.32),
           "KEY SIGNALS", size=9, bold=True, color=GREY_TEXT)

    top = findings[:5]
    row_h = Inches(0.92)
    for i, f in enumerate(top):
        y   = Inches(1.72) + i * (row_h + Inches(0.06))
        rag = f.get("rag", "not_collected")
        col = RAG_RGB.get(rag, RGBColor(0x9C, 0xA3, 0xAF))

        _rect(sl, Inches(4.4), y, Inches(8.6), row_h, fill=GREY_LT, line=GREY_MID)
        _rect(sl, Inches(4.4), y, Inches(0.22), row_h, fill=col)

        # Finding ID + module
        _txbox(sl, Inches(4.72), y + Inches(0.06), Inches(2.5), Inches(0.28),
               f"{f.get('id','')}  ·  {f.get('module_label', f.get('module',''))}",
               size=8, bold=True, color=col)
        # Observation
        _txbox(sl, Inches(4.72), y + Inches(0.32), Inches(8.0), Inches(0.36),
               f.get("observation", ""), size=9, color=DARK)
        # Significance
        sig = f.get("significance", "")
        if sig:
            _txbox(sl, Inches(4.72), y + Inches(0.62), Inches(8.0), Inches(0.26),
                   sig, size=8, color=GREY_TEXT, italic=True)

    _footer(sl, date, mode)
    return sl


# ── Public API ────────────────────────────────────────────────────────────────
def render_pptx(metrics, scores, findings, mode="rde"):
    ctx     = metrics.get("_context", {})
    client  = ctx.get("client", "Client").upper()
    date    = ctx.get("generated_on", "")
    mod_scores = {k: v.get("module_score") for k, v in scores.items()}
    overall    = _overall_score(mod_scores)

    prs = _prs()
    _slide_cover(prs, client, date, overall, mode)
    _slide_bar(prs, scores, overall, date, mode)
    _slide_scorecard(prs, scores, date, mode)
    _slide_governance(prs, metrics, date, mode)
    _slide_findings(prs, findings, date, mode)
    _slide_next_steps(prs, mode, findings, date)
    _slide_summary(prs, metrics, scores, findings, overall, date, mode)
    return prs


def write_pptx(metrics, scores, findings, out_dir, mode="rde"):
    os.makedirs(out_dir, exist_ok=True)
    prs  = render_pptx(metrics, scores, findings, mode=mode)
    path = os.path.join(out_dir, "spm-leadership-deck.pptx")
    prs.save(path)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render SPM leadership PowerPoint deck")
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--out",     required=True)
    ap.add_argument("--mode",    default="rde", choices=["rde", "fde"])
    args = ap.parse_args(argv)

    with open(args.metrics, encoding="utf-8") as f:
        metrics = json.load(f)

    from scripts.scoring  import score_all, enrich_coverage_matrix
    from scripts.metrics  import _coverage_matrix
    from scripts.findings import generate_findings

    if not metrics.get("coverage_matrix"):
        metrics["coverage_matrix"] = _coverage_matrix(metrics.get("modules", {}))
    scores   = score_all(metrics)
    metrics["coverage_matrix"] = enrich_coverage_matrix(metrics, scores)
    findings = generate_findings(metrics, scores)

    path = write_pptx(metrics, scores, findings, args.out, mode=args.mode)
    print(f"PowerPoint written: {path}")


if __name__ == "__main__":
    main()
