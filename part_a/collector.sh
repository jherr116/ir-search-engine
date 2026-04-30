#!/bin/bash
# =============================================================================
# collector.sh — Part A Entry Point
#
# Usage:
#   ./collector.sh <query> <max-posts> <output-dir>
#
# Example:
#   ./collector.sh "artificial intelligence" 5000 ../data
#
# Credentials are read from environment variables:
#   export BSKY_HANDLE="yourhandle.bsky.social"
#   export BSKY_PASSWORD="your-app-password"
#
# Or you can hardcode them below for grading convenience (see CONFIGURATION).
# =============================================================================

# ── CONFIGURATION (fill these in before submitting) ──────────────────────────
BSKY_HANDLE="jherr116.bsky.social"
BSKY_PASSWORD="wc4v-foz5-vwvr-tedm"

# ── Argument Parsing ─────────────────────────────────────────────────────────
QUERY="${1:-artificial intelligence}"
MAX_POSTS="${2:-5000}"
OUTPUT_DIR="${3:-../data}"

echo "============================================================"
echo "  IR Project — Part A: Bluesky Collector"
echo "  Query      : $QUERY"
echo "  Max posts  : $MAX_POSTS"
echo "  Output dir : $OUTPUT_DIR"
echo "============================================================"

# ── Dependency Check ─────────────────────────────────────────────────────────
echo ""
echo "[1/3] Checking Python..."
python3 --version || { echo "ERROR: python3 not found."; exit 1; }

echo "[2/3] Installing dependencies..."
pip install -r requirements.txt --quiet

# ── Run Collector ─────────────────────────────────────────────────────────────
echo "[3/3] Starting collection..."
python3 collector.py \
    --query      "$QUERY" \
    --max-posts  "$MAX_POSTS" \
    --output-dir "$OUTPUT_DIR" \
    --handle     "$BSKY_HANDLE" \
    --password   "$BSKY_PASSWORD"

echo ""
echo "Collection complete. Files are in: $OUTPUT_DIR"
