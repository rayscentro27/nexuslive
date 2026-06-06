/**
 * useApprovalNotifier — creates Supabase notifications + triggers Telegram
 * whenever an approval item changes status.
 *
 * Calls /.netlify/functions/approval-notify which handles:
 *   - Supabase notification creation
 *   - Approval history event logging
 *   - Telegram send (with dedup, priority gate, policy checks)
 *
 * On missing config the function returns a graceful JSON error — this hook
 * logs it but never crashes the UI.
 */
import { useCallback } from 'react';
import { useAuth } from '../AuthProvider';

export type ApprovalAction = 'pending' | 'approved' | 'rejected' | 'needs_edits';

export interface NotifyPayload {
  approval_id: string;
  action_type: string;
  description: string;
  priority: string;
  status: ApprovalAction;
  requested_by?: string;
  review_notes?: string;
}

export interface NotifyResult {
  notification_created: boolean;
  telegram_sent: boolean;
  telegram_skipped_reason: string;
  dedup_hit: boolean;
  event_logged: boolean;
  error?: string;
}

export function useApprovalNotifier() {
  const { user } = useAuth();

  const notify = useCallback(
    async (payload: NotifyPayload): Promise<NotifyResult> => {
      const empty: NotifyResult = {
        notification_created: false,
        telegram_sent: false,
        telegram_skipped_reason: 'not attempted',
        dedup_hit: false,
        event_logged: false,
      };

      try {
        const res = await fetch('/.netlify/functions/approval-notify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...payload, user_id: user?.id }),
          signal: AbortSignal.timeout(12000),
        });

        if (!res.ok) {
          const errText = await res.text().catch(() => `HTTP ${res.status}`);
          console.warn('[ApprovalNotifier] Function error:', errText);
          return { ...empty, error: errText };
        }

        const result: NotifyResult = await res.json();

        if (result.telegram_skipped_reason) {
          console.info('[ApprovalNotifier] Telegram skip reason:', result.telegram_skipped_reason);
        }
        if (result.telegram_sent) {
          console.info('[ApprovalNotifier] Telegram sent for approval', payload.approval_id);
        }

        return result;
      } catch (err) {
        // Network error / function not deployed — log clearly, never crash UI
        const msg = String(err);
        if (msg.includes('Failed to fetch') || msg.includes('NetworkError')) {
          console.warn('[ApprovalNotifier] approval-notify function not reachable — running offline or not deployed');
        } else {
          console.warn('[ApprovalNotifier] Unexpected error:', msg);
        }
        return { ...empty, error: msg };
      }
    },
    [user],
  );

  return { notify };
}
