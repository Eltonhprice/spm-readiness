# scripts/icons.py
# Tabler icon SVG path data (https://tabler-icons.io, MIT license)
# All icons use viewBox="0 0 24 24", stroke="currentColor", fill="none"

# Briefcase — represents SPM domain
DOMAIN_ICON = (
    "M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z "
    "M8 5V3h8v2"
)

# Chart bar — demand
_DEMAND = "M3 12h4v8H3zm7-5h4v13h-4zm7-3h4v16h-4z"

# Folder — projects/PPM
_PPM = (
    "M4 4h6l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2"
)

# Users — resource management
_RESOURCE = (
    "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 "
    "M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8 "
    "M23 21v-2a4 4 0 0 0-3-3.87 "
    "M16 3.13a4 4 0 0 1 0 7.75"
)

# Currency dollar — financial
_FINANCIAL = (
    "M12 1v22 "
    "M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"
)

# Rocket — agile
_AGILE = (
    "M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 "
    "2.18 0 0 0-2.91-.09z "
    "M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11 "
    "A22.35 22.35 0 0 1 12 15z "
    "M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0 "
    "M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"
)

# Layout — APM
_APM = (
    "M4 4h6v6H4z "
    "M14 4h6v6h-6z "
    "M4 14h6v6H4z "
    "M17 17m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0"
)

# Bulb — innovation
_INNOVATION = (
    "M9 18h6 "
    "M10 22h4 "
    "M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 "
    "1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"
)

MODULE_ICONS = {
    "demand": _DEMAND,
    "ppm": _PPM,
    "resource": _RESOURCE,
    "financial": _FINANCIAL,
    "agile": _AGILE,
    "apm": _APM,
    "innovation": _INNOVATION,
}


def icon_svg(path, size=20, color="#A100FF"):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="{path}"/></svg>'
    )
