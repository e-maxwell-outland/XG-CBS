#!/usr/bin/env bash
# generate_stimuli.sh — produce all 15 study figures (5 environments × 3 conditions).
#
# Run from the repository root:
#   bash study/generate_stimuli.sh
#
# Prerequisites:
#   - ./build/Planner binary must exist (run ./run.sh first if needed)
#   - Python 3 with matplotlib, numpy, pyyaml installed
#
# Outputs (all under study/figures/):
#   condition_a/env_N.png  — full path, colour-gradient + time dots
#   condition_b/env_N.png  — fixed-interval segments (XG-CBS + k extra)
#   condition_c/env_N.png  — XG-CBS optimal segmentation
#
# Configurable variables:
K=${K:-2}                        # extra segments for Condition B (default 2)
COST_BOUND=${COST_BOUND:-8}      # XG-CBS explanation cost bound (raised: some envs need >4 segments)
TIME_LIMIT=${TIME_LIMIT:-300.0}  # planner time limit in seconds (5 min per env)
PLANNER_BIN=./build/Planner
STUDY_DIR=study

set -euo pipefail

# Colour helpers
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# Validate prerequisites
[[ -x "$PLANNER_BIN" ]] || error "Planner binary not found at $PLANNER_BIN. Run ./run.sh to build."
python3 -c "import matplotlib, numpy, yaml" 2>/dev/null \
    || error "Python dependencies missing. Run: pip install matplotlib numpy pyyaml"

# Create output directories
mkdir -p "$STUDY_DIR/figures/condition_a" \
         "$STUDY_DIR/figures/condition_b" \
         "$STUDY_DIR/figures/condition_c"

ENVS=("env_1" "env_2" "env_3" "env_4" "env_5")
FAILED=()

for ENV in "${ENVS[@]}"; do
    ENV_YAML="$STUDY_DIR/envs/${ENV}.yaml"
    [[ -f "$ENV_YAML" ]] || { warn "Missing $ENV_YAML — skipping"; continue; }

    info "===== $ENV ====="

    # --- Run XG-CBS ---
    info "Running XG-CBS on $ENV…"
    # Stamp a temp file before running the planner so we can find the new result dir.
    _TS=$(mktemp)
    $PLANNER_BIN Plan "$ENV_YAML" XG-CBS XG-A "$TIME_LIMIT" "$COST_BOUND" 2>&1
    RESULT_DIR=$(find results -maxdepth 3 -name "result.json" -newer "$_TS" \
                   -exec dirname {} \; 2>/dev/null | head -1)
    rm -f "$_TS"
    [[ -n "$RESULT_DIR" && -f "$RESULT_DIR/result.json" ]] \
        || error "Could not locate result directory after planning $ENV — did the planner succeed?"
    info "Result written to $RESULT_DIR"

    # --- Verify segment_cost >= 2 ---
    SEG_COST=$(python3 -c "
import json, sys
with open('$RESULT_DIR/result.json') as f:
    d = json.load(f)
print(d['metrics'].get('segment_cost', 1))
")
    if [[ "$SEG_COST" -lt 2 ]]; then
        warn "$ENV produced segment_cost=$SEG_COST (need >= 2). Add obstacles to force crossings."
        FAILED+=("$ENV (segment_cost=$SEG_COST)")
        continue
    fi
    info "$ENV: segment_cost=$SEG_COST ✓"

    # --- Condition C: XG-CBS optimal segmentation ---
    info "Generating Condition C figure…"
    python3 visualize.py "$RESULT_DIR" \
        --segments \
        -o "$STUDY_DIR/figures/condition_c/${ENV}.png"

    # --- Apply fixed-interval segmentation (Condition B) ---
    B_OUT="$STUDY_DIR/results/condition_b/$ENV"
    info "Applying fixed-interval segmentation (k=$K)…"
    python3 study/apply_fixed_interval.py "$RESULT_DIR" --k "$K" -o "$B_OUT"

    # --- Condition B: fixed-interval segments ---
    info "Generating Condition B figure…"
    python3 visualize.py "$B_OUT" \
        --condition-b \
        -o "$STUDY_DIR/figures/condition_b/${ENV}.png"

    # --- Condition A: full path with gradient + time dots ---
    info "Generating Condition A figure…"
    python3 visualize.py "$RESULT_DIR" \
        --condition-a --k "$K" \
        -o "$STUDY_DIR/figures/condition_a/${ENV}.png"

    info "$ENV complete."
    echo
done

# --- Summary ---
echo "========================================"
if [[ ${#FAILED[@]} -eq 0 ]]; then
    info "All 5 environments completed successfully."
    info "Figures saved under $STUDY_DIR/figures/"
else
    warn "The following environments need redesign (segment_cost < 2):"
    for F in "${FAILED[@]}"; do
        warn "  • $F"
    done
    warn "Edit the YAML files in $STUDY_DIR/envs/ to add obstacles that force path crossings,"
    warn "then re-run this script."
    exit 1
fi
