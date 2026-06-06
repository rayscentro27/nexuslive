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
