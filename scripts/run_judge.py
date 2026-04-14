#!/usr/bin/env python3
"""Offline semantic judge for eval_v2.

Reads osmosis eval output (results_*.json + samples_*.jsonl) and benchmark
parquets, calls Gemini to judge semantic faithfulness of compiling samples,
writes judged/<bench>.jsonl.

Usage:
    python eval_v2/run_judge.py --model-dir eval_v2/results/grpo-tk \
        --benchmarks-dir eval/benchmarks_v3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from google import genai
from google.genai.types import GenerateContentConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gemini-3-flash-preview")
MAX_JUDGE_RETRIES = 3
CONCURRENCY = 32

BENCHMARKS = ["proofnet", "gaokao", "putnam"]

JUDGE_SYSTEM_PROMPT = """\
You are an expert Lean 4 / Mathlib reviewer. You will be given:
1. A ground-truth Lean 4 theorem statement.
2. A candidate Lean 4 theorem statement produced by a model.

Both compile successfully. Judge how semantically faithful
the candidate is to the ground truth, ignoring superficial differences
(variable names, open declarations, import style).

Score on a scale of 0.0 to 1.0:
- 1.0 = semantically identical formalization
- 0.7-0.9 = minor differences that don't change meaning
- 0.3-0.6 = partially captures the statement but with meaningful errors
- 0.0-0.2 = wrong or unrelated formalization

Respond with ONLY a JSON object: {"score": <float>, "reason": "<brief explanation>"}
"""

JUDGE_USER_TEMPLATE = """\
Evaluate the semantic similarity of these two Lean 4 formalizations:

**Generated formalization:**
```lean4
{generated}
```

**Ground truth formalization:**
```lean4
{ground_truth}
```"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise json.JSONDecodeError("No JSON object found", text, 0)


async def call_judge(client: genai.Client, candidate: str, ground_truth: str) -> tuple[float, str]:
    prompt = JUDGE_SYSTEM_PROMPT + "\n\n" + JUDGE_USER_TEMPLATE.format(
        generated=candidate, ground_truth=ground_truth
    )
    last_error = None
    for attempt in range(MAX_JUDGE_RETRIES):
        try:
            response = await client.aio.models.generate_content(
                model=JUDGE_MODEL,
                contents=prompt,
                config=GenerateContentConfig(max_output_tokens=1024),
            )
            text = None
            try:
                text = response.text
            except Exception:
                pass
            if not text or not text.strip():
                raise ValueError(f"Empty response (attempt {attempt + 1})")
            result = _extract_json(text)
            score = float(result.get("score", 0.0))
            reason = str(result.get("reason", result.get("reasoning", "")))
            return max(0.0, min(1.0, score)), reason
        except Exception as e:
            last_error = e
            logger.warning("Judge attempt %d/%d failed: %s", attempt + 1, MAX_JUDGE_RETRIES, e)
            await asyncio.sleep(1)
    raise ValueError(f"Judge failed after {MAX_JUDGE_RETRIES} attempts: {last_error}")


def load_eval_data(model_dir: Path, bench: str) -> tuple[list[dict], list[dict]]:
    """Load results (runs) and samples for a benchmark."""
    compile_dir = model_dir / f"{bench}__compile"
    if not compile_dir.exists():
        return [], []

    results_files = sorted(compile_dir.rglob("results_*.json"))
    samples_files = sorted(compile_dir.rglob("samples_*.jsonl"))

    if not results_files or not samples_files:
        return [], []

    with open(results_files[-1]) as f:
        results_data = json.load(f)
    runs = results_data.get("runs", [])

    samples = []
    with open(samples_files[-1]) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))

    return runs, samples


def extract_lean_code(text: str) -> str | None:
    for pattern in [r"```lean4\s*\n(.*?)```", r"```(?:lean)?\s*\n(.*?)```"]:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return None


async def judge_benchmark(
    model_dir: Path,
    model_slug: str,
    bench: str,
    benchmarks_dir: Path,
    client: genai.Client,
) -> list[dict]:
    """Judge all samples for a single benchmark."""
    runs, samples = load_eval_data(model_dir, bench)
    if not runs or not samples:
        logger.warning("No data for %s/%s", model_slug, bench)
        return []

    parquet_path = benchmarks_dir / f"{bench}.parquet"
    df = pd.read_parquet(parquet_path)

    compile_map: dict[tuple[int, int], tuple[bool, int]] = {}
    for r in runs:
        score = list(r["scores"].values())[0] if r["scores"] else 0.0
        compile_map[(r["row_index"], r["run_index"])] = (score >= 1.0, r.get("tokens", 0))

    entries = []
    for s in samples:
        row_idx = s["row_index"]
        run_idx = s["run_index"]
        msgs = s["messages"]

        assistant_msg = next((m for m in msgs if m["role"] == "assistant"), None)
        user_msg = next((m for m in msgs if m["role"] == "user"), None)
        if not assistant_msg:
            continue

        generated_text = assistant_msg.get("content", "")
        nl_problem = user_msg["content"] if user_msg else ""
        gt_lean4 = str(df.iloc[row_idx]["ground_truth"]) if row_idx < len(df) else ""
        compiles, tokens = compile_map.get((row_idx, run_idx), (False, 0))

        entries.append({
            "problem_id": f"{bench}_{row_idx:04d}",
            "benchmark": bench,
            "model": model_slug,
            "rollout_idx": run_idx,
            "row_index": row_idx,
            "nl_problem": nl_problem,
            "ground_truth_lean4": gt_lean4,
            "generated_lean4": generated_text,
            "total_tokens": tokens,
            "compiles": compiles,
            "semantic_score": 0.0,
            "semantic_reason": "",
        })

    compiling_entries = [e for e in entries if e["compiles"]]
    logger.info(
        "%s/%s: %d total samples, %d compiling → judging",
        model_slug, bench, len(entries), len(compiling_entries),
    )

    sem = asyncio.Semaphore(CONCURRENCY)

    async def judge_one(entry: dict) -> None:
        code = extract_lean_code(entry["generated_lean4"])
        if not code:
            entry["semantic_score"] = 0.0
            entry["semantic_reason"] = "no lean code extracted"
            return
        async with sem:
            try:
                score, reason = await call_judge(client, code, entry["ground_truth_lean4"])
                entry["semantic_score"] = score
                entry["semantic_reason"] = reason
            except Exception as e:
                logger.error("Judge failed for %s rollout %d: %s", entry["problem_id"], entry["rollout_idx"], e)
                entry["semantic_score"] = 0.0
                entry["semantic_reason"] = f"judge_error: {e}"

    tasks = [judge_one(e) for e in compiling_entries]
    done = 0
    batch_size = 100
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i + batch_size]
        await asyncio.gather(*batch)
        done += len(batch)
        logger.info("  %s/%s: judged %d/%d compiling samples", model_slug, bench, done, len(compiling_entries))

    return entries


async def main_async(model_dir: Path, model_slug: str, benchmarks_dir: Path) -> None:
    client = genai.Client(api_key=GEMINI_API_KEY)
    judged_dir = model_dir / "judged"
    judged_dir.mkdir(exist_ok=True)

    for bench in BENCHMARKS:
        logger.info("Judging %s / %s ...", model_slug, bench)
        entries = await judge_benchmark(model_dir, model_slug, bench, benchmarks_dir, client)
        if not entries:
            continue

        out_path = judged_dir / f"{bench}.jsonl"
        with open(out_path, "w") as f:
            for e in sorted(entries, key=lambda x: (x["row_index"], x["rollout_idx"])):
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        logger.info("Wrote %d entries to %s", len(entries), out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline semantic judge for eval_v2")
    parser.add_argument("--model-dir", required=True, help="Path to model results dir")
    parser.add_argument("--model-slug", required=True, help="Short model name for output")
    parser.add_argument("--benchmarks-dir", required=True, help="Path to benchmarks_v3/")
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required to run semantic judging.")

    asyncio.run(main_async(
        Path(args.model_dir),
        args.model_slug,
        Path(args.benchmarks_dir),
    ))


if __name__ == "__main__":
    main()
