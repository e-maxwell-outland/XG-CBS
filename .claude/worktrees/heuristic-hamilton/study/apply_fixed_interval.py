#!/usr/bin/env python3
"""
Apply fixed-interval segmentation to an XG-CBS result.json.

Takes the XG-CBS optimal segment count N and re-assigns each state's
'cost' field using uniform time slices with N+k total segments (k extra).
The modified result is written to an output directory alongside a copy
of env.yaml, so it can be fed directly into visualize.py.

Usage:
    python3 study/apply_fixed_interval.py <result_dir_or_json> [--k 2] [-o output_dir]
"""
import argparse
import json
import math
import shutil
import sys
from pathlib import Path


def apply_fixed_interval(result: dict, k: int) -> dict:
    """Return a new result dict with cost fields re-assigned by time slice."""
    import copy
    result = copy.deepcopy(result)

    n_optimal = result["metrics"].get("segment_cost", 1)
    n_slices = n_optimal + k

    # Use the longest path as the global time horizon so all agents share
    # the same absolute timestep boundaries (global slicing).
    T_max = max(len(path) for path in result["plans"].values())

    new_plans = {}
    for agent, path in result["plans"].items():
        new_path = []
        for t, state in enumerate(path):
            # Assign cost = which global slice this timestep falls into (1-indexed).
            cost = min(math.ceil((t + 1) / (T_max / n_slices)), n_slices)
            cost = max(cost, 1)
            new_state = dict(state)
            new_state["cost"] = cost
            new_path.append(new_state)
        new_plans[agent] = new_path

    result["plans"] = new_plans
    result["metrics"]["segment_cost"] = n_slices
    result["metrics"]["fixed_interval_k"] = k
    result["metrics"]["xgcbs_segment_cost"] = n_optimal
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Re-slice an XG-CBS result.json with fixed-interval segments."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to experiment directory or result.json",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=2,
        help="Extra segments beyond XG-CBS optimal (default: 2)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output directory (default: <path>/../condition_b_k<k>/)",
    )
    args = parser.parse_args()

    # Resolve input
    p = Path(args.path)
    if p.is_file() and p.name == "result.json":
        result_path = p
        exp_dir = p.parent
    elif p.is_dir():
        result_path = p / "result.json"
        exp_dir = p
    else:
        print(f"Error: {p} is not a result.json or experiment directory", file=sys.stderr)
        sys.exit(1)

    if not result_path.exists():
        print(f"Error: {result_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(result_path) as f:
        result = json.load(f)

    modified = apply_fixed_interval(result, args.k)

    # Determine output directory
    if args.output is None:
        out_dir = exp_dir.parent / f"condition_b_k{args.k}" / exp_dir.name
    else:
        out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write modified result.json
    out_result = out_dir / "result.json"
    with open(out_result, "w") as f:
        json.dump(modified, f, indent=2)
    print(f"Wrote {out_result}")

    # Copy env.yaml alongside so visualize.py can find it
    for name in ("env.yaml", "environment.yaml"):
        env_src = exp_dir / name
        if env_src.exists():
            shutil.copy2(env_src, out_dir / name)
            print(f"Copied {env_src.name} → {out_dir / name}")
            break

    n_opt = result["metrics"].get("segment_cost", 1)
    print(f"XG-CBS segments: {n_opt}  →  fixed-interval segments: {n_opt + args.k}  (k={args.k})")


if __name__ == "__main__":
    main()
