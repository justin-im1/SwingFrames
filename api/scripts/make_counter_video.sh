#!/usr/bin/env bash
# Frame-counter clip for verifying browser seek. Frame n shows n on screen
# and has PTS n/fps. Do not validate the player against ffmpeg -ss.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$ROOT/storage/counter.mp4}"
mkdir -p "$(dirname "$OUT")"
ffmpeg -y -f lavfi -i "testsrc=size=640x480:rate=60:duration=10" \
  -vf "drawtext=text='%{n}':fontsize=72:x=20:y=20:fontcolor=white:box=1:boxcolor=black" \
  -c:v libx264 -g 2 -keyint_min 1 -sc_threshold 0 -an -pix_fmt yuv420p \
  -movflags +faststart "$OUT"
echo "Wrote $OUT"
