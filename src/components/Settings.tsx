import React, { useState, useEffect } from 'react';
import {
  User,
  Shield,
  CreditCard,
  Building2,
  Bell,
  Link as LinkIcon,
  Upload,
  Trash2,
  ChevronRight,
  LogOut,
  Smartphone,
  Download,
  Plus,
  HelpCircle,
  Mail,
  MessageSquare,
  Loader2,
  Save,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';
import { useAuth } from './AuthProvider';
import { getProfile, updateProfile, getSettings, updateSettings, getBusinessEntity, UserProfile, UserSettings, BusinessEntity } from '../lib/db';

const tabs = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'billing', label: 'Billing', icon: CreditCard },
  { id: 'business', label: 'Business Info', icon: Building2 },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'integrations', label: 'Integrations', icon: LinkIcon },
];

function Toggle({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!on)}
      className={cn(
        "w-6 h-3 rounded-full relative transition-colors",
        on ? "bg-[#5B7CFA]" : "bg-slate-200"
      )}
    >
      <div className={cn(
        "absolute top-0.5 w-2 h-2 bg-white rounded-full shadow-sm transition-all",
        on ? "right-0.5" : "left-0.5"
      )} />
    </button>
  );
}

export function Settings() {
  const { user, signOut } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [business, setBusiness] = useState<BusinessEntity | null>(null);
  const [loading, setLoading] = useState(true);

  // Profile edit state
  const [nameInput, setNameInput] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      getProfile(user.id),
      getSettings(user.id),
      getBusinessEntity(user.id),
    ]).then(([{ data: p }, { data: s }, { data: b }]) => {
      setProfile(p);
      setSettings(s);
      setBusiness(b);
      setNameInput(p?.full_name ?? user.user_metadata?.full_name ?? '');
      setLoading(false);
    });
  }, [user]);

  const handleSaveProfile = async () => {
    if (!user || !nameInput.trim()) return;
    setSavingProfile(true);
    const { data } = await updateProfile(user.id, { full_name: nameInput.trim() });
    if (data) setProfile(data);
    setSavingProfile(false);
    setProfileSaved(true);
    setTimeout(() => setProfileSaved(false), 2000);
  };

  const handleToggle = async (key: keyof UserSettings, value: boolean) => {
    if (!user) return;
    const optimistic = { ...settings, [key]: value } as UserSettings;
    setSettings(optimistic);
    await updateSettings(user.id, { [key]: value });
  };

  const displayName = profile?.full_name || user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User';
  const email = user?.email ?? '';
  const avatarUrl = profile?.avatar_url || user?.user_metadata?.avatar_url;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto h-full flex flex-col">
      <div className="space-y-0.5 shrink-0">
        <h2 className="text-2xl font-bold text-[#1A2244]">Settings</h2>
        <p className="text-xs text-slate-500 font-medium">Manage your profile, security, billing, and business information.</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1.5 p-1 bg-slate-100 rounded-xl w-fit shrink-0 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-1.5 rounded-lg text-[10px] font-bold transition-all whitespace-nowrap",
                isActive ? "bg-white text-[#5B7CFA] shadow-sm" : "text-slate-500 hover:text-slate-700"
              )}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-slate-300 animate-spin" />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto scrollbar-hide space-y-6 pr-1">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column */}
            <div className="lg:col-span-2 space-y-6">

              {/* Profile */}
              {(activeTab === 'profile' || activeTab === 'business') && (
                <div className="glass-card p-6 space-y-6 relative overflow-hidden">
                  <div className="absolute -top-4 -right-4 opacity-10">
                    <BotAvatar type="setup" size="xl" />
                  </div>
                  <h3 className="text-base font-bold text-[#1A2244] relative z-10">Profile Information</h3>

                  <div className="flex items-center gap-6">
                    <div className="relative group shrink-0">
                      {avatarUrl ? (
                        <img
                          src={avatarUrl}
                          alt={displayName}
                          referrerPolicy="no-referrer"
                          className="w-16 h-16 rounded-2xl object-cover border-2 border-white shadow-sm"
                        />
                      ) : (
                        <div className="w-16 h-16 rounded-2xl bg-[#C5C9F7] flex items-center justify-center border-2 border-white shadow-sm">
                          <span className="text-2xl font-black text-[#5B7CFA]">{displayName.charAt(0).toUpperCase()}</span>
                        </div>
                      )}
                      <button className="absolute -bottom-1 -right-1 p-1.5 bg-[#5B7CFA] text-white rounded-lg shadow-lg hover:scale-110 transition-transform">
                        <Upload className="w-3 h-3" />
                      </button>
                    </div>
                    <div className="space-y-0.5">
                      <p className="text-lg font-bold text-[#1A2244]">{displayName}</p>
                      <p className="text-xs text-slate-500 font-medium">{email}</p>
                      {business?.business_name && (
                        <p className="text-xs font-bold text-slate-700">{business.business_name}</p>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Full Name</label>
                      <input
                        type="text"
                        value={nameInput}
                        onChange={e => setNameInput(e.target.value)}
                        className="w-full bg-slate-50 border border-slate-100 rounded-lg px-3 py-2 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/10"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Email</label>
                      <input
                        type="email"
                        value={email}
                        readOnly
                        className="w-full bg-slate-50 border border-slate-100 rounded-lg px-3 py-2 text-xs font-medium text-slate-400 cursor-not-allowed"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Plan</label>
                      <input
                        type="text"
                        value={profile?.subscription_plan ?? 'free'}
                        readOnly
                        className="w-full bg-slate-50 border border-slate-100 rounded-lg px-3 py-2 text-xs font-medium text-slate-400 cursor-not-allowed capitalize"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Role</label>
                      <input
                        type="text"
                        value={(profile?.role ?? 'client').replace('_', ' ')}
                        readOnly
                        className="w-full bg-slate-50 border border-slate-100 rounded-lg px-3 py-2 text-xs font-medium text-slate-400 cursor-not-allowed capitalize"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <button
                      onClick={handleSaveProfile}
                      disabled={savingProfile || nameInput.trim() === (profile?.full_name ?? '')}
                      className={cn(
                        "flex items-center gap-2 px-5 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all",
                        profileSaved
                          ? "bg-green-500 text-white"
                          : "bg-[#5B7CFA] text-white hover:bg-[#4A6BEB] disabled:opacity-40"
                      )}
                    >
                      {savingProfile ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                      {profileSaved ? 'Saved!' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              )}

              {/* Business Info tab */}
              {activeTab === 'business' && (
                <div className="glass-card p-6 space-y-4">
                  <h3 className="text-base font-bold text-[#1A2244] flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-[#5B7CFA]" />
                    Business Entity
                  </h3>
                  {business ? (
                    <div className="grid grid-cols-2 gap-4">
                      {[
                        { label: 'Entity Name', value: business.business_name },
                        { label: 'Entity Type', value: business.entity_type },
                        { label: 'EIN', value: business.ein },
                        { label: 'DUNS Number', value: business.duns_number },
                        { label: 'Formation State', value: business.formation_state },
                        { label: 'Formation Date', value: business.formation_date },
                      ].map(({ label, value }) => (
                        <div key={label} className="space-y-1">
                          <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
                          <p className="text-xs font-bold text-slate-700">{value ?? '—'}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[10px] text-slate-400 font-bold">No business entity on file yet.</p>
                  )}
                </div>
              )}

              {/* Notifications tab */}
              {activeTab === 'notifications' && (
                <div className="glass-card p-6 space-y-5">
                  <h3 className="text-base font-bold text-[#1A2244]">Notification Preferences</h3>
                  <div className="space-y-4">
                    {[
                      { key: 'notification_email' as const, icon: Mail, label: 'Email', desc: 'Tasks, funding updates, documents' },
                      { key: 'notification_sms' as const, icon: MessageSquare, label: 'SMS', desc: 'Real-time alerts' },
                      { key: 'notification_push' as const, icon: Bell, label: 'Push Notifications', desc: 'Browser push alerts' },
                    ].map(({ key, icon: Icon, label, desc }) => (
                      <div key={key} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center border border-slate-100 shadow-sm">
                            <Icon className="w-3.5 h-3.5 text-slate-400" />
                          </div>
                          <div>
                            <p className="text-[10px] font-bold text-[#1A2244]">{label}</p>
                            <p className="text-[8px] text-slate-400 font-medium">{desc}</p>
                          </div>
                        </div>
                        <Toggle
                          on={settings?.[key] ?? false}
                          onChange={(v) => handleToggle(key, v)}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Billing tab */}
              {activeTab === 'billing' && (
                <div className="glass-card p-6 space-y-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-bold text-[#1A2244]">Subscription & Billing</h3>
                    <span className="px-2 py-0.5 rounded-md bg-green-50 text-green-600 text-[8px] font-bold uppercase tracking-widest">Active</span>
                  </div>
                  <div className="p-4 bg-slate-50 border border-slate-100 rounded-xl flex items-center justify-between">
                    <div className="space-y-0.5">
                      <p className="text-xs font-bold text-[#1A2244] capitalize">{profile?.subscription_plan ?? 'Free'} Plan</p>
                      <p className="text-[10px] text-slate-500 font-medium">Manage your subscription below</p>
                    </div>
                  </div>
                  <button className="w-full py-3 bg-[#5B7CFA] text-white font-black text-xs rounded-xl shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">
                    Manage Subscription
                  </button>
                </div>
              )}

              {/* Default: show profile tab content for security/integrations placeholders */}
              {(activeTab === 'security' || activeTab === 'integrations') && (
                <div className="glass-card p-6 flex items-center justify-center min-h-[200px]">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                    {activeTab === 'security' ? 'Security settings coming soon' : 'Integrations coming soon'}
                  </p>
                </div>
              )}
            </div>

            {/* Right Column */}
            <div className="space-y-6">
              <div className="glass-card p-5 space-y-5">
                <h3 className="text-sm font-bold text-[#1A2244]">Quick Actions</h3>
                <div className="space-y-1.5">
                  <button className="w-full flex items-center justify-between p-2.5 bg-slate-50 border border-slate-100 rounded-lg hover:bg-slate-100 transition-all group">
                    <div className="flex items-center gap-2.5">
                      <Shield className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#5B7CFA]" />
                      <span className="text-[10px] font-bold text-slate-700">Change Password</span>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                  </button>
                  <div className="w-full flex items-center justify-between p-2.5 bg-slate-50 border border-slate-100 rounded-lg">
                    <div className="flex items-center gap-2.5">
                      <Smartphone className="w-3.5 h-3.5 text-slate-400" />
                      <span className="text-[10px] font-bold text-slate-700">2-Factor Auth</span>
                    </div>
                    <Toggle
                      on={settings?.two_factor_enabled ?? false}
                      onChange={(v) => handleToggle('two_factor_enabled', v)}
                    />
                  </div>
                  <button className="w-full flex items-center justify-between p-2.5 bg-slate-50 border border-slate-100 rounded-lg hover:bg-slate-100 transition-all group">
                    <div className="flex items-center gap-2.5">
                      <Download className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#5B7CFA]" />
                      <span className="text-[10px] font-bold text-slate-700">Download My Data</span>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                  </button>
                </div>
                <button
                  onClick={signOut}
                  className="w-full py-2 text-[10px] font-black text-red-500 uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-red-50 rounded-lg transition-all"
                >
                  <LogOut className="w-3.5 h-3.5" /> Sign Out
                </button>
              </div>

              {/* Notifications quick panel */}
              <div className="glass-card p-5 space-y-5">
                <h3 className="text-sm font-bold text-[#1A2244]">Notifications</h3>
                <div className="space-y-3">
                  {[
                    { key: 'notification_email' as const, icon: Mail, label: 'Email', desc: 'Tasks & funding' },
                    { key: 'notification_sms' as const, icon: MessageSquare, label: 'SMS', desc: 'Real-time alerts' },
                  ].map(({ key, icon: Icon, label, desc }) => (
                    <div key={key} className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-slate-50 flex items-center justify-center">
                          <Icon className="w-3.5 h-3.5 text-slate-400" />
                        </div>
                        <div className="text-left">
                          <p className="text-[10px] font-bold text-[#1A2244]">{label}</p>
                          <p className="text-[8px] text-slate-400 font-medium">{desc}</p>
                        </div>
                      </div>
                      <Toggle
                        on={settings?.[key] ?? false}
                        onChange={(v) => handleToggle(key, v)}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="glass-card p-5 space-y-3">
                <h3 className="text-sm font-bold text-[#1A2244]">Support & Help</h3>
                <div className="space-y-1">
                  <button className="w-full flex items-center justify-between p-2 hover:bg-slate-50 rounded-lg transition-all group">
                    <div className="flex items-center gap-2.5">
                      <HelpCircle className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#5B7CFA]" />
                      <span className="text-[10px] font-bold text-slate-700">Help Center</span>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                  </button>
                  <button className="w-full flex items-center justify-between p-2 hover:bg-slate-50 rounded-lg transition-all group">
                    <div className="flex items-center gap-2.5">
                      <Mail className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#5B7CFA]" />
                      <span className="text-[10px] font-bold text-slate-700">Contact Support</span>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
