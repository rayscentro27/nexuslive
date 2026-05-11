# Supabase Brain Spec

## Overview
The "Supabase Brain" is the centralized knowledge and coordination layer for the Nexus platform. It stores long-term memory, research data, trading logs, and agent coordination state.

## Primary Databases
Nexus uses Supabase as its primary backend, leveraging its PostgreSQL features for both structured data and semantic search (vector memory).

## Key Table Groups

### 1. Research & Strategy
- `research`: General trading knowledge and market intelligence.
- `research_briefs`: Curated summaries for client consumption.
- `strategies`: Extracted trading strategies and indicators.
- `youtube_channels`: Sources for research ingestion.
- `research_artifacts`: Raw ingestion data (internal use only).

### 2. Coordination & Activity
- `coord_tasks`: Pending and completed tasks assigned to specific agents (Claude, Codex, Hermes).
- `coord_activity`: Audit log of agent actions and file modifications.
- `coord_context`: Shared key-value store for cross-agent context synchronization.

### 3. Trading & Risk
- `trade_logs`: History of executed trades and outcomes.
- `reviewed_signal_proposals`: Log of signals that have undergone review.
- `risk_decisions`: Internal audit of risk management actions.

### 4. Control Plane
- `worker_control_plane`: Desired state and schedules for autonomous workers.
- `worker_control_actions`: Log of control commands issued via Hermes or the dashboard.

## Knowledge Accumulation Pipeline
1. **Ingestion**: `research-engine` pulls data from sources (YouTube, web).
2. **Processing**: AI agents summarize and extract strategies.
3. **Storage**: Data is stored in Supabase with vector embeddings for semantic retrieval.
4. **Retrieval**: Agents query Supabase before hitting the LLM to minimize costs and ensure grounding in the local knowledge base.

## Access Policy
- **Internal**: All tables accessible by OpenClaw agents and Mac Mini services.
- **Client-Facing**: Restricted access via Oracle VM to approved tables only (`research_briefs`, `grant_opportunities`, `business_opportunities`).
- **Security**: Service-role keys are required for core operations; PII is redacted at the boundary.

## Migration & Setup
- `docs/supabase_migration.sql`: Main migration script for system tables.
- `docs/SUPABASE_SETUP.sql`: Initial schema setup.
- `supabase/migrations/`: Ongoing versioned migrations.
