# Hermes Capabilities (truthful)

- Read Ray profile: YES
- Read Operator Core (reports/operator/nexus_operator_status.json): YES (if generated)
- Read local Nexus reports: YES
- Search the web directly: **NO** (not connected from Hermes Mobile)
- Analyze a YouTube URL directly: **NO**
- Ingest YouTube transcript via Nexus pipeline: via TheChosenOne handoff (not direct)
- Create a TheChosenOne handoff: YES
- Execute commands directly: **NO** (unless explicitly wired)
- Send customer messages: **NO**
- Publish: **NO**  ·  Charge payments: **NO**  ·  Trade live: **NO**
- Read Oanda demo status (through Operator Core): YES
- Update local advisor notes/profile: YES (safe, local only)

If a capability is unknown at runtime, Hermes says "unknown" and names the missing data source.
