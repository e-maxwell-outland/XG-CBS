#!/usr/bin/env python3
"""
Visualize agent paths from a result directory (results/{M-D}/exp-{N}/).
Reads env.yaml (or environment.yaml) for map dimensions and obstacles,
and result.json for agent plans. Draws the grid, obstacles, and paths.
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import yaml


def load_result_dir(exp_dir: Path):
    """Load env yaml and result.json from an experiment directory."""
    exp_dir = Path(exp_dir)
    if not exp_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {exp_dir}")

    # Prefer env.yaml, fallback to environment.yaml
    env_path = exp_dir / "env.yaml"
    if not env_path.exists():
        env_path = exp_dir / "environment.yaml"
    if not env_path.exists():
        raise FileNotFoundError(f"No env.yaml or environment.yaml in {exp_dir}")

    result_path = exp_dir / "result.json"
    if not result_path.exists():
        raise FileNotFoundError(f"No result.json in {exp_dir}")

    with open(env_path) as f:
        env = yaml.safe_load(f)
    with open(result_path) as f:
        result = json.load(f)

    return env, result


def visualize(env: dict, result: dict, ax=None, show_start_goal=True):
    """Draw grid, obstacles, and agent paths on ax (or current axes)."""
    if ax is None:
        ax = plt.gca()

    dims = env["map"]["dimensions"]
    nx, ny = dims[0], dims[1]
    obstacles = env["map"].get("obstacles") or []
    agents_cfg = {a["name"]: a for a in env["agents"]}
    plans = result["plans"]

    # Grid: use cell centers at (0.5, 0.5), (1.5, 0.5), ... so cells are [0,1] x [0,1] etc.
    ax.set_xlim(-0.5, nx - 0.5)
    ax.set_ylim(-0.5, ny - 0.5)
    ax.set_aspect("equal")
    ax.set_facecolor("#f8f8f8")

    # Grid lines
    for x in range(nx + 1):
        ax.axvline(x - 0.5, color="#ccc", linewidth=0.8)
    for y in range(ny + 1):
        ax.axhline(y - 0.5, color="#ccc", linewidth=0.8)

    # Obstacles
    for cell in obstacles:
        x, y = cell[0], cell[1]
        rect = mpatches.Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor="#333", edgecolor="#111")
        ax.add_patch(rect)

    # Distinct colors for agents
    colors = [
        "#377eb8", "#e41a1c", "#4daf4a", "#984ea3",
        "#ff7f00", "#a65628", "#f781bf", "#999999",
    ]

    for i, (agent_name, path) in enumerate(plans.items()):
        color = colors[i % len(colors)]
        xs = [p["x"] for p in path]
        ys = [p["y"] for p in path]

        # Path line (cell centers for clarity)
        ax.plot(xs, ys, color=color, linewidth=2, zorder=3, alpha=0.9)
        ax.scatter(xs, ys, c=color, s=28, zorder=4, edgecolors="white", linewidths=0.8)

        if show_start_goal and agent_name in agents_cfg:
            start = agents_cfg[agent_name]["start"]
            goal = agents_cfg[agent_name]["goal"]
            ax.scatter(
                [start[0]], [start[1]],
                marker="o", s=180, c=color, edgecolors="black", linewidths=1.5,
                zorder=5, label=f"{agent_name} start"
            )
            ax.scatter(
                [goal[0]], [goal[1]],
                marker="*", s=320, c=color, edgecolors="black", linewidths=1,
                zorder=5, label=f"{agent_name} goal"
            )

    # Single legend entry per agent
    handles, labels = ax.get_legend_handles_labels()
    by_agent = {}
    for h, l in zip(handles, labels):
        agent = l.replace(" start", "").replace(" goal", "")
        if agent not in by_agent:
            by_agent[agent] = h
    ax.legend(by_agent.values(), by_agent.keys(), loc="upper left", fontsize=8)
    return ax


def main():
    parser = argparse.ArgumentParser(
        description="Visualize MAPF result: grid, obstacles, and agent paths."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to experiment dir (e.g. results/3-11/exp-0) or to result.json",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Save figure to this path instead of showing",
    )
    parser.add_argument(
        "--no-start-goal",
        action="store_true",
        help="Do not draw start/goal markers",
    )
    args = parser.parse_args()

    path = Path(args.path)
    if path.is_file() and path.name == "result.json":
        exp_dir = path.parent
    else:
        exp_dir = path

    try:
        env, result = load_result_dir(exp_dir)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    fig, ax = plt.subplots(figsize=(8, 6))
    visualize(env, result, ax=ax, show_start_goal=not args.no_start_goal)

    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Saved to {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
