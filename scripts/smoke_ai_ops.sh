#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run_test() {
  local label="$1"
  local cmd="$2"
  printf "\n==================================================\n"
  printf "AI OPS SMOKE: %s\n" "$label"
  printf "==================================================\n"
  (cd "$ROOT_DIR" && eval "$cmd")
}

run_test "Infrastructure Foundation" "python3 scripts/test_infra_foundation.py"
run_test "Hermes Model Router" "python3 scripts/test_hermes_model_router.py"
run_test "Hermes Router Circuit Breaker" "python3 scripts/test_hermes_router_circuit_breaker.py"
run_test "Hermes Telegram Pipeline" "python3 scripts/test_hermes_telegram_pipeline.py"
run_test "Telegram Policy Guard" "python3 scripts/test_telegram_policy.py"
run_test "Telegram JS Bypass Guard" "python3 scripts/test_telegram_js_bypass.py"
run_test "Swarm Coordinator" "python3 scripts/test_swarm_coordinator.py"
run_test "AI Ops Control Center" "python3 scripts/test_ai_ops_control_center.py"
run_test "Hermes Knowledge Brain" "python3 scripts/test_hermes_knowledge_brain.py"
run_test "AI Employee Registry" "python3 scripts/test_ai_employee_registry.py"
run_test "Swarm Approval Queue" "python3 scripts/test_swarm_approval_queue.py"
run_test "Controlled Agents" "python3 scripts/test_controlled_agents.py"
run_test "Agent Collaboration" "python3 scripts/test_agent_collaboration.py"
run_test "Executive Reports" "python3 scripts/test_executive_reports.py"
run_test "AI Ops Scorecard" "python3 scripts/test_ai_ops_scorecard.py"
run_test "Email Reports" "python3 scripts/test_email_reports.py"
run_test "Hermes Dev Agent Bridge" "python3 scripts/test_hermes_dev_agent_bridge.py"

printf "\n✅ AI Ops smoke suite passed.\n"
