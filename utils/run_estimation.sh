#!/bin/bash
# Quick Cost Estimation Runner
# Run this with: bash run_estimation.sh YOUR_API_KEY_HERE

if [ -z "$1" ]; then
    echo "❌ Error: No API key provided"
    echo ""
    echo "Usage: bash run_estimation.sh YOUR_GEMINI_API_KEY"
    echo ""
    echo "Get your free API key at: https://aistudio.google.com/app/apikey"
    exit 1
fi

export GEMINI_API_KEY="$1"

echo "🚀 Starting Enhanced Cost Estimation Pipeline"
echo "=============================================="
echo "Model: gemini-1.5-flash (15 req/min for free tier)"
echo "Input: enriched_data/6-report_enriched.json"
echo "Output: cost_estimates/6-report_enhanced_estimates.json"
echo ""

python enhanced_cost_estimator.py \
    --input enriched_data/6-report_enriched.json \
    --model gemini-1.5-flash \
    --temperature 0.3

echo ""
echo "✅ Estimation complete! Check cost_estimates/ for results"

