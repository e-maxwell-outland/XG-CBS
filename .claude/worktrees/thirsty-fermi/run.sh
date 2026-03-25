#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

BUILD_DIR="build"
RUN_ARGS=("$@")

# Configure and build
cmake -B "$BUILD_DIR" -S . -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD_DIR" -j

EXE="$BUILD_DIR/Planner"
if [[ ${#RUN_ARGS[@]} -gt 0 ]]; then
  exec "$EXE" "${RUN_ARGS[@]}"
else
  echo "Build complete: $EXE"
  echo "Usage examples (YAMLs in envs/):"
  echo "  ./$EXE Plan example.yaml CBS A <time_limit>"
  echo "  ./$EXE Plan example.yaml XG-CBS XG-A <time_limit> <cost_bound>"
  echo "  ./$EXE Benchmark <Low-Level> example.yaml <time_limit> <output>.csv"
fi
