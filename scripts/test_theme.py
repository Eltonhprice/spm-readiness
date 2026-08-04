# scripts/test_theme.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.theme import render_header, render_footer, section_badge, RAG_COLORS

def test_header_contains_title():
    h = render_header("SPM Readiness", client="Acme Corp", date="2026-08-04")
    assert "SPM Readiness" in h
    assert "Acme Corp" in h
    assert "2026-08-04" in h

def test_header_has_badge():
    h = render_header("X", badge="SPM Readiness · AS-IS")
    assert "SPM Readiness · AS-IS" in h

def test_footer_contains_sage():
    f = render_footer(date="2026-08-04")
    assert "SAGE" in f
    assert "2026-08-04" in f

def test_section_badge_contains_label():
    b = section_badge("Demand Management", "M3 12h4")
    assert "Demand Management" in b

def test_rag_colors_keys():
    assert set(RAG_COLORS.keys()) == {"green", "amber", "red", "not_collected"}

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("theme.py tests passed.")
