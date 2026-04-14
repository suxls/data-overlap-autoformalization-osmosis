# Eval Kickstart Prompt

Copy-paste this prompt to an AI assistant or teammate to set up and execute all evaluation runs.

---

## PROMPT START

You are helping me run a comprehensive evaluation suite for a research paper on Lean 4 autoformalization. I need inference runs + semantic evaluation across multiple models and benchmarks. Here is everything you need.

---

### CONTEXT

We have a paper studying how SFT priming affects downstream GRPO performance for Lean 4 autoformalization. We need to re-run evaluations to collect:
1. Raw generated Lean 4 outputs (not just aggregate numbers)
2. Compile pass@k (typecheck against Mathlib v4.27.0)
3. Semantic pass@k (compile AND LLM judge score >= 0.7)
4. Mean semantic score (average judge score across all rollouts, and across compiling rollouts only)

---

### MODELS TO EVALUATE (6 total)

**Internal models (4) -- we have checkpoints for these:**

| Model ID | Checkpoint | Thinking | Description |
|---|---|---|---|
| `base-nt` | `Qwen/Qwen3-8B` | Disabled (`enable_thinking=False`) | Base model, no training |
| `sft-nt` | `xiaolesu/OsmosisProofling-SFT` | Disabled | SFT on 20K heterogeneous data, thinking off |
| `grpo-nt` | `xiaolesu/OsmosisProofling-GRPO-NT` | Disabled | GRPO on base model, thinking off |
| `sft-grpo-nt` | `xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT` | Disabled | SFT then GRPO, thinking off |

**External baselines (2) -- download from HuggingFace:**

| Model ID | HuggingFace Repo | Thinking | Description |
|---|---|---|---|
| `kimina-7b` | `AI-MO/Kimina-Autoformalizer-7B` | N/A (Qwen2 arch, no think tokens) | Specialized 7B formalizer, current SOTA at this scale |
| `deepseek-r1-7b` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | Enabled (natural) | Strong general reasoning model, StepFun's base |

---

### BENCHMARKS (3 total)

| Benchmark | Problems | Source |
|---|---|---|
| Gaokao | 495 | Chinese college entrance exam, formalized in Lean 4 |
| ProofNet | 371 | Undergraduate-level theorems |
| Putnam | 672 | Putnam competition problems, formalized in Lean 4 |

Total: 1,538 problems. With n=8 rollouts each = 12,304 generations per model.

---

### INFERENCE CONFIGURATION

**For internal models (base-nt, sft-nt, grpo-nt, sft-grpo-nt):**

System prompt:
```
You are an assistant that translates natural-language math statements into Lean 4 theorems that compile with Mathlib. The preamble `import Mathlib` and `open BigOperators Real Nat Topology Rat` is already provided. Given a math problem or statement, output only a single Lean 4 theorem whose type states the claim, ending the proof with `:= by sorry`. Do not include any proof steps, explanations, comments, or extra text. Wrap your output in a ```lean4``` code block.
```

User message: `{nl_problem}`

Inference params:
- `enable_thinking=False` (for Qwen3 chat template)
- `temperature=1.0`
- `top_p=1.0`
- `max_tokens=16384`
- `n=8` (8 rollouts per problem)

Serve with vLLM on H200 GPUs.

---

**For Kimina-Autoformalizer-7B:**

System prompt:
```
You are an expert in mathematics and Lean 4.
```

User message:
```
Please autoformalize the following problem in Lean 4 with a header. Use the following theorem names: my_favorite_theorem.

{nl_problem}
```

Inference params:
- Standard Qwen2 chat template (no thinking tokens)
- `temperature=0.6`
- `top_p=0.95`
- `max_tokens=2048`
- `n=8` (8 rollouts per problem)

NOTE: Kimina generates the full Lean 4 code including `import Mathlib` header. Do NOT prepend a preamble. The model was trained to output everything from scratch.

---

**For DeepSeek-R1-Distill-Qwen-7B:**

System prompt (same as internal models):
```
You are an assistant that translates natural-language math statements into Lean 4 theorems that compile with Mathlib. The preamble `import Mathlib` and `open BigOperators Real Nat Topology Rat` is already provided. Given a math problem or statement, output only a single Lean 4 theorem whose type states the claim, ending the proof with `:= by sorry`. Do not include any proof steps, explanations, comments, or extra text. Wrap your output in a ```lean4``` code block.
```

User message: `{nl_problem}`

Inference params:
- Let the model think naturally (it will produce `<think>...</think>` traces)
- `temperature=0.6`
- `top_p=0.95`
- `max_tokens=16384`
- `n=8` (8 rollouts per problem)

Record total tokens generated (including think tokens) for each rollout.

---

### OUTPUT FORMAT

For each model x benchmark x rollout, save a JSONL file with one line per rollout:

```json
{
  "problem_id": "gaokao_001",
  "benchmark": "gaokao",
  "model": "sft-grpo-nt",
  "rollout_idx": 0,
  "nl_problem": "The original natural language problem text...",
  "ground_truth_lean4": "theorem foo (n : Nat) : ... := by sorry",
  "generated_lean4": "theorem bar (n : Nat) : ... := by sorry",
  "total_tokens": 142,
  "compiles": true,
  "compile_errors": null
}
```

If your existing eval pipeline outputs a different format, that's fine -- just make sure the raw generated Lean 4 code, the compile result, the NL problem, and the ground truth are all preserved. We need them for the semantic judge step.

---

### STEP 2: SEMANTIC EVALUATION (post-processing)

After inference + compile checking is done, run the Gemini Flash 3 semantic judge on every compiling output.

**Judge prompt (Gemini Flash 3):**

```
You are an expert Lean 4 / Mathlib reviewer. You will be given:

1. A natural-language math problem.
2. A ground-truth Lean 4 theorem statement.
3. A candidate Lean 4 theorem statement produced by a model.

Both the ground truth and the candidate compile successfully. Judge how semantically faithful the candidate is to the ground truth, ignoring superficial differences (variable names, open declarations, import style).

Score on a scale of 0.0 to 1.0:
- 1.0 = semantically identical formalization
- 0.7-0.9 = minor differences that don't change meaning
- 0.3-0.6 = partially captures the statement but with meaningful errors
- 0.0-0.2 = wrong or unrelated formalization

Respond with ONLY a JSON object: {"score": <float>, "reason": "<brief explanation>"}
```

**Judge input for each compiling rollout:**
```
### Natural Language Problem
{nl_problem}

### Ground Truth (Lean 4)
{ground_truth_lean4}

### Candidate (Lean 4)
{generated_lean4}
```

**For non-compiling rollouts:** skip the judge call, assign semantic_score = 0.0.

**Gemini API params:**
- Model: `gemini-2.0-flash` (or whatever version of Gemini Flash 3 you used during training)
- `temperature=0.0` (deterministic judging)
- `max_output_tokens=256`

Save the judge score back into the JSONL:
```json
{
  ...existing fields...,
  "semantic_score": 0.85,
  "semantic_reason": "Correctly captures the theorem statement with minor variable naming differences."
}
```

---

### STEP 3: COMPUTE METRICS

For each model x benchmark combination, compute:

**1. Compile pass@k (k = 1, 4, 8)**

Using the unbiased estimator. For each problem with n=8 rollouts:
- Count c = number of compiling rollouts
- pass@k = 1 - C(n-c, k) / C(n, k)

Average across all problems in the benchmark.

**2. Semantic pass@k (k = 1, 4, 8) with threshold 0.7**

Same estimator, but count c = number of rollouts where `compiles=true AND semantic_score >= 0.7`.

**3. Mean semantic scores**

- **Overall mean**: average `semantic_score` across ALL rollouts (non-compiling = 0.0)
- **Compiling-only mean**: average `semantic_score` across rollouts where `compiles=true`

**4. Token statistics (per benchmark)**

- Mean tokens per rollout
- Median tokens per rollout
- For compiling+semantic rollouts: tokens per correct formalization

---

### EXPECTED OUTPUT TABLES

**Table 1: Main results (compile + semantic pass@k)**

```
Model              | Gaokao          | ProofNet        | Putnam          | Avg
                   | C@1  S@1  C@8   | C@1  S@1  C@8   | C@1  S@1  C@8   | C@1  S@1
-------------------+-----------------+-----------------+-----------------+---------
Base-NT            |                 |                 |                 |
SFT-NT             |                 |                 |                 |
GRPO-NT            |                 |                 |                 |
SFT+GRPO-NT        |                 |                 |                 |
Kimina-7B          |                 |                 |                 |
DeepSeek-R1-D-7B   |                 |                 |                 |
```

Where C@k = compile pass@k, S@k = semantic pass@k (threshold 0.7).

**Table 2: Efficiency**

```
Model              | Putnam Avg Tokens | Putnam Tok/Correct | Gaokao Avg Tokens
-------------------+-------------------+--------------------+------------------
Base-NT            |                   |                    |
SFT+GRPO-NT        |                   |                    |
Kimina-7B          |                   |                    |
DeepSeek-R1-D-7B   |                   |                    |
```

---

### EXECUTION ORDER

1. **Start inference runs for all 6 models in parallel** (if GPU capacity allows). Each model needs ~12K generations across 3 benchmarks with n=8.
   - Internal models: serve each checkpoint with vLLM, run eval script
   - Kimina-7B: download `AI-MO/Kimina-Autoformalizer-7B`, serve with vLLM, use Kimina's prompt format
   - DeepSeek-R1-D-7B: download `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`, serve with vLLM, use our system prompt, let it think

2. **Compile check** all generated outputs against Mathlib v4.27.0 (via `lake env lean`).

3. **Run Gemini judge** on all compiling outputs. Estimated API calls: ~6 models x ~6K compiling outputs = ~36K calls. At ~$0.001/call = ~$36 total.

4. **Compute all metrics** and produce the two tables above.

---

### IMPORTANT NOTES

- Use each model's own prompt format (Kimina gets its own prompt, DeepSeek gets ours). This is standard practice -- see StepFun-Formalizer paper Section 5.2.
- For Kimina, the model outputs full Lean 4 including headers. For compile checking, use the output as-is. For our models, prepend the standard preamble before compile checking (same as during training/eval).
- For DeepSeek-R1, strip the `<think>...</think>` block before compile checking. Record total tokens (including think) for the efficiency comparison.
- The Gemini judge should be called with `temperature=0.0` for reproducibility.
- Save ALL raw outputs. We may need them for qualitative analysis in the paper.

## PROMPT END
