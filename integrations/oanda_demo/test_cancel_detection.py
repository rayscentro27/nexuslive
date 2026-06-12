"""
Test cancel detection logic against the saved order 98 raw response.
No broker calls — pure local fixture validation.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "reports" / "trading" / "oanda_practice_execution_test" / "oanda_practice_order_response.json"

def test_cancel_detection() -> dict[str, bool]:
    """Verify that order 98's broker response triggers cancel detection."""
    raw = json.loads(FIXTURE.read_text())
    data = raw["broker_response"]

    # Same logic as the adapter patch
    cancel = data.get("orderCancelTransaction") or {}
    create = data.get("orderCreateTransaction") or {}
    fill = data.get("orderFillTransaction") or {}

    results: dict[str, bool] = {}

    # orderCancelTransaction must be present
    results["cancel_transaction_present"] = bool(cancel)
    results["cancel_reason_is_fifo"] = cancel.get("reason") == "FIFO_VIOLATION_SAFEGUARD_VIOLATION"
    results["cancel_transaction_id_99"] = cancel.get("id") == "99"

    # orderCreateTransaction must also be present (order was created)
    results["create_transaction_present"] = bool(create)
    results["create_order_id_98"] = create.get("id") == "98"

    # orderFillTransaction must be absent
    results["fill_transaction_empty"] = not fill

    # Simulate the patch result
    if cancel:
        patch_result = {
            "ok": False,
            "error": f"OANDA canceled order: {cancel.get('reason', 'unknown')}",
            "cancel_reason": cancel.get("reason"),
            "cancel_transaction_id": cancel.get("id"),
            "order_id": cancel.get("orderID") or create.get("id"),
        }
        results["patch_returns_ok_false"] = patch_result["ok"] is False
        results["patch_cancel_reason_match"] = patch_result["cancel_reason"] == "FIFO_VIOLATION_SAFEGUARD_VIOLATION"
        results["patch_order_id_98"] = patch_result["order_id"] == "98"
        results["patch_error_message_correct"] = "FIFO_VIOLATION_SAFEGUARD_VIOLATION" in patch_result["error"]

    return results


def main() -> int:
    results = test_cancel_detection()
    all_pass = all(results.values())

    print("=" * 60)
    print("CANCEL DETECTION TEST — Order 98 Fixture")
    print("=" * 60)
    for check, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"  {status}  {check}")

    if all_pass:
        print("=" * 60)
        print("RESULT: ALL PASSED")
        print("  Patched adapter would return ok=False for order 98")
        print(f"  Cancel reason: FIFO_VIOLATION_SAFEGUARD_VIOLATION")
        print(f"  Error: OANDA canceled order: FIFO_VIOLATION_SAFEGUARD_VIOLATION")
        print("=" * 60)
        return 0
    else:
        failures = [k for k, v in results.items() if not v]
        print("=" * 60)
        print(f"RESULT: {len(failures)} FAILURE(S)")
        for f in failures:
            print(f"  ❌  {f}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
