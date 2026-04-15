import React from 'react';
import { Check, ArrowRight, Shield, Zap, Star } from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';

interface PricingProps {
  onSelectPlan: (plan: string) => void;
  onShowLegal: () => void;
}

export function Pricing({ onSelectPlan, onShowLegal }: PricingProps) {
  const plans = [
    {
      name: 'Free',
      price: '$0',
      description: 'Essential tools to get your business started.',
      features: [
        'Basic Business Setup Guide',
        'Limited Document Storage (500MB)',
        'Public Grants Search',
        'Community Support',
        'Basic Credit Tips'
      ],
      icon: Zap,
      color: 'text-blue-500',
      buttonText: 'Get Started Free',
      popular: false
    },
    {
      name: 'Pro',
      price: '$49',
      period: '/mo',
      description: 'Advanced features for growing businesses.',
      features: [
        'Full Business Formation Suite',
        'Unlimited Document Storage',
        'AI-Powered Grant Matching',
        'Priority Advisor Access',
        'Advanced Credit Analysis',
        'Trading Lab Access'
      ],
      icon: Star,
      color: 'text-indigo-500',
      buttonText: 'Start Pro Trial',
      popular: true
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      description: 'Tailored solutions for large scale operations.',
      features: [
        'Dedicated Capital Strategist',
        'Custom Funding Roadmaps',
        'White-label Portal Options',
        'API Access & Integrations',
        'Concierge Business Setup',
        'Multi-user Management'
      ],
      icon: Shield,
      color: 'text-emerald-500',
      buttonText: 'Contact Sales',
      popular: false
    }
  ];

  return (
    <div className="min-h-screen bg-[#F8FAFF] py-20 px-4 font-sans">
      <div className="max-w-7xl mx-auto space-y-16">
        
        {/* Header */}
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

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map((plan) => (
            <div 
              key={plan.name}
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
                  <plan.icon className="w-6 h-6" />
                </div>
                <h3 className="text-2xl font-black text-[#1A2244] mb-2">{plan.name}</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-black text-[#1A2244]">{plan.price}</span>
                  {plan.period && <span className="text-slate-400 font-bold uppercase text-xs tracking-widest">{plan.period}</span>}
                </div>
                <p className="mt-4 text-sm text-slate-500 font-medium leading-relaxed">
                  {plan.description}
                </p>
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
                onClick={() => onSelectPlan(plan.name)}
                className={cn(
                  "w-full py-4 rounded-2xl font-black flex items-center justify-center gap-2 transition-all active:scale-95 shadow-lg",
                  plan.popular 
                    ? "bg-[#5B7CFA] text-white hover:bg-[#4A6BEB] shadow-blue-500/20" 
                    : "bg-white text-[#1A2244] border border-slate-100 hover:bg-slate-50 shadow-slate-200/50"
                )}
              >
                {plan.buttonText}
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>

        {/* Disclaimer & Footer */}
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
