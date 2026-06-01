"""
hermes_language_pack.py
Maps common natural language to broad intent categories.
Phrase matching is substring-based for conversational flexibility.
"""
from __future__ import annotations

# ── Small talk ─────────────────────────────────────────────────────────────────
SMALL_TALK_PHRASES = frozenset([
    "did you sleep", "did you get sleep", "did you rest", "do you sleep",
    "how are you", "how are you doing", "how's it going", "hows it going",
    "are you awake", "are you online", "are you there", "are you up",
    "you awake", "you up", "you online",
    "good morning", "good afternoon", "good evening", "good night",
    "morning hermes", "hey hermes", "hello hermes",
    "wake up", "you still there", "still there",
])

SMALL_TALK_RESPONSE = (
    "I don't sleep, but I'm online and ready. "
    "I can help with Nexus status, content drafts, opportunities, "
    "action queue, decisions, scouts, and memory sources."
)

# ── Capability questions ────────────────────────────────────────────────────────
CAPABILITY_PHRASES = frozenset([
    "what can you answer", "what can you do", "what can i ask",
    "what do you know", "what can i ask you", "what can you help with",
    "what are your capabilities", "what are you able to do",
    "what questions can you answer", "what commands do you know",
    "how can you help", "help me understand what you can do",
    "show me what you can do", "what do you support",
    "what topics do you cover",
    "help", "/help",
])

CAPABILITY_RESPONSE = """\
I can help with:

• Nexus status — 'what is the system health', 'check backend health'
• Content drafts — 'show it', 'make it simpler', 'turn it into a lead magnet'
• What changed — 'what changed', 'compare versions'
• Recommendations — 'what do you recommend', 'what is the next best move'
• Opportunities — 'what opportunities should we review'
• Monetization — 'what is the best money making opportunity right now'
• Memory sources — 'show memory sources', 'where did that answer come from'
• Approval queue — 'what needs my approval'
• Decision log — 'what did hermes decide'
• Knowledge gaps — 'show knowledge gaps', 'show unanswered questions'

Ask me anything Nexus-related and I'll route or log it."""

# ── System health questions ────────────────────────────────────────────────────
SYSTEM_HEALTH_PHRASES = frozenset([
    "what is system health", "what is the system health", "system health",
    "is nexus healthy", "what is broken", "what is down", "what's down",
    "what's broken", "provider status", "are the systems running",
    "how is the system", "how is nexus", "how are the systems",
    "system status", "what is wrong", "anything broken",
    "is everything working", "check system", "health check",
    "backend health", "what is the status of the system",
    "any issues", "are we up", "is everything up",
])

SYSTEM_HEALTH_COMMAND = "check backend health"

# ── Monetization / revenue questions ──────────────────────────────────────────
MONETIZATION_PHRASES = frozenset([
    "best money making opportunity right now",
    "what can make money right now", "what should we monetize",
    "best revenue move", "next best money move",
    "how do we make money today", "what can make money this week",
    "best money making", "money making opportunity",
    "top opportunity", "best opportunity right now",
    "what makes money", "best way to make money",
    "revenue opportunity", "make money this week", "best revenue",
    "what should we focus on for revenue", "what is the top revenue move",
    "monetization strategy", "money move", "revenue move",
    "what can generate revenue", "how to make money today",
])

MONETIZATION_COMMAND = "what opportunities should we review"

# ── Content asset questions ────────────────────────────────────────────────────
# These are handled by the continuity dict — we just need to classify them
CONTENT_ASSET_PHRASES = frozenset([
    "show it", "make it better", "make it simpler", "make it shorter",
    "what changed", "what do you recommend", "turn it into a lead magnet",
    "create a newsletter from this", "create a video script from this",
    "revise it", "improve it", "clean it up", "show the draft",
    "show latest draft", "show the checklist",
])

CONTENT_ASSET_REDIRECT = (
    "Use a content draft command: 'show it', 'make it simpler', "
    "'turn it into a lead magnet', 'what do you recommend', or 'what changed'."
)

# ── Memory source questions ────────────────────────────────────────────────────
MEMORY_SOURCE_PHRASES = frozenset([
    "show memory sources", "where did that answer come from",
    "what memory did you use", "show archived executive memory",
    "show stale memory debug", "memory sources",
    "where does your memory come from", "where do you get memory from",
    "what sources do you use",
])

# ── External info — requires tools not connected ──────────────────────────────
EXTERNAL_INFO_KEYWORDS = [
    "weather", "temperature", "forecast", "rain", "sunny",
    "latest news", "breaking news", "news today", "news right now",
    "stock price", "stock market", "market price",
    "sports score", "game score", "score of the game",
    "price of bitcoin", "price of ethereum", "crypto price",
    "current price of", "live web search", "search the web",
    "what time is it", "current time", "what's the time",
    "exchange rate", "currency rate", "forex rate",
]

def is_external_info(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in EXTERNAL_INFO_KEYWORDS)

def external_info_topic(text: str) -> str:
    t = text.lower()
    for kw in EXTERNAL_INFO_KEYWORDS:
        if kw in t:
            return kw
    return "that"

def format_external_unavailable_response(topic: str) -> str:
    return (
        f"I don't currently have a live {topic} provider connected in Telegram. "
        "I logged this as a capability gap so we can decide whether to add that support. "
        "For live Nexus data, ask: 'nexus status', 'show memory sources', or 'what opportunities should we review'."
    )

# ── Unknown / unresolved fallback ─────────────────────────────────────────────
UNKNOWN_FALLBACK_RESPONSE = (
    "I could not answer that from active Nexus memory yet. "
    "I logged it as a knowledge gap for review. "
    "You can ask me about: Nexus status, action queue, content drafts, "
    "opportunities, decisions, scouts, or memory sources."
)

# ── Category names ─────────────────────────────────────────────────────────────
CATEGORY_SMALL_TALK         = "small_talk"
CATEGORY_CAPABILITY         = "capability_question"
CATEGORY_SYSTEM_HEALTH      = "system_health"
CATEGORY_MONETIZATION       = "monetization_question"
CATEGORY_CONTENT_ASSET      = "content_asset_question"
CATEGORY_MEMORY_SOURCE      = "memory_source_question"
CATEGORY_EXTERNAL_INFO      = "external_info_question"
CATEGORY_UNKNOWN            = "unknown_or_unresolved"

ALL_CATEGORIES = {
    CATEGORY_SMALL_TALK, CATEGORY_CAPABILITY, CATEGORY_SYSTEM_HEALTH,
    CATEGORY_MONETIZATION, CATEGORY_CONTENT_ASSET, CATEGORY_MEMORY_SOURCE,
    CATEGORY_EXTERNAL_INFO, CATEGORY_UNKNOWN,
}

# ── Gap reason codes ───────────────────────────────────────────────────────────
GAP_MISSING_ROUTE           = "missing_route"
GAP_MISSING_PROVIDER        = "missing_provider"
GAP_MISSING_ACTIVE_MEMORY   = "missing_active_memory"
GAP_UNCLEAR_FOLLOWUP        = "unclear_followup"
GAP_STALE_MEMORY_BLOCKED    = "stale_memory_blocked"
GAP_UNSUPPORTED_EXTERNAL    = "unsupported_external_info"
GAP_HANDLER_ERROR           = "handler_error"
GAP_LOW_CONFIDENCE          = "low_confidence_answer"
