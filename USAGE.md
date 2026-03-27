# Usage Guide

This guide covers how to build and run XG-CBS in the VS Code Dev Container setup. For the original project overview and input format, see [README.md](README.md).

---

## Environment Setup (My Machine is a Mac)

This repo uses a **Docker-based Dev Container** so dependencies are handled automatically. You need:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (must be running — whale 🐳 in menu bar on Mac)
- [VS Code](https://code.visualstudio.com/) with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Opening the project
1. Open the `XG-CBS` folder in VS Code
2. When prompted, click **"Reopen in Container"** (or `Cmd+Shift+P` → "Dev Containers: Reopen in Container")
3. VS Code will build the container and drop you in — this takes ~2-3 min the first time, then it's instant

---

## Building

### Via VS Code (recommended)
Press **`Cmd+Shift+B`** — this runs `./run.sh`, which compiles all C++ source files and produces `build/Planner`.

You'll see the build output in the terminal panel. A successful build ends with:
```
[100%] Built target Planner
Build complete: build/Planner
```

### Via terminal
```bash
./run.sh
```

> **When to rebuild:** only when you change C++ source files (`.cpp` / `.h`). If you're just running experiments with different parameters or environments, skip straight to running.

---

## Running Experiments

### Via VS Code tasks (recommended)
1. `Cmd+Shift+P` → **"Tasks: Run Task"**
2. Pick a planner configuration:

| Task | What it runs |
|---|---|
| **Run: CBS (baseline)** | Standard MAPF, no explainability constraint |
| **Run: XG-CBS with XG-A\*** | Complete, tracks full path history |
| **Run: XG-CBS with WXG-A\* (weighted)** | Weighted blend of path length + segment cost |
| **Run: XG-CBS with SR-A\* (fast)** | Fastest, comparable to CBS runtime |
| **Benchmark: single map** | Runs all low-level variants on one map |
| **Benchmark: all maps in envs/** | Runs all low-level variants on every map in `envs/` |

3. VS Code will prompt you for parameters as needed (environment file, time limit, cost bound, etc.)

### Via terminal
```bash
# CBS baseline
./build/Planner Plan <env>.yaml CBS A <time_limit>

# XG-CBS variants
./build/Planner Plan <env>.yaml XG-CBS XG-A   <time_limit> <cost_bound>
./build/Planner Plan <env>.yaml XG-CBS XG-A-H <time_limit> <cost_bound> <weight>
./build/Planner Plan <env>.yaml XG-CBS S-A    <time_limit> <cost_bound>

# Benchmarking
./build/Planner Benchmark      <low-level> <env>.yaml <time_limit> <output>.csv
./build/Planner MultiBenchmark <low-level> envs       <time_limit> <output>.csv
```

### Parameter reference
| Parameter | Meaning | Suggested starting value |
|---|---|---|
| `env` | YAML file in `envs/` — reference by filename only | `intersection.yaml` |
| `time_limit` | Max planning time (seconds) | `60.0` |
| `cost_bound` | Max allowed segments `r`. Lower = harder to solve, more explainable | `2` |
| `weight` | `WXG-A*` only — blend between path cost and segment cost `[0,1]` | `0.5` |
| `low-level` | One of: `A`, `XG-A`, `XG-A-H`, `S-A` | `XG-A` or `S-A` |

---

## Environments

### Built-in small maps (`envs/`)

| File | Grid | Agents | Notes |
|---|---|---|---|
| `intersection.yaml` | 7×7 | 3 | Good starting point |
| `roadCrossing.yaml` | 9×6 | 4 | Slightly harder |

See [README.md](README.md) for the full YAML format spec to create your own.

### Random map generator

`generate_map.py` creates a random YAML environment at any scale:

```bash
python3 generate_map.py \
    --width 16 --height 16 \
    --agents 16 --obstacles 0.15 \
    --seed 42 -o envs/large.yaml
```

All agent starts and goals are guaranteed reachable from each other. Use `--seed` for reproducibility.

---

## Results

Each run writes output to `results/<month-day>/exp-N/` (auto-incremented, nothing gets overwritten):

| File | Contents |
|---|---|
| `result.json` | Planned paths + segment decomposition |
| `env.yaml` | Copy of the environment used |
| `plot.png` | Visualization of the plan and segments |

Results are visible directly on your Mac in the repo's `results/` folder (via the Docker volume mount).

---

## Visualization

`visualize.py` has several modes:

```bash
# Default: full path overview
python3 visualize.py <exp_dir> -o output.png

# Segment subplot (all segments in one figure)
python3 visualize.py <exp_dir> --segments -o output.png

# Individual PNG per segment — for study participants to arrow through
python3 visualize.py <exp_dir> --segments-dir path/to/output_dir/

# Animated MP4 of agent trajectories (requires ffmpeg)
python3 visualize.py <exp_dir> --animate -o trajectories.mp4
python3 visualize.py <exp_dir> --animate --fps 6 -o trajectories.mp4
```

---

## Study Stimuli (Advisor Demo + User Study)

To generate all study outputs — 5 random 16×16 environments, trajectory videos, and per-segment images for both CBS ("random") and XG-CBS SR-A* ("optimized") conditions:

```bash
bash study/generate_stimuli.sh
```

This produces under `study/figures/`:

| Output | Description |
|---|---|
| `trajectories/env_N.mp4` | Animated agent trajectories (CBS paths) |
| `cbs_segments/env_N/seg_K.png` | One image per segment — CBS ("random" segmentation) |
| `xgcbs_segments/env_N/seg_K.png` | One image per segment — XG-CBS ("optimized" segmentation) |

Override defaults via environment variables:

```bash
WIDTH=32 HEIGHT=32 AGENTS=25 TIME_LIMIT=600 bash study/generate_stimuli.sh
```

---

## Suggested Pilot Workflow

A good sequence for comparing baseline vs. explainable planning:

```bash
# 1. Generate a 16×16 map
python3 generate_map.py --width 16 --height 16 --agents 16 --seed 42 -o envs/large.yaml

# 2. Baseline — standard CBS
./build/Planner Plan large.yaml CBS A 300.0

# 3. XG-CBS with SR-A* — fast, minimizes segments
./build/Planner Plan large.yaml XG-CBS S-A 300.0 8

# 4. Animate trajectories from CBS result
python3 visualize.py results/<date>/exp-0 --animate -o cbs_traj.mp4

# 5. Individual segment images
python3 visualize.py results/<date>/exp-1 --segments-dir xgcbs_segs/
```

Compare segment counts and segment images across the CBS and XG-CBS runs.
