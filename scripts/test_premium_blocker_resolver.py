"""Test PremiumBlockerResolver — verify artifacts and recommendations for beehiiv."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from lib.premium_blocker_resolver import PremiumBlockerResolver

def main():
    resolver = PremiumBlockerResolver()

    print("[test_blocker] Known blockers:", resolver.all_known_blockers())

    for tool in ["beehiiv", "openai", "unknown_tool_xyz"]:
        print(f"\n[test_blocker] Resolving: {tool}")
        packet = resolver.resolve(tool, context="unit_test")
        report_path = Path(packet.get("report_path", ""))

        if tool == "unknown_tool_xyz":
            assert packet["top_recommendation"] is None, f"Expected None for unknown tool, got {packet['top_recommendation']}"
            print(f"  ✅ Unknown tool → no recommendation (correct)")
        else:
            assert packet["top_recommendation"] is not None, f"No recommendation for {tool}"
            assert report_path.exists(), f"Report not saved: {report_path}"
            print(f"  ✅ Top pick: {packet['top_recommendation']['name']}")
            print(f"  ✅ Report: {report_path.name}")

    print("\n✅ All blocker resolver tests passed.")

if __name__ == "__main__":
    main()
