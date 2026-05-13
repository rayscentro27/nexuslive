import React, { useState, useEffect, useRef } from 'react';
import { Shield, TrendingUp, AlertCircle, FileText, Upload, Download, ArrowRight, CheckCircle2, Clock, Loader2, Zap, Star } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from './AuthProvider';
import { useAnalytics } from '../hooks/useAnalytics';
import { getCreditReport, getDisputes, CreditReport, CreditDispute } from '../lib/db';
import { CreditBoostEngine } from './CreditBoostEngine';
import { ApprovalSimulator } from './ApprovalSimulator';
import { supabase } from '../lib/supabase';

function scoreBandColor(band: string | null) {
  switch (band?.toLowerCase()) {
    case 'excellent': return 'bg-green-50 text-green-600';
    case 'good':      return 'bg-blue-50 text-blue-600';
    case 'fair':      return 'bg-amber-50 text-amber-600';
    case 'poor':      return 'bg-red-50 text-red-600';
    default:          return 'bg-slate-50 text-slate-500';
  }
}

function disputeStatusColor(status: CreditDispute['status']) {
  switch (status) {
    case 'submitted': return 'bg-blue-50 text-blue-600';
    case 'resolved':  return 'bg-green-50 text-green-600';
    case 'rejected':  return 'bg-red-50 text-red-600';
    default:          return 'bg-amber-50 text-amber-600';
  }
}

function formatCurrency(n: number | null) {
  if (n === null) return '—';
  return '$' + n.toLocaleString();
}

function formatRange(min: number | null, max: number | null) {
  if (!min && !max) return 'N/A';
  if (min && max) return `${formatCurrency(min)} – ${formatCurrency(max)}`;
  return formatCurrency(min ?? max);
}

type CreditTab = 'analysis' | 'boost' | 'simulator';

export function CreditAnalysis({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const { user } = useAuth();
  const { emit } = useAnalytics();
  const [report, setReport] = useState<CreditReport | null>(null);
  const [disputes, setDisputes] = useState<CreditDispute[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<CreditTab>('analysis');
  const [uploading, setUploading] = useState(false);
  const [showAllDisputes, setShowAllDisputes] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFileUpload(file: File) {
    if (!user) return;
    setUploading(true);
    const ext = file.name.split('.').pop();
    const path = `${user.id}/${Date.now()}.${ext}`;
    const { data: storageData, error: storageError } = await supabase.storage
      .from('credit-reports')
      .upload(path, file, { upsert: true });
    if (storageError || !storageData) { setUploading(false); return; }
    const { data: { publicUrl } } = supabase.storage.from('credit-reports').getPublicUrl(path);
    const { data: inserted } = await supabase.from('credit_reports').insert({
      user_id: user.id,
      report_file_url: publicUrl,
      report_date: new Date().toISOString().split('T')[0],
    }).select().single();
    if (inserted) setReport(inserted as CreditReport);
    setUploading(false);
  }

  useEffect(() => {
    if (!user) return;
    Promise.all([
      getCreditReport(user.id),
      getDisputes(user.id),
    ]).then(([{ data: r }, { data: d }]) => {
      setReport(r);
      setDisputes(d);
      setLoading(false);
    });
    emit('page_view', { event_name: 'credit_analysis_viewed', feature: 'credit', page: '/credit' });
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fallback values when no report exists
  const score = report?.score ?? 0;
  const scoreBand = report?.score_band ?? null;
  const fundingRange = formatRange(report?.funding_range_min ?? null, report?.funding_range_max ?? null);
  const utilization = report?.utilization_percent ?? 0;
  const totalDebt = report?.total_debt ?? 0;
  const lastUpdated = report?.report_date
    ? new Date(report.report_date).toLocaleDateString()
    : report?.created_at
    ? new Date(report.created_at).toLocaleDateString()
    : null;

  const hasReport = report !== null;
  const circumference = 226;
  const scoreOffset = score > 0 ? circumference - (circumference * score) / 850 : circumference;

  return (
    <div className="p-4 max-w-6xl mx-auto space-y-4 h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="flex flex-col space-y-3 shrink-0">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h1 className="text-xl font-black text-[#1A2244]">Credit Analysis</h1>
          {/* Tab switcher */}
          <div style={{ display: 'flex', gap: 6, background: '#f0f0f8', borderRadius: 12, padding: 4 }}>
            {([
              { id: 'analysis', label: 'Analysis', icon: Shield },
              { id: 'boost', label: 'Boost Engine', icon: Zap },
              { id: 'simulator', label: 'Simulator', icon: Star },
            ] as { id: CreditTab; label: string; icon: React.ElementType }[]).map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                style={{
                  padding: '6px 12px', borderRadius: 8, border: 'none', cursor: 'pointer',
                  fontSize: 12, fontWeight: 700,
                  background: activeTab === tab.id ? '#fff' : 'transparent',
                  color: activeTab === tab.id ? '#3d5af1' : '#8b8fa8',
                  boxShadow: activeTab === tab.id ? '0 2px 6px rgba(60,80,180,0.1)' : 'none',
                  display: 'flex', alignItems: 'center', gap: 5,
                }}>
                <tab.icon size={12} />{tab.label}
              </button>
            ))}
          </div>
        </div>
        {activeTab === 'analysis' && (
        <div className="flex items-center gap-3">
          {hasReport && scoreBand ? (
            <span className={cn("px-2 py-0.5 text-[10px] font-black uppercase rounded-md flex items-center gap-1.5", scoreBandColor(scoreBand))}>
              <CheckCircle2 className="w-3 h-3" />
              {scoreBand}
            </span>
          ) : (
            <span className="px-2 py-0.5 bg-slate-50 text-slate-400 text-[10px] font-black uppercase rounded-md flex items-center gap-1.5">
              <Clock className="w-3 h-3" />
              No Report
            </span>
          )}
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
            {hasReport ? 'Funding Readiness: Active' : 'Upload a report to get started'}
          </p>
        </div>
        )}
      </div>

      {/* Tab content */}
      {activeTab === 'boost' && <CreditBoostEngine />}
      {activeTab === 'simulator' && <ApprovalSimulator onNavigate={onNavigate} />}
      {activeTab === 'analysis' && (loading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-slate-300 animate-spin" />
        </div>
      ) : (
        <div className="flex-1 space-y-4">
          {/* Main Stats Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Funding Range Card */}
            <div className="lg:col-span-2 glass-card p-5 bg-gradient-to-br from-white to-blue-50/30">
              <div className="flex items-center justify-between mb-4">
                <div className="space-y-1">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Estimated Funding Range</p>
                  <h2 className="text-2xl font-black text-[#1A2244]">
                    {hasReport ? fundingRange : 'Upload report to unlock'}
                  </h2>
                  <p className="text-[10px] text-slate-400 font-medium">Approval odds based on readiness</p>
                </div>
                {lastUpdated && (
                  <div className="text-right">
                    <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Last Updated</p>
                    <p className="text-[10px] font-bold text-slate-600">{lastUpdated}</p>
                  </div>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setActiveTab('boost')}
                  className="bg-[#5B7CFA] text-white px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2"
                >
                  Generate Dispute Letters
                  <ArrowRight className="w-3 h-3" />
                </button>
                {report?.report_file_url && (
                  <a
                    href={report.report_file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-white border border-slate-100 text-[#1A2244] px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-50 transition-all flex items-center gap-2"
                  >
                    <Download className="w-3 h-3" />
                    Download
                  </a>
                )}
              </div>
            </div>

            {/* Score Card */}
            <div className="glass-card p-4 flex flex-col items-center justify-center text-center space-y-2">
              <div className="relative w-20 h-20 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90">
                  <circle cx="40" cy="40" r="36" stroke="currentColor" strokeWidth="5" fill="transparent" className="text-slate-100" />
                  <circle
                    cx="40" cy="40" r="36"
                    stroke="currentColor" strokeWidth="5" fill="transparent"
                    strokeDasharray={circumference}
                    strokeDashoffset={scoreOffset}
                    className={score >= 700 ? "text-[#5B7CFA]" : score >= 580 ? "text-amber-500" : "text-red-400"}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-xl font-black text-[#1A2244]">{score > 0 ? score : '—'}</span>
                  <span className="text-[7px] font-black text-slate-400 uppercase">Score</span>
                </div>
              </div>
              <div className="space-y-0.5">
                <h3 className="text-[11px] font-black text-[#1A2244]">
                  {scoreBand ? `Score Band: ${scoreBand}` : 'No score on file'}
                </h3>
                {!hasReport && (
                  <p className="text-[9px] text-slate-400 font-bold">Upload a report</p>
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Disputes / Negative Items */}
            <div className="glass-card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-red-50 text-red-600 rounded-lg">
                    <AlertCircle className="w-4 h-4" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">Negative Items</h3>
                </div>
                <span className="text-xl font-black text-red-600">{disputes.length}</span>
              </div>
              <p className="text-xs text-slate-500">Opportunities to dispute derogatory marks</p>
              {disputes.length > 0 ? (
                <ul className="space-y-1.5">
                  {(showAllDisputes ? disputes : disputes.slice(0, 3)).map(d => (
                    <li key={d.id} className="flex items-center gap-2 text-xs text-slate-600">
                      <div className="w-1 h-1 bg-red-400 rounded-full shrink-0" />
                      {d.creditor} — {d.reason}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-400">No disputes on file.</p>
              )}
              {disputes.length > 0 && (
                <button
                  onClick={() => setShowAllDisputes(v => !v)}
                  className="w-full py-2 bg-slate-50 text-slate-600 text-xs font-bold rounded-xl hover:bg-slate-100 transition-all flex items-center justify-center gap-2"
                >
                  {showAllDisputes ? 'Show Less' : `View All ${disputes.length} Disputes`} <ArrowRight className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Utilization */}
            <div className="glass-card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-amber-50 text-amber-600 rounded-lg">
                    <TrendingUp className="w-4 h-4" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">Usage</h3>
                </div>
                <span className="text-xl font-black text-amber-600">
                  {hasReport ? `${utilization}%` : '—'}
                </span>
              </div>
              <p className="text-xs text-slate-500">Utilization across all accounts</p>
              <div className="space-y-1.5">
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all", utilization > 50 ? "bg-red-400" : utilization > 30 ? "bg-amber-500" : "bg-green-500")}
                    style={{ width: `${Math.min(utilization, 100)}%` }}
                  />
                </div>
                <div className="flex justify-between text-[10px] font-bold text-slate-400 uppercase">
                  <span>Total Debt</span>
                  <span className="text-slate-600">{formatCurrency(totalDebt)}</span>
                </div>
              </div>
              <button
                onClick={() => onNavigate?.('action-center')}
                className="w-full py-2 bg-slate-50 text-slate-600 text-xs font-bold rounded-xl hover:bg-slate-100 transition-all flex items-center justify-center gap-2"
              >
                Improve Utilization <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </div>

          {/* Upload */}
          <div className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 px-2">History & Upload</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <label
                className="glass-card p-6 border-dashed border-2 flex flex-col items-center justify-center text-center space-y-3 hover:bg-slate-50/50 transition-all cursor-pointer"
                onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFileUpload(f); }}
                onDragOver={e => e.preventDefault()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  className="hidden"
                  onChange={e => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); }}
                />
                <div className="w-10 h-10 bg-blue-50 text-[#5B7CFA] rounded-full flex items-center justify-center">
                  {uploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Upload className="w-5 h-5" />}
                </div>
                <div className="space-y-0.5">
                  <h3 className="text-sm font-bold text-slate-900">{uploading ? 'Uploading…' : 'Upload New Report'}</h3>
                  <p className="text-[10px] text-slate-500">Click or drag & drop — PDF, JPG, PNG</p>
                </div>
              </label>

              {report?.report_file_url ? (
                <div className="glass-card p-5 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">Credit Report</h3>
                        <p className="text-[10px] text-slate-500">{lastUpdated ?? 'On file'}</p>
                      </div>
                    </div>
                    <a href={report.report_file_url} target="_blank" rel="noopener noreferrer" className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400">
                      <ArrowRight className="w-4 h-4" />
                    </a>
                  </div>
                  <div className="mt-4 flex gap-2">
                    <a href={report.report_file_url} target="_blank" rel="noopener noreferrer" className="flex-1 py-1.5 bg-slate-50 text-slate-600 text-[10px] font-bold rounded-lg hover:bg-slate-100 text-center">View</a>
                    <a href={report.report_file_url} download className="flex-1 py-1.5 bg-slate-50 text-slate-600 text-[10px] font-bold rounded-lg hover:bg-slate-100 text-center">Download</a>
                  </div>
                </div>
              ) : (
                <div className="glass-card p-5 flex items-center justify-center text-center opacity-50">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">No report on file yet</p>
                </div>
              )}
            </div>
          </div>

          {/* Dispute Assistant */}
          <div className="glass-card overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-blue-50 text-[#5B7CFA] rounded-lg">
                  <Shield className="w-4 h-4" />
                </div>
                <h2 className="text-base font-bold text-slate-900">Dispute Assistant</h2>
              </div>
              <span className="text-xs font-bold text-[#5B7CFA]">{disputes.length} Items</span>
            </div>
            {disputes.length > 0 ? (
              <div className="divide-y divide-slate-100">
                {disputes.map(d => (
                  <div key={d.id} className="p-4 flex items-center justify-between hover:bg-slate-50/50 transition-all">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center text-slate-400">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-slate-900">{d.creditor}</h4>
                        <p className="text-xs text-slate-500">
                          {d.reason}{d.amount ? ` (${formatCurrency(d.amount)})` : ''}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={cn("px-2 py-0.5 rounded-full text-[8px] font-bold uppercase tracking-wider", disputeStatusColor(d.status))}>
                        {d.status}
                      </span>
                      <button className="p-1.5 text-slate-300 hover:text-slate-600">
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">No disputes on file</p>
                <p className="text-xs text-slate-400 mt-1">Upload a credit report to identify dispute opportunities</p>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
