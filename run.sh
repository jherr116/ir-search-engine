#!/bin/bash
# =============================================================
# run.sh — One-command launcher for Part B
# Builds index from ../data and starts the search UI
#
# Usage: ./run.sh
# Then open http://localhost:5000 in your browser
# =============================================================

set -e  # stop on any error

DATA_DIR="./data"
INDEX_DIR="./part_b/index"

echo "============================================================"
echo "  IR Search Engine — Full Launch"
echo "============================================================"

# Check data exists
if [ ! "$(ls -A $DATA_DIR/*.jsonl 2>/dev/null)" ]; then
    echo "ERROR: No .jsonl files found in $DATA_DIR"
    echo "Run Part A first: cd part_a && ./collector.sh"
    exit 1
fi

echo "[1/2] Building PyLucene index..."
cd part_b
python3 indexer.py \
    --data-dir ../data \
    --index-dir ./index

echo "[2/2] Starting search UI..."
echo "Open http://localhost:5000 in your browser"
python3 app.py \
    --index-dir ./index \
    --port 5000 \
    --host 0.0.0.0