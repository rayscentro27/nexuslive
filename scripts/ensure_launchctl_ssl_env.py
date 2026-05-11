#!/usr/bin/env python3
"""Ensure launchctl SSL CA bundle vars are set to certifi bundle."""

from __future__ import annotations

import subprocess
import sys

import certifi


def launchctl_getenv(key: str) -> str:
    result = subprocess.run(["launchctl", "getenv", key], capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def launchctl_setenv(key: str, value: str) -> bool:
    result = subprocess.run(["launchctl", "setenv", key, value], capture_output=True, text=True)
    return result.returncode == 0


def main() -> int:
    target = certifi.where()
    keys = ["SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"]

    ok = True
    print(f"target_cert_bundle={target}")

    for key in keys:
        current = launchctl_getenv(key)
        if current != target:
            if not launchctl_setenv(key, target):
                ok = False
                print(f"{key}=update_failed")
                continue
            current = launchctl_getenv(key)
        print(f"{key}={'set' if current else 'unset'}")
        if current:
            print(f"{key}_value={current}")
        if current != target:
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
