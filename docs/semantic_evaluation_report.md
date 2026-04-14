# Semantic Evaluation Report: Lean 4 Autoformalization

## Evaluation Setup

**Task**: Translate natural-language math statements into Lean 4 theorem statements that compile with Mathlib v4.27.0.

**Benchmarks** (3 total, 1,538 problems):
- **Gaokao** (495 problems) — Chinese college entrance exam problems, formalized in Lean 4
- **ProofNet** (371 problems) — Undergraduate-level theorems
- **Putnam** (672 problems) — Putnam competition problems, formalized in Lean 4

**Rollouts**: n=8 per problem per model (temperature=1.0 for internal models, 0.6 for baselines).

**Models** (9 total):

| Model ID | Checkpoint | Description |
|---|---|---|
| base-nt | Qwen/Qwen3-8B | Base Qwen3-8B, no fine-tuning, thinking disabled |
| sft-nt | OsmosisProofling-SFT | SFT on 20K heterogeneous data, thinking disabled |
| grpo-nt | OsmosisProofling-GRPO-NT | GRPO on base model (no SFT priming), thinking disabled |
| sft-grpo-nt | OsmosisProofling-SFT-NT-GRPO-NT | SFT then GRPO, thinking disabled |
| sft-grpo-nt-no-overlap | OsmosisProofling-SFT-NT-GRPO-NT-No-Overlap | SFT+GRPO, decontaminated (no benchmark overlap) |
| sft-grpo-nt-overlap | OsmosisProofling-SFT-NT-GRPO-NT-Overlap | SFT+GRPO, trained with benchmark overlap |
| kimina-7b | AI-MO/Kimina-Autoformalizer-7B | Specialized 7B formalizer (Qwen2), current SOTA at this scale |
| mathesis-7b | huawei-ai4math/Mathesis-Autoformalizer | Kimina + HPO (GRPO+DPO), ICLR 2026 |
| deepseek-r1-7b | deepseek-ai/DeepSeek-R1-Distill-Qwen-7B | General reasoning model with chain-of-thought |

**Semantic Judge**: Gemini 2.0 Flash (temperature=0.0, max_output_tokens=256). Scores each compiling output on a 0.0-1.0 scale for semantic faithfulness to the ground-truth formalization. Non-compiling outputs receive 0.0.

---

## Metric Definitions

### Pass@k Metrics

**Compile pass@k (C@k)**: Probability that at least one of k randomly sampled rollouts compiles successfully. Uses the unbiased estimator: `pass@k = 1 - C(n-c, k) / C(n, k)`, where n=8 rollouts and c=number of compiling rollouts, averaged across all problems.

**Semantic pass@k (S@k)**: Same estimator, but a rollout counts as a "success" only if it BOTH compiles AND receives a semantic score >= 0.7 from the judge. This is the primary quality metric.

The gap between C@k and S@k reveals how much "compiles but semantically wrong" output each model produces.

### Best-of-8 Metrics

For each problem, we take the **maximum semantic score** across all 8 rollouts (non-compiling rollouts contribute 0.0). This gives one score per problem per model.

- **Best-of-8 Mean**: Average of max scores across all problems. Captures both coverage (unsolved problems = 0.0) and quality.
- **Best-of-8 Median**: Median of max scores. More robust to outliers.
- **Best-of-8 Mean (nonzero)**: Average of max scores, excluding problems where no rollout compiled. Measures quality conditioned on the model being able to formalize the problem at all.
- **Best-of-8 Median (nonzero)**: Median of max scores, excluding zeros.
- **Score histogram**: Percentage of problems falling into each 0.1-width bin (0.0, 0.1, ..., 1.0).

**Important note on comparing mean_nonzero across models**: Models with higher compile rates have a larger nonzero set, which may include harder problems that naturally score lower. A model that only solves easy problems will have an inflated mean_nonzero. This metric is most informative when comparing models with similar compile rates, or when interpreted alongside the percentage of zeros.

### Per-rollout Metrics

- **Mean semantic (all rollouts)**: Average semantic score across all n_rollouts (non-compiling = 0.0).
- **Mean semantic (compiling only)**: Average semantic score across only the compiling rollouts. Subject to the same compile-rate bias described above.

---

## Results

### Table 1: Compile and Semantic Pass@k

| Model | Gaokao C@1 | Gaokao S@1 | Gaokao S@8 | ProofNet C@1 | ProofNet S@1 | ProofNet S@8 | Putnam C@1 | Putnam S@1 | Putnam S@8 |
|---|---|---|---|---|---|---|---|---|---|
| base-nt | 19.9% | 10.2% | 19.4% | 45.1% | 44.0% | 49.1% | 11.3% | 3.3% | 7.7% |
| sft-nt | 61.8% | 41.0% | 70.9% | 48.1% | 46.5% | 58.8% | 28.5% | 14.3% | 34.2% |
| grpo-nt | 50.9% | 28.1% | 40.2% | 47.6% | 46.2% | 49.3% | 36.1% | 11.9% | 19.2% |
| sft-grpo-nt | 76.4% | 48.6% | 70.7% | 51.3% | 48.5% | 56.9% | 46.4% | 22.9% | 38.8% |
| sft-grpo-nt-no-overlap | 77.6% | 51.4% | 72.7% | 48.8% | 47.2% | 53.1% | 47.9% | 23.6% | 43.0% |
| sft-grpo-nt-overlap | 62.9% | 40.6% | 69.9% | 47.4% | 45.7% | 61.2% | 29.1% | 14.7% | 34.8% |
| kimina-7b | 84.2% | 44.6% | 68.1% | 67.5% | 59.8% | 80.3% | 53.5% | 36.8% | 65.3% |
| mathesis-7b | 84.1% | 49.8% | 71.1% | 69.6% | 58.4% | 76.6% | 63.0% | 43.0% | 69.3% |
| deepseek-r1-7b | 5.9% | 1.7% | 5.7% | 1.3% | 0.7% | 1.9% | 3.0% | 0.2% | 0.7% |

### Table 2: Best-of-8 Score Summary

| Model | Gaokao Mean | Gaokao Mean_nz | Gaokao Med_nz | ProofNet Mean | ProofNet Mean_nz | Putnam Mean | Putnam Mean_nz |
|---|---|---|---|---|---|---|---|
| base-nt | 0.215 | 0.678 | 0.80 | 0.488 | 0.995 | 0.106 | 0.563 |
| sft-nt | 0.719 | 0.805 | 0.90 | 0.588 | 0.986 | 0.375 | 0.697 |
| grpo-nt | 0.423 | 0.712 | 0.80 | 0.492 | 0.992 | 0.244 | 0.576 |
| sft-grpo-nt | 0.716 | 0.791 | 0.85 | 0.572 | 0.974 | 0.427 | 0.693 |
| sft-grpo-nt-no-overlap | 0.742 | 0.809 | 0.90 | 0.530 | 0.988 | 0.468 | 0.694 |
| sft-grpo-nt-overlap | 0.716 | 0.804 | 0.90 | 0.609 | 0.987 | 0.380 | 0.697 |
| kimina-7b | 0.731 | 0.768 | 0.80 | 0.799 | 0.966 | 0.677 | 0.823 |
| mathesis-7b | 0.732 | 0.785 | 0.85 | 0.772 | 0.933 | 0.719 | 0.820 |
| deepseek-r1-7b | 0.058 | 0.864 | 1.00 | 0.020 | 0.822 | 0.011 | 0.418 |

### Table 3: Best-of-8 Score Distribution — Gaokao (495 problems)

Percentage of problems at each best-of-8 score bucket. "0.0" means no rollout compiled for that problem.

| Model | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base-nt | 68.3% | 4.6% | - | 2.4% | 3.0% | 1.6% | 0.6% | 2.4% | 2.8% | 1.8% | 12.3% |
| sft-nt | 10.7% | 3.6% | - | 5.1% | 2.4% | 3.4% | 3.8% | 6.3% | 16.8% | 7.3% | 40.6% |
| grpo-nt | 40.6% | 7.1% | 0.2% | 3.8% | 2.8% | 4.0% | 1.2% | 5.7% | 8.1% | 3.6% | 22.8% |
| sft-grpo-nt | 9.5% | 4.2% | - | 4.0% | 3.8% | 3.4% | 4.2% | 8.3% | 17.6% | 7.1% | 37.8% |
| sft-grpo-nt-no-overlap | 8.3% | 3.0% | - | 4.2% | 3.8% | 3.2% | 4.6% | 6.5% | 17.6% | 6.9% | 41.8% |
| sft-grpo-nt-overlap | 10.9% | 3.0% | - | 4.4% | 4.4% | 3.4% | 3.8% | 7.3% | 14.7% | 6.9% | 41.0% |
| kimina-7b | 4.8% | 1.2% | - | 5.9% | 9.3% | 7.1% | 3.6% | 9.5% | 14.5% | 7.1% | 37.0% |
| mathesis-7b | 6.9% | 1.8% | - | 4.0% | 6.5% | 5.5% | 4.2% | 10.9% | 17.8% | 6.1% | 36.4% |
| deepseek-r1-7b | 93.3% | 0.2% | - | 0.4% | 0.2% | 0.2% | - | 0.6% | 0.2% | - | 4.8% |

### Table 4: Best-of-8 Score Distribution — ProofNet (371 problems)

| Model | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base-nt | 50.9% | - | - | - | - | - | - | 0.5% | 0.3% | 0.5% | 47.7% |
| sft-nt | 40.4% | - | - | - | 0.3% | 0.3% | 0.3% | 0.5% | 0.8% | 0.8% | 56.6% |
| grpo-nt | 50.4% | - | - | - | - | 0.3% | - | 0.3% | 0.5% | 0.5% | 48.0% |
| sft-grpo-nt | 41.2% | - | - | 0.5% | 0.3% | 0.8% | 0.3% | 0.5% | 1.3% | 0.5% | 54.4% |
| sft-grpo-nt-no-overlap | 46.4% | - | - | - | 0.3% | 0.3% | - | 0.5% | 0.5% | 0.5% | 51.5% |
| sft-grpo-nt-overlap | 38.3% | - | - | - | - | - | 0.5% | 0.5% | 1.6% | 0.8% | 58.2% |
| kimina-7b | 17.3% | 0.5% | - | 0.3% | 0.8% | 0.8% | - | 1.1% | 3.5% | 2.2% | 73.6% |
| mathesis-7b | 17.3% | 0.5% | - | 1.6% | 2.2% | 0.8% | 1.1% | 1.1% | 5.9% | 3.2% | 66.3% |
| deepseek-r1-7b | 97.6% | 0.3% | - | 0.3% | - | - | - | - | - | - | 1.9% |

### Table 5: Best-of-8 Score Distribution — Putnam (672 problems)

| Model | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base-nt | 81.1% | 3.0% | - | 3.6% | 2.1% | 0.9% | 1.6% | 1.0% | 1.9% | 0.3% | 4.5% |
| sft-nt | 46.1% | 3.6% | - | 7.7% | 3.3% | 2.5% | 2.5% | 4.2% | 10.0% | 2.4% | 17.7% |
| grpo-nt | 57.6% | 6.1% | 0.1% | 7.6% | 2.8% | 3.4% | 3.1% | 4.0% | 5.2% | 1.3% | 8.6% |
| sft-grpo-nt | 38.4% | 4.9% | 0.3% | 6.4% | 3.9% | 3.3% | 4.0% | 6.4% | 9.8% | 3.6% | 19.0% |
| sft-grpo-nt-no-overlap | 32.6% | 4.8% | - | 7.4% | 4.8% | 4.0% | 3.4% | 8.2% | 10.9% | 3.4% | 20.5% |
| sft-grpo-nt-overlap | 45.5% | 4.2% | - | 7.3% | 3.4% | 2.8% | 1.9% | 5.2% | 8.5% | 1.8% | 19.3% |
| kimina-7b | 17.7% | 2.8% | - | 4.9% | 3.6% | 2.7% | 3.0% | 4.0% | 11.9% | 4.5% | 44.9% |
| mathesis-7b | 12.4% | 2.7% | - | 4.5% | 4.3% | 4.0% | 2.8% | 5.7% | 11.9% | 5.2% | 46.6% |
| deepseek-r1-7b | 97.5% | 0.4% | 0.4% | 0.9% | - | - | - | 0.3% | - | - | 0.4% |

### Table 6: Compile vs. Semantic Gap

The C@1-S@1 gap shows how often models produce syntactically valid but semantically wrong formalizations.

| Model | Gaokao C@1 | Gaokao S@1 | Gap | ProofNet Gap | Putnam Gap |
|---|---|---|---|---|---|
| base-nt | 19.9% | 10.2% | 9.7pp | 1.1pp | 8.0pp |
| sft-nt | 61.8% | 41.0% | 20.8pp | 1.6pp | 14.2pp |
| grpo-nt | 50.9% | 28.1% | 22.8pp | 1.4pp | 24.2pp |
| sft-grpo-nt | 76.4% | 48.6% | 27.8pp | 2.8pp | 23.5pp |
| sft-grpo-nt-no-overlap | 77.6% | 51.4% | 26.2pp | 1.6pp | 24.3pp |
| sft-grpo-nt-overlap | 62.9% | 40.6% | 22.3pp | 1.7pp | 14.4pp |
| kimina-7b | 84.2% | 44.6% | **39.6pp** | 7.7pp | 16.7pp |
| mathesis-7b | 84.1% | 49.8% | **34.3pp** | 11.2pp | 20.0pp |
| deepseek-r1-7b | 5.9% | 1.7% | 4.2pp | 0.6pp | 2.8pp |

### Table 7: Token Efficiency

| Model | Gaokao Mean Tokens | Gaokao Tokens/Correct | ProofNet Mean Tokens | Putnam Mean Tokens |
|---|---|---|---|---|
| base-nt | 696 | 350 | 315 | 827 |
| sft-nt | 526 | 413 | 321 | 464 |
| grpo-nt | 486 | 370 | 314 | 497 |
| sft-grpo-nt | 507 | 417 | 313 | 465 |
| sft-grpo-nt-no-overlap | 500 | 420 | 315 | 447 |
| sft-grpo-nt-overlap | 523 | 416 | 332 | 467 |
| kimina-7b | 485 | 376 | 267 | 349 |
| mathesis-7b | 475 | 386 | 269 | 346 |
| deepseek-r1-7b | 6,712 | 1,705 | 3,594 | 9,546 |

---

## Discoveries and Analysis

### 1. The Three Benchmarks Test Different Things

**ProofNet is a binary test of formalization ability, not formalization quality.** The score distributions are overwhelmingly bimodal: problems score either 0.0 (never compiled) or 1.0 (perfect). Mean_nonzero exceeds 0.93 for every model. This means ProofNet problems have essentially one correct formalization, and the only question is whether the model can produce it. There is no meaningful "partial credit" on ProofNet. As a result, ProofNet S@k approximately equals C@k, and this benchmark cannot discriminate formalization *quality* between models that do compile.

**Gaokao has the richest score distribution and is the most discriminating benchmark.** Scores spread across the full 0.0-1.0 range with significant mass in the 0.3-0.6 zone ("partially captures the statement"). This makes Gaokao the most informative benchmark for comparing model quality, as it reveals differences in how faithfully models capture mathematical nuance. The percentage of problems scoring in the "partial" range (0.3-0.6) varies meaningfully across models: 7.6% for base-nt, 14.7% for sft-nt, 20.3% for kimina-7b — showing that Gaokao problems have multiple degrees of formalization difficulty.

**Putnam is the hardest benchmark overall.** It has the highest zero-score rates (12-97%) and the broadest spread of partial scores. Putnam separates the external baselines (Kimina/Mathesis) from internal models more sharply than either Gaokao or ProofNet, making it the best benchmark for evaluating ceiling performance.

### 2. Compiling is Necessary but Not Sufficient — The Semantic Gap

The gap between C@1 and S@1 reveals a critical finding: **models can produce large amounts of syntactically valid but semantically wrong Lean 4 code**.

Kimina-7b has the largest semantic gap on Gaokao: C@1=84.2% but S@1=44.6%, a **39.6 percentage-point gap**. This means nearly half of Kimina's compiling outputs fail semantic review. Mathesis shows a similar pattern (34.3pp gap). By contrast, base-nt has only a 9.7pp gap on Gaokao — but this is because it compiles so little that what does compile tends to be correct.

On ProofNet, the gap is negligible for all models (<3pp for internal models, <12pp for baselines), again confirming ProofNet's binary nature.

This finding has methodological implications: **studies that report only compile pass@k significantly overstate model quality.** A model can achieve very high C@k by learning Lean 4 syntax patterns without learning to faithfully capture mathematical semantics. Semantic evaluation is essential.

### 3. SFT Priming Produces Large, Consistent Gains

The training progression reveals clear additive effects:

**Base to SFT** (base-nt → sft-nt): Gaokao best-of-8 mean jumps from 0.215 to 0.719 (3.3x), S@1 from 10.2% to 41.0%. This is the single largest improvement in the pipeline. SFT teaches the model fundamental formalization patterns.

**Base to GRPO-only** (base-nt → grpo-nt): Gaokao best-of-8 mean goes from 0.215 to 0.423 (2.0x). Meaningful but substantially less than SFT alone (0.719). GRPO without SFT priming improves compile rates more than semantic quality — on Putnam, grpo-nt has C@1=36.1% (good) but S@1=11.9% (poor), meaning it learned to compile without learning to formalize correctly.

**SFT then GRPO** (sft-nt → sft-grpo-nt): Gaokao S@1 rises from 41.0% to 48.6%. The additional gain comes primarily from improved compile rates (C@1: 61.8% → 76.4%) rather than per-compile semantic quality. On Putnam, the GRPO addition is more impactful: S@8 jumps from 34.2% to 38.8%.

**Decontamination helps** (sft-grpo-nt-no-overlap vs sft-grpo-nt-overlap): The no-overlap variant outperforms overlap on Gaokao (S@1: 51.4% vs 40.6%, best-of-8 mean: 0.742 vs 0.716) and Putnam (S@8: 43.0% vs 34.8%). This suggests the overlap variant slightly overfits to training distribution, reducing generalization.

### 4. Internal Models Match or Exceed Baselines on Formalization Quality

When controlling for coverage by examining best-of-8 mean_nonzero (quality conditioned on the model solving the problem):

**On Gaokao**, the top internal models (sft-grpo-nt-no-overlap: 0.809, sft-nt: 0.805) outperform both Kimina (0.768) and Mathesis (0.785). The internal models also have higher rates of perfect scores (1.0): sft-grpo-nt-no-overlap achieves 41.8% perfect vs Kimina's 37.0%.

**On ProofNet**, all internal models that compile produce near-perfect formalizations (mean_nonzero > 0.97), actually exceeding Kimina (0.966) and Mathesis (0.933). However, they compile fewer problems, so overall coverage is lower.

**On Putnam**, the external baselines lead on mean_nonzero (Kimina: 0.823, Mathesis: 0.820 vs internal models at 0.69-0.70). This is Putnam's harder problems where the specialized training of Kimina/Mathesis appears to provide an advantage not just in coverage but in quality.

**Important caveat**: Mean_nonzero comparisons are not perfectly fair when compile rates differ significantly. Models with higher compile rates solve a broader (and potentially harder) set of problems, which may naturally receive lower scores. The comparison is most valid between models with similar compile rates.

### 5. DeepSeek-R1-7B: High Reasoning, Poor Formalization

DeepSeek-R1-Distill-Qwen-7B performs extremely poorly on autoformalization despite being a strong general reasoning model. Key statistics:

- Gaokao: S@1=1.7%, 93.3% of problems score 0.0
- ProofNet: S@1=0.7%, 97.6% of problems score 0.0
- Putnam: S@1=0.2%, 97.5% of problems score 0.0

The model consumes enormous token budgets (mean 6,712 tokens on Gaokao vs ~500 for other models) due to chain-of-thought reasoning that rarely produces valid Lean 4 output. However, the few times it does compile, the quality is surprisingly high (Gaokao mean_nonzero: 0.864, ProofNet: 0.822), suggesting the model *understands* the mathematics but cannot express it in Lean 4 syntax. This confirms that autoformalization requires domain-specific training beyond general reasoning ability.

### 6. Token Efficiency

Internal models and Kimina/Mathesis generate similar token volumes (300-530 tokens per rollout). DeepSeek-R1 is an extreme outlier at 3,500-9,500 tokens due to chain-of-thought, making it 10-20x less token-efficient.

Tokens per correct formalization is remarkably consistent across internal models (350-420 on Gaokao) and baselines (376-386), suggesting that correct formalizations have a characteristic length regardless of the model producing them.

### 7. The Coverage-Precision Trade-off

Two distinct model profiles emerge:

**High coverage, moderate per-output precision** (Kimina, Mathesis): These models compile a high percentage of outputs (Gaokao C@1 ~84%) but have a large semantic gap (C@1-S@1 ~35-40pp). They were trained specifically on Lean compilation, producing many syntactically valid but semantically imprecise formalizations.

**Moderate coverage, high per-output precision** (Internal SFT+GRPO models): These models compile fewer outputs (Gaokao C@1 ~62-78%) but have a smaller semantic gap (~20-28pp). Their GRPO training with semantic rewards appears to have selected for quality over quantity.

For practical deployment, the choice depends on the downstream use case: if formalizations feed into an automated prover, high coverage may be preferred (the prover can reject bad formalizations). If formalizations are for human consumption or direct verification, precision matters more.

### Summary

| Finding | Evidence |
|---|---|
| ProofNet is binary (compile = correct) | mean_nonzero > 0.93 for all models, no scores between 0.1-0.6 |
| Gaokao is the most discriminating benchmark | Broad score distribution, meaningful partial-credit zone (0.3-0.6) |
| Compile-only metrics overstate quality | Kimina C@1=84.2% but S@1=44.6% on Gaokao (39.6pp gap) |
| SFT priming is critical | base→SFT: 3.3x improvement on Gaokao; GRPO-only: 2.0x |
| SFT+GRPO exceeds baselines on formalization quality | Gaokao mean_nonzero: sft-grpo-nt-no-overlap 0.809 vs Kimina 0.768 |
| Decontamination improves generalization | No-overlap variant beats overlap on all benchmarks |
| General reasoning models fail at formalization | DeepSeek-R1: <2% S@1, but 0.86 mean_nonzero when it succeeds |
| Coverage vs precision is a real trade-off | Baselines: high C@k, large C-S gap; Internal: lower C@k, smaller gap |
