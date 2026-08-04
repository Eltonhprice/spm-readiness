# scripts/run_analysis.py
import argparse
import os

_DEFAULT_INPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "spm-inputs", "mock")
_DEFAULT_OUT   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "spm-outputs", "mock")


def run(input_dir, out_dir):
    from scripts.load     import load_all
    from scripts.metrics  import compute_metrics, _coverage_matrix
    from scripts.facts    import write_facts, write_csvs
    from scripts.scoring  import score_all, enrich_coverage_matrix, overall_score
    from scripts.findings import generate_findings
    from scripts.profile  import write_profile
    from scripts.html_deck import write_deck

    client = os.path.basename(os.path.normpath(out_dir))
    os.makedirs(out_dir, exist_ok=True)
    data_dir = os.path.join(out_dir, "data")

    print(f"[1/7] Loading exports from {input_dir} ...")
    buckets = load_all(input_dir)
    print(f"      {len(buckets)} tables/sidecars loaded.")

    print("[2/7] Computing metrics ...")
    metrics = compute_metrics(buckets, client, input_dir)
    metrics["coverage_matrix"] = _coverage_matrix(metrics["modules"])

    print("[3/7] Writing metrics.json + CSVs ...")
    facts_path = write_facts(metrics, out_dir)
    write_csvs(metrics, data_dir)
    print(f"      metrics.json -> {facts_path}")

    print("[4/7] Scoring modules ...")
    scores = score_all(metrics)
    metrics["coverage_matrix"] = enrich_coverage_matrix(metrics, scores)
    write_facts(metrics, out_dir)

    overall_scores = {k: v.get("module_score") for k, v in scores.items()}
    overall = overall_score(overall_scores)
    print(f"      Overall SPM Readiness Score: {overall}%")
    for mod, s in scores.items():
        ms = s.get("module_score")
        r  = s.get("rag", "")
        print(f"        {mod:12s}: {ms}%  [{r}]" if ms is not None else f"        {mod:12s}: not_collected")

    print("[5/7] Generating findings ...")
    findings = generate_findings(metrics, scores)
    print(f"      {len(findings)} findings generated.")

    print("[6/7] Writing markdown profile ...")
    profile_path = write_profile(metrics, scores, findings, out_dir)
    print(f"      Profile -> {profile_path}")

    print("[7/7] Rendering HTML leadership deck ...")
    deck_path = write_deck(metrics, scores, findings, out_dir)
    print(f"      Deck -> {deck_path}")

    print("\nDone.")
    print(f"  Overall Score : {overall}%")
    if findings:
        worst = min(scores.items(), key=lambda x: x[1].get("module_score") or 101)
        print(f"  Weakest Module: {worst[0]} -- {worst[1].get('module_score')}% [{worst[1].get('rag')}]")
        print(f"  Top Finding   : {findings[0]['id']} -- {findings[0]['observation']}")
    print(f"\n  Profile : {profile_path}")
    print(f"  Deck    : {deck_path}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run SPM readiness analysis")
    ap.add_argument("--input", default=_DEFAULT_INPUT, help="Input directory (spm-inputs/<client>)")
    ap.add_argument("--out",   default=_DEFAULT_OUT,   help="Output directory (spm-outputs/<client>)")
    args = ap.parse_args(argv)
    run(args.input, args.out)


if __name__ == "__main__":
    main()
