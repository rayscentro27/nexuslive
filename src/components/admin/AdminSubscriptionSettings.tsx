import React, { useState, useEffect } from 'react';
import { DollarSign, Save, RefreshCw, Check, AlertCircle, Percent } from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { cn } from '../../lib/utils';

interface PlanSetting {
  id: string;
  name: string;
  price: number;
  commission_rate: number;
  stripe_price_id: string;
  features: string[];
  active: boolean;
}

const DEFAULT_PLANS: PlanSetting[] = [
  {
    id: 'free', name: 'Free', price: 0, commission_rate: 0,
    stripe_price_id: '',
    features: ['Basic Business Setup Guide', 'Limited Document Storage (500MB)', 'Public Grants Search', 'Community Support', 'Basic Credit Tips'],
    active: true,
  },
  {
    id: 'pro', name: 'Pro', price: 50, commission_rate: 10,
    stripe_price_id: '',
    features: ['Full Business Formation Suite', 'Unlimited Document Storage', 'AI-Powered Grant Matching', 'Priority Advisor Access', 'Advanced Credit Analysis', 'Trading Lab Access'],
    active: true,
  },
  {
    id: 'elite', name: 'Elite', price: 100, commission_rate: 10,
    stripe_price_id: '',
    features: ['Dedicated Capital Strategist', 'Custom Funding Roadmaps', 'Concierge Business Setup', 'Multi-user Management', 'API Access & Integrations', 'White-label Portal Options'],
    active: true,
  },
];

export function AdminSubscriptionSettings() {
  const [plans, setPlans] = useState<PlanSetting[]>(DEFAULT_PLANS);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadPlans();
  }, []);

  async function loadPlans() {
    const { data } = await supabase.from('subscription_plans').select('*').order('price');
    if (data && data.length > 0) setPlans(data);
  }

  function updatePlan(id: string, field: keyof PlanSetting, value: any) {
    setPlans(prev => prev.map(p => p.id === id ? { ...p, [field]: value } : p));
  }

  async function savePlans() {
    setSaving(true);
    setError('');
    try {
      for (const plan of plans) {
        await supabase.from('subscription_plans').upsert(plan, { onConflict: 'id' });
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: any) {
      setError(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">Subscription Plans</h2>
          <p className="text-sm text-slate-500 mt-1">Update pricing — changes apply immediately across the site</p>
        </div>
        <button
          onClick={savePlans}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#5B7CFA] text-white rounded-xl text-sm font-black shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all disabled:opacity-50"
        >
          {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
          {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-100 rounded-2xl text-red-700 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {plans.map(plan => (
          <div key={plan.id} className="bg-white border border-slate-200 rounded-3xl p-6 space-y-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h3 className="font-black text-[#1A2244] text-lg">{plan.name}</h3>
              <label className="flex items-center gap-2 cursor-pointer">
                <span className="text-xs text-slate-400 font-bold">Active</span>
                <div
                  onClick={() => updatePlan(plan.id, 'active', !plan.active)}
                  className={cn(
                    "w-10 h-5 rounded-full transition-colors cursor-pointer",
                    plan.active ? "bg-[#5B7CFA]" : "bg-slate-200"
                  )}
                >
                  <div className={cn("w-4 h-4 bg-white rounded-full shadow mt-0.5 transition-transform", plan.active ? "translate-x-5" : "translate-x-1")} />
                </div>
              </label>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest block mb-1.5">Monthly Price ($)</label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="number"
                    value={plan.price}
                    onChange={e => updatePlan(plan.id, 'price', parseFloat(e.target.value) || 0)}
                    disabled={plan.id === 'free'}
                    className="w-full pl-8 pr-4 py-2.5 border border-slate-200 rounded-xl text-sm font-bold text-[#1A2244] focus:outline-none focus:ring-2 focus:ring-[#5B7CFA]/30 disabled:bg-slate-50 disabled:text-slate-400"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest block mb-1.5">Commission on Funding (%)</label>
                <div className="relative">
                  <Percent className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="number"
                    value={plan.commission_rate}
                    onChange={e => updatePlan(plan.id, 'commission_rate', parseFloat(e.target.value) || 0)}
                    min={0} max={100} step={0.5}
                    className="w-full pl-8 pr-4 py-2.5 border border-slate-200 rounded-xl text-sm font-bold text-[#1A2244] focus:outline-none focus:ring-2 focus:ring-[#5B7CFA]/30"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest block mb-1.5">Stripe Price ID</label>
                <input
                  type="text"
                  value={plan.stripe_price_id}
                  onChange={e => updatePlan(plan.id, 'stripe_price_id', e.target.value)}
                  placeholder={plan.id === 'free' ? 'Not required' : 'price_xxxxx'}
                  disabled={plan.id === 'free'}
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm font-mono text-slate-600 focus:outline-none focus:ring-2 focus:ring-[#5B7CFA]/30 disabled:bg-slate-50 disabled:text-slate-400"
                />
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100">
              <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-2">Summary</p>
              <p className="text-sm font-bold text-slate-600">
                {plan.price === 0 ? 'Free forever' : `$${plan.price}/mo`}
                {plan.commission_rate > 0 && ` + ${plan.commission_rate}% on funding`}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="p-5 bg-amber-50 border border-amber-100 rounded-2xl">
        <p className="text-xs font-black text-amber-700 uppercase tracking-widest mb-1">Important</p>
        <p className="text-sm text-amber-800 font-medium">
          Changing prices here updates the display immediately. To change what Stripe charges, you must also update the Stripe Price ID to match a price you've created in your Stripe dashboard.
        </p>
      </div>
    </div>
  );
}
