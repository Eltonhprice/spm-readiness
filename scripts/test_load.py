# scripts/test_load.py
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def test_loads_single_table():
    records = [{"sys_id": "abc", "state": "open"}]
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(tmp, "demand", "pm_demand.txt"),
               json.dumps(records) + "\n// SPM collector: table=pm_demand chunk=0 rows=1 total=1 status=COMPLETE\n")
        from scripts.load import load_all
        buckets = load_all(tmp)
        assert "pm_demand" in buckets
        assert len(buckets["pm_demand"]) == 1
        assert buckets["pm_demand"][0]["state"] == "open"

def test_merges_chunks():
    chunk1 = [{"sys_id": str(i)} for i in range(3)]
    chunk2 = [{"sys_id": str(i)} for i in range(3, 5)]
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(tmp, "ppm", "pm_project.001.txt"),
               json.dumps(chunk1) + "\n// SPM collector: table=pm_project chunk=0 rows=3 total=5 status=MORE_RECORDS_EXIST\n")
        _write(os.path.join(tmp, "ppm", "pm_project.002.txt"),
               json.dumps(chunk2) + "\n// SPM collector: table=pm_project chunk=1 rows=2 total=5 status=COMPLETE\n")
        from scripts.load import load_all
        buckets = load_all(tmp)
        assert len(buckets["pm_project"]) == 5

def test_loads_sidecar():
    data = {"plugins": {"com.snc.sdlc.ppm_core": True}, "roles": {}}
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(tmp, "sidecars", "_sidecar_spm_adoption.txt"),
               json.dumps(data) + "\n// SPM sidecar: name=_sidecar_spm_adoption status=COMPLETE\n")
        from scripts.load import load_all
        buckets = load_all(tmp)
        assert "_sidecar_spm_adoption" in buckets
        assert buckets["_sidecar_spm_adoption"]["plugins"]["com.snc.sdlc.ppm_core"] is True

def test_table_not_found_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(tmp, "demand", "pm_demand.txt"),
               "[]\n// SPM collector: table=pm_demand chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND\n")
        from scripts.load import load_all
        buckets = load_all(tmp)
        assert buckets.get("pm_demand", []) == []

def test_missing_table_not_in_buckets():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "demand"))
        from scripts.load import load_all
        buckets = load_all(tmp)
        assert "pm_demand" not in buckets

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("load.py tests passed.")
