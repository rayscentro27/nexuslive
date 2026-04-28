# ── Hermes Ollama Backend — Kaggle Notebook ──────────────────────────────────
# Run all cells top to bottom. At the end you get a URL to paste into your
# Mac mini. Keep this tab open — closing it kills the session.

# ── Cell 1: Install Ollama ────────────────────────────────────────────────────
import subprocess, time, os

result = subprocess.run(
    "curl -fsSL https://ollama.com/install.sh | sh",
    shell=True, capture_output=True, text=True
)
print(result.stdout[-500:] if result.stdout else "")
print(result.stderr[-200:] if result.stderr else "")
print("✅ Ollama installed")

# ── Cell 2: Start Ollama server ───────────────────────────────────────────────
env = os.environ.copy()
env["OLLAMA_HOST"] = "0.0.0.0:11434"

server = subprocess.Popen(
    ["ollama", "serve"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    env=env
)
time.sleep(4)
print(f"✅ Ollama server running (PID {server.pid})")

# ── Cell 3: Pull model ────────────────────────────────────────────────────────
# qwen2.5:14b — fits in 16GB T4, excellent tool use for Hermes
print("Pulling qwen2.5:14b — this takes ~5 minutes on first run...")
subprocess.run(["ollama", "pull", "qwen2.5:14b"], check=True)
print("✅ Model ready")

# ── Cell 4: Verify model works ────────────────────────────────────────────────
import urllib.request, json

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=json.dumps({"model": "qwen2.5:14b", "prompt": "say pong", "stream": False}).encode(),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=30) as r:
    resp = json.loads(r.read())
print(f"✅ Model test: {resp.get('response','').strip()}")

# ── Cell 5: Open ngrok tunnel ─────────────────────────────────────────────────
subprocess.run(["pip", "install", "pyngrok", "-q"], check=True)
from pyngrok import ngrok, conf

conf.get_default().auth_token = "2cw7fIS2cGRpdM1RWEDAqSNu7Rv_7BRe2Gn7tXFpZwkFCDRw"
tunnel = ngrok.connect(11434, "http")
url = tunnel.public_url

print("\n" + "="*55)
print("  KAGGLE SESSION ACTIVE — keep this tab open!")
print("="*55)
print(f"\n  Ollama URL:  {url}")
print(f"\n  Run this on your Mac mini:")
print(f"\n  ~/nexus-ai/scripts/update_kaggle_url.sh {url}")
print("\n" + "="*55)
print("\nWhen done, run on Mac mini:")
print("  ~/nexus-ai/scripts/reset_hermes_openrouter.sh")
