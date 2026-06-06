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

export type OsSection =
  | 'command-center'
  | 'hermes-chat'
  | 'approvals'
  | 'notifications'
  | 'tools'
  | 'revenue'
  | 'content'
  | 'trading'
  | 'knowledge';
