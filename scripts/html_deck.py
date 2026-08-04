# scripts/html_deck.py
import argparse
import json
import math
import os

from scripts.scoring import overall_score as _overall_score
from scripts.theme import RAG_COLORS

_MODULE_LABELS = {
    "demand":     "Demand",
    "ppm":        "PPM",
    "resource":   "Resource",
    "financial":  "Financial",
    "agile":      "Agile",
    "apm":        "APM",
    "innovation": "Innovation",
}

_DIMS = ["activation", "data_volume", "data_completeness", "process_adoption", "integration"]
_DIM_SHORT = {
    "activation":        "Activation",
    "data_volume":       "Data Vol.",
    "data_completeness": "Completeness",
    "process_adoption":  "Adoption",
    "integration":       "Integration",
}

PURPLE = "#A100FF"
_SLIDE_BG = "#ffffff"
_DECK_BG  = "#f4f4f6"


def write_deck(metrics, scores, findings, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    html = render_deck(metrics, scores, findings)
    path = os.path.join(out_dir, "spm-leadership-deck.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def render_deck(metrics, scores, findings):
    ctx     = metrics.get("_context", {})
    client  = ctx.get("client", "Client").upper()
    date    = ctx.get("generated_on", "")
    mod_scores = {k: v.get("module_score") for k, v in scores.items()}
    overall    = _overall_score(mod_scores)

    slides = [
        _slide_cover(client, date, overall),
        _slide_radar(scores, overall),
        _slide_scorecard(scores),
        _slide_governance(metrics),
        _slide_findings(findings),
        _slide_next_steps(),
    ]
    return _page_shell(slides, client, date)


def _page_shell(slides, client, date):
    slide_html = "\n".join(
        f'<div class="slide" id="slide-{i+1}">{s}</div>'
        for i, s in enumerate(slides)
    )
    nav_dots = "".join(
        f'<span class="dot {"active" if i == 0 else ""}" onclick="goTo({i})"></span>'
        for i in range(len(slides))
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SPM Readiness — {client}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
          background: {_DECK_BG}; display:flex; flex-direction:column;
          align-items:center; min-height:100vh; padding:20px; }}
  .deck {{ width:960px; max-width:100%; }}
  .slide {{ background:{_SLIDE_BG}; border-radius:8px; padding:48px 56px;
            box-shadow:0 2px 12px rgba(0,0,0,.08); margin-bottom:20px;
            min-height:540px; display:none; }}
  .slide.visible {{ display:block; }}
  .nav {{ display:flex; justify-content:center; gap:8px; margin:8px 0 20px; }}
  .dot {{ width:10px; height:10px; border-radius:50%;
          background:#d1d5db; cursor:pointer; transition:background .2s; }}
  .dot.active {{ background:{PURPLE}; }}
  .btn {{ border:none; background:{PURPLE}; color:#fff; padding:8px 20px;
          border-radius:4px; cursor:pointer; font-size:13px; }}
  .btn-row {{ display:flex; justify-content:space-between; margin-top:16px; }}
  table {{ border-collapse:collapse; width:100%; font-size:13px; }}
  th {{ background:#f9f5ff; color:{PURPLE}; text-align:left; padding:8px 10px;
        border-bottom:2px solid {PURPLE}; font-size:12px; }}
  td {{ padding:7px 10px; border-bottom:1px solid #f0e8ff; vertical-align:middle; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:3px;
            font-size:11px; font-weight:700; color:#fff; }}
  h1 {{ font-size:28px; font-weight:800; color:#1a1a1a; }}
  h2 {{ font-size:20px; font-weight:700; color:{PURPLE}; margin-bottom:16px; }}
  h3 {{ font-size:15px; font-weight:600; color:#333; margin-bottom:8px; }}
  .score-big {{ font-size:72px; font-weight:900; line-height:1; }}
  .label {{ font-size:11px; text-transform:uppercase; letter-spacing:1.5px;
            color:#999; margin-bottom:4px; }}
  .purple {{ color:{PURPLE}; }}
</style>
</head>
<body>
<div class="deck">
{slide_html}
<div class="nav">{nav_dots}</div>
</div>
<script>
var current = 0;
var slides = document.querySelectorAll('.slide');
var dots   = document.querySelectorAll('.dot');
function goTo(n) {{
  slides[current].classList.remove('visible');
  dots[current].classList.remove('active');
  current = (n + slides.length) % slides.length;
  slides[current].classList.add('visible');
  dots[current].classList.add('active');
}}
goTo(0);
document.addEventListener('keydown', function(e) {{
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goTo(current + 1);
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   goTo(current - 1);
}});
</script>
</body>
</html>"""


def _slide_cover(client, date, overall):
    score_str = f"{overall}%" if overall is not None else "—"
    rag_color = RAG_COLORS.get(
        "green" if (overall or 0) >= 70 else "amber" if (overall or 0) >= 40 else "red",
        "#9ca3af"
    )
    return f"""
<div class="label">Accenture SAGE · SPM Readiness Assessment · AS-IS</div>
<h1 style="margin:12px 0 4px;">{client}</h1>
<div style="font-size:13px;color:#888;margin-bottom:40px;">{date}</div>
<div class="label">Overall SPM Readiness Score</div>
<div class="score-big" style="color:{rag_color};">{score_str}</div>
<div style="margin-top:24px;font-size:13px;color:#666;">
  Score is a weighted average of 7 SPM modules × 5 readiness dimensions.<br>
  Green &ge;70% &nbsp;&middot;&nbsp; Amber 40&ndash;69% &nbsp;&middot;&nbsp; Red &lt;40%
</div>
<div class="btn-row">
  <span></span>
  <button class="btn" onclick="goTo(1)">Next &rarr;</button>
</div>"""


def _slide_radar(scores, overall):
    labels = list(_MODULE_LABELS.values())
    vals   = [scores.get(k, {}).get("module_score") or 0
              for k in _MODULE_LABELS.keys()]
    colors = [RAG_COLORS.get(scores.get(k, {}).get("rag", "not_collected"), "#9ca3af")
              for k in _MODULE_LABELS.keys()]
    svg = _radar_svg(labels, vals, colors)
    overall_str = f"{overall}%" if overall is not None else "—"
    return f"""
<h2>Readiness at a Glance</h2>
<div style="display:flex;align-items:center;gap:40px;">
  <div>{svg}</div>
  <div>
    <div class="label">Overall Score</div>
    <div style="font-size:48px;font-weight:900;color:{PURPLE};">{overall_str}</div>
    <div style="margin-top:20px;font-size:13px;color:#555;">
      {''.join(f'<div style="margin:4px 0;"><span class="badge" style="background:{colors[i]};">{labels[i]}</span> &nbsp;{vals[i]}%</div>' for i in range(len(labels)))}
    </div>
  </div>
</div>
<div class="btn-row">
  <button class="btn" onclick="goTo(0)">&larr; Back</button>
  <button class="btn" onclick="goTo(2)">Next &rarr;</button>
</div>"""


def _radar_svg(labels, scores, colors, size=340):
    n  = len(labels)
    cx = cy = size / 2
    r  = size / 2 - 70
    angles = [2 * math.pi * i / n - math.pi / 2 for i in range(n)]

    grid = ""
    for pct in [0.25, 0.5, 0.75, 1.0]:
        pts = " ".join(
            f"{cx + pct*r*math.cos(a):.1f},{cy + pct*r*math.sin(a):.1f}"
            for a in angles
        )
        grid += f'<polygon points="{pts}" fill="none" stroke="#e5e7eb" stroke-width="1"/>'

    axes = "".join(
        f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx+r*math.cos(a):.1f}" y2="{cy+r*math.sin(a):.1f}" stroke="#e5e7eb" stroke-width="1"/>'
        for a in angles
    )

    pts = " ".join(
        f"{cx + (scores[i]/100)*r*math.cos(angles[i]):.1f},{cy + (scores[i]/100)*r*math.sin(angles[i]):.1f}"
        for i in range(n)
    )
    poly = f'<polygon points="{pts}" fill="rgba(161,0,255,0.15)" stroke="{PURPLE}" stroke-width="2"/>'

    lbls = ""
    for i, (lbl, score, col) in enumerate(zip(labels, scores, colors)):
        a  = angles[i]
        lx = cx + (r + 42) * math.cos(a)
        ly = cy + (r + 42) * math.sin(a)
        lbls += (
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="11" font-family="sans-serif" fill="#333">{lbl}</text>'
            f'<text x="{lx:.1f}" y="{ly+14:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="10" font-weight="bold" '
            f'font-family="sans-serif" fill="{col}">{score}%</text>'
        )

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'{grid}{axes}{poly}{lbls}</svg>'
    )


def _slide_scorecard(scores):
    header = "<tr><th>Module</th>" + "".join(f"<th>{_DIM_SHORT[d]}</th>" for d in _DIMS) + "<th>Score</th><th>RAG</th></tr>"
    rows = ""
    for mod_key, mod_label in _MODULE_LABELS.items():
        s = scores.get(mod_key, {})
        cells = ""
        for dim in _DIMS:
            v = s.get(dim)
            if v is None:
                cells += '<td style="color:#ccc;">—</td>'
            else:
                r   = "green" if v >= 70 else "amber" if v >= 40 else "red"
                bg  = RAG_COLORS[r]
                cells += f'<td><span class="badge" style="background:{bg};">{v}%</span></td>'
        ms = s.get("module_score")
        mr = s.get("rag", "not_collected")
        mc = RAG_COLORS.get(mr, "#9ca3af")
        ms_str = f"{ms}%" if ms is not None else "—"
        rows += f"<tr><td><strong>{mod_label}</strong></td>{cells}<td><strong>{ms_str}</strong></td><td><span class=\"badge\" style=\"background:{mc};\">{mr.upper()}</span></td></tr>"

    return f"""
<h2>Module Readiness Scorecard</h2>
<table><thead>{header}</thead><tbody>{rows}</tbody></table>
<div style="margin-top:12px;font-size:11px;color:#888;">
  Green &ge;70% &nbsp;&middot;&nbsp; Amber 40&ndash;69% &nbsp;&middot;&nbsp; Red &lt;40% &nbsp;&middot;&nbsp; &mdash; = not collected
</div>
<div class="btn-row">
  <button class="btn" onclick="goTo(1)">&larr; Back</button>
  <button class="btn" onclick="goTo(3)">Next &rarr;</button>
</div>"""


def _slide_governance(metrics):
    gov = metrics.get("governance", {})
    ts  = gov.get("timesheets", {})
    app = gov.get("approvals", {})
    sr  = gov.get("status_reports", {})
    sm  = gov.get("scoring_models", {})

    rows = [
        ("Active Timesheet Periods",      ts.get("active_periods"),   ts.get("collected")),
        ("Timesheet Entries (total)",      ts.get("total_entries"),    ts.get("collected")),
        ("Demands with Approvals",         app.get("demand_records_with_approvals"), app.get("collected")),
        ("Projects with Approvals",        app.get("project_records_with_approvals"), app.get("collected")),
        ("Project Status Reports (total)", sr.get("total"),            sr.get("collected")),
        ("Portfolio Scoring Criteria",     sm.get("criteria_count"),   sm.get("collected")),
        ("Records with Portfolio Score",   sm.get("scored_records"),   sm.get("collected")),
    ]
    rows_html = ""
    for label, val, collected in rows:
        display = str(val) if val is not None else "—"
        status  = f'<span class="badge" style="background:#22c55e;">Collected</span>' \
                  if collected else \
                  f'<span class="badge" style="background:#9ca3af;">Not collected</span>'
        rows_html += f"<tr><td>{label}</td><td><strong>{display}</strong></td><td>{status}</td></tr>"

    return f"""
<h2>Governance & Process Adoption</h2>
<table>
  <thead><tr><th>Signal</th><th>Value</th><th>Status</th></tr></thead>
  <tbody>{rows_html}</tbody>
</table>
<div class="btn-row">
  <button class="btn" onclick="goTo(2)">&larr; Back</button>
  <button class="btn" onclick="goTo(4)">Next &rarr;</button>
</div>"""


def _slide_findings(findings):
    top5 = findings[:5]
    if not top5:
        body = "<p style='color:#888;'>No significant findings generated from the available data.</p>"
    else:
        rows = ""
        for f in top5:
            r   = f.get("rag", "")
            col = RAG_COLORS.get(r, "#9ca3af")
            rows += (
                f'<tr>'
                f'<td><span class="badge" style="background:{col};">{f.get("id")}</span></td>'
                f'<td>{f.get("module_label", f.get("module", ""))}</td>'
                f'<td>{f.get("observation", "")}</td>'
                f'</tr>'
            )
        body = f'<table><thead><tr><th>ID</th><th>Module</th><th>Observation</th></tr></thead><tbody>{rows}</tbody></table>'

    return f"""
<h2>Top Findings</h2>
{body}
<div style="margin-top:12px;font-size:11px;color:#888;">
  Showing top {len(top5)} findings. Full findings list in the markdown profile.
</div>
<div class="btn-row">
  <button class="btn" onclick="goTo(3)">&larr; Back</button>
  <button class="btn" onclick="goTo(5)">Next &rarr;</button>
</div>"""


def _slide_next_steps():
    return f"""
<h2>Recommended Next Steps</h2>
<div style="background:#f9f5ff;border-left:4px solid {PURPLE};padding:16px 20px;border-radius:4px;margin-bottom:24px;">
  <div style="font-size:12px;font-weight:700;color:{PURPLE};text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">For Discussion</div>
  <div style="color:#555;font-size:13px;">This slide is intentionally left as a structured placeholder.<br>
  The consultant completes this section during the FDE conversation with the client.</div>
</div>
<table>
  <thead><tr><th>#</th><th>Initiative</th><th>Module</th><th>Priority</th></tr></thead>
  <tbody>
    <tr><td>1</td><td><em>[Consultant to complete]</em></td><td>—</td><td>—</td></tr>
    <tr><td>2</td><td><em>[Consultant to complete]</em></td><td>—</td><td>—</td></tr>
    <tr><td>3</td><td><em>[Consultant to complete]</em></td><td>—</td><td>—</td></tr>
  </tbody>
</table>
<div class="btn-row">
  <button class="btn" onclick="goTo(4)">&larr; Back</button>
  <span></span>
</div>"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render SPM leadership HTML deck from metrics.json")
    ap.add_argument("--metrics", required=True, help="Path to metrics.json")
    ap.add_argument("--out",     required=True, help="Output directory")
    args = ap.parse_args(argv)

    with open(args.metrics, encoding="utf-8") as f:
        metrics = json.load(f)

    from scripts.scoring import score_all, enrich_coverage_matrix
    from scripts.metrics import _coverage_matrix
    from scripts.findings import generate_findings

    if not metrics.get("coverage_matrix"):
        metrics["coverage_matrix"] = _coverage_matrix(metrics.get("modules", {}))
    scores   = score_all(metrics)
    metrics["coverage_matrix"] = enrich_coverage_matrix(metrics, scores)
    findings = generate_findings(metrics, scores)

    path = write_deck(metrics, scores, findings, args.out)
    print(f"Deck written: {path}")


if __name__ == "__main__":
    main()
