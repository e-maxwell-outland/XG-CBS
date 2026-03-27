#!/usr/bin/env python3
"""
Generate a random MAPF environment YAML file.

Usage:
    python3 generate_map.py --width 16 --height 16 --agents 16 --obstacles 0.15 --seed 42 -o study/envs/env_1.yaml
"""
import argparse
import random
from collections import deque
from pathlib import Path

import yaml


def _bfs_reachable(grid, start, width, height):
    """Return the set of cells reachable from start (4-connected BFS)."""
    visited = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx2, ny2 = x + dx, y + dy
            if (0 <= nx2 < width and 0 <= ny2 < height
                    and (nx2, ny2) not in visited
                    and grid[ny2][nx2] == 0):
                visited.add((nx2, ny2))
                queue.append((nx2, ny2))
    return visited


def generate_map(width, height, n_agents, obstacle_density, seed, max_retries=2000):
    """
    Return a dict matching the XG-CBS YAML environment format.

    Guarantees:
    - All start and goal positions are on different cells.
    - All start and goal positions are 4-connected reachable from each other.
    """
    rng = random.Random(seed)
    all_cells = [(x, y) for y in range(height) for x in range(width)]
    n_obstacles = int(width * height * obstacle_density)

    for attempt in range(max_retries):
        # Place obstacles
        obstacle_cells = set(rng.sample(all_cells, n_obstacles))
        grid = [[0] * width for _ in range(height)]
        for x, y in obstacle_cells:
            grid[y][x] = 1

        free_cells = [c for c in all_cells if c not in obstacle_cells]

        if len(free_cells) < 2 * n_agents:
            continue  # Not enough free space — try a new obstacle layout

        # Pick 2*n_agents distinct free cells for starts and goals
        positions = rng.sample(free_cells, 2 * n_agents)
        starts = positions[:n_agents]
        goals = positions[n_agents:]

        # Connectivity check: all starts and goals reachable from starts[0]
        reachable = _bfs_reachable(grid, starts[0], width, height)
        if not all(pos in reachable for pos in starts + goals):
            continue

        obstacles_list = sorted([x, y] for x, y in obstacle_cells)
        agents = [
            {"name": f"agent{i}", "start": list(s), "goal": list(g)}
            for i, (s, g) in enumerate(zip(starts, goals))
        ]

        return {
            "map": {
                "dimensions": [width, height],
                "obstacles": obstacles_list,
            },
            "agents": agents,
        }

    raise RuntimeError(
        f"Could not generate a valid map after {max_retries} attempts. "
        "Try reducing --agents or --obstacles."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate a random MAPF environment YAML for XG-CBS."
    )
    parser.add_argument("--width", type=int, default=16, help="Grid width (default: 16)")
    parser.add_argument("--height", type=int, default=16, help="Grid height (default: 16)")
    parser.add_argument("--agents", type=int, default=16, help="Number of agents (default: 16)")
    parser.add_argument(
        "--obstacles", type=float, default=0.15,
        help="Fraction of cells that are obstacles (default: 0.15)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output YAML path")
    args = parser.parse_args()

    env = generate_map(args.width, args.height, args.agents, args.obstacles, args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        yaml.dump(env, f, default_flow_style=False, sort_keys=False)

    n_obs = len(env["map"]["obstacles"])
    print(
        f"Generated {args.width}x{args.height} map: "
        f"{args.agents} agents, {n_obs} obstacles → {args.output}"
    )


if __name__ == "__main__":
    main()
