# scripts/test_findings.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _scores_with_reds():
    return {
        "demand":     {"activation": 100, "data_volume": 100, "data_completeness": 35,
                       "process_adoption": 30, "integration": 44, "module_score": 55, "rag": "amber"},
        "ppm":        {"activation": 100, "data_volume": 60,  "data_completeness": 65,
                       "process_adoption": 25, "integration": 60, "module_score": 54, "rag": "amber"},
        "resource":   {"activation": None, "data_volume": None, "data_completeness": None,
                       "process_adoption": None, "integration": None, "module_score": None, "rag": "not_collected"},
        "financial":  {"activation": 0,   "data_volume": 0,   "data_completeness": 0,
                       "process_adoption": 0,  "integration": 0,  "module_score": 0, "rag": "red"},
        "agile":      {"activation": 0,   "data_volume": 0,   "data_completeness": None,
                       "process_adoption": 0,  "integration": None, "module_score": 0, "rag": "red"},
        "apm":        {"activation": 0,   "data_volume": 20,  "data_completeness": 55,
                       "process_adoption": None, "integration": 40, "module_score": 28, "rag": "red"},
        "innovation": {"activation": 0,   "data_volume": 0,   "data_completeness": None,
                       "process_adoption": None, "integration": None, "module_score": 0, "rag": "red"},
    }

def _minimal_metrics():
    return {
        "modules": {
            "demand":     {"total": 500, "with_approval_pct": 30.0, "no_owner_pct": 18.0},
            "ppm":        {"total": 80,  "status_report_30d_pct": 25.0},
            "resource":   {"total": 0},
            "financial":  {"projects_with_cost_plan_pct": 0.0},
            "agile":      {"total_stories": 0},
            "apm":        {"total": 45},
            "innovation": {"total": 0},
        },
    }

def test_returns_list():
    from scripts.findings import generate_findings
    f = generate_findings(_minimal_metrics(), _scores_with_reds())
    assert isinstance(f, list)

def test_findings_have_required_keys():
    from scripts.findings import generate_findings
    findings = generate_findings(_minimal_metrics(), _scores_with_reds())
    for f in findings:
        for key in ["id", "module", "dimension", "rag", "observation", "significance"]:
            assert key in f, f"Missing key '{key}' in finding {f.get('id')}"

def test_ids_are_sequential():
    from scripts.findings import generate_findings
    findings = generate_findings(_minimal_metrics(), _scores_with_reds())
    for i, f in enumerate(findings, 1):
        assert f["id"] == f"SPM-{i:03d}", f"Expected SPM-{i:03d}, got {f['id']}"

def test_red_modules_produce_findings():
    from scripts.findings import generate_findings
    findings = generate_findings(_minimal_metrics(), _scores_with_reds())
    modules_with_findings = {f["module"] for f in findings}
    assert "financial" in modules_with_findings
    assert "agile" in modules_with_findings

def test_not_collected_does_not_produce_finding():
    from scripts.findings import generate_findings
    findings = generate_findings(_minimal_metrics(), _scores_with_reds())
    for f in findings:
        assert f["rag"] != "not_collected"

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("findings.py tests passed.")
