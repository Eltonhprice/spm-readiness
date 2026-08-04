# scripts/theme.py
from datetime import date as _date

PURPLE = "#A100FF"
LIGHT_PURPLE = "#F9F5FF"
BORDER_PURPLE = "#E9D5FF"

RAG_COLORS = {
    "green": "#22c55e",
    "amber": "#f59e0b",
    "red": "#ef4444",
    "not_collected": "#9ca3af",
}

RAG_BG = {
    "green": "#f0fdf4",
    "amber": "#fffbeb",
    "red": "#fef2f2",
    "not_collected": "#f9fafb",
}


def render_header(title, badge="SPM Readiness · AS-IS", client="", date=""):
    date_str = date or _date.today().isoformat()
    client_str = f" &nbsp;·&nbsp; {client}" if client else ""
    return (
        f'<div style="border-left:6px solid {PURPLE};background:{LIGHT_PURPLE};'
        f'padding:16px 20px;margin-bottom:24px;border-radius:4px;">\n'
        f'<div style="display:flex;align-items:center;gap:12px;">\n'
        f'<div style="flex:1;">\n'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:2px;'
        f'color:{PURPLE};text-transform:uppercase;margin-bottom:4px;">{badge}</div>\n'
        f'<div style="font-size:22px;font-weight:800;color:#1a1a1a;">{title}</div>\n'
        f'<div style="font-size:12px;color:#666;margin-top:4px;">'
        f'{date_str}{client_str} &nbsp;·&nbsp; Accenture SAGE</div>\n'
        f'</div>\n</div>\n</div>\n'
    )


def render_footer(date=""):
    date_str = date or _date.today().isoformat()
    return (
        f'\n<div style="border-top:3px solid {PURPLE};margin-top:40px;'
        f'padding-top:12px;font-size:11px;color:#999;text-align:center;">\n'
        f'SAGE · SPM Readiness Assessment · AS-IS Profile · {date_str} · Accenture\n'
        f'</div>\n'
    )


def section_badge(label, icon_path="", color=PURPLE):
    icon_html = ""
    if icon_path:
        icon_html = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
            f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'style="vertical-align:middle;margin-right:6px;">'
            f'<path d="{icon_path}"/></svg>'
        )
    return (
        f'<div style="display:inline-flex;align-items:center;'
        f'background:{LIGHT_PURPLE};border:1px solid {BORDER_PURPLE};'
        f'border-radius:4px;padding:4px 10px;margin:8px 0 4px 0;">'
        f'{icon_html}'
        f'<span style="font-size:12px;font-weight:700;color:{color};">{label}</span>'
        f'</div>\n'
    )
