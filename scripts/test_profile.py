# scripts/test_profile.py
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _make_inputs():
    from scripts.metrics import compute_metrics, _coverage_matrix
    from scripts.scoring import score_all, enrich_coverage_matrix
    from scripts.findings import generate_findings

    mock_buckets = {
        "pm_demand": [
            {"sys_id": "d1", "state": "open", "assigned_to": "u1",
             "project": "p1", "sys_created_on": "2026-01-01 00:00:00", "priority": "2"},
        ],
        "pm_project": [
            {"sys_id": "p1", "state": "in_progress", "program": "pg1",
             "business_owner": "o1", "start_date": "2026-01-01",
             "end_date": "2026-12-31", "actual_end_date": "",
             "sys_created_on": "2026-01-01 00:00:00",
             "sys_updated_on": "2026-07-01 00:00:00"},
        ],
        "_sidecar_spm_adoption": {
            "plugins": {"com.snc.sdlc.ppm_core": True, "com.snc.rm": False,
                        "com.snc.financial_mgmt": False, "com.snc.agile": False,
                        "com.snc.apm": False, "com.snc.innovation_mgmt": False},
            "roles": {"portfolio_manager": 2, "project_manager": 5},
            "spm_workspace_active": False,
            "active_users_90d": {"pm_demand": 4},
        },
        "_sidecar_portfolio_health": {
            "project_completeness_pct": 65, "demand_priority_set_pct": 50,
            "resource_plan_named_pct": None, "projects_stale_90d": 0,
            "projects_stale_90d_pct": 0, "demands_stale_90d": 0, "demands_stale_90d_pct": 0,
        },
    }
    metrics = compute_metrics(mock_buckets, "test", "/tmp")
    metrics["coverage_matrix"] = _coverage_matrix(metrics["modules"])
    scores = score_all(metrics)
    metrics["coverage_matrix"] = enrich_coverage_matrix(metrics, scores)
    findings = generate_findings(metrics, scores)
    return metrics, scores, findings

def test_profile_file_created():
    metrics, scores, findings = _make_inputs()
    with tempfile.TemporaryDirectory() as tmp:
        from scripts.profile import write_profile
        path = write_profile(metrics, scores, findings, tmp)
        assert os.path.exists(path)

def test_profile_has_required_sections():
    metrics, scores, findings = _make_inputs()
    with tempfile.TemporaryDirectory() as tmp:
        from scripts.profile import write_profile
        path = write_profile(metrics, scores, findings, tmp)
        content = open(path, encoding="utf-8").read()
        required = [
            "SPM Readiness",
            "Executive Summary",
            "SPM Readiness Scorecard",
            "Demand Management",
            "Project Portfolio",
            "Leading-Practice Coverage",
            "Candidate Findings",
            "Collector Coverage",
        ]
        for section in required:
            assert section in content, f"Missing section: {section}"

def test_profile_no_disposition_language():
    metrics, scores, findings = _make_inputs()
    with tempfile.TemporaryDirectory() as tmp:
        from scripts.profile import write_profile
        path = write_profile(metrics, scores, findings, tmp)
        content = open(path, encoding="utf-8").read().lower()
        for word in ["should", "recommend", "migrate", "replace"]:
            assert word not in content, f"Disposition language found: '{word}'"

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("profile.py tests passed.")
