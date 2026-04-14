# Data Overlap as a Post-Training Hyperparameter for Autoformalization

This repository accompanies the paper **"Data Overlap as a Post-Training Hyperparameter for Autoformalization"** and provides the release artifacts needed for reproducibility: the paper, evaluation scripts, and pointers to external artifacts.

## Repository Layout

- `paper/`: final paper PDF and LaTeX source.
- `scripts/`: compile evaluation runner, semantic judge, and metrics aggregation scripts.
- `docs/`: semantic evaluation report and evaluation kickstart prompt.

## Paper

- PDF: `paper/paper_v4.pdf`
- LaTeX source: `paper/paper_v4.tex`

## Reproducibility Quickstart

1. Create Python environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Prepare benchmark parquet files (`proofnet.parquet`, `gaokao.parquet`, `putnam.parquet`) in `benchmarks_v3/` or set a custom path via `BENCHMARKS_DIR`.

3. Run compile evaluation:

```bash
BENCHMARKS_DIR="$(pwd)/benchmarks_v3" \
./scripts/run_compile.sh "xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT" sft-grpo-nt 0 8003
```

4. Run semantic judging:

```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
python scripts/run_judge.py \
  --model-dir scripts/results/sft-grpo-nt \
  --model-slug sft-grpo-nt \
  --benchmarks-dir benchmarks_v3
```

5. Compute metrics:

```bash
python scripts/compute_metrics.py --results-dir scripts/results
```

## External Artifacts

### Weights & Biases (W&B)

- Training/eval dashboards: `TODO: add your public W&B report links`

### Hugging Face Models

- `https://huggingface.co/xiaolesu/OsmosisProofling-SFT`
- `https://huggingface.co/xiaolesu/OsmosisProofling-GRPO-NT`
- `https://huggingface.co/xiaolesu/OsmosisProofling-SFT-NT-GRPO-NT`
- `https://huggingface.co/AI-MO/Kimina-Autoformalizer-7B`
- `https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`

### Datasets

- Gaokao benchmark reference: `https://arxiv.org/abs/2305.12474`
- PutnamBench reference: `https://arxiv.org/abs/2407.11214`
- ProofNet reference: `https://arxiv.org/abs/2302.12433`
- Release dataset links used in experiments: `TODO: add canonical dataset URLs`

## Notes

- Large artifacts (checkpoints, raw datasets, logs) are intentionally not tracked in git.
- Secrets (API keys/tokens) must be provided via environment variables.

## Citation

See `CITATION.cff` for machine-readable citation metadata.
