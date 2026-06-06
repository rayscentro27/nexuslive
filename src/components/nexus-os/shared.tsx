import React from 'react';
import { cn } from '../../lib/utils';

export function OSCard({
  children,
  className,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-white border border-slate-200 rounded-2xl shadow-sm',
        onClick && 'cursor-pointer hover:border-[#5B7CFA]/40 hover:shadow-md transition-all',
        className,
      )}
    >
      {children}
    </div>
  );
}

export function OSSection({
  title,
  icon: Icon,
  action,
  children,
}: {
  title: string;
  icon: React.ElementType;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <OSCard>
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-[#5B7CFA]" />
          <span className="text-[10px] font-black text-[#1A2244] uppercase tracking-widest">{title}</span>
        </div>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </OSCard>
  );
}

export function StatusDot({ status }: { status: 'online' | 'offline' | 'limited' | 'unknown' | 'pending' | 'ok' }) {
  const colors: Record<string, string> = {
    online: 'bg-green-500',
    ok: 'bg-green-500',
    offline: 'bg-red-500',
    limited: 'bg-amber-400',
    unknown: 'bg-slate-300',
    pending: 'bg-blue-400 animate-pulse',
  };
  return <span className={cn('inline-block w-2 h-2 rounded-full shrink-0', colors[status] ?? 'bg-slate-300')} />;
}

export function Badge({
  label,
  variant = 'default',
}: {
  label: string;
  variant?: 'default' | 'success' | 'warn' | 'danger' | 'info' | 'mock';
}) {
  const styles: Record<string, string> = {
    default: 'bg-slate-100 text-slate-600',
    success: 'bg-green-50 text-green-700',
    warn: 'bg-amber-50 text-amber-700',
    danger: 'bg-red-50 text-red-700',
    info: 'bg-blue-50 text-blue-700',
    mock: 'bg-violet-50 text-violet-600 border border-violet-200',
  };
  return (
    <span className={cn('px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide', styles[variant])}>
      {label}
    </span>
  );
}

export function MockLabel() {
  return (
    <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest bg-violet-50 text-violet-500 border border-violet-200">
      MOCK DATA
    </span>
  );
}

export function NotConnectedLabel() {
  return (
    <span className="text-slate-400 text-xs italic">Not connected yet</span>
  );
}

export function EmptyState({ message, icon: Icon }: { message: string; icon?: React.ElementType }) {
  const I = Icon;
  return (
    <div className="flex flex-col items-center justify-center py-10 gap-3 text-slate-400">
      {I && <I className="w-8 h-8 opacity-30" />}
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}

export function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 rounded-full bg-slate-100 overflow-hidden">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-slate-400 font-medium">{pct}%</span>
    </div>
  );
}

export function PriorityBadge({ priority }: { priority: string }) {
  if (priority === 'urgent') return <Badge label="Urgent" variant="danger" />;
  if (priority === 'normal') return <Badge label="Normal" variant="info" />;
  return <Badge label="Low" variant="default" />;
}

export function RiskBadge({ level }: { level: string }) {
  if (level === 'critical') return <Badge label="Critical" variant="danger" />;
  if (level === 'high') return <Badge label="High Risk" variant="danger" />;
  if (level === 'medium') return <Badge label="Medium" variant="warn" />;
  return <Badge label="Low Risk" variant="success" />;
}

export function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ─────────────────────────────────────────────────────────────────────────────
// NEXUS OS DESIGN SYSTEM — layout primitives (see docs/design/NEXUS_DESIGN.md)
// ─────────────────────────────────────────────────────────────────────────────

/** PageHeader — title + subtitle + optional right-aligned action. */
export function PageHeader({
  title,
  accent,
  subtitle,
  action,
}: {
  title: string;
  accent?: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 flex-wrap">
      <div className="min-w-0">
        <h2 className="text-lg sm:text-xl font-black text-[#1A2244] leading-tight">
          {title}{accent && <span className="text-[#5B7CFA]"> {accent}</span>}
        </h2>
        {subtitle && <p className="text-slate-400 text-xs mt-1">{subtitle}</p>}
      </div>
      {action && <div className="flex items-center gap-2 flex-wrap shrink-0">{action}</div>}
    </div>
  );
}

/** SectionHeader — compact labelled header for sub-sections inside a page. */
export function SectionHeader({
  title,
  icon: Icon,
  action,
}: {
  title: string;
  icon?: React.ElementType;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-2 mb-3">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="w-3.5 h-3.5 text-[#5B7CFA]" />}
        <span className="text-[11px] font-black text-[#1A2244] uppercase tracking-widest">{title}</span>
      </div>
      {action}
    </div>
  );
}

/**
 * WidgetGrid — responsive auto-fit grid so cards keep natural widths instead of
 * stretching edge-to-edge. `min` controls the smallest card width before wrap.
 */
export function WidgetGrid({
  children,
  min = 260,
  className,
}: {
  children: React.ReactNode;
  min?: number;
  className?: string;
}) {
  return (
    <div
      className={cn('grid gap-4', className)}
      style={{ gridTemplateColumns: `repeat(auto-fit, minmax(min(${min}px, 100%), 1fr))` }}
    >
      {children}
    </div>
  );
}

/** MetricCard — compact KPI widget. Not a giant box. */
export function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
  tone = 'default',
  onClick,
}: {
  icon?: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  tone?: 'default' | 'blue' | 'green' | 'amber' | 'red' | 'purple';
  onClick?: () => void;
}) {
  const toneMap: Record<string, string> = {
    default: 'bg-slate-100 text-slate-500',
    blue: 'bg-blue-50 text-[#5B7CFA]',
    green: 'bg-green-50 text-green-600',
    amber: 'bg-amber-50 text-amber-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
  };
  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-white border border-slate-200 rounded-2xl shadow-sm p-4 flex items-center gap-3',
        onClick && 'cursor-pointer hover:border-[#5B7CFA]/40 hover:shadow-md transition-all',
      )}
    >
      {Icon && (
        <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center shrink-0', toneMap[tone] ?? toneMap.default)}>
          <Icon className="w-5 h-5" />
        </div>
      )}
      <div className="min-w-0">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest truncate">{label}</p>
        <p className="text-lg font-black text-[#1A2244] leading-tight truncate">{value}</p>
        {sub && <p className="text-[9px] text-slate-400 truncate mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

/** StatusPill — small status chip with a dot. */
export function StatusPill({
  label,
  tone = 'muted',
}: {
  label: string;
  tone?: 'locked' | 'ok' | 'warn' | 'danger' | 'muted';
}) {
  const map: Record<string, { dot: string; text: string; bg: string }> = {
    locked: { dot: 'bg-green-500', text: 'text-green-700', bg: 'bg-green-50 border-green-100' },
    ok: { dot: 'bg-green-500', text: 'text-green-700', bg: 'bg-green-50 border-green-100' },
    warn: { dot: 'bg-amber-400', text: 'text-amber-700', bg: 'bg-amber-50 border-amber-100' },
    danger: { dot: 'bg-red-500', text: 'text-red-700', bg: 'bg-red-50 border-red-100' },
    muted: { dot: 'bg-slate-300', text: 'text-slate-500', bg: 'bg-slate-50 border-slate-100' },
  };
  const s = map[tone] ?? map.muted;
  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-bold', s.bg, s.text)}>
      <span className={cn('w-1.5 h-1.5 rounded-full', s.dot)} />
      {label}
    </span>
  );
}

/** SafetyChips — compact strip showing locked/disabled guardrails (not alarmist). */
export function SafetyChips() {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <StatusPill label="Live trading locked" tone="locked" />
      <StatusPill label="Publishing off" tone="locked" />
      <StatusPill label="Email/social off" tone="locked" />
      <StatusPill label="Ad spend off" tone="locked" />
      <StatusPill label="Executor off" tone="locked" />
    </div>
  );
}
