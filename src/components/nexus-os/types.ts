// Nexus OS shared types

export interface ApprovalItem {
  id: string;
  action_type: string;
  description: string;
  payload?: Record<string, unknown> | null;
  requested_by: string;
  priority: 'urgent' | 'normal' | 'low';
  status: 'pending' | 'approved' | 'rejected' | 'needs_edits';
  review_notes?: string | null;
  expires_at?: string | null;
  created_at: string;
  reviewed_at?: string | null;
}

export interface SystemAlert {
  id: string;
  event_source: string;
  event_type: string;
  classification: 'critical_alert' | 'actionable' | 'informational' | 'suppress';
  aggregated_summary?: string | null;
  created_at: string;
}

export interface Lead {
  id: string;
  name?: string | null;
  business_name?: string | null;
  status: string;
  lead_score: number;
  estimated_value?: number | null;
  created_at: string;
}

export interface RevenueEvent {
  id: string;
  event_type: string;
  amount: number;
  currency: string;
  created_at: string;
}

export interface KnowledgeItem {
  id: string;
  source_title: string;
  source_type: string;
  category: string;
  summary: string;
  key_takeaways: string[];
  confidence_score?: number | null;
  approved_for_user_display: boolean;
  created_at: string;
}

export interface PaperTrade {
  id: string;
  strategy_id: string;
  market: string;
  direction: 'long' | 'short' | 'neutral';
  entry_date: string;
  entry_price: number;
  stop_loss: number;
  exit_price?: number | null;
  paper_pnl_usd?: number | null;
  result_r?: number | null;
  status: string;
  thesis?: string | null;
  lesson?: string | null;
  created_at: string;
}

export interface ToolRegistryEntry {
  id: string;
  name: string;
  type: 'ai_model' | 'platform' | 'integration' | 'service' | 'agent';
  status: 'online' | 'offline' | 'limited' | 'unknown';
  best_use: string;
  cost_level: 'free' | 'low' | 'medium' | 'high';
  auth_method: string;
  allowed_actions: string[];
  approval_required: boolean;
  log_path?: string;
  notes?: string;
  last_success?: string | null;
  last_failure?: string | null;
}

export interface HermesMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  confidence?: number;
  sources?: string[];
  recommended_action?: string;
  approval_needed?: boolean;
}

// Revenue Hub campaign (maps to nexus_os_revenue_campaigns + migration 000003 columns)
export interface RevenueCampaign {
  id: string;
  program_name: string;
  niche: string;
  campaign_type: 'affiliate' | 'direct' | 'partnership' | 'content' | 'referral_program';
  application_status: 'not_applied' | 'applied' | 'pending' | 'approved' | 'rejected' | 'paused';
  link_status: 'none' | 'pending' | 'active' | 'expired';
  affiliate_link?: string | null;      // stored in DB; never rendered in DOM
  landing_page_status: 'none' | 'draft' | 'review' | 'ready';
  landing_page_url?: string | null;
  compliance_ok: boolean;
  disclosure_ok: boolean;
  traffic_source?: string | null;
  content_queue_count: number;
  clicks?: number | null;
  conversions?: number | null;
  revenue_usd?: number | null;
  next_action?: string | null;
  notes?: string | null;
  offer_url?: string | null;
  priority: 'high' | 'medium' | 'low';
  estimated_value?: number | null;
  approval_status: 'not_required' | 'pending_review' | 'approved' | 'blocked';
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export type CampaignFormData = Omit<RevenueCampaign, 'id' | 'created_at' | 'updated_at'>;

// Rules-based recommendation from the Next Best Revenue Action engine
export interface RevenueRecommendation {
  campaign_id: string;
  campaign_name: string;
  score: number;          // 0-100
  next_action: string;
  why: string;
  blockers: string[];
  approval_needed: boolean;
  approval_action?: string;
  confidence: 'high' | 'medium' | 'low';
  source: 'rules_engine';
  freshness: string;      // ISO timestamp
}

// ── Content Studio types ────────────────────────────────────────────────────

export interface PlatformVariation {
  platform: string;
  draft_text: string;
  caption: string;
  hashtags: string[];
  cta: string;
  disclosure_note: string;
  status: 'empty' | 'draft' | 'ready' | 'approved';
  approval_required: boolean;
}

export interface ContentItem {
  id: string;
  title: string;
  type: string;                      // legacy column, kept for DB compat
  content_type: string;              // primary type used in UI
  status: 'idea' | 'draft' | 'needs_review' | 'approval_requested' | 'approved' | 'scheduled' | 'published' | 'archived';
  source_id?: string | null;
  source_artifact_id?: string | null;
  source_description?: string | null;
  source_type?: string | null;
  source_url?: string | null;
  related_campaign_id?: string | null;
  content_body?: string | null;
  global_draft?: string | null;
  platform_variations: PlatformVariation[];
  platform_targets: string[];
  compliance_note?: string | null;
  compliance_status: 'not_reviewed' | 'in_review' | 'approved' | 'blocked';
  disclosure_required: boolean;
  disclosure_added: boolean;
  no_earnings_claims: boolean;
  no_guarantees: boolean;
  approval_status: 'not_required' | 'pending_review' | 'approved' | 'blocked';
  approval_id?: string | null;
  priority: 'high' | 'medium' | 'low';
  next_action?: string | null;
  notes?: string | null;
  archived: boolean;
  scheduled_at?: string | null;
  published_at?: string | null;
  analytics_url?: string | null;
  lesson_stored: boolean;
  created_by_agent?: string | null;
  views?: number | null;
  clicks?: number | null;
  conversions?: number | null;
  revenue_attributed?: number | null;
  performance_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export type ContentItemFormData = Omit<ContentItem, 'id' | 'created_at' | 'updated_at'>;

export interface ContentSource {
  id: string;
  title: string;
  type: string;
  status: string;
  content_url?: string | null;
  summary?: string | null;
  ideas: string[];
  tags: string[];
  created_at: string;
}

export interface ContentRecommendation {
  item_id: string;
  item_title: string;
  score: number;
  next_action: string;
  why: string;
  blockers: string[];
  approval_needed: boolean;
  approval_action?: string;
  confidence: 'high' | 'medium' | 'low';
  source: 'rules_engine';
  freshness: string;
}

// ── Knowledge Graph types ────────────────────────────────────────────────────

export type GraphEntityType =
  | 'source' | 'artifact' | 'revenue_campaign' | 'content_item' | 'approval'
  | 'notification' | 'decision' | 'lesson' | 'tool' | 'provider'
  | 'trading_strategy' | 'transcript' | 'repo_reference'
  // legacy values still valid
  | 'task' | 'agent' | 'workflow' | 'skill' | 'rule' | 'client' | 'campaign'
  | 'blocker' | 'failure' | 'metric' | 'output' | 'prompt' | 'sop';

export type GraphRelationshipType =
  | 'derived_from' | 'supports' | 'blocks' | 'related_to' | 'created_content_for'
  | 'requires_approval' | 'approved_by' | 'resulted_in' | 'learned_from'
  | 'references' | 'belongs_to_campaign' | 'generated_from_source'
  | 'recommended_by_hermes'
  // legacy values still valid
  | 'produced_by' | 'belongs_to' | 'depends_on' | 'blocked_by' | 'tested_by'
  | 'improves' | 'replaces' | 'contradicts' | 'deployed_to';

export interface GraphEntity {
  id: string;
  type: GraphEntityType;
  name: string;
  title?: string | null;
  description?: string | null;
  summary?: string | null;
  source_table?: string | null;
  source_id?: string | null;
  status?: string | null;
  confidence?: number | null;
  archived: boolean;
  metadata: Record<string, unknown>;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface GraphRelationship {
  id: string;
  from_entity_id: string;
  to_entity_id: string;
  relationship: GraphRelationshipType;
  weight?: number | null;
  evidence_summary?: string | null;
  source_table?: string | null;
  source_id?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface GraphSyncResult {
  table: string;
  created: number;
  skipped: number;
  relationships_created: number;
}

export type OsSection =
  | 'overview'
  | 'command-center'
  | 'hermes-chat'
  | 'hermes-training'
  | 'approvals'
  | 'notifications'
  | 'tools'
  | 'revenue'
  | 'content'
  | 'trading'
  | 'knowledge'
  | 'graph';
