"""Test OANDA practice account connectivity (no order placed)."""
import sys, os
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[2]))

from integrations.oanda_demo import OandaDemoAdapter

def main():
    print("[oanda_test] Checking practice account connection…")
    adapter = OandaDemoAdapter()
    status = adapter.connection_status()
    if status["ok"]:
        print(f"[oanda_test] ✅ Connected | environment={status['environment']}")
        print(f"[oanda_test]    account_id: {status.get('account_id')}")
        print(f"[oanda_test]    currency:   {status.get('currency')}")
        print(f"[oanda_test]    balance:    {status.get('balance')}")
        print(f"[oanda_test]    NAV:        {status.get('nav')}")
    else:
        print(f"[oanda_test] ❌ Connection failed: {status['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
