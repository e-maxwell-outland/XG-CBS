# Explanation-Guided Conflict-Based Search for Explainable MAPF

This project implements **Explanation-Guided Conflict-Based Search (XG-CBS)** for explainable Multi-Agent Path Finding (MAPF), as described in the paper *Conflict-Based Search for Explainable Multi-Agent Path Finding* (ICAPS 2022). It extends Conflict-Based Search (CBS) with explainability constraints so that plans can be presented as a short sequence of disjoint trajectory segments.

## Requirements

- **C++20** compiler (e.g. GCC 10+, Clang 10+)
- **libyaml-cpp** (YAML parsing)
- **Boost** (program_options, functional/hash)

### Installing dependencies

**Ubuntu / Debian:**

```bash
sudo apt-get update
sudo apt-get install build-essential libyaml-cpp-dev libboost-all-dev
```

**Fedora:**

```bash
sudo dnf install gcc-c++ yaml-cpp-devel boost-devel
```

## Building

**Using the build script (recommended):**

```bash
chmod +x run.sh
./run.sh
```

This configures with CMake, builds in a `build/` directory, and produces `build/Planner`. To build and then run in one go, pass the planner arguments:

```bash
./run.sh Plan example.yaml XG-CBS XG-A 60.0 2
```

**Using CMake directly:**

```bash
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/Planner  # run with your arguments
```

### Using Docker

A Docker image with the required libraries is provided:

```bash
docker build -t xg-cbs .
docker run -it -v $(pwd):/workspace xg-cbs bash
```

Inside the container, install CMake if needed (`apt-get install cmake`), then run `./run.sh` from `/workspace`.

## Input format

Place your MAPF instance YAML files in the **`envs/`** directory. You can pass either a bare filename (e.g. `example.yaml`) or a path; bare filenames are looked up in `envs/`.

The planner expects YAML files with this structure:

```yaml
map:
  dimensions: [width, height]   # grid size
  obstacles:                    # optional list of blocked cells
    - [x1, y1]
    - [x2, y2]

agents:
  - name: "agent0"
    start: [x, y]
    goal: [x, y]
  - name: "agent1"
    start: [x, y]
    goal: [x, y]
```

Example minimal file (e.g. `envs/example.yaml`):

```yaml
map:
  dimensions: [5, 5]
  obstacles: []

agents:
  - name: "agent0"
    start: [0, 0]
    goal: [4, 4]
  - name: "agent1"
    start: [4, 0]
    goal: [0, 4]
```

## Running

### Planning

**CBS (standard MAPF):**

```bash
./build/Planner Plan example.yaml CBS A <time_limit>
```

**XG-CBS (explainable MAPF)** with different low-level search options:

- A* only:  
  `./build/Planner Plan example.yaml XG-CBS A <time_limit> <explanation_cost_bound>`
- XG-A*:  
  `./build/Planner Plan example.yaml XG-CBS XG-A <time_limit> <explanation_cost_bound>`
- XG-A*-H (with explanation weight):  
  `./build/Planner Plan example.yaml XG-CBS XG-A-H <time_limit> <explanation_cost_bound> <weight_on_exp_cost>`
- S-A*:  
  `./build/Planner Plan example.yaml XG-CBS S-A <time_limit> <explanation_cost_bound>`

- `time_limit`: max planning time in seconds (e.g. `60.0`).
- `explanation_cost_bound`: **maximum** allowed number of segments (explanation cost). The planner accepts any solution whose segment cost is **≤** this value. A *high* bound (e.g. 10) therefore allows many segments, so the first feasible solution (often with segment cost 1) is usually accepted immediately. Use a *low* bound (e.g. 1) to force the search to find solutions that are explainable in at most that many segments.
- `weight_on_exp_cost`: weight in [0, 1] for XG-A-H.

Results (including `env.yaml`, `result.json`, and `plot.png`) are written to `results/<month-day>/exp-<N>/` (e.g. `results/3-11/exp-0/`). Each run gets the next `exp-N` directory. A plot is generated automatically when Python 3 with matplotlib and PyYAML is available.

```bash
./build/Planner Plan example.yaml XG-CBS XG-A 60.0 10
```

### Benchmarking

**Single map:** (bare filename is looked up in `envs/`)

```bash
./build/Planner Benchmark <Low-Level> example.yaml <time_limit> <output>.csv [weight_for_XG-A-H]
```

**Multiple maps:** (pass directory; bare name with no `/` defaults to `envs/`)

```bash
./build/Planner MultiBenchmark <Low-Level> envs <time_limit> <output>.csv [weight_for_XG-A-H]
```

`<Low-Level>` is one of: `A`, `XG-A`, `XG-A-H`, `S-A`. For `XG-A-H`, append the weight as the last argument.

## Reference

- Justin Kottinger, Shaull Almagor, Morteza Lahijanian. **Conflict-Based Search for Explainable Multi-Agent Path Finding.** ICAPS 2022.
