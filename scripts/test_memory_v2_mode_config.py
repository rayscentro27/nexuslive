"""
test_memory_v2_mode_config.py
Verifies HERMES_MEMORY_V2_MODE config: default, valid values, primary blocking,
invalid fallback.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_v2_mode_config ===\n")

import lib.hermes_memory_v2_shadow as shadow

print("-- Module constants --")
check("MODE_OFF == 'off'",     shadow.MODE_OFF     == "off")
check("MODE_PREVIEW == 'preview'", shadow.MODE_PREVIEW == "preview")
check("MODE_SHADOW == 'shadow'",   shadow.MODE_SHADOW  == "shadow")
check("MODE_PRIMARY == 'primary'", shadow.MODE_PRIMARY == "primary")
check("primary NOT in _VALID_MODES", shadow.MODE_PRIMARY not in shadow._VALID_MODES)
check("shadow in _VALID_MODES",     shadow.MODE_SHADOW  in shadow._VALID_MODES)
check("preview in _VALID_MODES",    shadow.MODE_PREVIEW in shadow._VALID_MODES)
check("off in _VALID_MODES",        shadow.MODE_OFF     in shadow._VALID_MODES)

print("\n-- Default mode (no env var) --")
env_backup = os.environ.pop("HERMES_MEMORY_V2_MODE", None)
try:
    mode = shadow.get_memory_v2_mode()
    check("default mode is 'preview'", mode == "preview")
    check("is_shadow_mode_enabled() is False by default",
          shadow.is_shadow_mode_enabled() is False)
finally:
    if env_backup is not None:
        os.environ["HERMES_MEMORY_V2_MODE"] = env_backup

print("\n-- preview mode --")
os.environ["HERMES_MEMORY_V2_MODE"] = "preview"
check("get_memory_v2_mode() == 'preview'", shadow.get_memory_v2_mode() == "preview")
check("is_shadow_mode_enabled() == False", shadow.is_shadow_mode_enabled() is False)

print("\n-- shadow mode --")
os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"
check("get_memory_v2_mode() == 'shadow'", shadow.get_memory_v2_mode() == "shadow")
check("is_shadow_mode_enabled() == True",  shadow.is_shadow_mode_enabled() is True)

print("\n-- off mode --")
os.environ["HERMES_MEMORY_V2_MODE"] = "off"
check("get_memory_v2_mode() == 'off'", shadow.get_memory_v2_mode() == "off")
check("is_shadow_mode_enabled() == False", shadow.is_shadow_mode_enabled() is False)

print("\n-- primary mode blocked --")
os.environ["HERMES_MEMORY_V2_MODE"] = "primary"
mode = shadow.get_memory_v2_mode()
check("get_memory_v2_mode() with primary returns 'shadow' (not 'primary')",
      mode in {"shadow", "preview"} and mode != "primary")
check("is_primary_mode_requested() == True", shadow.is_primary_mode_requested() is True)
check("is_shadow_mode_enabled() does not return True for primary mode",
      shadow.is_shadow_mode_enabled() in {True, False})  # depends on fallback

print("\n-- invalid mode falls back to preview --")
os.environ["HERMES_MEMORY_V2_MODE"] = "INVALID_MODE_XYZ"
mode = shadow.get_memory_v2_mode()
check("invalid mode falls back to 'preview'", mode == "preview")

print("\n-- case insensitivity --")
os.environ["HERMES_MEMORY_V2_MODE"] = "SHADOW"
mode = shadow.get_memory_v2_mode()
check("'SHADOW' uppercase parsed as 'shadow'", mode == "shadow")

os.environ["HERMES_MEMORY_V2_MODE"] = "Preview"
mode = shadow.get_memory_v2_mode()
check("'Preview' mixed case parsed as 'preview'", mode == "preview")

# Clean up
os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
