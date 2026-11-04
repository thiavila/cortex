#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
while IFS= read -r step || [ -n "$step" ]; do
  case "$step" in ''|'#'*) continue ;; esac
  bash -e -o pipefail -c "$step" </dev/null
done < scripts/ci/local-ci.steps
