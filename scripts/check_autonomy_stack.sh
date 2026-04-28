#!/usr/bin/env bash
# =============================================================================
# Nexus Autonomy Stack Check
# Verifies the current non-Telegram autonomy path:
# - OpenRouter completion
# - Gmail IMAP auth
# - email pipeline launch agent
# - scheduler launch agent
# =============================================================================

set -u

ROOT="/Users/raymonddavis/nexus-ai"
HERMES_CONFIG="$HOME/.hermes/config.yaml"
EMAIL_PLIST="$HOME/Library/LaunchAgents/ai.nexus.email-pipeline.plist"
SCHEDULER_LABEL="com.raymonddavis.nexus.scheduler"
EMAIL_LABEL="ai.nexus.email-pipeline"

section() {
  echo
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

status_line() {
  printf "  %-18s %s\n" "$1" "$2"
}

section "Nexus Autonomy Stack — $(date)"

section "OpenRouter"
read -r OR_MODEL OR_BASE_URL OR_API_KEY < <(
  python3 - <<'PY'
from pathlib import Path

config_path = Path.home() / ".hermes" / "config.yaml"
api_key = ""
model = ""
base_url = ""
in_model = False
for line in config_path.read_text(errors="ignore").splitlines():
    if not in_model:
        if line.startswith("model:"):
            in_model = True
        continue
    if line and not line.startswith(" "):
        break
    stripped = line.strip()
    if stripped.startswith("api_key:"):
        api_key = stripped.split(":", 1)[1].strip()
    elif stripped.startswith("base_url:"):
        base_url = stripped.split(":", 1)[1].strip()
    elif stripped.startswith("default:"):
        model = stripped.split(":", 1)[1].strip()
print(model, base_url, api_key)
PY
)

if [[ -z "${OR_MODEL:-}" || -z "${OR_BASE_URL:-}" || -z "${OR_API_KEY:-}" ]]; then
  echo "  FAIL              could not parse model config"
else
  OR_RESPONSE=$(curl -sS --max-time 20 "${OR_BASE_URL%/}/chat/completions" \
    -H "Authorization: Bearer ${OR_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${OR_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: pong\"}],\"max_tokens\":16}" 2>&1)
  if printf '%s' "$OR_RESPONSE" | rg -q '"content":"pong"'; then
    echo "  PASS              model=${OR_MODEL}"
    OR_RESPONSE_JSON="$OR_RESPONSE" python3 - <<'PY'
import json
import os

data = json.loads(os.environ["OR_RESPONSE_JSON"])
usage = data.get("usage", {})
content = data["choices"][0]["message"]["content"].strip()
print(f"  Response          {content}")
print(f"  Usage             total_tokens={usage.get('total_tokens', '?')} cost={usage.get('cost', '?')}")
PY
  else
    echo "  FAIL              ${OR_RESPONSE}"
  fi
fi

section "Gmail Auth"
python3 - <<'PY'
import imaplib
import subprocess
import sys

try:
    raw = subprocess.check_output(["plutil", "-p", str((__import__("pathlib").Path.home() / "Library/LaunchAgents/ai.nexus.email-pipeline.plist"))], text=True)
except Exception as e:
    print(f"  FAIL              could not read email plist: {e}")
    sys.exit(0)

email = None
password = None
for line in raw.splitlines():
    line = line.strip()
    if '"NEXUS_EMAIL" =>' in line:
        email = line.split("=>", 1)[1].strip().strip('"')
    elif '"NEXUS_EMAIL_PASSWORD" =>' in line:
        password = line.split("=>", 1)[1].strip().strip('"')

if not email or not password:
    print("  FAIL              email credentials not present in plist")
    sys.exit(0)

try:
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(email, password)
    imap.logout()
    print(f"  PASS              {email}")
except Exception as e:
    print(f"  FAIL              {e}")
PY

section "Launch Agents"
check_launchd() {
  local label="$1"
  local pretty="$2"
  local raw
  if ! raw=$(launchctl print "gui/$(id -u)/$label" 2>/dev/null); then
    status_line "$pretty" "not loaded"
    return
  fi
  local state
  local exit_code
  state=$(printf '%s\n' "$raw" | awk -F'= ' '/state =/ {print $2; exit}')
  exit_code=$(printf '%s\n' "$raw" | awk -F'= ' '/last exit code =/ {print $2; exit}')
  status_line "$pretty" "state=${state:-unknown} last_exit=${exit_code:-unknown}"
}

check_launchd "$EMAIL_LABEL" "Email pipeline"
check_launchd "$SCHEDULER_LABEL" "Scheduler"
check_launchd "ai.hermes.gateway" "Hermes gateway"

section "Recent Signals"
if [[ -f "$ROOT/logs/scheduler.err.log" ]]; then
  tail -n 8 "$ROOT/logs/scheduler.err.log" | sed 's/^/  /'
else
  echo "  missing scheduler log"
fi

section "Summary"
echo "  This check reflects the current non-Telegram control path:"
echo "  OpenRouter + Gmail + launchd workers."
