#!/usr/bin/env bash
# generate_stimuli.sh — generate 5 large random environments and produce all study outputs.
#
# Run from the REPOSITORY ROOT:
#   bash study/generate_stimuli.sh
#
# Prerequisites:
#   - ./build/Planner binary must exist  (run ./run.sh to build)
#   - Python 3 with matplotlib, numpy, pyyaml  (pip install -r requirements.txt)
#   - ffmpeg  (installed in the Docker container; apt-get update && apt-get install -y ffmpeg)
#
# Design: only XG-CBS is run. The "random" condition reuses the same XG-CBS
# trajectories but re-slices them into ceil(N × SEG_FACTOR) time-based segments,
# isolating segmentation count as the sole variable between conditions.
#
# Outputs (all under study/):
#   figures/trajectories/env_N.mp4            — animated agent trajectories
#   figures/random_segments/env_N/seg_K.png   — re-sliced segments ("random")
#   figures/optimal_segments/env_N/seg_K.png  — XG-CBS segments ("optimized")
#   results/optimal/env_N/{result.json,env.yaml}
#   results/random/env_N/{result.json,env.yaml}
#
# Override any parameter via environment variable, e.g.:
#   AGENTS=20 TIME_LIMIT=600 bash study/generate_stimuli.sh
WIDTH=${WIDTH:-16}
HEIGHT=${HEIGHT:-16}
AGENTS=${AGENTS:-16}
OBSTACLES=${OBSTACLES:-0.15}
COST_BOUND=${COST_BOUND:-8}     # XG-CBS explanation cost bound
TIME_LIMIT=${TIME_LIMIT:-300.0} # planner time limit per environment (seconds)
SEG_FACTOR=${SEG_FACTOR:-2.0}   # random segments = ceil(optimal segments × factor)

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
    || error "ffmpeg not found. Install with: apt-get update && apt-get install -y ffmpeg"

# ── Output directories ────────────────────────────────────────────────────────
mkdir -p \
    "$STUDY_DIR/envs" \
    "$STUDY_DIR/results/optimal" \
    "$STUDY_DIR/results/random" \
    "$STUDY_DIR/figures/trajectories" \
    "$STUDY_DIR/figures/optimal_segments" \
    "$STUDY_DIR/figures/random_segments"

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

    # ── 2. Run XG-CBS (SR-A*) — the one and only planner call ────────────────
    info "Running XG-CBS (SR-A*) on $ENV_NAME…"
    _TS=$(mktemp)
    timeout "${TIME_LIMIT%.*}" \
        $PLANNER_BIN Plan "$ENV_YAML" XG-CBS S-A "$TIME_LIMIT" "$COST_BOUND" 2>&1 | tail -5 || true
    XG_RAW=$(newest_result "$_TS")
    rm -f "$_TS"
    if [[ -z "$XG_RAW" ]]; then
        warn "XG-CBS failed or timed out for $ENV_NAME — skipping."
        FAILED+=("$ENV_NAME (XG-CBS failed — try raising TIME_LIMIT or COST_BOUND)")
        continue
    fi

    # Stable result locations
    OPT_RESULT="$STUDY_DIR/results/optimal/$ENV_NAME"
    RND_RESULT="$STUDY_DIR/results/random/$ENV_NAME"
    mkdir -p "$OPT_RESULT" "$RND_RESULT"
    cp "$XG_RAW/result.json" "$XG_RAW/env.yaml" "$OPT_RESULT/"

    # ── 3. Build "random" condition: same paths, more segments ────────────────
    # Copy XG-CBS result then re-label cost fields to create ceil(N×factor) segs.
    cp "$OPT_RESULT/result.json" "$OPT_RESULT/env.yaml" "$RND_RESULT/"

    OPT_SEG=$(python3 -c "
import json
d = json.load(open('$OPT_RESULT/result.json'))
print(d['metrics']['segment_cost'])")

    RND_SEG=$(python3 - "$RND_RESULT/result.json" "$OPT_SEG" "$SEG_FACTOR" <<'PYEOF'
import json, math, sys

result_file = sys.argv[1]
opt_seg      = int(sys.argv[2])
factor       = float(sys.argv[3])

d = json.load(open(result_file))

target_desired = max(opt_seg + 1, math.ceil(opt_seg * factor))
# Cannot have more segments than the shortest path (each segment needs ≥1 step)
min_len = min(len(p) for p in d["plans"].values())
target  = min(target_desired, min_len)

if target <= opt_seg:
    print(f"WARNING: shortest path ({min_len} steps) limits random condition to "
          f"{target} segments instead of {target_desired}. "
          f"Consider a larger map or fewer obstacles.", file=sys.stderr)

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

    info "$ENV_NAME: optimal=$OPT_SEG segments  |  random=$RND_SEG segments"

    # ── 4. Trajectory video (from XG-CBS paths) ───────────────────────────────
    info "Generating trajectory video…"
    python3 visualize.py "$OPT_RESULT" \
        --animate -o "$STUDY_DIR/figures/trajectories/${ENV_NAME}.mp4"

    # ── 5. Segment PNGs — "optimized" condition ───────────────────────────────
    info "Generating optimal segment images ($OPT_SEG segments)…"
    python3 visualize.py "$OPT_RESULT" \
        --segments-dir "$STUDY_DIR/figures/optimal_segments/$ENV_NAME"

    # ── 6. Segment PNGs — "random" condition (same paths, more segments) ──────
    info "Generating random segment images ($RND_SEG segments)…"
    python3 visualize.py "$RND_RESULT" \
        --segments-dir "$STUDY_DIR/figures/random_segments/$ENV_NAME"

    info "$ENV_NAME complete."
    echo
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo "════════════════════════════════════════"
if [[ ${#FAILED[@]} -eq 0 ]]; then
    info "All 5 environments completed successfully."
    info "Outputs under $STUDY_DIR/:"
    info "  figures/trajectories/      — 5 MP4 trajectory videos"
    info "  figures/optimal_segments/  — per-segment PNGs, XG-CBS (\"optimized\")"
    info "  figures/random_segments/   — per-segment PNGs, re-sliced (\"random\")"
    info "  results/optimal/           — XG-CBS planner output"
    info "  results/random/            — re-labelled copy for random condition"
else
    warn "The following environments encountered errors:"
    for F in "${FAILED[@]}"; do
        warn "  • $F"
    done
    exit 1
fi
