# Client Portal Spec

## Overview
The Client Portal (`goclearonline.cc`) is the public interface for Nexus clients. It provides educational content, AI-powered strategy insights, performance dashboards, and a specialized "Client Portal Assistant" to answer curated questions.

## Architecture
The portal operates across a distributed environment for security and performance:
- **Frontend (Netlify)**: React-based user interface.
- **Backend API (Oracle VM)**: Handles authentication, tenant validation, and rate limiting.
- **Knowledge Service (Mac Mini)**: Resolves queries using the Nexus research brain via the `client_portal_assistant.js` logic.

## Client Portal Assistant
The assistant uses a "Knowledge-First" policy to provide safe, grounded answers:
1. **Intent Classification**: Categorizes queries into types like `grant_lookup`, `business_ideas`, `credit_guidance`, etc.
2. **Escalation Detection**: Identifies account-specific or sensitive queries (e.g., billing, disputes) and escalates them to human staff.
3. **Knowledge Lookup**: Queries approved Supabase tables (`research_briefs`, `grant_opportunities`, `business_opportunities`).
4. **Response Generation**: Returns a safe, curated summary without exposing raw research data.

## Security & Scoping
- **Hard-Blocked Tables**: Raw research data (`research_artifacts`, `research_claims`, etc.) and internal trading logs are never accessible to clients.
- **Tenant Isolation**: `tenant_id` validation ensures clients can only see data relevant to their own accounts.
- **Escalation Policy**: "Personal account" questions always bypass AI and go to human team members to ensure privacy and accuracy.

## Request Flow
1. Client submits a query on the portal.
2. Oracle VM validates the session and rate limits the request.
3. Mac Mini `resolvePortalQuery` processes the sanitized query.
4. If an answer is found in approved tables, a structured response is returned.
5. If no answer is found, the system prompts for human follow-up.

## Components
- `docs/CLIENT_PORTAL_ASSISTANT.md`: Detailed assistant logic and boundaries.
- `workflows/ai_workforce/client_portal_assistant/`: Local Mac Mini implementation.
- `nexus-oracle-api`: Windows/Oracle VM endpoint for the portal frontend.
