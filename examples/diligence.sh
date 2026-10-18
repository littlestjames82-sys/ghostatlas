#!/bin/sh
# Build a diligence-audience GhostAtlas for the ground-truth fixture.
# Local only, no network. Usage: ./diligence.sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(dirname "$HERE")
OUT=$(mktemp -d)
export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m ghostatlas build "$REPO/tests/fixtures/ground_truth/project" -o "$OUT/atlas.html" --audience diligence
echo "HTML map:  $OUT/atlas.html"
echo "Brief:     $OUT/ATLAS.md  (diligence ordering, checked / not-checked box)"
