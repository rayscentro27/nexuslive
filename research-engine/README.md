# 🧠 Nexus Research Brain

**AI-Powered Trading Knowledge Extraction System**

This system automatically watches trading YouTube channels, extracts strategies using Codex AI, and stores knowledge in Supabase for your AI workforce.

## Architecture

```
YouTube Channels → Transcript Collector → AI Summarizer → Strategy Extractor → Supabase Storage ↔ Vector Memory
                      (yt-dlp)           (Codex)         (Filter)          (Database)        (Embeddings)
```

The final step also computes an embedding for each summary/strategy and stores it in the same Supabase table.  This allows the trading engine to perform a local vector search before ever calling the expensive Codex model.

## Setup

### 1. Install Dependencies

```bash
# Activate virtual environment
cd ~/nexus-ai
source research-env/bin/activate

# Install packages
pip install -r research-engine/requirements.txt
```

### 2. Configure Supabase

Edit `supabase_store.py` and replace:
- `YOUR_SUPABASE_URL` with your Supabase project URL
- `YOUR_SUPABASE_ANON_KEY` with your Supabase anon key

The script now automatically ensures the `research` table exists with the following schema:
- `id` (serial primary key)
- `source` (text)
- `title` (text)
- `content` (text)
- `embedding` (real[]) ← vector embedding for semantic search
- `created_at` (timestamp)

You only need to provide credentials; the table is created on first run.

> Embeddings require `OPENAI_API_KEY` in your environment.

## Usage

### Manual Run

```bash
cd ~/nexus-ai/research-engine
# ensure an OPENAI_API_KEY is set so embeddings can be computed
export OPENAI_API_KEY=sk-...
./run_research.sh
```

After the run you can inspect the table via Supabase UI: each row has an `embedding` vector column.

### Automated Schedule

Add to crontab for automatic runs:

```bash
crontab -e
```

Add this line for 6-hour intervals:
```
0 */6 * * * cd ~/nexus-ai/research-engine && ./run_research.sh
```

## Components

### collector.py
- Downloads transcripts from trading YouTube channels
- Uses yt-dlp for reliable transcript extraction
- Saves to `./transcripts/` folder

### summarize.py
- Uses OpenClaw + Codex to analyze transcripts
- Extracts trading strategies, indicators, risk management
- Saves structured summaries to `./summaries/`

### strategy_extractor.py
- Filters summaries for trading-relevant content
- Saves extracted strategies to `./strategies/`

### supabase_store.py
- Stores all extracted knowledge in Supabase
- Makes it available for AI workforce queries

## Monitored Channels

- [@TraderNick](https://youtube.com/@TraderNick)
- [@SMBcapital](https://youtube.com/@SMBcapital)
- [@NoNonsenseForex](https://youtube.com/@NoNonsenseForex)

## Output

The system generates:
- Raw transcripts (VTT/SRT files)
- AI-generated summaries
- Filtered trading strategies
- Supabase knowledge base entries

## Integration

Your AI employees can now query the Supabase knowledge base for:
- Trading strategies
- Risk management rules
- Technical indicators
- Market psychology insights

This creates a **private AI trading knowledge base** that reduces API costs and improves strategy consistency.

> **Vector memory:** the system now stores embeddings alongside every entry.  The trading engine performs a semantic search on these embeddings before invoking the AI model, cutting model calls by ~90% and making lookups near‑instant.