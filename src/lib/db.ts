/**
 * Nexus Data Layer
 * All Supabase queries go through here — typed, consistent, easy to find.
 */

import { supabase } from './supabase';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface UserProfile {
  id: string;
  full_name: string | null;
  avatar_url: string | null;
  role: 'client' | 'admin' | 'super_admin';
  readiness_score: number;
  business_potential: string | null;
  current_funding_level: number;
  next_milestone: string | null;
  subscription_plan: 'free' | 'pro' | 'elite';
  onboarding_complete: boolean;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  category: string;
  status: 'pending' | 'in_progress' | 'complete';
  priority: number;
  readiness_impact: number;
  is_primary: boolean;
  duration_minutes: number | null;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface BotProfile {
  id: string;
  agent_key: string;
  name: string;
  role: string;
  division: string | null;
  description: string | null;
  status: 'active' | 'idle' | 'offline';
  efficiency: number | null;
  avatar_style: string;
  sort_order: number;
}

export interface ActivityItem {
  id: string;
  user_id: string;
  actor: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface FundingStage {
  id: string;
  user_id: string;
  stage_number: number;
  title: string;
  description: string | null;
  status: 'completed' | 'current' | 'locked';
  funding_range_min: number | null;
  funding_range_max: number | null;
  readiness_required: number;
  projected_approvals: number | null;
  timeline_weeks: number | null;
}

export interface FundingAction {
  id: string;
  stage_id: string;
  user_id: string;
  title: string;
  description: string | null;
  status: 'pending' | 'in_progress' | 'complete';
  readiness_impact: number;
  sort_order: number;
}

export interface FundingApplication {
  id: string;
  user_id: string;
  lender_name: string | null;
  product_type: string | null;
  requested_amount: number | null;
  approved_amount: number | null;
  interest_rate: number | null;
  approval_odds: number | null;
  status: string;
  notes: string | null;
  applied_at: string | null;
  created_at: string;
}

export interface ChatConversation {
  id: string;
  user_id: string;
  contact_id: string;
  contact_name: string;
  contact_role: string | null;
  contact_type: 'ai' | 'human' | 'system';
  last_message_at: string;
  unread_count: number;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  is_user_message: boolean;
  read_at: string | null;
  created_at: string;
}

export interface Document {
  id: string;
  user_id: string;
  filename: string;
  file_url: string;
  file_size: number | null;
  mime_type: string | null;
  category: string;
  document_type: string | null;
  status: 'pending' | 'verified' | 'attention';
  uploaded_by: 'client' | 'admin';
  notes: string | null;
  created_at: string;
}

export interface CreditReport {
  id: string;
  user_id: string;
  score: number | null;
  score_band: string | null;
  funding_range_min: number | null;
  funding_range_max: number | null;
  utilization_percent: number | null;
  total_debt: number | null;
  report_file_url: string | null;
  report_date: string | null;
  is_current: boolean;
  created_at: string;
}

export interface BusinessEntity {
  id: string;
  user_id: string;
  business_name: string | null;
  entity_type: string | null;
  ein: string | null;
  duns_number: string | null;
  formation_state: string | null;
  formation_date: string | null;
  naics_code: string | null;
  secretary_of_state_status: string;
  duns_report_status: string;
  tradelines_status: string;
  status: string;
}

// ─── User Profile ─────────────────────────────────────────────────────────────

export async function getProfile(userId: string) {
  const { data, error } = await supabase
    .from('user_profiles')
    .select('*')
    .eq('id', userId)
    .single();
  return { data: data as UserProfile | null, error };
}

export async function updateProfile(userId: string, updates: Partial<UserProfile>) {
  const { data, error } = await supabase
    .from('user_profiles')
    .update({ ...updates, updated_at: new Date().toISOString() })
    .eq('id', userId)
    .select()
    .single();
  return { data: data as UserProfile | null, error };
}

// ─── Tasks ─────────────────────────────────────────────────────────────────────

export async function getTasks(userId: string) {
  const { data, error } = await supabase
    .from('tasks')
    .select('*')
    .eq('user_id', userId)
    .order('priority', { ascending: true })
    .order('created_at', { ascending: true });
  return { data: (data ?? []) as Task[], error };
}

export async function updateTaskStatus(
  taskId: string,
  status: Task['status']
) {
  const updates: Partial<Task> = {
    status,
    updated_at: new Date().toISOString(),
  } as any;
  if (status === 'complete') {
    (updates as any).completed_at = new Date().toISOString();
  }
  const { data, error } = await supabase
    .from('tasks')
    .update(updates)
    .eq('id', taskId)
    .select()
    .single();
  return { data: data as Task | null, error };
}

export async function createTask(task: Omit<Task, 'id' | 'created_at' | 'updated_at'>) {
  const { data, error } = await supabase
    .from('tasks')
    .insert(task)
    .select()
    .single();
  return { data: data as Task | null, error };
}

// ─── Activity Log ──────────────────────────────────────────────────────────────

export async function getActivity(userId: string, limit = 20) {
  const { data, error } = await supabase
    .from('activity_log')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })
    .limit(limit);
  return { data: (data ?? []) as ActivityItem[], error };
}

export async function logActivity(
  userId: string,
  actor: string,
  action: string,
  entityType?: string,
  entityId?: string,
  metadata?: Record<string, unknown>
) {
  const { error } = await supabase
    .from('activity_log')
    .insert({ user_id: userId, actor, action, entity_type: entityType, entity_id: entityId, metadata });
  return { error };
}

// ─── Bots ──────────────────────────────────────────────────────────────────────

export async function getBotProfiles() {
  const { data, error } = await supabase
    .from('bot_profiles')
    .select('*')
    .order('sort_order', { ascending: true });
  return { data: (data ?? []) as BotProfile[], error };
}

// ─── Funding Stages ────────────────────────────────────────────────────────────

export async function getFundingStages(userId: string) {
  const { data, error } = await supabase
    .from('funding_stages')
    .select('*, funding_actions(*)')
    .eq('user_id', userId)
    .order('stage_number', { ascending: true });
  return { data: (data ?? []) as (FundingStage & { funding_actions: FundingAction[] })[], error };
}

export async function getFundingApplications(userId: string) {
  const { data, error } = await supabase
    .from('funding_applications')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false });
  return { data: (data ?? []) as FundingApplication[], error };
}

// ─── Messages ─────────────────────────────────────────────────────────────────

export async function getConversations(userId: string) {
  const { data, error } = await supabase
    .from('chat_conversations')
    .select('*')
    .eq('user_id', userId)
    .order('last_message_at', { ascending: false });
  return { data: (data ?? []) as ChatConversation[], error };
}

export async function getMessages(conversationId: string) {
  const { data, error } = await supabase
    .from('chat_messages')
    .select('*')
    .eq('conversation_id', conversationId)
    .order('created_at', { ascending: true });
  return { data: (data ?? []) as ChatMessage[], error };
}

export async function sendMessage(
  conversationId: string,
  senderId: string,
  senderName: string,
  content: string,
  isUserMessage = true
) {
  const { data, error } = await supabase
    .from('chat_messages')
    .insert({ conversation_id: conversationId, sender_id: senderId, sender_name: senderName, content, is_user_message: isUserMessage })
    .select()
    .single();

  if (!error) {
    // Update conversation last_message_at
    await supabase
      .from('chat_conversations')
      .update({ last_message_at: new Date().toISOString() })
      .eq('id', conversationId);
  }

  return { data: data as ChatMessage | null, error };
}

export async function getOrCreateConversation(
  userId: string,
  contactId: string,
  contactName: string,
  contactRole: string,
  contactType: ChatConversation['contact_type'] = 'ai'
) {
  // Try to find existing
  const { data: existing } = await supabase
    .from('chat_conversations')
    .select('*')
    .eq('user_id', userId)
    .eq('contact_id', contactId)
    .single();

  if (existing) return { data: existing as ChatConversation, error: null };

  // Create new
  const { data, error } = await supabase
    .from('chat_conversations')
    .insert({ user_id: userId, contact_id: contactId, contact_name: contactName, contact_role: contactRole, contact_type: contactType })
    .select()
    .single();
  return { data: data as ChatConversation | null, error };
}

// ─── Documents ────────────────────────────────────────────────────────────────

export async function getDocuments(userId: string) {
  const { data, error } = await supabase
    .from('documents')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false });
  return { data: (data ?? []) as Document[], error };
}

// ─── Credit ───────────────────────────────────────────────────────────────────

export async function getCreditReport(userId: string) {
  const { data, error } = await supabase
    .from('credit_reports')
    .select('*')
    .eq('user_id', userId)
    .eq('is_current', true)
    .order('created_at', { ascending: false })
    .limit(1)
    .single();
  return { data: data as CreditReport | null, error };
}

// ─── Credit Disputes ──────────────────────────────────────────────────────────

export interface CreditDispute {
  id: string;
  user_id: string;
  creditor: string;
  account_number: string | null;
  amount: number | null;
  reason: string;
  status: 'pending' | 'submitted' | 'resolved' | 'rejected';
  letter_url: string | null;
  notes: string | null;
  submitted_at: string | null;
  resolved_at: string | null;
  created_at: string;
}

export async function getDisputes(userId: string) {
  const { data, error } = await supabase
    .from('credit_disputes')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false });
  return { data: (data ?? []) as CreditDispute[], error };
}

// ─── Business Entity ──────────────────────────────────────────────────────────

export async function getBusinessEntity(userId: string) {
  const { data, error } = await supabase
    .from('business_entities')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })
    .limit(1)
    .single();
  return { data: data as BusinessEntity | null, error };
}

export async function upsertBusinessEntity(userId: string, updates: Partial<BusinessEntity>) {
  const { data, error } = await supabase
    .from('business_entities')
    .upsert({ user_id: userId, ...updates, updated_at: new Date().toISOString() }, { onConflict: 'id' })
    .select()
    .single();
  return { data: data as BusinessEntity | null, error };
}

// ─── User Settings ────────────────────────────────────────────────────────────

export interface UserSettings {
  user_id: string;
  notification_email: boolean;
  notification_sms: boolean;
  notification_push: boolean;
  two_factor_enabled: boolean;
  profile_visibility: string;
  ai_communication_style: string;
  language: string;
  timezone: string;
  updated_at: string;
}

export async function getSettings(userId: string) {
  const { data, error } = await supabase
    .from('user_settings')
    .select('*')
    .eq('user_id', userId)
    .single();
  return { data: data as UserSettings | null, error };
}

export async function updateSettings(userId: string, updates: Partial<UserSettings>) {
  const { data, error } = await supabase
    .from('user_settings')
    .upsert({ user_id: userId, ...updates, updated_at: new Date().toISOString() }, { onConflict: 'user_id' })
    .select()
    .single();
  return { data: data as UserSettings | null, error };
}

// ─── Admin ────────────────────────────────────────────────────────────────────

export async function getAllClients() {
  const { data, error } = await supabase
    .from('user_profiles')
    .select('*')
    .in('role', ['client', 'admin'])
    .order('created_at', { ascending: false });
  return { data: (data ?? []) as UserProfile[], error };
}

export async function getAllDocuments() {
  const { data, error } = await supabase
    .from('documents')
    .select('*')
    .order('created_at', { ascending: false });
  return { data: (data ?? []) as Document[], error };
}

export async function getAllFundingApplications() {
  const { data, error } = await supabase
    .from('funding_applications')
    .select('*')
    .order('created_at', { ascending: false });
  return { data: (data ?? []) as FundingApplication[], error };
}

export async function updateDocumentStatus(docId: string, status: 'pending' | 'verified' | 'attention') {
  const { data, error } = await supabase
    .from('documents')
    .update({ status })
    .eq('id', docId)
    .select()
    .single();
  return { data: data as Document | null, error };
}

export async function getAllCreditReports() {
  const { data, error } = await supabase
    .from('credit_reports')
    .select('*')
    .order('created_at', { ascending: false });
  return { data: (data ?? []) as CreditReport[], error };
}

export async function getAllCreditDisputes() {
  const { data, error } = await supabase
    .from('credit_disputes')
    .select('*')
    .order('created_at', { ascending: false });
  return { data: (data ?? []) as CreditDispute[], error };
}

// ─── Business Opportunities ───────────────────────────────────────────────────

export interface BusinessOpportunity {
  id: string;
  created_by: string | null;
  title: string;
  description: string | null;
  type: string;
  source: string | null;
  value_min: number | null;
  value_max: number | null;
  deadline: string | null;
  eligibility: string | null;
  status: 'active' | 'archived' | 'applied';
  is_client_facing: boolean;
  linked_user_id: string | null;
  created_at: string;
}

export async function getBusinessOpportunities() {
  const { data, error } = await supabase
    .from('business_opportunities')
    .select('*')
    .order('created_at', { ascending: false });
  return { data: (data ?? []) as BusinessOpportunity[], error };
}

export async function createBusinessOpportunity(opp: Partial<BusinessOpportunity>) {
  const { data, error } = await supabase
    .from('business_opportunities')
    .insert(opp)
    .select()
    .single();
  return { data: data as BusinessOpportunity | null, error };
}

export async function updateBusinessOpportunity(id: string, updates: Partial<BusinessOpportunity>) {
  const { data, error } = await supabase
    .from('business_opportunities')
    .update(updates)
    .eq('id', id)
    .select()
    .single();
  return { data: data as BusinessOpportunity | null, error };
}
