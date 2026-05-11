#!/usr/bin/env python3
"""
Nexus AI Research Brain
Pipeline: YouTube transcripts → AI summaries → strategy extraction → signal candidates
Wraps existing research-engine scripts into a single callable module.
"""
import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger("ResearchBrain")

BASE = Path(__file__).parent.parent / "research-engine"
TRANSCRIPTS = BASE / "transcripts"
SUMMARIES   = BASE / "summaries"
STRATEGIES  = BASE / "strategies"

STATE_FILE = Path(__file__).parent / "brain_state.json"

# ─────────────────────────────────────────────
# State helpers
# ─────────────────────────────────────────────

def _load_state() -> Dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "last_run": None,
        "total_transcripts": 0,
        "total_summaries": 0,
        "total_strategies": 0,
        "last_error": None,
        "pipeline_status": "idle",
    }

def _save_state(state: Dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))

# ─────────────────────────────────────────────
# Pipeline steps
# ─────────────────────────────────────────────

def collect_transcripts(max_videos: int = 1) -> Dict[str, Any]:
    """Run yt-dlp collector via subprocess (network-dependent, may be slow)."""
    env = os.environ.copy()
    env["COLLECTOR_MAX_VIDEOS"] = str(max_videos)
    try:
        result = subprocess.run(
            [sys.executable, str(BASE / "collector.py")],
            capture_output=True, text=True, cwd=str(BASE), env=env, timeout=300
        )
        success = result.returncode == 0
        stdout = result.stdout[-2000:]
        stderr = result.stderr[-1000:] if not success else ""
    except subprocess.TimeoutExpired:
        logger.warning("collect_transcripts timed out — continuing with existing transcripts")
        success = False
        stdout = "[timed out]"
        stderr = ""
    count = len([f for f in TRANSCRIPTS.glob("*.vtt")] + [f for f in TRANSCRIPTS.glob("*.srt")])
    return {"success": success, "transcript_count": count, "stdout": stdout, "stderr": stderr}


def summarize_transcripts() -> Dict[str, Any]:
    """Summarize transcripts inline (no subprocess)."""
    orig_dir = os.getcwd()
    try:
        os.chdir(str(BASE))
        sys.path.insert(0, str(BASE))
        import importlib.util
        spec = importlib.util.spec_from_file_location("summarize", BASE / "summarize.py")
        mod = importlib.util.module_from_spec(spec)
        # Capture stdout
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            spec.loader.exec_module(mod)
            mod.main()
        stdout = buf.getvalue()
    except Exception as e:
        stdout = f"[error: {e}]"
    finally:
        os.chdir(orig_dir)
    count = len(list(SUMMARIES.glob("*.summary")))
    return {"success": True, "summary_count": count, "stdout": stdout[-2000:]}


def extract_strategies() -> Dict[str, Any]:
    """Filter summaries into strategy candidates — runs inline, no subprocess."""
    STRATEGIES.mkdir(exist_ok=True)
    keywords = ["strategy", "indicator", "risk", "trade", "setup"]
    extracted = []
    for f in SUMMARIES.glob("*.summary"):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if any(kw in text.lower() for kw in keywords):
            out = STRATEGIES / f.name
            out.write_text(text, encoding="utf-8")
            extracted.append(f.name)
    count = len(list(STRATEGIES.glob("*.summary")))
    return {"success": True, "strategy_count": count, "stdout": f"Extracted {len(extracted)} strategies"}


def store_to_supabase() -> Dict[str, Any]:
    """Upsert strategies into Supabase research table (inline, no subprocess)."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        return {"success": False, "stdout": "", "stderr": "SUPABASE_URL/SUPABASE_KEY not set"}
    try:
        from supabase import create_client
        sb = create_client(supabase_url, supabase_key)
        records = []
        for f in STRATEGIES.glob("*.summary"):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                records.append({"source": "local", "title": f.stem, "content": content})
            except Exception:
                continue
        inserted = 0
        errors = 0
        for rec in records:
            try:
                sb.table("research").upsert(rec, on_conflict="title").execute()
                inserted += 1
            except Exception:
                errors += 1
        return {
            "success": errors == 0,
            "stdout": f"Upserted {inserted} records, {errors} errors",
            "stderr": "",
        }
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e)}


def publish_research_artifacts(limit: int = 25) -> Dict[str, Any]:
    """Publish summary-derived research artifacts into Supabase."""
    try:
        from research_intelligence.transcript_artifact_pipeline import publish
        result = publish(limit=limit)
        result["success"] = True
        return result
    except Exception as e:
        return {
            "success": False,
            "inserted": 0,
            "skipped": 0,
            "topics": {},
            "stderr": str(e),
        }


def generate_recommendation_packets(limit: int = 10) -> Dict[str, Any]:
    """Create Hermes-ready recommendation packets from current research outputs."""
    try:
        from research_intelligence.recommendation_packet_engine import run
        result = run(limit=limit)
        result["success"] = True
        return result
    except Exception as e:
        return {
            "success": False,
            "inserted": 0,
            "domains": [],
            "stderr": str(e),
        }

def get_latest_strategies(n: int = 5) -> List[Dict]:
    """Return the n most recent strategy files as dicts."""
    files = sorted(STRATEGIES.glob("*.summary"), key=lambda f: f.stat().st_mtime, reverse=True)
    results = []
    for f in files[:n]:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            results.append({
                "title": f.stem.replace(".en.vtt", ""),
                "content": content[:1500],
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
        except Exception:
            pass
    return results

# ─────────────────────────────────────────────
# Full pipeline
# ─────────────────────────────────────────────

def run_pipeline(collect: bool = True) -> Dict[str, Any]:
    state = _load_state()
    state["pipeline_status"] = "running"
    state["last_run"] = datetime.now().isoformat()
    _save_state(state)

    report = {"started": datetime.now().isoformat(), "steps": {}}
    try:
        if collect:
            logger.info("Step 1: Collecting transcripts...")
            r = collect_transcripts()
            report["steps"]["collect"] = r
            state["total_transcripts"] = r["transcript_count"]

        logger.info("Step 2: Summarizing transcripts...")
        r = summarize_transcripts()
        report["steps"]["summarize"] = r
        state["total_summaries"] = r["summary_count"]

        logger.info("Step 3: Extracting strategies...")
        r = extract_strategies()
        report["steps"]["extract"] = r
        state["total_strategies"] = r["strategy_count"]

        logger.info("Step 4: Storing to Supabase...")
        r = store_to_supabase()
        report["steps"]["store"] = r

        logger.info("Step 5: Publishing research artifacts...")
        r = publish_research_artifacts()
        report["steps"]["artifacts"] = r

        logger.info("Step 6: Generating recommendation packets...")
        r = generate_recommendation_packets()
        report["steps"]["recommendations"] = r

        state["pipeline_status"] = "idle"
        state["last_error"] = None
    except Exception as e:
        state["pipeline_status"] = "error"
        state["last_error"] = str(e)
        report["error"] = str(e)
        logger.error(f"Pipeline error: {e}")

    _save_state(state)
    report["finished"] = datetime.now().isoformat()
    return report

def get_status() -> Dict:
    state = _load_state()
    state["transcript_count"] = len(list(TRANSCRIPTS.glob("*.vtt"))) + len(list(TRANSCRIPTS.glob("*.srt")))
    state["summary_count"]    = len(list(SUMMARIES.glob("*.summary")))
    state["strategy_count"]   = len(list(STRATEGIES.glob("*.summary")))
    return state

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--no-collect", action="store_true")
    p.add_argument("--status", action="store_true")
    args = p.parse_args()
    if args.status:
        print(json.dumps(get_status(), indent=2))
    else:
        report = run_pipeline(collect=not args.no_collect)
        print(json.dumps(report, indent=2, default=str))
