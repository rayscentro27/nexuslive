/**
 * Checks if the current user has a free full access override (pilot/invite system).
 * When subscription_required = false, user gets access to all plan-gated features.
 */

import { useEffect, useState } from 'react';
import { useAuth } from '../components/AuthProvider';
import { supabase } from '../lib/supabase';

interface AccessOverride {
  subscription_required: boolean;
  subscription_status: string;
  access_type: string;
}

export function useAccessOverride() {
  const { user } = useAuth();
  const [override, setOverride] = useState<AccessOverride | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) { setOverride(null); setLoading(false); return; }
    supabase
      .from('user_access_overrides')
      .select('subscription_required, subscription_status, access_type')
      .eq('user_id', user.id)
      .single()
      .then(({ data }) => {
        setOverride(data as AccessOverride | null);
        setLoading(false);
      });
  }, [user]);

  const hasFreeFullAccess = override?.subscription_required === false;

  return { override, hasFreeFullAccess, loading };
}
