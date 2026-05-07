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
run_test "AI Ops Control Center" "python3 scripts/test_ai_ops_control_center.py"
run_test "AI Employee Registry" "python3 scripts/test_ai_employee_registry.py"

printf "\n✅ AI Ops smoke suite passed.\n"
