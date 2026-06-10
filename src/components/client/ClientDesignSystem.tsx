import React from 'react';
import { motion } from 'motion/react';
import { Sparkles } from 'lucide-react';

export function ClientPageShell({
  title,
  subtitle,
  actions,
  rail,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  rail?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="client-page-shell">
      <div className="client-page-head">
        <div>
          <h1>{title}</h1>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {actions ? <div>{actions}</div> : null}
      </div>
      <div className="client-page-grid">
        <div className="client-page-main">{children}</div>
        {rail ? <aside className="client-page-rail">{rail}</aside> : null}
      </div>
    </div>
  );
}

export function NexusWidget({
  title,
  subtitle,
  children,
  tone = 'default',
}: {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  tone?: 'default' | 'dark' | 'success' | 'warning';
}) {
  return (
    <motion.section whileHover={{ y: -2 }} className={`nexus-widget nexus-widget-${tone}`}>
      {(title || subtitle) && (
        <div className="nexus-widget-head">
          {title ? <h3>{title}</h3> : null}
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      )}
      {children}
    </motion.section>
  );
}

export function IntelligenceRail({ children }: { children: React.ReactNode }) {
  return <div className="intelligence-rail">{children}</div>;
}

export function MetricTile({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="metric-tile">
      <p>{label}</p>
      <h4>{value}</h4>
      {hint ? <span>{hint}</span> : null}
    </div>
  );
}

export function ProgressRing({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value));
  const circumference = 219.9;
  const offset = circumference * (1 - pct / 100);
  return (
    <div className="progress-ring-wrap" aria-label={`${label} ${pct}%`}>
      <svg viewBox="0 0 84 84" className="progress-ring-svg">
        <circle cx="42" cy="42" r="35" className="progress-ring-bg" />
        <circle cx="42" cy="42" r="35" className="progress-ring-fill" strokeDasharray={circumference} strokeDashoffset={offset} />
      </svg>
      <div>
        <strong>{pct}%</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

export function ReadinessHero({
  score,
  level,
  range,
  nextAction,
  cta,
}: {
  score: number;
  level: number;
  range: string;
  nextAction: string;
  cta?: React.ReactNode;
}) {
  return (
    <NexusWidget tone="dark">
      <div className="readiness-hero">
        <div>
          <span>Funding Readiness Command Center</span>
          <h2>{score}% Ready · Level {level}</h2>
          <p>{range}</p>
          <div className="readiness-hero-next">
            <Sparkles size={14} />
            Next best action: {nextAction}
          </div>
          {cta ? <div className="readiness-hero-cta">{cta}</div> : null}
        </div>
        <ProgressRing value={score} label="Readiness" />
      </div>
    </NexusWidget>
  );
}

export function EmptyStateUpgrade({ title, body, cta }: { title: string; body: string; cta?: React.ReactNode }) {
  return (
    <div className="empty-upgrade">
      <h4>{title}</h4>
      <p>{body}</p>
      {cta ? <div>{cta}</div> : null}
    </div>
  );
}
