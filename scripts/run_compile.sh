#!/usr/bin/env bash
set -euo pipefail
# ============================================================
#  eval_v2 compile-only runner
#
#  USAGE:
#    ./run_compile.sh MODEL SLUG GPU PORT
#    ./run_compile.sh "xiaolesu/OsmosisProofling-GRPO-TK" grpo-tk 2 8003
#
#  Thinking is ON by default. To disable:
#    QWEN3_DISABLE_THINKING=1 ./run_compile.sh ...
# ============================================================

MODEL="${1:?Usage: $0 MODEL SLUG GPU PORT}"
SLUG="${2:?Usage: $0 MODEL SLUG GPU PORT}"
VLLM_GPU="${3:-1}"
VLLM_PORT="${4:-8003}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
N="${N:-8}"
BATCH_SIZE="${BATCH_SIZE:-16}"
MAX_TURNS=1
GPU_MEM_UTIL=0.85

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCKER_IMAGE="lean-eval-bench"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"
BENCHMARKS_DIR="${BENCHMARKS_DIR:-$SCRIPT_DIR/../benchmarks_v3}"

if [ ! -d "$BENCHMARKS_DIR" ]; then
    echo "ERROR: BENCHMARKS_DIR not found: $BENCHMARKS_DIR" >&2
    echo "Set BENCHMARKS_DIR to the folder containing proofnet.parquet, gaokao.parquet, putnam.parquet." >&2
    exit 1
fi

export HF_HOME="/opt/dlami/nvme/hf_cache"
export HUGGINGFACE_HUB_CACHE="/opt/dlami/nvme/hf_cache/hub"
mkdir -p "$HF_HOME"

EXTRA_DOCKER_ENV=()
if [[ "${QWEN3_DISABLE_THINKING:-0}" == "1" ]]; then
    EXTRA_DOCKER_ENV=( -e QWEN3_DISABLE_THINKING=1 )
fi

RESULTS_ROOT="$SCRIPT_DIR/results"
MODEL_DIR="$RESULTS_ROOT/$SLUG"
LOG_DIR="$MODEL_DIR/logs"
mkdir -p "$LOG_DIR"

LOG="$LOG_DIR/run.log"

DATASETS=("proofnet.parquet" "gaokao.parquet" "putnam.parquet")
BENCHES=("proofnet"          "gaokao"          "putnam")

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

start_vllm() {
    log "Starting vLLM: $MODEL (max_model_len=$MAX_MODEL_LEN, GPU=$VLLM_GPU, port=$VLLM_PORT)"
    CUDA_VISIBLE_DEVICES=$VLLM_GPU python3 -m vllm.entrypoints.openai.api_server \
        --model "$MODEL" \
        --host 0.0.0.0 --port "$VLLM_PORT" \
        --tensor-parallel-size 1 \
        --max-model-len "$MAX_MODEL_LEN" \
        --gpu-memory-utilization "$GPU_MEM_UTIL" \
        --dtype auto \
        --trust-remote-code \
        > "$LOG_DIR/vllm.log" 2>&1 &
    VLLM_PID=$!
    for i in $(seq 1 600); do
        if ! kill -0 "$VLLM_PID" 2>/dev/null; then
            log "ERROR: vLLM process died (check $LOG_DIR/vllm.log)"; return 1
        fi
        curl -s "http://localhost:$VLLM_PORT/health" > /dev/null 2>&1 && {
            log "vLLM ready (${i}s)"; return 0
        }
        sleep 1
    done
    log "ERROR: vLLM failed to start within 600s"; return 1
}

stop_vllm() {
    log "Stopping vLLM..."
    kill "$VLLM_PID" 2>/dev/null || true
    wait "$VLLM_PID" 2>/dev/null || true
    sleep 3
}

run_one() {
    local dataset="$1" bench_slug="$2"
    local tag="${bench_slug}__compile"
    local outdir="$MODEL_DIR/$tag"

    if find "$outdir" -name "results_*.json" 2>/dev/null | head -1 | grep -q .; then
        local s
        s=$(cat "$(find "$outdir" -name 'results_*.json' | sort | tail -1)" 2>/dev/null \
            | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
        if [ "$s" = "completed" ]; then log "SKIP $tag (already completed)"; return 0; fi
    fi

    log "START $tag"
    local cname="eval-v2-${SLUG}-compile-${bench_slug}"
    docker rm -f "$cname" 2>/dev/null || true

    docker run --network host \
        --name "$cname" \
        -e LEAN_WORKDIR=/workspace/lean_project \
        -e OPENAI_API_KEY="dummy" \
        -e GEMINI_API_KEY="$GEMINI_API_KEY" \
        "${EXTRA_DOCKER_ENV[@]}" \
        -v "$MODEL_DIR:/workspace/results" \
        -v "$BENCHMARKS_DIR:/workspace/benchmarks_v3:ro" \
        "$DOCKER_IMAGE" \
        osmosis eval \
            -m eval.eval_server:agent_loop \
            -d "/workspace/benchmarks_v3/${dataset}" \
            --eval-fn "eval.eval_rewards:eval_compile_only" \
            --model "$MODEL" \
            --base-url "http://localhost:$VLLM_PORT/v1" \
            --api-key dummy \
            --n "$N" --batch-size "$BATCH_SIZE" --max-turns "$MAX_TURNS" \
            --fresh --log-samples \
            -o "/workspace/results/${tag}" \
        > "$MODEL_DIR/${tag}.stdout" 2>&1

    local rc=$?
    log "DONE $tag (exit=$rc)"
    docker rm -f "$cname" 2>/dev/null || true

    local latest
    latest=$(find "$outdir" -name "results_*.json" 2>/dev/null | sort | tail -1)
    if [ -n "$latest" ]; then
        chmod a+r "$latest" 2>/dev/null || sudo chmod a+r "$latest" 2>/dev/null || true
        python3 -c "
import json
with open('$latest') as f:
    d = json.load(f)
ef = list(d['summary']['eval_fns'].values())[0]
parts = [f'pass_at_{k}={ef[f\"pass_at_{k}\"]:.4f}' for k in [1,2,4,8] if f'pass_at_{k}' in ef]
print(f'  RESULT $tag: {\" \".join(parts)}')
" | tee -a "$LOG" 2>/dev/null || true
    fi
    return $rc
}

# ── main ─────────────────────────────────────────────────────
log "=========================================================="
log "  Model : $MODEL"
log "  Slug  : $SLUG"
log "  GPU   : $VLLM_GPU    Port: $VLLM_PORT"
log "  Output: $MODEL_DIR"
log "  N=$N  BATCH_SIZE=$BATCH_SIZE  MAX_MODEL_LEN=$MAX_MODEL_LEN"
if [[ ${#EXTRA_DOCKER_ENV[@]} -gt 0 ]]; then
    log "  Thinking: DISABLED"
else
    log "  Thinking: ENABLED"
fi
log "=========================================================="

log "Pre-downloading model..."
python3 -c "
from huggingface_hub import snapshot_download
import os
os.environ['HF_HOME'] = '/opt/dlami/nvme/hf_cache'
snapshot_download('$MODEL', cache_dir='/opt/dlami/nvme/hf_cache/hub')
print('Done.')
" 2>&1 | tee -a "$LOG"
log "Model downloaded."

if start_vllm; then
    pids=()
    for i in "${!BENCHES[@]}"; do
        run_one "${DATASETS[$i]}" "${BENCHES[$i]}" &
        pids+=($!)
    done
    for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null; done
    stop_vllm
else
    log "FATAL: vLLM failed to start - aborting"
    exit 1
fi

log ""
log "=========================================================="
log "  COMPILATION COMPLETE"
log "=========================================================="
