#!/bin/bash

# Nexus Research Brain - Automated Pipeline
echo "🧠 Starting Nexus Research Brain..."

# Load environment variables
if [ -f ../.env ]; then
    set -a
    source ../.env
    set +a
fi

# Activate virtual environment
source ../research-env/bin/activate 2>/dev/null || true

echo "📥 Collecting YouTube transcripts..."
python3 collector.py

echo "🤖 Summarizing with Codex..."
python3 summarize.py

echo "🎯 Extracting trading strategies..."
python3 strategy_extractor.py

echo "💾 Storing in Supabase..."
python3 supabase_store.py

echo "📊 Ranking strategies..."
python3 strategy_ranker.py --limit 30

echo "🔬 Enhancing ranked strategies..."
python3 strategy_enhancer.py --limit 20

echo "✅ Research cycle complete!"
echo "🦞 Nexus AI workforce updated with fresh trading knowledge."