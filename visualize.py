#!/usr/bin/env python3
"""
Visualize agent paths from a result directory (results/{M-D}/exp-{N}/).
Reads env.yaml (or environment.yaml) for map dimensions and obstacles,
and result.json for agent plans. Draws the grid, obstacles, and paths.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.collections as mcollections
import numpy as np
import yaml


# Per-agent sequential colormaps for Condition A gradient
_AGENT_CMAPS = [
    "Blues", "Reds", "Greens", "Purples",
    "Oranges", "YlOrBr", "PuRd", "Greys",
]

# Shared discrete palette (same order across all visualisation modes)
_AGENT_COLORS = [
    "#377eb8", "#e41a1c", "#4daf4a", "#984ea3",
    "#ff7f00", "#a65628", "#f781bf", "#999999",
]


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


def _draw_grid(ax, nx, ny, obstacles):
    """Draw grid lines and obstacle patches."""
    ax.set_xlim(-0.5, nx - 0.5)
    ax.set_ylim(-0.5, ny - 0.5)
    ax.set_aspect("equal")
    ax.set_facecolor("#f8f8f8")
    for x in range(nx + 1):
        ax.axvline(x - 0.5, color="#ccc", linewidth=0.8)
    for y in range(ny + 1):
        ax.axhline(y - 0.5, color="#ccc", linewidth=0.8)
    for cell in obstacles:
        rect = mpatches.Rectangle(
            (cell[0] - 0.5, cell[1] - 0.5), 1, 1,
            facecolor="#333", edgecolor="#111",
        )
        ax.add_patch(rect)


def visualize(env: dict, result: dict, ax=None, show_start_goal=True):
    """Draw grid, obstacles, and agent paths on ax (or current axes)."""
    if ax is None:
        ax = plt.gca()

    dims = env["map"]["dimensions"]
    nx, ny = dims[0], dims[1]
    obstacles = env["map"].get("obstacles") or []
    agents_cfg = {a["name"]: a for a in env["agents"]}
    plans = result["plans"]

    _draw_grid(ax, nx, ny, obstacles)

    for i, (agent_name, path) in enumerate(plans.items()):
        color = _AGENT_COLORS[i % len(_AGENT_COLORS)]
        xs = [p["x"] for p in path]
        ys = [p["y"] for p in path]

        ax.plot(xs, ys, color=color, linewidth=2, zorder=3, alpha=0.9)
        ax.scatter(xs, ys, c=color, s=28, zorder=4, edgecolors="white", linewidths=0.8)

        if show_start_goal and agent_name in agents_cfg:
            start = agents_cfg[agent_name]["start"]
            goal = agents_cfg[agent_name]["goal"]
            ax.scatter(
                [start[0]], [start[1]],
                marker="o", s=180, c=color, edgecolors="black", linewidths=1.5,
                zorder=5, label=f"{agent_name} start",
            )
            ax.scatter(
                [goal[0]], [goal[1]],
                marker="*", s=320, c=color, edgecolors="black", linewidths=1,
                zorder=5, label=f"{agent_name} goal",
            )

    handles, labels = ax.get_legend_handles_labels()
    by_agent = {}
    for h, l in zip(handles, labels):
        agent = l.replace(" start", "").replace(" goal", "")
        if agent not in by_agent:
            by_agent[agent] = h
    ax.legend(by_agent.values(), by_agent.keys(), loc="upper left", fontsize=8)
    return ax


def visualize_segments(env: dict, result: dict, segment_cost: int,
                       segment_label_fmt: str = "Segment {i} of {n}"):
    """Create a figure with one subfigure per segment cost level.

    Args:
        segment_label_fmt: format string with {i} (1-based) and {n} (total).
            Default  → "Segment 1 of N"
            Condition B override → "Time interval {i} of {n}"
    """
    dims = env["map"]["dimensions"]
    nx, ny = dims[0], dims[1]
    obstacles = env["map"].get("obstacles") or []
    agents_cfg = {a["name"]: a for a in env["agents"]}
    plans = result["plans"]

    n_segments = segment_cost
    n_cols = int(n_segments ** 0.5) + (1 if n_segments ** 0.5 != int(n_segments ** 0.5) else 0)
    n_rows = (n_segments + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
    if n_segments == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    for seg_idx in range(n_segments):
        cost_level = seg_idx + 1
        ax = axes[seg_idx]

        _draw_grid(ax, nx, ny, obstacles)
        title = segment_label_fmt.format(i=cost_level, n=n_segments)
        ax.set_title(title, fontsize=12, fontweight="bold")

        for i, (agent_name, path) in enumerate(plans.items()):
            color = _AGENT_COLORS[i % len(_AGENT_COLORS)]
            positions_at_cost = [p for p in path if p["cost"] == cost_level]

            if positions_at_cost:
                xs = [p["x"] for p in positions_at_cost]
                ys = [p["y"] for p in positions_at_cost]
                ax.scatter(xs, ys, c=color, s=100, zorder=4,
                           edgecolors="white", linewidths=1.5,
                           label=agent_name, alpha=0.9)
                if len(positions_at_cost) > 1:
                    ax.plot(xs, ys, color=color, linewidth=2, zorder=3, alpha=0.7)

        for i, (agent_name, path) in enumerate(plans.items()):
            if agent_name not in agents_cfg:
                continue
            color = _AGENT_COLORS[i % len(_AGENT_COLORS)]
            start = agents_cfg[agent_name]["start"]
            goal = agents_cfg[agent_name]["goal"]
            if any(p["x"] == start[0] and p["y"] == start[1] and p["cost"] == cost_level
                   for p in path):
                ax.scatter([start[0]], [start[1]], marker="o", s=200, c=color,
                           edgecolors="black", linewidths=2, zorder=5)
            if any(p["x"] == goal[0] and p["y"] == goal[1] and p["cost"] == cost_level
                   for p in path):
                ax.scatter([goal[0]], [goal[1]], marker="*", s=350, c=color,
                           edgecolors="black", linewidths=1.5, zorder=5)

        if seg_idx == 0:
            ax.legend(loc="upper left", fontsize=8)

    for idx in range(n_segments, len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    return fig


def visualize_condition_a(env: dict, result: dict, k: int = 2, ax=None,
                          show_start_goal: bool = True):
    """Condition A: full geometric paths with per-agent color gradient + time dots.

    Each agent's path is drawn as a LineCollection whose color fades through
    a sequential colormap (light → dark = early → late).  Dot markers are placed
    at the same uniform time-slice points that Condition B would use (n_xgcbs + k
    intervals), labeled with their timestep, so the temporal structure is visible
    without imposing an explicit segmentation framing.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    else:
        fig = ax.get_figure()

    dims = env["map"]["dimensions"]
    nx, ny = dims[0], dims[1]
    obstacles = env["map"].get("obstacles") or []
    agents_cfg = {a["name"]: a for a in env["agents"]}
    plans = result["plans"]

    _draw_grid(ax, nx, ny, obstacles)

    n_optimal = result["metrics"].get("segment_cost", 1)
    n_slices = n_optimal + k

    legend_handles = []

    for i, (agent_name, path) in enumerate(plans.items()):
        cmap = plt.get_cmap(_AGENT_CMAPS[i % len(_AGENT_CMAPS)])
        dark_color = cmap(0.85)      # darkest shade — used for dots/markers
        n = len(path)

        # --- Gradient line via LineCollection ---
        coords = np.array([[p["x"], p["y"]] for p in path], dtype=float)
        points = coords.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        # Map segment index to colormap value [0.35, 0.95]
        n_segs = len(segments)
        seg_colors = [cmap(0.35 + 0.60 * t / max(n_segs - 1, 1)) for t in range(n_segs)]
        lc = mcollections.LineCollection(segments, colors=seg_colors,
                                         linewidth=2.5, zorder=3)
        ax.add_collection(lc)

        # --- Time-slice dot markers ---
        # Use global T_max so all agents share the same absolute timestep
        # boundaries (consistent with Condition B's global slicing).
        T_max = max(len(p) for p in plans.values())
        global_cuts = [
            round((s + 1) * T_max / n_slices)
            for s in range(n_slices - 1)
        ]
        slice_indices = [min(g, n - 1) for g in global_cuts]
        for idx in slice_indices:
            p = path[idx]
            ax.scatter(p["x"], p["y"],
                       s=90, c="white", zorder=6,
                       edgecolors=dark_color, linewidths=1.8)
            ax.annotate(
                f"t={idx}",
                xy=(p["x"], p["y"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=6.5,
                color=dark_color,
                zorder=7,
            )

        # --- Start / goal markers ---
        if show_start_goal and agent_name in agents_cfg:
            start = agents_cfg[agent_name]["start"]
            goal = agents_cfg[agent_name]["goal"]
            ax.scatter(
                [start[0]], [start[1]],
                marker="o", s=180, color=dark_color,
                edgecolors="black", linewidths=1.5, zorder=5,
            )
            ax.scatter(
                [goal[0]], [goal[1]],
                marker="*", s=320, color=dark_color,
                edgecolors="black", linewidths=1, zorder=5,
            )

        # Legend patch using the dark shade
        legend_handles.append(
            mpatches.Patch(color=dark_color, label=agent_name)
        )

    ax.legend(handles=legend_handles, loc="upper left", fontsize=8)
    return fig, ax


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
    parser.add_argument(
        "--segments",
        action="store_true",
        help="Condition C: visualize plans segmented by cost (one subfigure per segment)",
    )
    parser.add_argument(
        "--condition-b",
        action="store_true",
        help="Like --segments but titles read 'Time interval N of M'",
    )
    parser.add_argument(
        "--condition-a",
        action="store_true",
        help="Condition A: full paths with per-agent color gradient and time-slice dots",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=2,
        help="Extra segments beyond XG-CBS optimal used for time-dot placement (default: 2)",
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

    if args.condition_a:
        fig, _ = visualize_condition_a(
            env, result, k=args.k,
            show_start_goal=not args.no_start_goal,
        )
    elif args.condition_b:
        segment_cost = result["metrics"].get("segment_cost", 1)
        fig = visualize_segments(
            env, result, segment_cost,
            segment_label_fmt="Time interval {i} of {n}",
        )
    elif args.segments:
        segment_cost = result["metrics"].get("segment_cost", 1)
        fig = visualize_segments(env, result, segment_cost)
    else:
        fig, ax = plt.subplots(figsize=(8, 6))
        visualize(env, result, ax=ax, show_start_goal=not args.no_start_goal)

    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Saved to {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
