"""
test_cfo_doctrine_loader.py
Phase 7B: CFO Doctrine Loader.
Verifies that hermes_cfo_doctrine.py loads all doctrine files
and returns the correct summaries.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

passes = 0
failures = 0

def check(label, cond):
    global passes, failures
    status = "PASS" if cond else "FAIL"
    if not cond:
        failures += 1
    else:
        passes += 1
    print(f"  [{status}] {label}")
    return cond


from lib.hermes_cfo_doctrine import (
    load_cfo_doctrine, get_cfo_behavior_rules, get_plain_language_rules,
    get_unknown_answer_rules, get_prompt_generation_rules, doctrine_files_exist,
)

print("\nCFO Doctrine Loader Tests")
print("=" * 50)

print("\n-- doctrine_files_exist --")
exists_map = doctrine_files_exist()
check("returns dict", isinstance(exists_map, dict))
check("has cfo_conversation key", "cfo_conversation" in exists_map)
check("has plain_language key", "plain_language" in exists_map)
check("has unknown_answer key", "unknown_answer" in exists_map)
check("has scout_dispatch key", "scout_dispatch" in exists_map)
check("has prompt_generation key", "prompt_generation" in exists_map)
check("has failure_learning key", "failure_learning" in exists_map)

print("\n-- load_cfo_doctrine --")
doctrine = load_cfo_doctrine()
check("returns dict", isinstance(doctrine, dict))
check("has content", len(doctrine) > 0)
for key in ["cfo_conversation", "plain_language", "unknown_answer",
            "scout_dispatch", "prompt_generation", "failure_learning"]:
    check(f"doctrine[{key!r}] is a string", isinstance(doctrine.get(key, None), str))

print("\n-- get_cfo_behavior_rules --")
rules = get_cfo_behavior_rules()
check("returns string", isinstance(rules, str))
check("has plain language rule", "plain language" in rules.lower())
check("has safety rule", "approval" in rules.lower() or "ray approval" in rules.lower())
check("has scout dispatch rule", "scout" in rules.lower() or "dispatch" in rules.lower())

print("\n-- get_plain_language_rules --")
pl_rules = get_plain_language_rules()
check("returns string", isinstance(pl_rules, str))
check("has answer first rule", "answer" in pl_rules.lower())
check("has bullet limit rule", "bullet" in pl_rules.lower() or "5" in pl_rules)

print("\n-- get_unknown_answer_rules --")
ua_rules = get_unknown_answer_rules()
check("returns string", isinstance(ua_rules, str))
check("has dispatch rule", "dispatch" in ua_rules.lower() or "scout" in ua_rules.lower())

print("\n-- get_prompt_generation_rules --")
pg_rules = get_prompt_generation_rules()
check("returns string", isinstance(pg_rules, str))
check("has implementation prompt rule", "implementation" in pg_rules.lower() or "prompt" in pg_rules.lower())

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
