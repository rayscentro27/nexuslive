/**
 * Lightweight analytics event emitter.
 * Inserts into analytics_events table via Supabase.
 * Never throws — all errors are swallowed so analytics never breaks UX.
 */
import { useCallback, useRef } from 'react';
import { useAuth } from '../components/AuthProvider';
import { supabase } from '../lib/supabase';

type EventType =
  | 'page_view'
  | 'feature_click'
  | 'onboarding_step'
  | 'cta_click'
  | 'grant_viewed'
  | 'opportunity_viewed'
  | 'trade_started'
  | 'invite_sent'
  | 'funding_applied'
  | 'credit_checked'
  | 'strategy_approved'
  | 'hermes_interaction'
  | 'app_installed'
  | 'error';

type Feature =
  | 'dashboard'
  | 'funding'
  | 'trading'
  | 'grants'
  | 'credit'
  | 'onboarding'
  | 'referral'
  | 'settings'
  | 'admin'
  | 'chat';

interface EmitOptions {
  event_name: string;
  feature?: Feature;
  page?: string;
  value?: number;
  duration_ms?: number;
  metadata?: Record<string, unknown>;
}

function getSessionId(): string {
  const key = 'nexus_session_id';
  let sid = sessionStorage.getItem(key);
  if (!sid) {
    sid = `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    sessionStorage.setItem(key, sid);
  }
  return sid;
}

function getDeviceType(): string {
  const ua = navigator.userAgent;
  if (/Mobi|Android/i.test(ua)) return 'mobile';
  if (/Tablet|iPad/i.test(ua)) return 'tablet';
  return 'desktop';
}

export function useAnalytics() {
  const { user } = useAuth();
  const sessionId = useRef(getSessionId());

  const emit = useCallback(
    async (event_type: EventType, opts: EmitOptions) => {
      try {
        const row = {
          user_id: user?.id ?? null,
          session_id: sessionId.current,
          event_type,
          event_name: opts.event_name,
          feature: opts.feature ?? null,
          page: opts.page ?? window.location.pathname,
          value: opts.value ?? null,
          duration_ms: opts.duration_ms ?? null,
          metadata: {
            ...opts.metadata,
            device: getDeviceType(),
            url: window.location.href,
          },
        };
        await supabase.from('analytics_events').insert(row);
      } catch {
        // analytics must never break UX
      }
    },
    [user?.id]
  );

  return { emit };
}
