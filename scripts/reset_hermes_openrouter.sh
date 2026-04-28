#!/bin/bash
# Resets Hermes back to OpenRouter when Kaggle session ends

CONFIG="$HOME/.hermes/config.yaml"

echo "Resetting Hermes to OpenRouter..."

~/.hermes/hermes-agent/venv/bin/python3 - <<EOF
import yaml

with open('$CONFIG', 'r') as f:
    config = yaml.safe_load(f)

config['model']['default'] = 'meta-llama/llama-3.3-70b-instruct'
config['model']['base_url'] = 'https://openrouter.ai/api/v1'
config['model']['api_key'] = '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'
config['model']['context_length'] = 65536
config['fallback_providers'][0]['api_key'] = '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'
config['fallback_providers'][0]['model'] = 'meta-llama/llama-3.1-8b-instruct'
config['fallback_providers'][0]['name'] = 'openrouter-llama-8b'

with open('$CONFIG', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

print("Config reset.")
EOF

launchctl unload ~/Library/LaunchAgents/ai.hermes.gateway.plist
sleep 1
launchctl load ~/Library/LaunchAgents/ai.hermes.gateway.plist

echo "Done — Hermes is back on OpenRouter"
