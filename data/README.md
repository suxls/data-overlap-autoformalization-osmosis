# Data

All datasets are hosted on Hugging Face. This folder exists as a reference index; no data files are stored in the repository.

## Training Data

| Dataset | Link | Records | Role |
|---|---|---|---|
| SFT Data | [xiaolesu/OsmosisProofling-SFT-Data](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-SFT-Data) | 20K | Supervised fine-tuning corpus of (natural-language, Lean 4) pairs |
| GRPO Data | [xiaolesu/OsmosisProofling-GRPO-Data](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-GRPO-Data) | 16K | GRPO prompts (30% overlap with SFT) |
| GRPO No-Overlap | [xiaolesu/OsmosisProofling-v2-GRPO-extended-no-overlap](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-v2-GRPO-extended-no-overlap) | 16K | GRPO prompts with 0% SFT overlap |
| GRPO Full-Overlap | [xiaolesu/OsmosisProofling-v2-GRPO-extended-full-overlap](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-v2-GRPO-extended-full-overlap) | 16K | GRPO prompts with 100% SFT overlap |

### Overlap conditions

The central variable of the paper is the fraction of GRPO prompts that also appear in the SFT corpus:

- **0% overlap** &rarr; SFT and GRPO draw from fully disjoint pools.
- **30% overlap** &rarr; ~4.8K of the 16K GRPO prompts coincide with SFT.
- **100% overlap** &rarr; all GRPO prompts are a subset of the SFT corpus.

## Evaluation Benchmarks

| Benchmark | Link | Problems | Description |
|---|---|---|---|
| Gaokao-Formal | [xiaolesu/OsmosisProofling-Gaokao-Bench](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-Gaokao-Bench) | 495 | Chinese college entrance exam problems formalized in Lean 4 |
| PutnamBench | [xiaolesu/OsmosisProofling-Putnam-Bench](https://huggingface.co/datasets/xiaolesu/OsmosisProofling-Putnam-Bench) | 672 | Putnam competition problems formalized in Lean 4 |
