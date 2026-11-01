#!/usr/bin/env bash
set -euo pipefail
command -v python3 >/dev/null || { echo 'Prepare Python 3.12+ and the README offline snapshot prerequisites first.' >&2; exit 1; }
command -v go >/dev/null || { echo 'Prepare cached Go 1.27.1 and engine dependencies explicitly first.' >&2; exit 1; }
export GOTOOLCHAIN=local GOPROXY=off GOSUMDB=off
[[ $(go env GOVERSION) == go1.27.1 ]] || { echo 'Expected cached Go 1.27.1; no toolchain downloads in hook.' >&2; exit 1; }
[[ -f .baseline-work/revision && -f .baseline-work/source/go.mod ]] || { echo 'Missing isolated snapshot. Follow README Offline checks before installing hooks; do not regenerate inventory or goldens.' >&2; exit 1; }
# Existing validator verifies pinned Git object/snapshot bytes and cached dependencies.
python3 scripts/baseline/baseline.py validate --engine ../hermes
python3 -m unittest discover -s scripts/baseline -p 'test_*.py' -v
