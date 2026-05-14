# NEXUS MASTER ACTIVE PROCESS MAP

Generated: 2026-05-14

| name | host | launch source | purpose | Telegram | Email | Supabase | active | should remain | action |
|---|---|---|---|---|---|---|---|---|---|
| telegram_bot.py --monitor | mac mini | launchd (`com.raymonddavis.nexus.telegram`) | Hermes conversational bot | yes | no | yes | yes | yes | kept |
| operations_center/scheduler.py | mac mini | launchd (`com.raymonddavis.nexus.scheduler`) | periodic ops tasks | indirect | yes | yes | yes | yes | kept/hardened |
| control_center_server.py | mac mini | launchd (`ai.nexus.control-center`) | admin API/control plane | possible | yes | yes | yes | yes | kept |
| hermes gateway | mac mini | launchd (`ai.hermes.gateway`) | Hermes gateway transport | no direct | no | no | yes | yes | kept |
| nexus-orchestrator (node) | mac mini | launchd | workflow orchestration | possible | no | yes | yes | yes | kept |
| nexus-research-worker (node) | mac mini | launchd | research pipeline worker | possible | no | yes | yes | yes | kept |
| opportunity worker | mac mini | launchd plist | auto opportunity summaries | yes | no | yes | no (removed) | no | removed |
| grant worker | mac mini | launchd plist | auto grant summaries | yes | no | yes | no (removed) | no | removed |
| research orchestrator transcript/grants | mac mini | launchd plist | auto brief runs | yes | no | yes | no (removed) | no | removed |
| ollama serve | mac mini | launchd | local model endpoint | no | no | no | yes | yes | kept |
