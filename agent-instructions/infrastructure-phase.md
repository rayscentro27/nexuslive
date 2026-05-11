# Infrastructure Phase Instructions

## Operating Principle
Prefer additive systemization over rewrite risk.

## Guardrails
- Keep Telegram manual-only by default.
- Preserve existing operator command behavior.
- Do not alter funding/readiness equations without explicit sign-off.
- Favor module-level adapters and wrappers for new capabilities.

## Recommended Build Order
1. Spec-first changes in `/specs`.
2. Additive telemetry/routing helpers in `lib/`.
3. Lightweight validation scripts in `scripts/`.
4. Incremental integration behind flags.

## Rollback Strategy
- Keep new behavior behind env flags.
- Preserve old code paths while new paths prove stable.
