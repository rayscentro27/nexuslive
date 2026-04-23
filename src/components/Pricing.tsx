import React, { useState, useEffect } from 'react';
import { Check, ArrowRight, Shield, Zap, Star, AlertCircle } from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';
import { supabase } from '../lib/supabase';
import { redirectToCheckout } from '../services/stripeService';

interface PricingProps {
  onSelectPlan: (plan: string) => void;
  onShowLegal: () => void;
}

interface PlanData {
  id: string;
  name: string;
  price: number;
  commission_rate: number;
  stripe_price_id: string;
  features: string[];
  active: boolean;
}

const STATIC_PLANS = [
  {
    id: 'free', name: 'Free', price: 0, commission_rate: 0, stripe_price_id: '',
    features: ['Basic Business Setup Guide', 'Limited Document Storage (500MB)', 'Public Grants Search', 'Community Support', 'Basic Credit Tips'],
    icon: Zap, color: 'text-blue-500', buttonText: 'Get Started Free', popular: false,
  },
  {
    id: 'pro', name: 'Pro', price: 50, commission_rate: 10, stripe_price_id: import.meta.env.VITE_STRIPE_PRICE_PRO || '',
    features: ['Full Business Formation Suite', 'Unlimited Document Storage', 'AI-Powered Grant Matching', 'Priority Advisor Access', 'Advanced Credit Analysis', 'Trading Lab Access', '10% commission on funded amounts'],
    icon: Star, color: 'text-indigo-500', buttonText: 'Start Pro', popular: true,
  },
  {
    id: 'elite', name: 'Elite', price: 100, commission_rate: 10, stripe_price_id: import.meta.env.VITE_STRIPE_PRICE_ELITE || '',
    features: ['Dedicated Capital Strategist', 'Custom Funding Roadmaps', 'Concierge Business Setup', 'Multi-user Management', 'API Access & Integrations', 'White-label Portal Options', '10% commission on funded amounts'],
    icon: Shield, color: 'text-emerald-500', buttonText: 'Go Elite', popular: false,
  },
];

const ICONS = { free: Zap, pro: Star, elite: Shield };
const COLORS = { free: 'text-blue-500', pro: 'text-indigo-500', elite: 'text-emerald-500' };
const POPULAR = { free: false, pro: true, elite: false };
const BUTTON_TEXT = { free: 'Get Started Free', pro: 'Start Pro', elite: 'Go Elite' };

export function Pricing({ onSelectPlan, onShowLegal }: PricingProps) {
  const [plans, setPlans] = useState(STATIC_PLANS);
  const [loading, setLoading] = useState<string | null>(null);
  const [stripeError, setStripeError] = useState('');

  useEffect(() => {
    supabase.from('subscription_plans').select('*').order('price').then(({ data }) => {
      if (data && data.length > 0) {
        const merged = data.map((p: PlanData) => ({
          ...p,
          icon: ICONS[p.id as keyof typeof ICONS] || Zap,
          color: COLORS[p.id as keyof typeof COLORS] || 'text-blue-500',
          popular: POPULAR[p.id as keyof typeof POPULAR] ?? false,
          buttonText: BUTTON_TEXT[p.id as keyof typeof BUTTON_TEXT] || 'Get Started',
        }));
        setPlans(merged);
      }
    });
  }, []);

  async function handleSelectPlan(plan: typeof plans[0]) {
    if (plan.id === 'free') {
      onSelectPlan(plan.name);
      return;
    }
    if (!plan.stripe_price_id) {
      onSelectPlan(plan.name);
      return;
    }
    setLoading(plan.id);
    setStripeError('');
    const { error } = await redirectToCheckout(plan.stripe_price_id, '', '');
    if (error) setStripeError(error);
    setLoading(null);
  }

  return (
    <div className="min-h-screen bg-[#F8FAFF] py-20 px-4 font-sans">
      <div className="max-w-7xl mx-auto space-y-16">

        <div className="text-center space-y-4 max-w-3xl mx-auto">
          <div className="flex justify-center mb-6">
            <BotAvatar type="funding" size="xl" />
          </div>
          <h1 className="text-4xl md:text-5xl font-black text-[#1A2244] tracking-tight">
            Choose Your <span className="text-[#5B7CFA]">Nexus</span> Journey
          </h1>
          <p className="text-lg text-slate-500 font-medium">
            Unlock the capital, tools, and expertise your business needs to thrive.
            Start for free and scale as you grow.
          </p>
        </div>

        {stripeError && (
          <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-100 rounded-2xl text-red-700 text-sm max-w-xl mx-auto">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {stripeError}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map((plan) => {
            const Icon = plan.icon;
            return (
              <div
                key={plan.id}
                className={cn(
                  "glass-card p-8 flex flex-col relative transition-all duration-500 hover:scale-[1.02]",
                  plan.popular ? "border-[#5B7CFA] ring-4 ring-[#5B7CFA]/5 shadow-2xl" : "hover:shadow-xl"
                )}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-[#5B7CFA] text-white text-[10px] font-black uppercase tracking-widest px-4 py-1.5 rounded-full shadow-lg">
                    Most Popular
                  </div>
                )}

                <div className="mb-8">
                  <div className={cn("w-12 h-12 rounded-2xl flex items-center justify-center mb-6 bg-white shadow-sm", plan.color)}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <h3 className="text-2xl font-black text-[#1A2244] mb-2">{plan.name}</h3>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-black text-[#1A2244]">
                      {plan.price === 0 ? '$0' : `$${plan.price}`}
                    </span>
                    {plan.price > 0 && (
                      <span className="text-slate-400 font-bold uppercase text-xs tracking-widest">/mo</span>
                    )}
                  </div>
                  {plan.commission_rate > 0 && (
                    <p className="mt-2 text-xs text-slate-400 font-medium">
                      + {plan.commission_rate}% commission on funded amounts
                    </p>
                  )}
                </div>

                <div className="flex-1 space-y-4 mb-8">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">What's included:</p>
                  {plan.features.map((feature) => (
                    <div key={feature} className="flex items-start gap-3 group">
                      <div className="mt-0.5 w-5 h-5 rounded-full bg-blue-50 flex items-center justify-center shrink-0 group-hover:bg-blue-100 transition-colors">
                        <Check className="w-3 h-3 text-[#5B7CFA]" />
                      </div>
                      <span className="text-sm font-bold text-slate-600 group-hover:text-[#1A2244] transition-colors">{feature}</span>
                    </div>
                  ))}
                </div>

                <button
                  onClick={() => handleSelectPlan(plan)}
                  disabled={loading === plan.id}
                  className={cn(
                    "w-full py-4 rounded-2xl font-black flex items-center justify-center gap-2 transition-all active:scale-95 shadow-lg disabled:opacity-60",
                    plan.popular
                      ? "bg-[#5B7CFA] text-white hover:bg-[#4A6BEB] shadow-blue-500/20"
                      : "bg-white text-[#1A2244] border border-slate-100 hover:bg-slate-50 shadow-slate-200/50"
                  )}
                >
                  {loading === plan.id ? (
                    <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      {plan.buttonText}
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>

        <div className="max-w-4xl mx-auto space-y-8 text-center">
          <div className="p-8 glass-card bg-amber-50/30 border-amber-100/50">
            <h4 className="text-xs font-black text-amber-700 uppercase tracking-widest mb-3">Important Disclosure</h4>
            <p className="text-sm text-amber-900/70 font-medium leading-relaxed">
              Nexus is an educational platform and business resource center. <strong>We are not financial advisors, legal counsel, or tax professionals.</strong> All information provided is for educational purposes only. We do not guarantee funding, credit approval, or specific financial outcomes. Please consult with qualified professionals before making significant financial decisions.
            </p>
          </div>

          <div className="flex flex-wrap justify-center gap-8 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            <button onClick={onShowLegal} className="hover:text-[#5B7CFA] transition-colors">Terms of Service</button>
            <button onClick={onShowLegal} className="hover:text-[#5B7CFA] transition-colors">Privacy Policy</button>
            <button onClick={onShowLegal} className="hover:text-[#5B7CFA] transition-colors">Cookie Policy</button>
            <button onClick={onShowLegal} className="hover:text-[#5B7CFA] transition-colors">Financial Disclosures</button>
          </div>
        </div>
      </div>
    </div>
  );
}
