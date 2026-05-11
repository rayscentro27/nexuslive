# Canonical Replay History

Builds a read-only report that picks one canonical replay path per proposal and
lists the duplicate `paper_trade_runs` / `replay_results` rows that should be
ignored by downstream analytics.

Script:

- `scripts/canonical_replay_history.py`

Usage:

```bash
python3 scripts/canonical_replay_history.py --format brief
python3 scripts/canonical_replay_history.py --format json
```

Output:

- writes `logs/canonical_replay_history.json`
- reports:
  - canonical run per proposal
  - canonical replay result per proposal
  - duplicate run rows
  - duplicate replay result rows

Notes:

- This script is read-only.
- It does not delete or mutate historical rows.
- It complements `scripts/strategy_paper_bridge.py`, which now also ignores duplicate replay rows in live scoring.
