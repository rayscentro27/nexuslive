import React, { useState, useRef } from 'react';
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
  EyeOff,
  AlertCircle
} from 'lucide-react';
import { Turnstile } from '@marsidev/react-turnstile';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';
import { supabase } from '../lib/supabase';

const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || '';

interface AuthProps {
  onShowLegal?: () => void;
  onBackToDashboard?: () => void;
}

export function Auth({ onShowLegal, onBackToDashboard }: AuthProps) {
  const [showPassword, setShowPassword] = useState(false);
  const [signUpLoading, setSignUpLoading] = useState(false);
  const [signInLoading, setSignInLoading] = useState(false);
  const [signUpError, setSignUpError] = useState<string | null>(null);
  const [signInError, setSignInError] = useState<string | null>(null);
  const [signUpSuccess, setSignUpSuccess] = useState(false);

  // Sign Up form state
  const [signUpName, setSignUpName] = useState('');
  const [signUpEmail, setSignUpEmail] = useState('');
  const [signUpPassword, setSignUpPassword] = useState('');

  // Sign In form state
  const [signInEmail, setSignInEmail] = useState('');
  const [signInPassword, setSignInPassword] = useState('');

  // Turnstile captcha tokens
  const [signUpToken, setSignUpToken] = useState('');
  const [signInToken, setSignInToken] = useState('');
  const signUpTurnstileRef = useRef<any>(null);
  const signInTurnstileRef = useRef<any>(null);

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setSignUpError(null);
    if (TURNSTILE_SITE_KEY && !signUpToken) {
      setSignUpError('Please wait for the security check to complete.');
      return;
    }
    setSignUpLoading(true);
    try {
      const { error } = await supabase.auth.signUp({
        email: signUpEmail,
        password: signUpPassword,
        options: {
          data: { full_name: signUpName },
          ...(TURNSTILE_SITE_KEY && signUpToken ? { captchaToken: signUpToken } : {}),
        }
      });
      if (error) throw error;
      setSignUpSuccess(true);
    } catch (err: any) {
      setSignUpError(err.message || 'Sign up failed. Please try again.');
      signUpTurnstileRef.current?.reset();
      setSignUpToken('');
    } finally {
      setSignUpLoading(false);
    }
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setSignInError(null);
    if (TURNSTILE_SITE_KEY && !signInToken) {
      setSignInError('Please wait for the security check to complete.');
      return;
    }
    setSignInLoading(true);
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email: signInEmail,
        password: signInPassword,
        options: TURNSTILE_SITE_KEY && signInToken ? { captchaToken: signInToken } : undefined,
      });
      if (error) throw error;
    } catch (err: any) {
      setSignInError(err.message || 'Sign in failed. Please check your credentials.');
      signInTurnstileRef.current?.reset();
      setSignInToken('');
    } finally {
      setSignInLoading(false);
    }
  };

  const handleOAuth = async (provider: 'google' | 'github') => {
    await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: window.location.origin }
    });
  };

  if (signUpSuccess) {
    return (
      <div className="min-h-screen bg-[#F8FAFF] flex items-center justify-center p-4 font-sans">
        <div className="max-w-md w-full glass-card p-10 text-center space-y-6">
          <div className="w-16 h-16 bg-green-50 rounded-2xl flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-8 h-8 text-green-500" />
          </div>
          <div>
            <h2 className="text-2xl font-black text-[#1A2244]">Check Your Email</h2>
            <p className="text-sm text-slate-500 font-medium mt-2">
              We sent a confirmation link to <strong>{signUpEmail}</strong>. Click it to activate your account.
            </p>
          </div>
          <button
            onClick={() => setSignUpSuccess(false)}
            className="text-[10px] font-black text-slate-400 uppercase tracking-widest hover:text-[#5B7CFA]"
          >
            Back to Sign In
          </button>
        </div>
      </div>
    );
  }

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

          <form onSubmit={handleSignUp} className="space-y-4 relative z-10">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Full Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  required
                  value={signUpName}
                  onChange={e => setSignUpName(e.target.value)}
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
                  value={signUpEmail}
                  onChange={e => setSignUpEmail(e.target.value)}
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
                  value={signUpPassword}
                  onChange={e => setSignUpPassword(e.target.value)}
                  placeholder="••••••••"
                  minLength={6}
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

            {signUpError && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-100 text-red-700">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <p className="text-xs font-medium">{signUpError}</p>
              </div>
            )}

            {TURNSTILE_SITE_KEY && (
              <Turnstile
                ref={signUpTurnstileRef}
                siteKey={TURNSTILE_SITE_KEY}
                onSuccess={setSignUpToken}
                onExpire={() => setSignUpToken('')}
                options={{ theme: 'light', size: 'flexible' }}
              />
            )}

            <button
              type="submit"
              disabled={signUpLoading || (TURNSTILE_SITE_KEY ? !signUpToken : false)}
              className="w-full bg-[#5B7CFA] text-white py-3.5 rounded-xl font-black shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all transform hover:-translate-y-0.5 active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {signUpLoading ? 'Creating Account...' : 'Sign Up'}
            </button>
          </form>

          <div className="space-y-4 relative z-10">
            <div className="flex items-center gap-4">
              <div className="flex-1 h-px bg-slate-100" />
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Or sign up with</span>
              <div className="flex-1 h-px bg-slate-100" />
            </div>

            <div className="grid grid-cols-4 gap-3">
              <button
                onClick={() => handleOAuth('google')}
                className="flex items-center justify-center p-2.5 bg-white border border-slate-100 rounded-xl hover:bg-slate-50 transition-all shadow-sm group"
              >
                <Chrome className="w-5 h-5 text-slate-400 group-hover:text-[#1A2244]" />
              </button>
              <button
                onClick={() => handleOAuth('github')}
                className="flex items-center justify-center p-2.5 bg-white border border-slate-100 rounded-xl hover:bg-slate-50 transition-all shadow-sm group"
              >
                <Github className="w-5 h-5 text-slate-400 group-hover:text-[#1A2244]" />
              </button>
              {[Facebook, Apple].map((Icon, i) => (
                <button
                  key={i}
                  className="flex items-center justify-center p-2.5 bg-white border border-slate-100 rounded-xl hover:bg-slate-50 transition-all shadow-sm group opacity-40 cursor-not-allowed"
                  disabled
                >
                  <Icon className="w-5 h-5 text-slate-400" />
                </button>
              ))}
            </div>
          </div>

          {onBackToDashboard && (
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
          )}
        </div>

        {/* Right Side: Log In & Benefits */}
        <div className="space-y-8">
          <div className="glass-card p-8 space-y-6 relative overflow-hidden">
            <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-blue-500/5 rounded-full blur-3xl" />

            <div className="flex items-center gap-4 mb-2">
              <BotAvatar type="referral" size="md" />
              <div>
                <h2 className="text-2xl font-black text-[#1A2244]">Welcome Back</h2>
                <p className="text-xs text-slate-500 font-medium">Sign in to your Nexus account.</p>
              </div>
            </div>

            <form onSubmit={handleSignIn} className="space-y-4">
              <h3 className="text-sm font-bold text-[#1A2244]">Log In to Nexus</h3>
              <div className="space-y-3">
                <input
                  type="email"
                  required
                  value={signInEmail}
                  onChange={e => setSignInEmail(e.target.value)}
                  placeholder="Email Address"
                  className="w-full bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/10 transition-all"
                />
                <input
                  type="password"
                  required
                  value={signInPassword}
                  onChange={e => setSignInPassword(e.target.value)}
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
                  <button
                    type="button"
                    onClick={async () => {
                      if (!signInEmail) return;
                      await supabase.auth.resetPasswordForEmail(signInEmail, {
                        redirectTo: `${window.location.origin}/reset-password`
                      });
                      alert('Password reset email sent!');
                    }}
                    className="text-[10px] font-bold text-[#5B7CFA] uppercase tracking-widest hover:underline"
                  >
                    Forgot Password?
                  </button>
                </div>

                {signInError && (
                  <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-100 text-red-700">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <p className="text-xs font-medium">{signInError}</p>
                  </div>
                )}

                {TURNSTILE_SITE_KEY && (
                  <Turnstile
                    ref={signInTurnstileRef}
                    siteKey={TURNSTILE_SITE_KEY}
                    onSuccess={setSignInToken}
                    onExpire={() => setSignInToken('')}
                    options={{ theme: 'light', size: 'flexible' }}
                  />
                )}

                <button
                  type="submit"
                  disabled={signInLoading || (TURNSTILE_SITE_KEY ? !signInToken : false)}
                  className="w-full bg-[#5B7CFA] text-white py-3 rounded-xl font-black shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {signInLoading ? 'Signing In...' : 'Log In'}
                </button>
              </div>
            </form>

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
