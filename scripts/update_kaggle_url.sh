#!/bin/bash
# Usage: ./update_kaggle_url.sh https://xxxx.ngrok-free.app
# Updates Hermes to use Kaggle Ollama as primary backend

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <ngrok-url>"
  echo "Example: $0 https://abc123.ngrok-free.app"
  exit 1
fi

NGROK_URL="${1%/}"  # strip trailing slash
CONFIG="$HOME/.hermes/config.yaml"

echo "Updating Hermes to use Kaggle Ollama at $NGROK_URL..."

~/.hermes/hermes-agent/venv/bin/python3 - <<EOF
import yaml

with open('$CONFIG', 'r') as f:
    config = yaml.safe_load(f)

config['model']['default'] = 'qwen2.5:14b'
config['model']['base_url'] = '$NGROK_URL/v1'
config['model']['api_key'] = 'ollama'
config['model']['context_length'] = 32768

with open('$CONFIG', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

print("Config updated.")
EOF

launchctl unload ~/Library/LaunchAgents/ai.hermes.gateway.plist
sleep 1
launchctl load ~/Library/LaunchAgents/ai.hermes.gateway.plist

echo "Done — Hermes is now using Kaggle Ollama (qwen2.5:14b)"
echo "When your Kaggle session ends, run this to switch back to OpenRouter:"
echo "  $HOME/nexus-ai/scripts/reset_hermes_openrouter.sh"
