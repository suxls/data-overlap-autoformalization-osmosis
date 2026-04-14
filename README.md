# Data Overlap as a Post-Training Hyperparameter for Autoformalization

**Xiaole Su** (Northeastern University, Osmosis AI) &middot; **Kasey Zhang** (Osmosis AI) &middot; **Andy Lyu** (Osmosis AI)

[[Paper]](paper/paper_v4.pdf)

## Abstract

Supervised fine-tuning (SFT) followed by Group Relative Policy Optimization (GRPO) is a common post-training recipe for Lean 4 autoformalization. We conduct a controlled ablation over SFT-GRPO data overlap, evaluating Qwen3-8B (thinking disabled) post-trained for Lean 4 autoformalization under six conditions that differ solely in training recipe: a base model, SFT-only, GRPO-only, and three SFT+GRPO configurations where 0%, 30%, or 100% of the GRPO prompts coincide with the SFT corpus. Keeping SFT and GRPO data disjoint consistently outperforms full overlap at zero additional compute cost. Evaluating on Gaokao-Formal and PutnamBench under both compile pass@k and semantic pass@k (assessed by an LLM judge), we find that: (1) lower overlap is monotonically associated with higher compilation and semantic accuracy; (2) at 0% overlap, GRPO yields a 10.4 percentage-point (pp) semantic gain over SFT alone on Gaokao; (3) at 100% overlap, both compilation and semantic accuracy remain flat, rendering the GRPO stage effectively redundant; (4) dual-metric evaluation reveals compile-semantic gaps exceeding 30 pp for the highest-compiling models, a disparity invisible under compile-only benchmarking.

## Results

Compile pass@k (C@k) and semantic pass@k (S@k) on Gaokao-Formal (495 problems) and PutnamBench (672 problems). &Delta;: compile-semantic gap (C@1 &minus; S@1).

| Model | Gaokao C@1 | Gaokao S@1 | Gaokao S@8 | Gaokao &Delta; | Putnam C@1 | Putnam S@1 | Putnam S@8 | Putnam &Delta; |
|---|---|---|---|---|---|---|---|---|
| Base | 19.9 | 10.2 | 19.4 | 9.7 | 11.3 | 3.3 | 7.7 | 8.0 |
| SFT | 61.8 | 41.0 | 70.9 | 20.8 | 28.5 | 14.3 | 34.2 | 14.2 |
| GRPO-only | 50.9 | 28.1 | 40.2 | 22.8 | 36.1 | 11.9 | 19.2 | 24.2 |
| **SFT+GRPO-0%** | **77.6** | **51.4** | **72.7** | 26.2 | **47.9** | **23.6** | **43.0** | 24.3 |
| SFT+GRPO-30% | 76.4 | 48.6 | 70.7 | 27.8 | 46.4 | 22.9 | 38.8 | 23.5 |
| SFT+GRPO-100% | 62.9 | 40.6 | 69.9 | 22.3 | 29.1 | 14.7 | 34.8 | 14.4 |
| Kimina-7B | 84.2 | 44.6 | 68.1 | 39.6 | 53.5 | 36.8 | 65.3 | 16.7 |
| Mathesis-7B | 84.1 | 49.8 | 71.1 | 34.3 | 63.0 | 43.0 | 69.3 | 20.0 |

## Artifacts

Models, datasets, and benchmarks are listed in [`artifacts/`](artifacts/).

## Citation

```bibtex
@article{su2026dataoverlap,
  title   = {Data Overlap as a Post-Training Hyperparameter for Autoformalization},
  author  = {Xiaole Su and Kasey Zhang and Andy Lyu},
  year    = {2026},
  url     = {https://github.com/suxls/data-overlap-autoformalization}
}
```

## License

[MIT](LICENSE)
