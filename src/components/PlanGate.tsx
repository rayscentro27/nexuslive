import React from 'react';
import { Lock, ArrowRight, Star, Shield } from 'lucide-react';
import { usePlan, PlanTier } from '../hooks/usePlan';

interface PlanGateProps {
  requiredPlan: PlanTier;
  featureName: string;
  children: React.ReactNode;
  onUpgrade?: () => void;
}

const PLAN_META: Record<PlanTier, { label: string; price: string; color: string; Icon: React.ElementType }> = {
  free:  { label: 'Free',  price: '$0/mo',   color: '#3d5af1', Icon: Lock },
  pro:   { label: 'Pro',   price: '$50/mo',  color: '#6366f1', Icon: Star },
  elite: { label: 'Elite', price: '$100/mo', color: '#10b981', Icon: Shield },
};

export function PlanGate({ requiredPlan, featureName, children, onUpgrade }: PlanGateProps) {
  const { isAtLeast } = usePlan();

  if (isAtLeast(requiredPlan)) return <>{children}</>;

  const meta = PLAN_META[requiredPlan];
  const PlanIcon = meta.Icon;

  return (
    <div className="h-full flex items-center justify-center p-6">
      <div className="max-w-md w-full glass-card p-10 text-center space-y-8">
        <div
          className="w-20 h-20 rounded-3xl flex items-center justify-center mx-auto"
          style={{ background: `${meta.color}15`, color: meta.color }}
        >
          <Lock className="w-10 h-10" />
        </div>

        <div className="space-y-2">
          <h2 className="text-2xl font-black" style={{ color: '#1a1c3a' }}>
            {featureName} Requires {meta.label}
          </h2>
          <p style={{ color: '#8b8fa8', fontWeight: 500 }}>
            Upgrade to <span style={{ color: meta.color, fontWeight: 700 }}>{meta.label} ({meta.price})</span> to unlock this feature.
          </p>
        </div>

        <div
          className="p-5 rounded-2xl text-left space-y-3"
          style={{ background: `${meta.color}08`, border: `1px solid ${meta.color}20` }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: `${meta.color}15`, color: meta.color }}
            >
              <PlanIcon className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-black" style={{ color: '#1a1c3a' }}>{meta.label} Plan</p>
              <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: '#8b8fa8' }}>
                {meta.price} · Cancel anytime
              </p>
            </div>
          </div>
        </div>

        {onUpgrade && (
          <button
            onClick={onUpgrade}
            className="w-full py-4 rounded-2xl font-black flex items-center justify-center gap-2 transition-all active:scale-95 shadow-lg"
            style={{ background: meta.color, color: '#fff' }}
          >
            Upgrade to {meta.label}
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
        {!onUpgrade && (
          <p className="text-xs font-bold" style={{ color: '#8b8fa8' }}>
            Contact your account manager to upgrade your plan.
          </p>
        )}
      </div>
    </div>
  );
}
