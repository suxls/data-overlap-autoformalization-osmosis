# Artifacts

All models, datasets, and benchmarks are hosted on Hugging Face. This folder serves as a reference index.

## Models

All checkpoints are Qwen3-8B with thinking disabled.

| Model | HuggingFace | Description |
|---|---|---|
| SFT | [xiaolesu/OsmosisProofling-SFT](https://huggingface.co/xiaolesu/OsmosisProofling-SFT) | SFT on 20K heterogeneous (NL, Lean 4) pairs |
| GRPO | [xiaolesu/OsmosisProofling-GRPO-NT](https://huggingface.co/xiaolesu/OsmosisProofling-GRPO-NT) | GRPO on base model (no SFT priming) |
| SFT+GRPO-0% | [xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT-No-Overlap](https://huggingface.co/xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT-No-Overlap) | SFT then GRPO, fully disjoint data **(best)** |
| SFT+GRPO-30% | [xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT](https://huggingface.co/xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT) | SFT then GRPO, 30% prompt overlap |
| SFT+GRPO-100% | [xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT-Overlap](https://huggingface.co/xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT-Overlap) | SFT then GRPO, full overlap |

## Quick Start with vLLM

```python
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer

model_name = "xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT-No-Overlap"
model = LLM(model_name, max_model_len=32768)

tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

problem = (
    "Let S be a set of rational numbers closed under addition and multiplication, "
    "with the property that for every rational r exactly one of r in S, -r in S, "
    "r = 0 holds. Prove that S is the set of all positive rationals."
)

messages = [
    {
        "role": "system",
        "content": (
            "You are an assistant that translates natural-language math statements "
            "into Lean 4 theorems that compile with Mathlib. The preamble "
            "`import Mathlib` and `open BigOperators Real Nat Topology Rat` is "
            "already provided. Given a math problem or statement, output only a "
            "single Lean 4 theorem whose type states the claim, ending the proof "
            "with `:= by sorry`. Do not include any proof steps, explanations, "
            "comments, or extra text. Wrap your output in a ```lean4 code block."
        ),
    },
    {"role": "user", "content": problem},
]

text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
    enable_thinking=False,
)

sampling_params = SamplingParams(temperature=1.0, top_p=1.0, max_tokens=16384)
output = model.generate(text, sampling_params=sampling_params)
print(output[0].outputs[0].text)
```

## Training Data

| Dataset | HuggingFace | Records | Role |
|---|---|---|---|
| SFT Data | [xiaolesu/OsmosisProofling-SFT-Data](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-SFT-Data) | 20K | Supervised fine-tuning corpus of (NL, Lean 4) pairs |
| GRPO Data | [xiaolesu/OsmosisProofling-GRPO-Data](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-GRPO-Data) | 16K | GRPO prompts (30% overlap with SFT) |
| GRPO No-Overlap | [xiaolesu/OsmosisProofling-v2-GRPO-extended-no-overlap](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-v2-GRPO-extended-no-overlap) | 16K | GRPO prompts with 0% SFT overlap |
| GRPO Full-Overlap | [xiaolesu/OsmosisProofling-v2-GRPO-extended-full-overlap](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-v2-GRPO-extended-full-overlap) | 16K | GRPO prompts with 100% SFT overlap |

### Overlap conditions

The central variable of the paper is the fraction of GRPO prompts that also appear in the SFT corpus:

- **0% overlap** -- SFT and GRPO draw from fully disjoint pools.
- **30% overlap** -- ~4.8K of the 16K GRPO prompts coincide with SFT.
- **100% overlap** -- all GRPO prompts are a subset of the SFT corpus.

## Evaluation Benchmarks

| Benchmark | HuggingFace | Problems | Description |
|---|---|---|---|
| Gaokao-Formal | [xiaolesu/OsmosisProofling-Gaokao-Bench](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-Gaokao-Bench) | 495 | Chinese college entrance exam problems formalized in Lean 4 |
| PutnamBench | [xiaolesu/OsmosisProofling-Putnam-Bench](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-Putnam-Bench) | 672 | Putnam competition problems formalized in Lean 4 |
