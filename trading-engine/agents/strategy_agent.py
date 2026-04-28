import requests
import json
from datetime import datetime
import os
import logging

# optional OpenAI embeddings
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class NexusStrategyAgent:
    """AI Trading Strategy Agent - Uses research knowledge to make trading decisions"""
    logger = logging.getLogger('StrategyAgent')

    def __init__(self):
        # Hermes configuration
        self.gateway_url = "http://localhost:8642"
        self.auth_token = "3658055de4324bc84b0ec1cf4d85af003094cc971c68987d"

        # Supabase for research knowledge (can be set via ENV or config file)
        self.supabase_url = os.getenv('SUPABASE_URL', "YOUR_SUPABASE_URL")
        self.supabase_key = os.getenv('SUPABASE_KEY', "YOUR_SUPABASE_ANON_KEY")
        self.supabase = None
        self.fast_mode = os.getenv('NEXUS_PAPER_FAST_MODE', 'true').lower() == 'true'

        if self.supabase_url != "YOUR_SUPABASE_URL":
            try:
                from supabase import create_client
                self.supabase = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                self.logger.warning(f"Supabase client unavailable, continuing without research DB: {e}")
                self.supabase = None

    def query_research_knowledge(self, query):
        """Query the research knowledge base for relevant strategies.

        This method now performs a vector search first.  If the Supabase table
        contains embeddings, it will compute the query embedding and fetch the
        top‑K similar entries locally, adding their content to the Codex prompt.
        This dramatically reduces model calls and costs.
        """
        if not self.supabase:
            return "Research knowledge not available - configure Supabase first"

        try:
            # perform vector search
            entries = self.vector_search(query)
            if entries:
                knowledge_text = "\n".join([f"{e['title']}: {e['content'][:500]}" for e in entries])
            else:
                # fallback to full table dump
                resp = self.supabase.table("research").select("title,content").execute()
                data = resp.data
                knowledge_text = "\n".join([f"{d['title']}: {d['content'][:500]}" for d in data])

            prompt = f"""
            Based on this trading research knowledge, answer: {query}

            Knowledge base:
            {knowledge_text[:2000]}

            Provide specific, actionable trading advice.
            """

            return self.ask_codex(prompt)
        except Exception as e:
            return f"Error querying knowledge: {e}"

    def analyze_market_conditions(self, symbol, timeframe, indicators):
        """Analyze current market conditions using research knowledge"""

        query = f"""
        Analyze {symbol} on {timeframe} timeframe with these indicators: {indicators}

        Based on trading research knowledge, what is the current market condition?
        Should we: BUY, SELL, or HOLD?
        What entry/exit levels?
        What risk management rules apply?
        """

        research_insights = self.query_research_knowledge(query)

        analysis_prompt = f"""
        You are a professional trading strategy analyst.

        Market Data:
        - Symbol: {symbol}
        - Timeframe: {timeframe}
        - Indicators: {indicators}

        Research Insights:
        {research_insights}

        Provide a structured trading decision:
        1. Market Analysis
        2. Trading Signal (BUY/SELL/HOLD)
        3. Entry Price
        4. Stop Loss
        5. Take Profit
        6. Risk Management Rules
        7. Confidence Level (0-100%)
        """

        if self.fast_mode:
            return self.build_fast_analysis(symbol, timeframe, indicators, research_insights)
        return self.ask_codex(analysis_prompt)

    def build_fast_analysis(self, symbol, timeframe, indicators, research_insights):
        """Cheap, deterministic fallback for paper autonomy."""
        return (
            f"FAST_PAPER_MODE\n"
            f"Symbol: {symbol}\n"
            f"Timeframe: {timeframe}\n"
            f"Indicators: {indicators}\n"
            f"Research: {str(research_insights)[:400]}\n"
            f"Decision: defer to incoming signal; use configured stop/take-profit; paper mode only."
        )

    def embed_text(self, text: str):
        """Compute embedding for text using local Hugging Face sentence-transformers."""
        if not hasattr(self, '_hf_model'):
            self._hf_model = os.getenv('HF_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise RuntimeError('sentence_transformers library not available')

        try:
            # Use local model for embeddings (no API calls, no costs!)
            model = SentenceTransformer(self._hf_model)
            embedding = model.encode(text)
            return [float(v) for v in embedding]
        except Exception as e:
            raise RuntimeError(f"Embedding computation error: {e}")

    def vector_search(self, query: str, top_k: int = 5):
        """Return top_k research entries most similar to the query."""
        try:
            # compute query embedding
            query_emb = self.embed_text(query)
            # pull all stored embeddings
            resp = self.supabase.table('research').select('title,content,embedding').execute()
            rows = resp.data or []

            def cosine(a, b):
                # simple cosine similarity
                dot = sum(x*y for x,y in zip(a,b))
                norm_a = sum(x*x for x in a) ** 0.5
                norm_b = sum(x*x for x in b) ** 0.5
                return dot / (norm_a * norm_b + 1e-8)

            scored = []
            for row in rows:
                emb = row.get('embedding')
                if emb:
                    score = cosine(query_emb, emb)
                    scored.append((score, row))
            scored.sort(key=lambda x: x[0], reverse=True)
            top = [r for s,r in scored[:top_k]]
            return top
        except Exception as e:
            logger = None
            try:
                import logging
                logger = logging.getLogger('StrategyAgent')
            except Exception:
                pass
            if logger:
                logger.error(f"Vector search error: {e}")
            return []

    def ask_codex(self, prompt):
        """Query Codex through Hermes"""
        payload = {
            "message": prompt,
            "model": "openai-codex/gpt-5.3-codex",
            "stream": False
        }

        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(f"{self.gateway_url}/agent", json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json().get("response", "No response from Codex")
            else:
                return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Connection error: {e}"

    def generate_trading_signal(self, market_data):
        """Generate a complete trading signal"""
        analysis = self.analyze_market_conditions(
            market_data.get('symbol', 'EURUSD'),
            market_data.get('timeframe', 'H1'),
            market_data.get('indicators', 'RSI, MACD, Moving Averages')
        )

        signal = {
            'timestamp': datetime.now().isoformat(),
            'analysis': analysis,
            'market_data': market_data,
            'generated_by': 'NexusStrategyAgent'
        }

        return signal
