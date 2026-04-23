import React from 'react';
import { ArrowRight, Check, Shield, Zap, Star, TrendingUp, Users, DollarSign, FileText, BookOpen, ChevronRight } from 'lucide-react';
import { BotAvatar } from './BotAvatar';

interface LandingProps {
  onGetStarted: () => void;
  onViewPricing: () => void;
  onShowLegal: () => void;
}

export function Landing({ onGetStarted, onViewPricing, onShowLegal }: LandingProps) {
  const features = [
    {
      icon: TrendingUp,
      title: 'Credit Optimization',
      desc: 'AI-powered credit analysis and personalized roadmaps to reach 700+ business credit scores.',
      color: 'bg-blue-50 text-[#5B7CFA]',
    },
    {
      icon: DollarSign,
      title: 'Capital Access',
      desc: 'Connect to grants, SBA loans, credit lines, and private funding matched to your profile.',
      color: 'bg-emerald-50 text-emerald-500',
    },
    {
      icon: FileText,
      title: 'Business Formation',
      desc: 'LLC setup, EIN registration, business banking guides, and legal document templates.',
      color: 'bg-purple-50 text-purple-500',
    },
    {
      icon: BookOpen,
      title: 'AI Grant Matching',
      desc: 'Search thousands of grants with AI filtering to find funding you actually qualify for.',
      color: 'bg-amber-50 text-amber-500',
    },
    {
      icon: Users,
      title: 'Priority Advisors',
      desc: 'On-demand access to business advisors and capital strategists for Pro and Elite members.',
      color: 'bg-rose-50 text-rose-500',
    },
    {
      icon: Zap,
      title: 'Trading Lab',
      desc: 'Learn trading fundamentals and explore capital markets as an additional income stream.',
      color: 'bg-indigo-50 text-indigo-500',
    },
  ];

  const stats = [
    { value: '$2.4M+', label: 'Funding Facilitated' },
    { value: '1,200+', label: 'Businesses Launched' },
    { value: '94%', label: 'Credit Score Improvement' },
    { value: '48hrs', label: 'Avg. Capital Match Time' },
  ];

  const steps = [
    { num: '01', title: 'Create Your Account', desc: 'Sign up free and complete your business readiness profile in minutes.' },
    { num: '02', title: 'Get Your Roadmap', desc: 'AI generates a personalized funding and credit roadmap based on your goals.' },
    { num: '03', title: 'Execute & Scale', desc: 'Follow guided steps to form your business, build credit, and access capital.' },
  ];

  return (
    <div className="min-h-screen bg-[#F8FAFF] font-sans">

      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#1A2244] rounded-xl flex items-center justify-center">
              <Zap className="w-4 h-4 text-[#5B7CFA]" />
            </div>
            <span className="text-lg font-black text-[#1A2244] tracking-tight">Nexus</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-[11px] font-black uppercase tracking-widest text-slate-400">
            <button onClick={onViewPricing} className="hover:text-[#5B7CFA] transition-colors">Pricing</button>
            <button onClick={onShowLegal} className="hover:text-[#5B7CFA] transition-colors">Legal</button>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onGetStarted}
              className="text-[11px] font-black uppercase tracking-widest text-slate-500 hover:text-[#1A2244] transition-colors px-3 py-2"
            >
              Sign In
            </button>
            <button
              onClick={onGetStarted}
              className="flex items-center gap-2 px-5 py-2.5 bg-[#1A2244] text-white rounded-xl text-[11px] font-black uppercase tracking-widest hover:bg-[#2A3354] transition-all shadow-lg shadow-slate-900/10"
            >
              Get Started
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 pt-20 pb-24 text-center">
        <div className="flex justify-center mb-8">
          <BotAvatar type="funding" size="xl" />
        </div>
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-100 rounded-full text-[10px] font-black uppercase tracking-widest text-[#5B7CFA] mb-8">
          <div className="w-1.5 h-1.5 rounded-full bg-[#5B7CFA] animate-pulse" />
          AI-Powered Business Capital Platform
        </div>
        <h1 className="text-5xl md:text-7xl font-black text-[#1A2244] tracking-tight leading-[1.05] mb-6 max-w-4xl mx-auto">
          Build Credit.<br />
          Access Capital.<br />
          <span className="text-[#5B7CFA]">Scale Your Business.</span>
        </h1>
        <p className="text-lg md:text-xl text-slate-500 font-medium max-w-2xl mx-auto mb-10 leading-relaxed">
          Nexus gives entrepreneurs the tools, guidance, and AI-powered strategies to build business credit,
          secure funding, and grow from idea to empire.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={onGetStarted}
            className="flex items-center justify-center gap-2 px-8 py-4 bg-[#5B7CFA] text-white rounded-2xl text-sm font-black shadow-2xl shadow-blue-500/25 hover:bg-[#4A6BEB] transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            Start Free Today
            <ArrowRight className="w-4 h-4" />
          </button>
          <button
            onClick={onViewPricing}
            className="flex items-center justify-center gap-2 px-8 py-4 bg-white text-[#1A2244] rounded-2xl text-sm font-black border border-slate-200 hover:border-[#5B7CFA]/30 hover:shadow-lg transition-all"
          >
            View Pricing
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
        <p className="mt-6 text-xs text-slate-400 font-medium">
          Free plan available · No credit card required · Cancel anytime
        </p>
      </section>

      {/* Stats */}
      <section className="bg-[#1A2244] py-16">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-3xl md:text-4xl font-black text-white mb-2">{s.value}</div>
                <div className="text-[10px] font-black uppercase tracking-widest text-slate-400">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <p className="text-[10px] font-black uppercase tracking-widest text-[#5B7CFA] mb-4">Everything You Need</p>
          <h2 className="text-4xl font-black text-[#1A2244] tracking-tight">The Complete Business Arsenal</h2>
          <p className="mt-4 text-slate-500 font-medium max-w-xl mx-auto text-sm">
            One platform with every tool you need to establish, fund, and grow a successful business.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => (
            <div key={f.title} className="bg-white border border-slate-100 rounded-3xl p-8 shadow-sm hover:shadow-lg hover:border-[#5B7CFA]/20 transition-all group">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center mb-6 ${f.color}`}>
                <f.icon className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-black text-[#1A2244] mb-3">{f.title}</h3>
              <p className="text-sm text-slate-500 font-medium leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-white border-y border-slate-100 py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-[10px] font-black uppercase tracking-widest text-[#5B7CFA] mb-4">Simple Process</p>
            <h2 className="text-4xl font-black text-[#1A2244] tracking-tight">From Zero to Funded in 3 Steps</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            {steps.map((step, i) => (
              <div key={step.num} className="text-center relative">
                {i < steps.length - 1 && (
                  <div className="hidden md:block absolute top-8 left-[60%] w-[80%] h-px bg-slate-100" />
                )}
                <div className="w-16 h-16 rounded-2xl bg-[#5B7CFA]/10 flex items-center justify-center mx-auto mb-6">
                  <span className="text-2xl font-black text-[#5B7CFA]">{step.num}</span>
                </div>
                <h3 className="text-lg font-black text-[#1A2244] mb-3">{step.title}</h3>
                <p className="text-sm text-slate-500 font-medium leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-6 py-24 text-center">
        <div className="bg-gradient-to-br from-[#1A2244] to-[#2A3354] rounded-3xl p-16 shadow-2xl relative overflow-hidden">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg width=60 height=60 viewBox=0 0 60 60 xmlns=http://www.w3.org/2000/svg%3E%3Cg fill=none fill-rule=evenodd%3E%3Cg fill=%235B7CFA fill-opacity=0.05%3E%3Cpath d=M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z/%3E%3C/g%3E%3C/g%3E%3C/svg%3E')] opacity-30" />
          <div className="relative z-10 space-y-6">
            <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight">
              Your Capital Journey<br />Starts Today
            </h2>
            <p className="text-slate-300 font-medium max-w-xl mx-auto text-sm leading-relaxed">
              Join over 1,200 entrepreneurs who've used Nexus to build business credit, access funding, and scale their companies.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
              <button
                onClick={onGetStarted}
                className="flex items-center justify-center gap-2 px-8 py-4 bg-[#5B7CFA] text-white rounded-2xl text-sm font-black shadow-2xl shadow-blue-500/25 hover:bg-[#4A6BEB] transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                Get Started Free
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={onViewPricing}
                className="flex items-center justify-center gap-2 px-8 py-4 bg-white/10 text-white rounded-2xl text-sm font-black border border-white/20 hover:bg-white/20 transition-all"
              >
                See All Plans
              </button>
            </div>
            <div className="flex flex-wrap justify-center gap-6 pt-4 text-[11px] font-bold text-slate-400">
              {['No credit card required', 'Free plan forever', 'Cancel anytime'].map(t => (
                <div key={t} className="flex items-center gap-1.5">
                  <Check className="w-3 h-3 text-[#5B7CFA]" />
                  {t}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Disclaimer Banner */}
      <section className="bg-amber-50 border-y border-amber-100 py-8">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <div className="flex justify-center mb-3">
            <Shield className="w-5 h-5 text-amber-600" />
          </div>
          <p className="text-xs text-amber-800 font-medium leading-relaxed">
            <strong>Educational Platform Disclosure:</strong> Nexus is an educational resource and business tools platform.
            We are not financial advisors, licensed attorneys, or registered investment advisors. All information is for educational
            purposes only and does not constitute financial, legal, or tax advice. Results vary. We do not guarantee funding approval
            or specific financial outcomes. Please consult with qualified licensed professionals before making financial decisions.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-100 py-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 bg-[#1A2244] rounded-lg flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-[#5B7CFA]" />
            </div>
            <span className="font-black text-[#1A2244] tracking-tight">Nexus</span>
          </div>
          <div className="flex flex-wrap justify-center gap-6 text-[10px] font-black text-slate-400 uppercase tracking-widest">
            <button onClick={onShowLegal} className="hover:text-[#5B7CFA] transition-colors">Terms of Service</button>
            <button onClick={onShowLegal} className="hover:text-[#5B7CFA] transition-colors">Privacy Policy</button>
            <button onClick={onShowLegal} className="hover:text-[#5B7CFA] transition-colors">Disclosures</button>
            <button onClick={onViewPricing} className="hover:text-[#5B7CFA] transition-colors">Pricing</button>
          </div>
          <p className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">© 2025 Nexus. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
