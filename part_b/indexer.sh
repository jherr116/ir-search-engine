#!/bin/bash
# =============================================================================
# indexer.sh — Part B Entry Point
#
# Usage:
#   ./indexer.sh <output-dir>
#
# Example:
#   ./indexer.sh ./index
#
# This script:
#   1. Installs Python dependencies
#   2. Runs the PyLucene indexer against ../data/*.jsonl
#   3. Writes the Lucene index to <output-dir>
# =============================================================================

INDEX_DIR="${1:-./index}"
DATA_DIR="${2:-../data}"

echo "============================================================"
echo "  IR Project — Part B: PyLucene Indexer"
echo "  Data dir  : $DATA_DIR"
echo "  Index dir : $INDEX_DIR"
echo "============================================================"

echo ""
echo "[1/3] Checking Python..."
python3 --version || { echo "ERROR: python3 not found."; exit 1; }

echo "[2/3] Installing dependencies..."
pip install -r requirements.txt --quiet

echo "[3/3] Building index..."
python3 indexer.py \
    --data-dir  "$DATA_DIR" \
    --index-dir "$INDEX_DIR"

echo ""
echo "Indexing complete. Index written to: $INDEX_DIR"
echo "Run the search UI with: python3 app.py --index-dir $INDEX_DIR"
