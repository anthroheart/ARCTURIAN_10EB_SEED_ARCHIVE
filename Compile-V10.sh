#!/bin/bash
# AnthroHeart v10 FIXED .dat freeze
set +H; set +o histexpand 2>/dev/null || true; set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
CPP="AnthroHeart-Future-Archive-Seed-V10-FIXED-DAT.cpp"
echo "Building $CPP — v10 FIXED .dat freeze..."
g++ -O2 -std=c++17 -Wall -Wextra "./$CPP" -o "./seed"
chmod +x "./seed"
echo "✅ Build OK"
if [[ "$1" == "--testrun" || "$1" == "-t" ]]; then
  ./seed --testrun
  ls -lh ./out_archive.zip
  echo "--- out_archive (all readable .txt now, no .dat freeze) ---"
  ls -R ./out_archive | head -300
else
  ./seed
fi
