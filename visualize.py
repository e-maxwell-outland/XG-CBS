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
import matplotlib.collections as mcollections
import numpy as np
import yaml


# Per-agent sequential colormaps for Condition A gradient
_AGENT_CMAPS = [
    "Blues", "Reds", "Greens", "Purples",
    "Oranges", "YlOrBr", "PuRd", "Greys",
]

# Shared discrete palette — 20 visually distinct colors, same order everywhere.
# Enough for 16+ agents without repeating.
_AGENT_COLORS = [
    "#377eb8",  # blue
    "#e41a1c",  # red
    "#4daf4a",  # green
    "#984ea3",  # purple
    "#ff7f00",  # orange
    "#a65628",  # brown
    "#f781bf",  # pink
    "#999999",  # grey
    "#e6ab02",  # gold
    "#1b9e77",  # teal
    "#d95f02",  # burnt orange
    "#7570b3",  # slate purple
    "#e7298a",  # hot pink
    "#66a61e",  # olive green
    "#e6194b",  # crimson
    "#4363d8",  # cobalt
    "#469990",  # dark cyan
    "#9a6324",  # khaki brown
    "#800000",  # maroon
    "#808000",  # olive
]


def load_result_dir(exp_dir: Path):
    """Load env yaml and result.json from an experiment directory."""
    exp_dir = Path(exp_dir)
    if not exp_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {exp_dir}")

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

    return ax


def visualize_segments(env: dict, result: dict, segment_cost: int,
                       segment_label_fmt: str = "Segment {i} of {n}"):
    """Create a figure with one subfigure per segment cost level.

    Args:
        segment_label_fmt: format string with {i} (1-based) and {n} (total).
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


    for idx in range(n_segments, len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    return fig


def visualize_segments_individual(env: dict, result: dict, segment_cost: int,
                                   output_dir: Path):
    """Save one PNG per segment to output_dir/seg_N.png.

    Each image shows:
    - Full agent paths grayed out for context
    - This segment's portion of each path in the agent's color
    - Start/goal markers (full opacity if in this segment, faded otherwise)
    - Title: "Segment N of M"
    """
    dims = env["map"]["dimensions"]
    nx, ny = dims[0], dims[1]
    obstacles = env["map"].get("obstacles") or []
    agents_cfg = {a["name"]: a for a in env["agents"]}
    plans = result["plans"]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for seg_idx in range(segment_cost):
        cost_level = seg_idx + 1

        fig, ax = plt.subplots(figsize=(7, 7))
        _draw_grid(ax, nx, ny, obstacles)
        ax.set_title(
            f"Segment {cost_level} of {segment_cost}",
            fontsize=14, fontweight="bold",
        )

        for i, (agent_name, path) in enumerate(plans.items()):
            color = _AGENT_COLORS[i % len(_AGENT_COLORS)]

            # This segment in full color
            seg_pts = [p for p in path if p["cost"] == cost_level]
            if seg_pts:
                xs = [p["x"] for p in seg_pts]
                ys = [p["y"] for p in seg_pts]
                ax.plot(xs, ys, color=color, linewidth=2.5, zorder=4, alpha=0.9)
                ax.scatter(xs, ys, c=color, s=80, zorder=5,
                           edgecolors="white", linewidths=1.2)

        # Goal stars: visible only in segment 1 (reference) and the segment
        # where the agent arrives (last segment of its path).
        for i, (agent_name, path) in enumerate(plans.items()):
            if agent_name not in agents_cfg:
                continue
            color = _AGENT_COLORS[i % len(_AGENT_COLORS)]
            goal = agents_cfg[agent_name]["goal"]

            goal_in = any(
                p["x"] == goal[0] and p["y"] == goal[1] and p["cost"] == cost_level
                for p in path
            )
            is_first_seg = (cost_level == 1)

            if goal_in or is_first_seg:
                ax.scatter([goal[0]], [goal[1]], marker="*", s=320, c=color,
                           edgecolors="black", linewidths=1, zorder=6)

        plt.tight_layout()

        out_path = output_dir / f"seg_{cost_level}.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved {out_path}")


def animate_trajectories(env: dict, result: dict, output_path: Path, fps: int = 4):
    """Animate agent trajectories frame-by-frame and export as MP4.

    Requires ffmpeg. Each frame shows all agents at one timestep, with faded
    goal markers as static reference points.
    """
    import matplotlib.animation as manim

    dims = env["map"]["dimensions"]
    nx, ny = dims[0], dims[1]
    obstacles = env["map"].get("obstacles") or []
    agents_cfg = {a["name"]: a for a in env["agents"]}
    plans = result["plans"]

    # Path index = timestep (wait actions appear as repeated positions).
    # CBS uses the "disappearing" model: agents vanish after reaching their goal,
    # so we hide each agent (and its goal marker) once it arrives.
    T_max = max(len(path) - 1 for path in plans.values())
    t_done = {name: len(path) - 1 for name, path in plans.items()}
    positions = {
        name: {t: (p["x"], p["y"]) for t, p in enumerate(path)}
        for name, path in plans.items()
    }

    fig, ax = plt.subplots(figsize=(8, 8))
    _draw_grid(ax, nx, ny, obstacles)

    # All scatters start empty — update() populates / clears them each frame.
    # This ensures blit doesn't preserve stale markers in the cached background.
    _empty = np.empty((0, 2))

    agent_scatters = []
    for i, agent_name in enumerate(plans):
        color = _AGENT_COLORS[i % len(_AGENT_COLORS)]
        sc = ax.scatter([], [], color=color, s=220, zorder=6,
                        edgecolors="white", linewidths=1.8)
        agent_scatters.append((agent_name, sc))

    goal_scatters = []
    for i, (agent_name, _) in enumerate(plans.items()):
        color = _AGENT_COLORS[i % len(_AGENT_COLORS)]
        sc = ax.scatter([], [], marker="*", color=color, s=300, zorder=3,
                        edgecolors="black", linewidths=1, alpha=0.55)
        goal_scatters.append((agent_name, sc))

    title = ax.set_title(f"Timestep 0 / {T_max}")

    def update(frame):
        for agent_name, sc in agent_scatters:
            if frame <= t_done[agent_name]:
                x, y = positions[agent_name][frame]
                sc.set_offsets([[x, y]])
            else:
                sc.set_offsets(_empty)

        for agent_name, sc in goal_scatters:
            if frame <= t_done[agent_name] and agent_name in agents_cfg:
                g = agents_cfg[agent_name]["goal"]
                sc.set_offsets([[g[0], g[1]]])
            else:
                sc.set_offsets(_empty)

        title.set_text(f"Timestep {frame} / {T_max}")
        return [sc for _, sc in agent_scatters] + [sc for _, sc in goal_scatters] + [title]

    ani = manim.FuncAnimation(
        fig, update, frames=T_max + 1,
        interval=1000 // fps, blit=True,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        writer = manim.FFMpegWriter(fps=fps, metadata={"title": "Agent Trajectories"})
        ani.save(str(output_path), writer=writer)
        print(f"Animation saved to {output_path}")
    except Exception as e:
        print(
            f"ERROR: Could not save MP4 ({e}).\n"
            "Make sure ffmpeg is installed: apt-get install ffmpeg",
            file=sys.stderr,
        )
        sys.exit(1)
    finally:
        plt.close(fig)


def visualize_condition_a(env: dict, result: dict, k: int = 2, ax=None,
                          show_start_goal: bool = True):
    """Condition A: full geometric paths with per-agent color gradient + time dots."""
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

    T_max = max(len(p) for p in plans.values())

    n_agents = len(plans)
    _DOT_RADIUS = 0.035
    _dot_offsets = [
        (
            _DOT_RADIUS * np.cos(2 * np.pi * i / n_agents),
            _DOT_RADIUS * np.sin(2 * np.pi * i / n_agents),
        )
        for i in range(n_agents)
    ]

    for i, (agent_name, path) in enumerate(plans.items()):
        cmap = plt.get_cmap(_AGENT_CMAPS[i % len(_AGENT_CMAPS)])
        dark_color = cmap(0.85)

        coords = np.array([[p["x"], p["y"]] for p in path], dtype=float)
        ddx, ddy = _dot_offsets[i]
        off_coords = coords + np.array([ddx, ddy])

        points = off_coords.reshape(-1, 1, 2)
        segs = np.concatenate([points[:-1], points[1:]], axis=1)
        seg_colors = [cmap(0.35 + 0.60 * t / max(T_max - 1, 1))
                      for t in range(len(segs))]
        lc = mcollections.LineCollection(segs, colors=seg_colors,
                                         linewidth=2.5, zorder=3)
        ax.add_collection(lc)

        if show_start_goal and agent_name in agents_cfg:
            ax.scatter([off_coords[0][0]], [off_coords[0][1]],
                       marker="o", s=180, color=dark_color,
                       edgecolors="black", linewidths=1.5, zorder=5)
            ax.scatter([off_coords[-1][0]], [off_coords[-1][1]],
                       marker="*", s=320, color=dark_color,
                       edgecolors="black", linewidths=1, zorder=5)

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
        help="Save figure to this path instead of showing (PNG, PDF, etc.)",
    )
    parser.add_argument(
        "--no-start-goal",
        action="store_true",
        help="Do not draw start/goal markers",
    )
    parser.add_argument(
        "--segments",
        action="store_true",
        help="Visualize plans segmented by cost (one subfigure per segment)",
    )
    parser.add_argument(
        "--segments-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Save one PNG per segment to DIR/seg_N.png. "
            "Each image shows the active segment's paths and faded goal markers."
        ),
    )
    parser.add_argument(
        "--animate",
        action="store_true",
        help="Export an animated MP4 of agent trajectories (requires ffmpeg). "
             "Use -o to set the output path (default: animation.mp4).",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=4,
        help="Frames per second for --animate (default: 4)",
    )
    parser.add_argument(
        "--condition-b",
        action="store_true",
        help="Like --segments but titles read 'Segment N of M'",
    )
    parser.add_argument(
        "--condition-a",
        action="store_true",
        help="Full paths with per-agent color gradient and time-slice dots",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=2,
        help="Extra segments beyond XG-CBS optimal (used with --condition-a, default: 2)",
    )
    args = parser.parse_args()

    path = Path(args.path)
    exp_dir = path.parent if (path.is_file() and path.name == "result.json") else path

    try:
        env, result = load_result_dir(exp_dir)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    # --segments-dir: individual PNGs (no figure to display/save via -o)
    if args.segments_dir is not None:
        segment_cost = result["metrics"].get("segment_cost", 1)
        visualize_segments_individual(env, result, segment_cost, args.segments_dir)
        return

    # --animate: MP4 export
    if args.animate:
        out = args.output or Path("animation.mp4")
        animate_trajectories(env, result, out, fps=args.fps)
        return

    # Static figure modes
    if args.condition_a:
        fig, _ = visualize_condition_a(
            env, result, k=args.k,
            show_start_goal=not args.no_start_goal,
        )
    elif args.condition_b:
        segment_cost = result["metrics"].get("segment_cost", 1)
        fig = visualize_segments(
            env, result, segment_cost,
            segment_label_fmt="Segment {i} of {n}",
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
