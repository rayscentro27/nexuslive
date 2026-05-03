/**
 * Nexus Feature Flag System
 * Flags are checked here first, then environment overrides, then admin DB overrides.
 * Non-enabled features show graceful fallback UI — they never break.
 */

export type FeatureFlag =
  | 'credit_boost_engine'
  | 'funding_readiness'
  | 'grants_engine'
  | 'trading_lab'
  | 'floating_chat'
  | 'notifications'
  | 'pilot_mode'
  | 'concierge'
  | 'approval_simulator'
  | 'partner_portal'
  | 'instant_ai_support'
  | 'bank_behavior'
  | 'vendor_tradelines'
  | 'business_credit'
  | 'white_label';

const DEFAULT_FLAGS: Record<FeatureFlag, boolean> = {
  credit_boost_engine:  true,
  funding_readiness:    true,
  grants_engine:        true,
  trading_lab:          true,
  floating_chat:        true,
  notifications:        true,
  pilot_mode:           true,
  concierge:            true,
  approval_simulator:   true,
  partner_portal:       false,
  instant_ai_support:   false,
  bank_behavior:        true,
  vendor_tradelines:    true,
  business_credit:      true,
  white_label:          false,
};

export function isFeatureEnabled(flag: FeatureFlag): boolean {
  const envKey = `VITE_FEATURE_${flag.toUpperCase()}`;
  const envValue = (import.meta as any).env?.[envKey];
  if (envValue !== undefined) return envValue === 'true';
  return DEFAULT_FLAGS[flag] ?? false;
}

export function useFeatureFlags() {
  return {
    enabled: isFeatureEnabled,
    flags: DEFAULT_FLAGS,
  };
}
