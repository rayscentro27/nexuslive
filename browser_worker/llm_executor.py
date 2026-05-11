"""
LLM-driven browser executor.
Hermes breaks a natural language task into browser steps; Playwright executes them.
Falls back to Netcup Ollama if Hermes is unavailable or returns empty.
"""
import json
import logging
import sys
import urllib.request
import os
from pathlib import Path

logger = logging.getLogger("BrowserWorker.LLM")

# Resolve nexus-ai root so lib/ is importable
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.ollama_fallback import run_ollama_fallback, HERMES_FALLBACK_ENABLED  # noqa: E402

HERMES_URL = os.getenv("HERMES_GATEWAY_URL", "http://localhost:8642")
HERMES_TOKEN = os.getenv("HERMES_GATEWAY_TOKEN", "")

STEP_SCHEMA = """
Return ONLY a JSON array of steps. Each step is an object with:
  {"action": "navigate"|"click"|"type"|"extract"|"screenshot"|"wait"|"scroll", ...params}

Actions and params:
  navigate:   {"action":"navigate","url":"https://..."}
  click:      {"action":"click","selector":"css selector or text description"}
  type:       {"action":"type","selector":"...","text":"..."}
  extract:    {"action":"extract","selector":"...","label":"friendly name"}
  screenshot: {"action":"screenshot","label":"description"}
  wait:       {"action":"wait","ms":2000}
  scroll:     {"action":"scroll","direction":"down"|"up"}

Keep it under 15 steps. If login is required, stop and set {"action":"stop","reason":"login required"}.
"""


def _parse_step_json(raw: str) -> list:
    """Strip markdown fences and parse a JSON step array. Returns [] on failure."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except Exception:
        return []


def plan_steps(task_description: str, page_url: str = "", page_text: str = "",
               model_source: str = "auto") -> list:
    """
    Ask Hermes to plan browser steps for a natural language task.

    model_source:
      "hermes"        → Hermes only
      "netcup_ollama" → Netcup Ollama directly
      "auto"          → Hermes first, Netcup fallback if Hermes fails/empty
    """
    context = f"Current URL: {page_url}\n" if page_url else ""
    if page_text:
        context += f"Page preview (first 500 chars):\n{page_text[:500]}\n"

    prompt = (
        f"{STEP_SCHEMA}\n\n"
        f"Task: {task_description}\n"
        f"{context}"
        "Respond with the JSON array only, no prose."
    )

    hermes_result = None

    # ── Skip Hermes if caller requested Netcup directly ───────────────────────
    if model_source != "netcup_ollama":
        data = json.dumps({
            "model": "hermes",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.2,
        }).encode()

        headers = {"Content-Type": "application/json"}
        if HERMES_TOKEN:
            headers["Authorization"] = f"Bearer {HERMES_TOKEN}"

        try:
            req = urllib.request.Request(
                f"{HERMES_URL}/v1/chat/completions",
                data=data, headers=headers,
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read())
            raw = resp["choices"][0]["message"]["content"].strip()
            hermes_result = _parse_step_json(raw)
            if hermes_result:
                logger.info("Hermes planning succeeded (%d steps)", len(hermes_result))
                return hermes_result
            logger.warning("Hermes planning returned empty step list")
        except Exception as e:
            logger.error("Hermes planning failed: %s", e)

    # ── Netcup Ollama fallback ────────────────────────────────────────────────
    should_fallback = (
        model_source == "netcup_ollama"
        or (model_source == "auto" and HERMES_FALLBACK_ENABLED and not hermes_result)
    )

    if should_fallback:
        logger.warning("Triggering Netcup Ollama fallback for browser planning")
        fb = run_ollama_fallback(prompt)
        if fb["success"]:
            steps = _parse_step_json(fb["response"])
            if steps:
                logger.info("Netcup Ollama fallback provided %d steps", len(steps))
                return steps
            logger.warning("Netcup Ollama response was not valid JSON steps; response=%s",
                           fb["response"][:120])
        else:
            logger.error("Netcup Ollama fallback failed: %s", fb["error"])

    return []


async def execute_steps(page, steps: list) -> dict:
    """Execute a list of planned steps on the given Playwright page."""
    results = []
    extracted = {}
    screenshots = []

    for i, step in enumerate(steps):
        action = step.get("action", "")
        logger.info(f"  Step {i+1}: {action} — {json.dumps(step)[:80]}")

        try:
            if action == "navigate":
                await page.goto(step["url"], wait_until="domcontentloaded", timeout=20000)
                results.append(f"Navigated to {step['url']}")

            elif action == "click":
                sel = step.get("selector", "")
                # Try CSS first, fall back to text match
                try:
                    await page.locator(sel).first.click(timeout=5000)
                except Exception:
                    await page.get_by_text(sel, exact=False).first.click(timeout=5000)
                results.append(f"Clicked '{sel}'")

            elif action == "type":
                sel = step.get("selector", "")
                text = step.get("text", "")
                await page.locator(sel).first.fill(text, timeout=5000)
                results.append(f"Typed into '{sel}'")

            elif action == "extract":
                sel = step.get("selector", "")
                label = step.get("label", sel)
                try:
                    el = page.locator(sel).first
                    text = await el.text_content(timeout=5000)
                    extracted[label] = (text or "").strip()
                    results.append(f"Extracted '{label}': {extracted[label][:60]}")
                except Exception:
                    extracted[label] = "(not found)"
                    results.append(f"Extract '{label}': not found")

            elif action == "screenshot":
                label = step.get("label", f"step_{i+1}")
                import base64
                data = await page.screenshot()
                screenshots.append({"label": label, "b64": base64.b64encode(data).decode()})
                results.append(f"Screenshot: {label}")

            elif action == "wait":
                import asyncio
                ms = int(step.get("ms", 1000))
                await asyncio.sleep(ms / 1000)
                results.append(f"Waited {ms}ms")

            elif action == "scroll":
                direction = step.get("direction", "down")
                delta = 600 if direction == "down" else -600
                await page.evaluate(f"window.scrollBy(0, {delta})")
                results.append(f"Scrolled {direction}")

            elif action == "stop":
                results.append(f"Stopped: {step.get('reason','?')}")
                break

        except Exception as e:
            results.append(f"Step {i+1} ({action}) failed: {str(e)[:100]}")
            logger.warning(f"Step {i+1} failed: {e}")

    return {
        "steps_run": len(results),
        "results": results,
        "extracted": extracted,
        "screenshots": screenshots,
        "summary": "\n".join(results),
    }


async def run_open_task(page, task_description: str,
                        model_source: str = "auto") -> dict:
    """
    Plan and execute a natural language browser task end-to-end.

    model_source: "hermes" | "netcup_ollama" | "auto"
    """
    logger.info("Open task: %s (model_source=%s)", task_description, model_source)

    try:
        current_url = page.url
        body_text = await page.evaluate("document.body?.innerText || ''")
    except Exception:
        current_url = ""
        body_text = ""

    steps = plan_steps(task_description, current_url, body_text, model_source=model_source)
    if not steps:
        return {
            "status": "error",
            "summary": "No provider could plan steps for this task",
            "source": "none",
            "fallback_used": model_source == "netcup_ollama",
        }

    logger.info("Planned %d steps", len(steps))
    execution = await execute_steps(page, steps)
    execution["status"] = "ok"
    execution["task"] = task_description
    execution["model_source"] = model_source
    return execution
