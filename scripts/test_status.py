# scripts/test_status.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.status import measured, not_collected, not_applicable, pct

def test_measured():
    r = measured(42)
    assert r == {"value": 42, "status": "measured"}

def test_measured_kwargs():
    r = measured(42, note="from sidecar")
    assert r["note"] == "from sidecar"
    assert r["status"] == "measured"

def test_not_collected():
    r = not_collected("table absent")
    assert r["value"] is None
    assert r["status"] == "not_collected"
    assert r["note"] == "table absent"

def test_not_applicable():
    r = not_applicable()
    assert r["status"] == "not_applicable"

def test_pct_normal():
    assert pct(38, 100) == 38.0

def test_pct_zero_denominator():
    assert pct(5, 0) is None

def test_pct_rounding():
    assert pct(1, 3) == 33.3

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("status.py tests passed.")
