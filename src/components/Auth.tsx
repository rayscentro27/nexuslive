import React, { useState } from 'react';
import { 
  Mail, 
  Lock, 
  User, 
  Github, 
  Chrome, 
  Facebook, 
  Apple,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff
} from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';
import { useAuth } from './AuthProvider';

interface AuthProps {
  onShowLegal?: () => void;
  onBackToDashboard?: () => void;
}

export function Auth({ onShowLegal, onBackToDashboard }: AuthProps) {
  const [isLogin, setIsLogin] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { mockLogin } = useAuth();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mockLogin();
  };

  return (
    <div className="min-h-screen bg-[#F8FAFF] flex items-center justify-center p-4 font-sans overflow-hidden relative">
      {onBackToDashboard && (
        <button 
          onClick={onBackToDashboard}
          className="absolute top-8 left-8 z-50 flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest hover:text-[#5B7CFA] transition-all group"
        >
          <ArrowRight className="w-4 h-4 rotate-180 group-hover:-translate-x-1 transition-transform" />
          Back to Dashboard
        </button>
      )}
      <div className="max-w-5xl w-full grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
        
        {/* Left Side: Sign Up Form */}
        <div className="glass-card p-8 space-y-6 relative overflow-hidden">
          <div className="absolute -top-10 -left-10 w-40 h-40 bg-blue-500/5 rounded-full blur-3xl" />
          
          <div className="text-center space-y-2 relative z-10">
            <div className="flex justify-center mb-4">
              <BotAvatar type="dashboard" size="lg" />
            </div>
            <h2 className="text-2xl font-black text-[#1A2244]">Sign Up to Nexus</h2>
            <p className="text-xs text-slate-500 font-medium">Welcome! Create your Nexus account.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 relative z-10">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Full Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input 
                  type="text" 
                  required
                  placeholder="John Doe"
                  className="w-full bg-white border border-slate-100 rounded-xl pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 transition-all shadow-sm"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input 
                  type="email" 
                  required
                  placeholder="name@company.com"
                  className="w-full bg-white border border-slate-100 rounded-xl pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 transition-all shadow-sm"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input 
                  type={showPassword ? "text" : "password"} 
                  required
                  placeholder="••••••••"
                  className="w-full bg-white border border-slate-100 rounded-xl pl-10 pr-10 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 transition-all shadow-sm"
                />
                <button 
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-[#5B7CFA]"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button type="submit" className="w-full bg-[#5B7CFA] text-white py-3.5 rounded-xl font-black shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all transform hover:-translate-y-0.5 active:scale-95">
              Sign Up
            </button>
          </form>

          <div className="space-y-4 relative z-10">
            <div className="flex items-center gap-4">
              <div className="flex-1 h-px bg-slate-100" />
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Or sign up with</span>
              <div className="flex-1 h-px bg-slate-100" />
            </div>

            <div className="grid grid-cols-4 gap-3">
              {[Chrome, Github, Facebook, Apple].map((Icon, i) => (
                <button 
                  key={i} 
                  onClick={mockLogin}
                  className="flex items-center justify-center p-2.5 bg-white border border-slate-100 rounded-xl hover:bg-slate-50 transition-all shadow-sm group"
                >
                  <Icon className="w-5 h-5 text-slate-400 group-hover:text-[#1A2244]" />
                </button>
              ))}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-50">
            <button 
              onClick={onBackToDashboard}
              className="w-full glass-card p-4 bg-blue-50/30 border-blue-100/50 flex items-center justify-between group cursor-pointer text-left"
            >
              <div className="flex items-center gap-3">
                <BotAvatar type="dashboard" size="sm" />
                <div>
                  <p className="text-[10px] font-bold text-[#1A2244]">Preview Client Portal</p>
                  <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">See what's inside</p>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-[#5B7CFA] group-hover:translate-x-1 transition-all" />
            </button>
          </div>
        </div>

        {/* Right Side: Log In & Benefits */}
        <div className="space-y-8">
          <div className="glass-card p-8 space-y-6 relative overflow-hidden">
            <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-blue-500/5 rounded-full blur-3xl" />
            
            <div className="flex items-center gap-4 mb-2">
              <BotAvatar type="referral" size="md" />
              <div>
                <h2 className="text-2xl font-black text-[#1A2244]">Sign Up <span className="text-slate-300">&</span> Log In</h2>
                <p className="text-xs text-slate-500 font-medium">Welcome Back! Sign in to your Nexus account.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6">
              <form onSubmit={handleSubmit} className="space-y-4">
                <h3 className="text-sm font-bold text-[#1A2244]">Log In to Nexus</h3>
                <div className="space-y-3">
                  <input 
                    type="email" 
                    required
                    placeholder="Email Address"
                    className="w-full bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/10 transition-all"
                  />
                  <input 
                    type="password" 
                    required
                    placeholder="Password"
                    className="w-full bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/10 transition-all"
                  />
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer group">
                      <div className="w-4 h-4 rounded border border-slate-200 bg-white flex items-center justify-center group-hover:border-[#5B7CFA] transition-all">
                        <div className="w-2 h-2 bg-[#5B7CFA] rounded-sm opacity-0 group-hover:opacity-100 transition-all" />
                      </div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Remember me</span>
                    </label>
                    <button type="button" className="text-[10px] font-bold text-[#5B7CFA] uppercase tracking-widest hover:underline">Forgot Password?</button>
                  </div>
                  <button type="submit" className="w-full bg-[#5B7CFA] text-white py-3 rounded-xl font-black shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">
                    Log In
                  </button>
                </div>
              </form>
            </div>
            
            <div className="pt-4 border-t border-slate-50">
              <p className="text-[9px] text-slate-400 font-medium leading-relaxed text-center">
                By continuing, you agree to our <span onClick={onShowLegal} className="text-[#5B7CFA] font-bold cursor-pointer hover:underline">Terms of Service</span> and <span onClick={onShowLegal} className="text-[#5B7CFA] font-bold cursor-pointer hover:underline">Privacy Policy</span>.
                <br /><br />
                <strong>Disclaimer:</strong> Nexus is an educational platform. We are not financial advisors.
              </p>
            </div>
          </div>

          <div className="glass-card p-8 space-y-6">
            <h3 className="text-lg font-black text-[#1A2244]">Discover the benefits we offer</h3>
            <div className="space-y-4">
              {[
                "Centralized Business Hub",
                "Personalized Funding Roadmap",
                "Continuous Credit Monitoring"
              ].map((benefit, i) => (
                <div key={i} className="flex items-center gap-3 group">
                  <div className="w-6 h-6 rounded-full bg-green-50 flex items-center justify-center text-green-500 group-hover:scale-110 transition-transform">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                  <p className="text-sm font-bold text-slate-600">{benefit}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
