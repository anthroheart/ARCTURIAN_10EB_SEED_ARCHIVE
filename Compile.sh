#!/bin/bash
# AnthroHeart v6 BBS LORD GOOD FILES v2 + 4K/8K - ROBUST, NO SUDO, handles spaces and ! in path
# Fixes: no out_archive created, sudo asking, can't find file

# Disable history expansion that breaks ! in path /home/anthro/! FOR_HUMANITY/TO_SEND
set +H
set +o histexpand 2>/dev/null || true
set -e

# Always work from script's own directory, even if called from elsewhere, handles spaces
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🦊 AnthroHeart — BBS LORD GOOD FILES v2 + 4K/8K + Disney Quality + INDIE SPEC — FIXED"
echo "PWD: $SCRIPT_DIR"
echo ""

# Check g++
if ! command -v g++ >/dev/null 2>&1; then
  echo "❌ g++ not found. Install: sudo apt install build-essential"
  exit 1
fi

# Warn if running under sudo (causes permission hell)
if [ "$EUID" -eq 0 ]; then
  echo "⚠️  You are running as root/sudo. This will create files owned by root and break next run."
  echo "   Please run WITHOUT sudo: bash ./Compile.sh --testrun"
  echo "   Fix ownership: sudo chown -R $USER:$USER \"$SCRIPT_DIR\""
  echo ""
fi

# Check write permission
if [ ! -w "$SCRIPT_DIR" ]; then
  echo "❌ No write permission in $SCRIPT_DIR"
  echo "   DO NOT USE SUDO. Fix with:"
  echo "   sudo chown -R $USER:$USER \"$SCRIPT_DIR\""
  echo "   chmod -R u+rw \"$SCRIPT_DIR\""
  exit 1
fi

# Ensure out_archive exists BEFORE compile so ls works
mkdir -p "$SCRIPT_DIR/out_archive"
chmod u+rw "$SCRIPT_DIR/out_archive"
echo "✅ out_archive folder ensured: $SCRIPT_DIR/out_archive"
ls -ld "$SCRIPT_DIR/out_archive"
echo ""

# Good g++ with quoted paths to handle spaces and ! 
echo "Building..."
g++ -O2 -std=c++17 "./AnthroHeart-Future-Archive-Seed-V6-FINAL.cpp" -o "./seed"
chmod +x "./seed"
echo ""
echo "✅ Build OK - $(ls -lh ./seed | awk '{print $5}') - ./seed exists in $SCRIPT_DIR"
echo ""

# Run
if [[ "$1" == "--testrun" || "$1" == "-t" ]]; then
  echo "=== Testrun GOOD (Small + Auto GOOD renders) ==="
  echo "Running: ./seed --testrun"
  ./seed --testrun
  echo ""
  echo "=== After Testrun ==="
  ls -lh ./out_archive.zip 2>&1 || echo "out_archive.zip not found"
  ls -lh ./out_archive/ 2>&1
  echo ""
  echo "=== Generating 10 HASHES for Internet Archive ==="
  python3 "./generate_10_hashes.py" || python3 "./out_archive/generate_10_hashes.py" || echo "hashes script not found, run python3 generate_10_hashes.py manually"
  ls -lh ./HASHES.txt ./out_archive.zip.* 2>&1 || true
else
  echo "=== Running BBS menu GOOD FILES ==="
  echo "Tip: bash ./Compile.sh --testrun  for auto test (good for rest)"
  echo "Tip: If path has ! and spaces, ALWAYS use: bash ./Compile.sh   not ./Compile.sh alone"
  echo ""
  ./seed
fi
