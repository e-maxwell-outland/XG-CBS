#!/usr/bin/env bash
# generate_stimuli.sh — generate 5 large random environments and produce all study outputs.
#
# Run from the REPOSITORY ROOT:
#   bash study/generate_stimuli.sh
#
# Prerequisites:
#   - ./build/Planner binary must exist  (run ./run.sh to build)
#   - Python 3 with matplotlib, numpy, pyyaml  (pip install -r requirements.txt)
#   - ffmpeg  (installed in the Docker container; apt-get install ffmpeg otherwise)
#
# Outputs (all under study/):
#   figures/trajectories/env_N.mp4         — animated agent trajectories (from CBS paths)
#   figures/cbs_segments/env_N/seg_K.png   — individual segment images, CBS  ("random")
#   figures/xgcbs_segments/env_N/seg_K.png — individual segment images, XG-CBS ("optimized")
#   results/cbs/env_N/{result.json,env.yaml}
#   results/xgcbs/env_N/{result.json,env.yaml}
#
# Override any parameter via environment variable, e.g.:
#   AGENTS=20 TIME_LIMIT=600 bash study/generate_stimuli.sh
WIDTH=${WIDTH:-16}
HEIGHT=${HEIGHT:-16}
AGENTS=${AGENTS:-16}
OBSTACLES=${OBSTACLES:-0.15}
COST_BOUND=${COST_BOUND:-8}     # XG-CBS explanation cost bound
TIME_LIMIT=${TIME_LIMIT:-300.0} # planner time limit per environment (seconds)
SEG_FACTOR=${SEG_FACTOR:-2.0}   # CBS segments = ceil(XG-CBS segments × factor)

PLANNER_BIN=./build/Planner
STUDY_DIR=study

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Prerequisites ─────────────────────────────────────────────────────────────
[[ -x "$PLANNER_BIN" ]] \
    || error "Planner binary not found at $PLANNER_BIN. Run ./run.sh to build first."
python3 -c "import matplotlib, numpy, yaml" 2>/dev/null \
    || error "Python dependencies missing. Run: pip install -r requirements.txt"
ffmpeg -version &>/dev/null \
    || error "ffmpeg not found. Install with: apt-get install ffmpeg"

# ── Output directories ────────────────────────────────────────────────────────
mkdir -p \
    "$STUDY_DIR/envs" \
    "$STUDY_DIR/results/cbs" \
    "$STUDY_DIR/results/xgcbs" \
    "$STUDY_DIR/figures/trajectories" \
    "$STUDY_DIR/figures/cbs_segments" \
    "$STUDY_DIR/figures/xgcbs_segments"

# ── Helper: find the newest result.json written since a timestamp file ────────
newest_result() {
    find results -maxdepth 3 -name "result.json" -newer "$1" \
        -exec dirname {} \; 2>/dev/null | head -1
}

FAILED=()

for N in 1 2 3 4 5; do
    ENV_NAME="env_${N}"
    ENV_YAML="$STUDY_DIR/envs/${ENV_NAME}.yaml"

    info "════════════════════════════════════════"
    info "  $ENV_NAME"
    info "════════════════════════════════════════"

    # ── 1. Generate random map ────────────────────────────────────────────────
    info "Generating ${WIDTH}×${HEIGHT} map, $AGENTS agents (seed=$N)…"
    python3 generate_map.py \
        --width "$WIDTH" --height "$HEIGHT" \
        --agents "$AGENTS" --obstacles "$OBSTACLES" \
        --seed "$N" -o "$ENV_YAML"

    # ── 2. Run CBS baseline ───────────────────────────────────────────────────
    info "Running CBS on $ENV_NAME…"
    _TS=$(mktemp)
    timeout "${TIME_LIMIT%.*}" \
        $PLANNER_BIN Plan "$ENV_YAML" CBS A "$TIME_LIMIT" 2>&1 | tail -5 || true
    CBS_RAW=$(newest_result "$_TS")
    rm -f "$_TS"
    if [[ -z "$CBS_RAW" ]]; then
        warn "CBS failed or timed out for $ENV_NAME — skipping."
        FAILED+=("$ENV_NAME (CBS planning failed — try a different seed or larger TIME_LIMIT)")
        continue
    fi

    # Copy to stable study location
    CBS_RESULT="$STUDY_DIR/results/cbs/$ENV_NAME"
    mkdir -p "$CBS_RESULT"
    cp "$CBS_RAW/result.json" "$CBS_RAW/env.yaml" "$CBS_RESULT/"

    # ── 3. Run XG-CBS with SR-A* ──────────────────────────────────────────────
    info "Running XG-CBS (SR-A*) on $ENV_NAME…"
    _TS=$(mktemp)
    timeout "${TIME_LIMIT%.*}" \
        $PLANNER_BIN Plan "$ENV_YAML" XG-CBS S-A "$TIME_LIMIT" "$COST_BOUND" 2>&1 | tail -5 || true
    XG_RAW=$(newest_result "$_TS")
    rm -f "$_TS"
    if [[ -z "$XG_RAW" ]]; then
        warn "XG-CBS failed or timed out for $ENV_NAME — skipping."
        FAILED+=("$ENV_NAME (XG-CBS planning failed — try raising TIME_LIMIT or COST_BOUND)")
        continue
    fi

    XGCBS_RESULT="$STUDY_DIR/results/xgcbs/$ENV_NAME"
    mkdir -p "$XGCBS_RESULT"
    cp "$XG_RAW/result.json" "$XG_RAW/env.yaml" "$XGCBS_RESULT/"

    # Read raw segment counts
    CBS_SEG_RAW=$(python3 -c "
import json
d = json.load(open('$CBS_RESULT/result.json'))
print(d['metrics']['segment_cost'])")
    XG_SEG=$(python3 -c "
import json
d = json.load(open('$XGCBS_RESULT/result.json'))
print(d['metrics']['segment_cost'])")

    # Re-label CBS cost fields so it always has ceil(XG_SEG × SEG_FACTOR) segments.
    # CBS uses the "disappearing" model, so its native segment count is meaningless
    # as a study condition — we impose a fixed ratio instead.
    CBS_SEG=$(python3 - "$CBS_RESULT/result.json" "$XG_SEG" "$SEG_FACTOR" <<'PYEOF'
import json, math, sys

result_file = sys.argv[1]
xg_seg      = int(sys.argv[2])
factor      = float(sys.argv[3])

d = json.load(open(result_file))

target_desired = max(xg_seg + 1, math.ceil(xg_seg * factor))
# Cannot have more segments than the shortest path (each segment needs ≥1 step)
min_len = min(len(p) for p in d["plans"].values())
target  = min(target_desired, min_len)

if target <= xg_seg:
    print(f"WARNING: shortest CBS path ({min_len} steps) prevents reaching "
          f"{target_desired} segments — using {target} (same as or close to XG-CBS={xg_seg}). "
          f"Consider a larger map or more obstacles.", file=sys.stderr)

for path in d["plans"].values():
    L = len(path)
    for i, step in enumerate(path):
        # Linearly map index 0 → segment 1, index L-1 → segment target
        step["cost"] = math.floor(i * (target - 1) / max(L - 1, 1)) + 1

d["metrics"]["segment_cost"] = target

with open(result_file, "w") as f:
    json.dump(d, f)

print(target)
PYEOF
)
    info "$ENV_NAME: CBS segments=$CBS_SEG_RAW → re-labelled=$CBS_SEG  |  XG-CBS segments=$XG_SEG"

    # ── 4. Trajectory video (animated MP4 from CBS paths) ─────────────────────
    info "Generating trajectory video…"
    python3 visualize.py "$CBS_RESULT" \
        --animate -o "$STUDY_DIR/figures/trajectories/${ENV_NAME}.mp4"

    # ── 5. Individual segment PNGs — CBS ("random" segmentation) ─────────────
    info "Generating CBS segment images ($CBS_SEG segments)…"
    python3 visualize.py "$CBS_RESULT" \
        --segments-dir "$STUDY_DIR/figures/cbs_segments/$ENV_NAME"

    # ── 6. Individual segment PNGs — XG-CBS ("optimized" segmentation) ────────
    info "Generating XG-CBS segment images ($XG_SEG segments)…"
    python3 visualize.py "$XGCBS_RESULT" \
        --segments-dir "$STUDY_DIR/figures/xgcbs_segments/$ENV_NAME"

    info "$ENV_NAME complete."
    echo
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo "════════════════════════════════════════"
if [[ ${#FAILED[@]} -eq 0 ]]; then
    info "All 5 environments completed successfully."
    info "Outputs under $STUDY_DIR/:"
    info "  figures/trajectories/    — 5 MP4 trajectory videos"
    info "  figures/cbs_segments/    — per-segment PNGs, CBS  (\"random\")"
    info "  figures/xgcbs_segments/  — per-segment PNGs, XG-CBS (\"optimized\")"
    info "  results/cbs/             — raw CBS planner output"
    info "  results/xgcbs/           — raw XG-CBS planner output"
else
    warn "The following environments encountered errors:"
    for F in "${FAILED[@]}"; do
        warn "  • $F"
    done
    exit 1
fi
