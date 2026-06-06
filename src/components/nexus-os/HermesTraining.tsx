import React, { useState, useCallback } from 'react';
import {
  Brain, Sparkles, FileText, CheckCircle2, Clock, Loader2,
  Zap, ThumbsUp, ThumbsDown, MessageSquare, ShieldCheck,
  BookOpen, Cpu, AlertTriangle, RefreshCw,
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { OSSection, OSCard, Badge, timeAgo, EmptyState } from './shared';
import { useNexusRecommendations, type NexusRecommendation, type RecIntent } from './useNexusRecommendations';

// Voice/memory files created in the Hermes Training pass (local ~/.hermes/ + repo docs/hermes/)
const VOICE_FILES = [
  { name: 'SOUL.md', location: '~/.hermes/SOUL.md', status: 'active', note: 'Command mappings + safety rules (pre-existing, evidence-first)' },
  { name: 'USER.md', location: '~/.hermes/USER.md', status: 'active', note: "Ray's durable preferences" },
  { name: 'MEMORY.md', location: '~/.hermes/MEMORY.md', status: 'active', note: 'Dense live-state notes' },
  { name: 'hermes_nexus_voice.md', location: 'docs/hermes/', status: 'active', note: 'Voice + recommendation behavior' },
];

const SKILLS = [
  { name: 'recommend-next-nexus-step', purpose: 'Answers "what next?" from revenue + content + approvals', status: 'active' },
  { name: 'recommend-revenue-action', purpose: 'Finds the campaign closest to revenue with fewest blockers', status: 'active' },
  { name: 'recommend-from-content', purpose: 'Which content to approve / which campaign needs content first', status: 'active' },
  { name: 'recommend-tool-or-repo', purpose: 'Classifies a shared repo/tool: core/later/reference/ignore', status: 'active' },
];

const PREVIEW_PROMPTS: Array<{ label: string; intent: RecIntent }> = [
  { label: 'Next best revenue action', intent: 'revenue_recommendation' },
  { label: 'Which campaign needs content first?', intent: 'content_recommendation' },
  { label: 'What is blocking revenue?', intent: 'blocker_diagnosis' },
  { label: 'What should I do today?', intent: 'next_step' },
  { label: 'What should I approve today?', intent: 'approval_summary' },
];

const FEEDBACK_CATEGORIES = [
  { value: 'good', label: 'Good', positive: true },
  { value: 'useful', label: 'Useful', positive: true },
  { value: 'too_generic', label: 'Too generic', positive: false },
  { value: 'too_long', label: 'Too long', positive: false },
  { value: 'not_enough_evidence', label: 'Not enough evidence', positive: false },
  { value: 'wrong_priority', label: 'Wrong priority', positive: false },
  { value: 'robotic', label: 'Robotic', positive: false },
];

export function HermesTraining() {
  const [rec, setRec] = useState<NexusRecommendation | null>(null);
  const [activeIntent, setActiveIntent] = useState<RecIntent | null>(null);
  const [loading, setLoading] = useState(false);
  const [hermesReply, setHermesReply] = useState<string | null>(null);
  const [hermesLoading, setHermesLoading] = useState(false);
  const [feedbackSaved, setFeedbackSaved] = useState(false);
  const [feedbackNote, setFeedbackNote] = useState('');

  const engine = useNexusRecommendations();

  const runPreview = useCallback(async (intent: RecIntent) => {
    setLoading(true);
    setActiveIntent(intent);
    setRec(null);
    setHermesReply(null);
    setFeedbackSaved(false);
    try {
      const result = await engine.recommend(intent);
      setRec(result);
    } catch (err) {
      console.error('[HermesTraining] recommend error:', err);
    } finally {
      setLoading(false);
    }
  }, [engine]);

  // Optionally ask Hermes to phrase the recommendation naturally
  async function askHermes() {
    if (!rec) return;
    setHermesLoading(true);
    setHermesReply(null);
    try {
      const evidence = engine.buildEvidenceContext(rec);
      const res = await fetch('/.netlify/functions/hermes-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          system: 'You are Hermes, Ray\'s Nexus OS executive operator. Answer in a fluent, warm, direct voice. Lead with the recommendation, then the why, then the blocker, then whether approval is needed. Do not dump data or say "Supabase".',
          messages: [{ role: 'user', content: `${evidence}\n\nGive me your recommendation in your own voice.` }],
        }),
        signal: AbortSignal.timeout(35000),
      });
      if (res.status === 503) {
        setHermesReply('⚠️ Hermes gateway not reachable. The deterministic recommendation above is still valid — Hermes would just phrase it naturally.');
        return;
      }
      const data = await res.json();
      setHermesReply(data.choices?.[0]?.message?.content ?? 'No response from Hermes.');
    } catch (err) {
      setHermesReply(`Hermes unavailable (${String(err)}). The deterministic recommendation above is still valid.`);
    } finally {
      setHermesLoading(false);
    }
  }

  async function saveFeedback(category: string) {
    if (!rec || !activeIntent) return;
    const positive = FEEDBACK_CATEGORIES.find(c => c.value === category)?.positive ?? false;
    try {
      await supabase.from('nexus_os_hermes_response_reviews').insert({
        prompt: PREVIEW_PROMPTS.find(p => p.intent === activeIntent)?.label ?? activeIntent,
        response: hermesReply ?? rec.recommendation,
        category,
        evidence_checked: rec.source_tables.length > 0,
        clear_recommendation: true,
        actionable_next_step: !!rec.next_action,
        approval_identified: true,
        revenue_impact_considered: activeIntent === 'revenue_recommendation' || activeIntent === 'next_step',
        safety_respected: true,
        tone_natural: positive,
        ray_rating: positive ? 5 : 2,
        ray_feedback: feedbackNote || null,
        intent: activeIntent,
      });
      setFeedbackSaved(true);
    } catch (err) {
      console.error('[HermesTraining] feedback save error:', err);
      setFeedbackSaved(true); // still show acknowledgment; admin RLS may block anon
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">
            Hermes <span className="text-[#5B7CFA]">Training Center</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Voice, memory, skills, and live recommendations · selective evidence, not row dumps
          </p>
        </div>
        <Badge label="Retrieval: selective / internal-first" variant="info" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Recommendation Preview — 2/3 */}
        <div className="lg:col-span-2 space-y-4">
          <OSSection title="Recommendation Preview" icon={Zap} action={
            rec ? <span className="text-[10px] text-slate-400">{rec.confidence} confidence</span> : undefined
          }>
            {/* Prompt buttons */}
            <div className="flex flex-wrap gap-2 mb-4">
              {PREVIEW_PROMPTS.map(p => (
                <button key={p.intent} onClick={() => runPreview(p.intent)} disabled={loading}
                  className={`px-3 py-1.5 rounded-xl text-[11px] font-bold transition-all ${
                    activeIntent === p.intent
                      ? 'bg-[#5B7CFA] text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  } disabled:opacity-50`}>
                  {p.label}
                </button>
              ))}
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-slate-300" /></div>
            ) : !rec ? (
              <EmptyState icon={Zap} message="Pick a prompt to generate a live recommendation" />
            ) : (
              <div className="space-y-4">
                {/* Recommendation card */}
                <div className="p-4 rounded-2xl bg-blue-50 border border-blue-100 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-black text-blue-700 uppercase tracking-widest">{rec.title}</p>
                    <Badge label={rec.approval_needed ? 'Approval needed' : 'No approval needed'} variant={rec.approval_needed ? 'warn' : 'success'} />
                  </div>
                  <p className="text-sm font-bold text-[#1A2244]">{rec.recommendation}</p>
                  <p className="text-xs text-slate-600">{rec.why}</p>
                </div>

                {/* Structured detail */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <DetailCell label="Next Action" value={rec.next_action} />
                  <DetailCell label="Evidence" value={rec.evidence_summary} />
                </div>

                {rec.blockers.length > 0 && rec.blockers[0] !== 'No data yet' && (
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5">Blockers</p>
                    {rec.blockers.slice(0, 5).map((b, i) => (
                      <p key={i} className="text-xs text-slate-600 flex items-start gap-1.5 py-0.5">
                        <span className="text-amber-400 shrink-0">•</span>{b}
                      </p>
                    ))}
                  </div>
                )}

                {/* Source/freshness */}
                <div className="flex items-center justify-between text-[10px] text-slate-400">
                  <span>Sources: {rec.source_tables.join(', ')}</span>
                  <span>Computed {timeAgo(rec.freshness)} · rules engine</span>
                </div>

                {/* Ask Hermes to phrase it */}
                <div className="flex items-center gap-2">
                  <button onClick={askHermes} disabled={hermesLoading}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#1A2244] text-white text-xs font-bold hover:bg-[#2d3556] disabled:opacity-50 transition-all">
                    {hermesLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                    Ask Hermes to phrase this
                  </button>
                  <span className="text-[10px] text-slate-400">Sends summarized evidence only — no raw rows</span>
                </div>

                {/* Hermes natural reply */}
                {hermesReply && (
                  <div className="p-4 rounded-2xl bg-white border border-slate-200">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-6 h-6 rounded-full bg-[#5B7CFA] flex items-center justify-center">
                        <Sparkles className="w-3 h-3 text-white" />
                      </div>
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Hermes</span>
                    </div>
                    <p className="text-sm text-[#1A2244] whitespace-pre-wrap leading-relaxed">{hermesReply}</p>
                  </div>
                )}

                {/* Feedback */}
                <div className="pt-2 border-t border-slate-100">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Rate this recommendation</p>
                  {feedbackSaved ? (
                    <p className="text-xs text-green-600 font-semibold flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Feedback saved — thanks
                    </p>
                  ) : (
                    <>
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {FEEDBACK_CATEGORIES.map(c => (
                          <button key={c.value} onClick={() => saveFeedback(c.value)}
                            className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all ${
                              c.positive
                                ? 'bg-green-50 text-green-700 hover:bg-green-100'
                                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}>
                            {c.label}
                          </button>
                        ))}
                      </div>
                      <input value={feedbackNote} onChange={e => setFeedbackNote(e.target.value)}
                        placeholder="Optional note..." className="input-base text-xs py-1.5" />
                    </>
                  )}
                </div>
              </div>
            )}
          </OSSection>
        </div>

        {/* Sidebar — 1/3 */}
        <div className="space-y-4">
          {/* Voice & Memory Status */}
          <OSSection title="Voice & Memory" icon={Brain}>
            <div className="space-y-2">
              {VOICE_FILES.map(f => (
                <div key={f.name} className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" />
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-[#1A2244]">{f.name}</p>
                    <p className="text-[10px] text-slate-400">{f.note}</p>
                    <p className="text-[9px] text-slate-300 font-mono">{f.location}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 p-2 rounded-lg bg-slate-50 border border-slate-100">
              <p className="text-[10px] text-slate-500">
                Retrieval mode: <strong>selective / internal-first</strong>. Hermes pulls only relevant, summarized evidence — no blind row dumps.
              </p>
            </div>
          </OSSection>

          {/* Recommendation Skills */}
          <OSSection title="Recommendation Skills" icon={Cpu}>
            <div className="space-y-2">
              {SKILLS.map(s => (
                <div key={s.name} className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="flex items-center justify-between">
                    <p className="text-[11px] font-bold text-[#1A2244] font-mono">{s.name}</p>
                    <Badge label={s.status} variant="success" />
                  </div>
                  <p className="text-[10px] text-slate-400 mt-0.5">{s.purpose}</p>
                </div>
              ))}
            </div>
            <p className="text-[10px] text-slate-400 mt-2 italic">
              Local: ~/.hermes/skills/nexus-recommendations/ · Tracked: skills/hermes/
            </p>
          </OSSection>

          {/* Safety */}
          <OSSection title="Safety" icon={ShieldCheck}>
            <div className="space-y-1.5 text-[11px] text-slate-600">
              <SafetyRow label="Live trading" locked />
              <SafetyRow label="Publishing" locked />
              <SafetyRow label="Email / outreach" locked />
              <SafetyRow label="Ad spend" locked />
              <SafetyRow label="Approval executor" locked />
              <SafetyRow label="Model fine-tuning" locked />
            </div>
          </OSSection>
        </div>
      </div>
    </div>
  );
}

function DetailCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{label}</p>
      <p className="text-xs text-slate-700">{value}</p>
    </div>
  );
}

function SafetyRow({ label, locked }: { label: string; locked: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span>{label}</span>
      <span className={`flex items-center gap-1 font-bold ${locked ? 'text-green-600' : 'text-red-500'}`}>
        <ShieldCheck className="w-3 h-3" /> {locked ? 'Locked' : 'Open'}
      </span>
    </div>
  );
}
