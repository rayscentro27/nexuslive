#!/bin/bash

# Test script for Nexus Research Brain
echo "🧠 Testing Nexus Research Brain..."

# Check if virtual environment exists
if [ ! -d "../research-env" ]; then
    echo "❌ Virtual environment not found. Run setup first."
    exit 1
fi

# Activate environment
source ../research-env/bin/activate

# Check if packages are installed
python3 -c "import yt_dlp, pandas, supabase, openai; print('✅ All packages installed')"

# Check if scripts exist
if [ ! -f "collector.py" ] || [ ! -f "summarize.py" ]; then
    echo "❌ Scripts missing"
    exit 1
fi

echo "✅ Nexus Research Brain is ready!"
echo ""
echo "To run the full pipeline:"
echo "  ./run_research.sh"
echo ""
echo "To test individual components:"
echo "  python3 collector.py"
echo "  python3 summarize.py"
echo "  python3 strategy_extractor.py"
echo "  python3 supabase_store.py"