#!/bin/sh
# Build a GhostAtlas for the ground-truth fixture project.
# Local only, no network. Usage: ./demo.sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(dirname "$HERE")
OUT=$(mktemp -d)
export PYTHONPATH="$REPO/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m ghostatlas build "$REPO/tests/fixtures/ground_truth/project" -o "$OUT/atlas.html"
echo "HTML map:  $OUT/atlas.html"
echo "Brief:     $OUT/ATLAS.md  (or next to the HTML output)"
