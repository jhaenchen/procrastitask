#!/bin/bash
# This script runs the perf tests over several previous commits and logs the runtime to a file for comparison
# To find a commit that was slow

set -euo pipefail

# Absolute path to consistent test file
FIXED_TEST_FILE=~/Desktop/test_performance.py
OUT_FILE=runtime_log.csv

# Clear or create log file
echo "commit_hash,runtime_s" > "$OUT_FILE"

cd ~/Documents/GitHub/procrastitask/

# Define the range of commits (adjust as needed)
COMMITS=$(git rev-list --reverse 5c569acf922e9e290efa91022e2d9f687894e94c..HEAD)

for commit in $COMMITS; do
  cd ~/Documents/GitHub/procrastitask/
  echo "Checking commit $commit"

  # Clean up any leftover test file before switching
  rm -f tests/test_performance.py

  git checkout -q "$commit" || { echo "Failed to checkout $commit"; continue; }

  # Ensure tests directory exists and inject the file
  mkdir -p tests
  cp "$FIXED_TEST_FILE" tests/test_performance.py

  # Run the test and parse runtime from "Total runtime: 0.4285 seconds"
  output=$(python3 -m unittest tests/test_performance.py -v -k test_main_path 2>&1 || true)
  runtime=$(echo "$output" | sed -nE 's/Total runtime: ([0-9]+\.[0-9]+) seconds/\1/p' | tail -1)

  if [[ -z "$runtime" ]]; then
    echo "Warning: no runtime for $commit"
    runtime="NA"
  fi

  cd ..

  echo "$commit,$runtime" >> "$OUT_FILE"
done

# Restore working branch
cd ~/Documents/GitHub/procrastitask/
git checkout perf-testing

