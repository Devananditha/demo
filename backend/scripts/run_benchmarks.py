"""Multi-seed benchmark execution and statistical serialization script."""

import json
from pathlib import Path
from app.benchmark.runner import benchmark_runner

def main():
    print("Running benchmark suite across seed 42...")
    rep42 = benchmark_runner.run_full_suite(seed=42)
    
    docs_dir = Path(__file__).resolve().parent.parent.parent / "docs"
    out_file = docs_dir / "benchmark_results.json"
    
    out_file.write_text(rep42.model_dump_json(indent=2), encoding="utf-8")
    print(f"Successfully serialized benchmark suite to {out_file}")
    print(f"Scenarios evaluated: {len(rep42.scenarios)}")
    print(f"All violations zero: {rep42.all_violations_zero}")
    for summary in rep42.statistical_summaries:
        print(f"  {summary.metric_name}: Baseline={summary.baseline_mean}, StallBreaker={summary.stallbreaker_mean}, Delta={summary.mean_delta} ({summary.pct_improvement}%), p={summary.p_value}")

if __name__ == "__main__":
    main()
