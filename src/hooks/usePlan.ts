import { useAuth } from '../components/AuthProvider';
import { useAccessOverride } from './useAccessOverride';

export type PlanTier = 'free' | 'pro' | 'elite';

const TIER_RANK: Record<PlanTier, number> = { free: 0, pro: 1, elite: 2 };

export function usePlan() {
  const { profile } = useAuth();
  const { hasFreeFullAccess } = useAccessOverride();
  const plan = (profile?.subscription_plan ?? 'free') as PlanTier;

  return {
    plan,
    hasFreeFullAccess,
    // Free full access overrides all plan gates
    isAtLeast: (tier: PlanTier) => hasFreeFullAccess || (TIER_RANK[plan] ?? 0) >= TIER_RANK[tier],
  };
}
