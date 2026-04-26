import { useAuth } from '../components/AuthProvider';

export type PlanTier = 'free' | 'pro' | 'elite';

const TIER_RANK: Record<PlanTier, number> = { free: 0, pro: 1, elite: 2 };

export function usePlan() {
  const { profile } = useAuth();
  const plan = (profile?.subscription_plan ?? 'free') as PlanTier;

  return {
    plan,
    isAtLeast: (tier: PlanTier) => (TIER_RANK[plan] ?? 0) >= TIER_RANK[tier],
  };
}
