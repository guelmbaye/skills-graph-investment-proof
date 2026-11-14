"""Run: python -m skills_graph.demo --backend baseline|relate|both"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .core import load_data, evaluate_baseline

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description="SG Skills Investment Proof — A→B→A")
    ap.add_argument("--backend", choices=("baseline", "relate", "both"), default="baseline")
    ap.add_argument("--data", default=str(ROOT / "data" / "scenario_synthetic.json"))
    ap.add_argument("--store", default=str(ROOT / "build" / "skills_graph-demo.rl"))
    ap.add_argument("--report", default=str(ROOT / "build" / "report.json"))
    args = ap.parse_args()
    model = load_data(args.data)
    result = {"data_kind": "SYNTHETIC_ONLY", "scenario": model["scenario"]}
    if args.backend in ("baseline", "both"):
        result["baseline"] = evaluate_baseline(model)
    if args.backend in ("relate", "both"):
        from .relate_backend import run_relate
        result["relate"] = run_relate(model, args.store)
    if args.backend == "both":
        a, b = result["baseline"], result["relate"]
        result["same_outcome"] = all(a[k] == b[k] for k in (
            "states", "impact_paths", "program_deltas", "affected_paths",
            "occupation_provider_paths", "skill_seat_opportunities",
            "occupation_bottleneck_proxies", "occupations_with_proxy_delta", "coverage_claim"
        ))
        if not result["same_outcome"]:
            raise AssertionError("Baseline vs Relate mismatch")
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
