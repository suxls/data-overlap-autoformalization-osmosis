#!/usr/bin/env python3
"""Compute all metrics from eval_v2 judged JSONL files.

Reads <results_dir>/<model>/judged/<bench>.jsonl and produces
<results_dir>/metrics.json with per-(model, benchmark) metrics:

  - compile pass@k  (k=1,4,8)
  - semantic pass@k  (k=1,4,8, threshold=0.7)
  - mean semantic score (all rollouts, non-compiling=0)
  - mean semantic score (compiling-only)
  - token statistics (mean, median, tokens per correct formalization)

Usage:
    python eval_v2/compute_metrics.py --results-dir eval_v2/results
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
from collections import defaultdict
from math import comb
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SEMANTIC_THRESHOLD = 0.7
PASS_AT_K = [1, 4, 8]
N_ROLLOUTS = 8

BENCHMARKS = ["proofnet", "gaokao", "putnam"]

EXCLUDE_MODELS = {"sft-nt-grpo-tk-v2", "sft-nt-grpo-nt-v2", "sft-nt-test-tk"}


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased estimator: pass@k = 1 - C(n-c, k) / C(n, k)."""
    if n - c < k:
        return 1.0
    if n < k:
        return 0.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def load_judged(results_dir: Path, model_slug: str, bench: str) -> list[dict]:
    """Load the judged JSONL for a model x benchmark."""
    path = results_dir / model_slug / "judged" / f"{bench}.jsonl"
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def compute_for_model_bench(entries: list[dict]) -> dict[str, Any]:
    """Compute all metrics for one model x benchmark from judged entries."""
    if not entries:
        return {}

    problems: dict[int, list[dict]] = defaultdict(list)
    for e in entries:
        problems[e["row_index"]].append(e)

    n_problems = len(problems)

    compile_pass = {}
    for k in PASS_AT_K:
        vals = []
        for row_idx in sorted(problems):
            rollouts = problems[row_idx]
            n = len(rollouts)
            c = sum(1 for r in rollouts if r["compiles"])
            if k <= n:
                vals.append(pass_at_k(n, c, k))
        compile_pass[k] = sum(vals) / len(vals) if vals else 0.0

    semantic_pass = {}
    for k in PASS_AT_K:
        vals = []
        for row_idx in sorted(problems):
            rollouts = problems[row_idx]
            n = len(rollouts)
            c = sum(
                1 for r in rollouts
                if r["compiles"] and r.get("semantic_score", 0.0) >= SEMANTIC_THRESHOLD
            )
            if k <= n:
                vals.append(pass_at_k(n, c, k))
        semantic_pass[k] = sum(vals) / len(vals) if vals else 0.0

    all_scores = [e.get("semantic_score", 0.0) for e in entries]
    compiling_scores = [
        e.get("semantic_score", 0.0) for e in entries if e["compiles"]
    ]
    mean_semantic_all = sum(all_scores) / len(all_scores) if all_scores else 0.0
    mean_semantic_compiling = (
        sum(compiling_scores) / len(compiling_scores) if compiling_scores else 0.0
    )

    all_tokens = [e.get("total_tokens", 0) for e in entries if e.get("total_tokens", 0) > 0]
    correct_tokens = [
        e.get("total_tokens", 0)
        for e in entries
        if e["compiles"]
        and e.get("semantic_score", 0.0) >= SEMANTIC_THRESHOLD
        and e.get("total_tokens", 0) > 0
    ]

    token_stats = {}
    if all_tokens:
        token_stats["mean_tokens"] = sum(all_tokens) / len(all_tokens)
        token_stats["median_tokens"] = float(statistics.median(all_tokens))
    if correct_tokens:
        token_stats["tokens_per_correct"] = sum(correct_tokens) / len(correct_tokens)
    else:
        token_stats["tokens_per_correct"] = None

    # -- Best-of-8 (max score per problem) distribution --
    best_scores: list[float] = []
    for row_idx in sorted(problems):
        rollouts = problems[row_idx]
        max_score = max(
            (r.get("semantic_score", 0.0) for r in rollouts if r["compiles"]),
            default=0.0,
        )
        best_scores.append(max_score)

    bins = [round(x * 0.1, 1) for x in range(11)]  # 0.0, 0.1, ..., 1.0
    histogram: dict[str, float] = {}
    for b in bins:
        lo = b - 0.05 if b > 0 else -0.01
        hi = b + 0.05
        count = sum(1 for s in best_scores if lo < s <= hi)
        histogram[f"{b:.1f}"] = count / len(best_scores) if best_scores else 0.0
    histogram["0.0"] = sum(1 for s in best_scores if s == 0.0) / len(best_scores) if best_scores else 0.0

    best_mean = sum(best_scores) / len(best_scores) if best_scores else 0.0
    best_median = float(statistics.median(best_scores)) if best_scores else 0.0
    nonzero_scores = [s for s in best_scores if s > 0.0]
    best_mean_nonzero = sum(nonzero_scores) / len(nonzero_scores) if nonzero_scores else 0.0
    best_median_nonzero = float(statistics.median(nonzero_scores)) if nonzero_scores else 0.0

    return {
        "n_problems": n_problems,
        "n_rollouts": len(entries),
        "n_compiling": sum(1 for e in entries if e["compiles"]),
        "n_semantic_pass": sum(
            1 for e in entries
            if e["compiles"] and e.get("semantic_score", 0.0) >= SEMANTIC_THRESHOLD
        ),
        "compile_pass_at": {str(k): v for k, v in compile_pass.items()},
        "semantic_pass_at": {str(k): v for k, v in semantic_pass.items()},
        "mean_semantic_all": mean_semantic_all,
        "mean_semantic_compiling": mean_semantic_compiling,
        "token_stats": token_stats,
        "best_of_8": {
            "histogram": histogram,
            "mean": best_mean,
            "median": best_median,
            "mean_nonzero": best_mean_nonzero,
            "median_nonzero": best_median_nonzero,
            "n_zero": sum(1 for s in best_scores if s == 0.0),
            "n_nonzero": len(nonzero_scores),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute eval_v2 metrics")
    parser.add_argument("--results-dir", required=True, help="Path to eval_v2/results/")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    model_dirs = sorted(
        p for p in results_dir.iterdir()
        if p.is_dir() and p.name not in ("logs", "tables") and p.name not in EXCLUDE_MODELS
    )

    all_metrics: dict[str, dict[str, Any]] = {}

    for model_dir in model_dirs:
        model_slug = model_dir.name
        judged_dir = model_dir / "judged"
        if not judged_dir.exists():
            continue

        for bench in BENCHMARKS:
            entries = load_judged(results_dir, model_slug, bench)
            if not entries:
                continue

            metrics = compute_for_model_bench(entries)
            key = f"{model_slug}/{bench}"
            all_metrics[key] = metrics

            cp1 = metrics["compile_pass_at"]["1"]
            sp1 = metrics["semantic_pass_at"]["1"]
            cp8 = metrics["compile_pass_at"]["8"]
            sp8 = metrics["semantic_pass_at"]["8"]
            logger.info(
                "  %s: C@1=%.4f  S@1=%.4f  C@8=%.4f  S@8=%.4f  (%d problems)",
                key, cp1, sp1, cp8, sp8, metrics["n_problems"],
            )

    out_path = results_dir / "metrics.json"
    with open(out_path, "w") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False)
    logger.info("Metrics written to %s (%d entries)", out_path, len(all_metrics))

    # Print summary table
    print("\n" + "=" * 120)
    print(f"{'Model':<28} | {'Gaokao':^30} | {'ProofNet':^30} | {'Putnam':^30}")
    print(f"{'':28} | {'C@1':>7} {'S@1':>7} {'C@8':>7} {'S@8':>7} | {'C@1':>7} {'S@1':>7} {'C@8':>7} {'S@8':>7} | {'C@1':>7} {'S@1':>7} {'C@8':>7} {'S@8':>7}")
    print("-" * 120)

    model_slugs = sorted(set(k.split("/")[0] for k in all_metrics.keys()))
    for model in model_slugs:
        row = f"{model:<28} |"
        for bench in ["gaokao", "proofnet", "putnam"]:
            key = f"{model}/{bench}"
            if key in all_metrics:
                m = all_metrics[key]
                cp1 = m["compile_pass_at"]["1"]
                sp1 = m["semantic_pass_at"]["1"]
                cp8 = m["compile_pass_at"]["8"]
                sp8 = m["semantic_pass_at"]["8"]
                row += f" {cp1:6.1%} {sp1:6.1%} {cp8:6.1%} {sp8:6.1%} |"
            else:
                row += f" {'--':>7} {'--':>7} {'--':>7} {'--':>7} |"
        print(row)
    print("=" * 120)

    # Best-of-8 score distribution table
    print("\n\nBest-of-8 Semantic Score Distribution (max score per problem across 8 rollouts)")
    print("=" * 160)
    header = f"{'Model':<28} |"
    for b in [f"{x*0.1:.1f}" for x in range(11)]:
        header += f" {b:>5}"
    header += " | {'mean':>6} {'med':>5} {'mean_nz':>7} {'med_nz':>6}"
    print(f"{'Model':<28} |  0.0   0.1   0.2   0.3   0.4   0.5   0.6   0.7   0.8   0.9   1.0  |   mean   med  mean_nz med_nz")
    print("-" * 160)

    for bench in ["gaokao", "proofnet", "putnam"]:
        print(f"\n  [{bench.upper()}]")
        for model in model_slugs:
            key = f"{model}/{bench}"
            if key not in all_metrics or "best_of_8" not in all_metrics[key]:
                continue
            b8 = all_metrics[key]["best_of_8"]
            hist = b8["histogram"]
            row = f"  {model:<26} |"
            for b in [f"{x*0.1:.1f}" for x in range(11)]:
                pct = hist.get(b, 0.0)
                row += f" {pct:4.0%}" if pct >= 0.005 else "    -"
            row += f"  | {b8['mean']:6.3f} {b8['median']:5.2f}  {b8['mean_nonzero']:6.3f}  {b8['median_nonzero']:5.2f}"
            print(row)

    print("=" * 160)


if __name__ == "__main__":
    main()
