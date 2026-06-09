"""
Test a 1-unit EUR/USD demo order on the OANDA practice account.
Requires OANDA_DEMO_ENABLED=true (Ray approval).
"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[2]))

from integrations.oanda_demo import OandaDemoAdapter
from integrations.oanda_demo.oanda_demo_adapter import OandaSafetyError

def main():
    print("[oanda_order_test] Placing 1-unit EUR_USD BUY on practice account…")
    adapter = OandaDemoAdapter()
    try:
        result = adapter.place_demo_order(
            instrument="EUR_USD",
            side="buy",
            units=1,
            reason="integration_test",
        )
    except OandaSafetyError as e:
        print(f"[oanda_order_test] ⛔ Safety block: {e}")
        sys.exit(2)

    if result["ok"]:
        fill = result.get("order_fill", {})
        print(f"[oanda_order_test] ✅ Order placed | environment={result['environment']}")
        print(f"[oanda_order_test]    instrument: {result['instrument']}")
        print(f"[oanda_order_test]    units:      {result['units']}")
        print(f"[oanda_order_test]    fill price: {fill.get('price', 'N/A')}")
        print(f"[oanda_order_test]    placed_at:  {result['placed_at']}")
    else:
        print(f"[oanda_order_test] ❌ Order failed: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
