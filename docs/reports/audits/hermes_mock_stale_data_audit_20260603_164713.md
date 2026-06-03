# Hermes Mock / Stale Data Audit

Timestamp: 20260603_164713

- telegram_bot.py:2059 — fake
  context: "  - fake sources\n"
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:11 — mock
  context: HERMES_CFO_LOOP_PROVIDER mock | openrouter | deepseek | local (default: mock)
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:38 — mock
  context: _VALID_PROVIDERS = ("mock", "openrouter", "deepseek", "local")
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:77 — I wasn't able to generate a quality response
  context: "i wasn't able to generate a quality response",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:85 — artifact_inventory
  context: "artifact_inventory",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:86 — I can answer from verified artifacts
  context: "i can answer from verified artifacts",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:89 — mock
  context: _MOCK_BLOCK_MARKERS = [
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:90 — Based on mock data
  context: "based on mock data",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:90 — mock
  context: "based on mock data",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:91 — sample
  context: "sample",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:92 — mock
  context: "mock",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:93 — Mailchimp opt-in form
  context: "mailchimp opt-in form",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:94 — Build and publish lead magnet landing page
  context: "build and publish lead magnet landing page",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:95 — Connect affiliate offer link
  context: "connect affiliate offer link",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:96 — research_scout_1
  context: "research_scout_1",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:97 — draft v2 approved
  context: "draft v2 approved",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:127 — mock
  context: """Return current provider. Defaults to mock (no network calls)."""
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:128 — mock
  context: raw = os.getenv("HERMES_CFO_LOOP_PROVIDER", "mock").lower().strip()
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:130 — mock
  context: return "mock"
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:275 — mock
  context: mock_blocked = False
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:292 — mock
  context: mock_blocked = any(marker in lowered_response for marker in _MOCK_BLOCK_MARKERS)
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:296 — mock
  context: elif mock_blocked:
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:297 — mock
  context: fallback_reason = "mock_output_blocked"
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:318 — mock
  context: mock_blocked=mock_blocked,
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:337 — mock
  context: mock_blocked: bool = False,
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:388 — mock
  context: "mock_blocked": mock_blocked,
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:549 — mock
  context: mock_blocked_count = sum(1 for t in traces if t.get("mock_blocked"))
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_cfo_loop_shadow.py:560 — mock
  context: f"Mock-blocked count: {mock_blocked_count}",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:5 — mock
  context: Default mode: mock model, deterministic simulated LLM decisions, no network calls, no Supabase writes.
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:25 — mock
  context: MOCK_MODE = not bool(os.getenv("HERMES_CFO_MODEL_PROVIDER"))
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:39 — artifact_inventory
  context: "artifact_inventory",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:40 — handoff dump
  context: "handoff dump",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:41 — I can answer from verified artifacts
  context: "i can answer from verified artifacts",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:42 — I wasn't able to generate a quality response
  context: "i wasn't able to generate a quality response",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:48 — mock
  context: MOCK_RESPONSE_MARKERS = (
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:49 — Based on mock data
  context: "based on mock data",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:49 — mock
  context: "based on mock data",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:50 — sample
  context: "sample",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:51 — mock
  context: "mock",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:52 — Mailchimp opt-in form
  context: "mailchimp opt-in form",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:53 — Build and publish lead magnet landing page
  context: "build and publish lead magnet landing page",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:54 — Connect affiliate offer link
  context: "connect affiliate offer link",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:55 — research_scout_1
  context: "research_scout_1",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:56 — draft v2 approved
  context: "draft v2 approved",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:108 — mock
  context: # ── Mock Fixtures ──────────────────────────────────────────────────────────────
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:110 — mock
  context: _MOCK_FIXTURES: dict[str, Any] = {
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:150 — research_scout_1
  context: {"scout": "research_scout_1", "task": "Monitor YouTube for new funding content creators", "status": "active", "last_run": "2026-06-02"},
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:151 — content_scout
  context: {"scout": "content_scout", "task": "Review competitor lead magnet landing pages", "status": "queued", "last_run": None},
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:164 — Build and publish lead magnet landing page
  context: "top_priority": "Build and publish lead magnet landing page",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:166 — draft v2 approved
  context: "1. Finalize landing page copy (draft v2 approved)",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:167 — Mailchimp opt-in form
  context: "2. Set up Mailchimp opt-in form",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:168 — Connect affiliate offer link
  context: "3. Connect affiliate offer link",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:200 — mock
  context: def _contains_mock_marker(text: str) -> bool:
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:202 — mock
  context: return any(marker in lowered for marker in MOCK_RESPONSE_MARKERS)
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:505 — mock
  context: evidence["tool_status"] = _MOCK_FIXTURES["tool_status"]
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:507 — mock
  context: evidence["revenue_packet"] = _MOCK_FIXTURES["revenue_packet"]
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:548 — mock
  context: In mock mode: deterministic rule-based tool selection.
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:574 — mock
  context: if MOCK_MODE:
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:575 — mock
  context: return self._mock_reason(message, state, evidence, intent_result)
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:578 — mock
  context: def _mock_reason(self, message: str, state: ConversationState, evidence: dict, intent_result: dict) -> dict:
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:597 — mock
  context: "mode": "mock",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:614 — content_scout
  context: return {"scout_type": "content_scout", "task": f"Check {topic} for new relevant content", "context": message}
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:664 — mock
  context: provider = os.getenv("HERMES_CFO_MODEL_PROVIDER", "mock")
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:668 — mock
  context: f"Provider configured: {provider}. Use mock mode for testing."
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:726 — mock
  context: queue = _MOCK_FIXTURES["approval_queue"]
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:815 — mock
  context: packet = _MOCK_FIXTURES["revenue_packet"]
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:852 — mock
  context: statuses = _MOCK_FIXTURES["tool_status"]
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:989 — content_scout
  context: f"  Scout: {a.get('scout', 'content_scout')}",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:1173 — mock
  context: "mode": reasoning.get("mode", "mock"),
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:1250 — mock
  context: "mode": "mock" if MOCK_MODE else "live",
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- prototypes/hermes_agentic_cfo_loop.py:1253 — mock
  context: "mock_response_blocked": _contains_mock_marker(response),
  live path risk: False
  test only: False
  prototype only: True
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- hermes_command_router/router.py:976 — old Executive Memory
  context: "- old Executive Memory defaults",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- hermes_command_router/router.py:977 — stale provider status
  context: "- stale provider status",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- hermes_command_router/router.py:1377 — old Executive Memory
  context: for legacy in ("old provider status", "old executive memory"):
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- hermes_command_router/router.py:3555 — fake
  context: # ── Evidence gate: block fake trading execution claims before any routing ──
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- hermes_command_router/router.py:3557 — fake
  context: from lib.hermes_evidence_mode import is_fake_trading_claim
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- hermes_command_router/router.py:3558 — fake
  context: if is_fake_trading_claim(raw_text):
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- hermes_command_router/router.py:3561 — fake
  context: what_happened="Fake trading execution claim detected.",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- hermes_command_router/intake.py:595 — old Executive Memory
  context: "what was in the old executive memory",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- hermes_command_router/intake.py:596 — old Executive Memory
  context: "show old executive memory", "show historical executive memory",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- hermes_command_router/intake.py:597 — old Executive Memory
  context: "old executive memory", "historical executive memory"],        "archived_executive_memory", "low",    False),
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/telegram_router.py:10 — fake
  context: is_fake_trading_claim as _is_fake_trading,
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/telegram_router.py:16 — fake
  context: def _is_fake_trading(t: str) -> bool: return False  # type: ignore[misc]
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/telegram_router.py:82 — fake
  context: # ── Evidence gate: block all fake trading execution claims globally ───
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/telegram_router.py:83 — fake
  context: if _EVIDENCE_GATING and _is_fake_trading(text):
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/telegram_router.py:149 — fake
  context: # ── Evidence gate: block fake trading claims before routing ───────────
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/telegram_router.py:150 — fake
  context: if _EVIDENCE_GATING and _is_fake_trading(text) and route == ROUTE_DEMO_STATUS:
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_response_quality.py:261 — I wasn't able to generate a quality response
  context: "I wasn't able to generate a quality response right now. "
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_internal_first.py:2230 — fake
  context: "  - fake sources",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_supabase_first.py:734 — fake
  context: st = classify_market_state({"trend_strength": 0.62, "volatility": 0.58, "liquidity": 0.66, "session": "new york", "momentum": 0.61, "fakeout_risk": 0.33})
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_supabase_first.py:737 — fake
  context: f"Confidence: {round(float(st.get('confidence') or 0)*100,1)}% | Volatility: {st.get('volatility')} | Fakeout risk: {st.get('fakeout_risk')}\n"
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_supabase_first.py:742 — fake
  context: st = classify_market_state({"trend_strength": 0.62, "volatility": 0.58, "liquidity": 0.66, "session": "new york", "momentum": 0.61, "fakeout_risk": 0.33})
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_supabase_first.py:746 — fake
  context: {"drawdown": 1.8, "fakeout_frequency": 0.22, "stability": 0.67},
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_supabase_first.py:751 — fake
  context: st = classify_market_state({"trend_strength": 0.28, "volatility": 0.82, "liquidity": 0.31, "session": "post-close", "momentum": 0.22, "fakeout_risk": 0.79, "news_instability": True})
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_supabase_first.py:766 — fake
  context: "fakeout_involvement": True,
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_supabase_first.py:781 — fake
  context: return "Common failing pattern right now: fakeout entries during unstable/news-driven or low-liquidity windows."
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_supabase_first.py:787 — fake
  context: {"name": "C", "fakeout_filter": "confirmation_close_required"},
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_supabase_first.py:789 — fake
  context: return f"Promising mutation: {m.get('name')} with {m.get('volatility_filter')} + {m.get('fakeout_filter')} (testing only)."
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_supabase_first.py:796 — fake
  context: f"• EURUSD: {p1.get('momentum_personality')} momentum, fakeout {p1.get('fakeout_tendency')}\n"
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_supabase_first.py:797 — fake
  context: f"• BTCUSD: {p2.get('momentum_personality')} momentum, fakeout {p2.get('fakeout_tendency')}"
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: False
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_plain_language_rewriter.py:39 — artifact_inventory
  context: "artifact_inventory", "handoff", "HERMES REPORT", "Evidence:", "Source:",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.

- lib/hermes_plain_language_rewriter.py:152 — artifact_inventory
  context: "artifact_inventory", "handoff_state", "What happened:",
  live path risk: True
  test only: False
  prototype only: False
  should block from primary: True
  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.
