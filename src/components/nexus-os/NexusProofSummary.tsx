import React from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle, Bot, CheckCircle2, ChevronRight, CircleDollarSign,
  FileCheck2, MessageSquare, Radio, ShieldCheck, Store, Workflow,
} from 'lucide-react';
import { showroomSocialApprovalManifest } from '../../data/showroomSocialApprovalManifest';
import type { OsSection } from './types';

interface NexusProofSummaryProps {
  onNavigate: (section: OsSection) => void;
}

const publishedProof = showroomSocialApprovalManifest.find(item => item.approvalStatus === 'published');
const queuedApprovals = showroomSocialApprovalManifest.filter(item => item.approvalStatus === 'queued_for_review');

export function NexusProofSummary({ onNavigate }: NexusProofSummaryProps) {
  return (
    <div className="space-y-5 nexus-ink">
      <div>
        <h1 className="text-2xl font-black flex items-center gap-2">
          Proof and Control <FileCheck2 className="w-5 h-5" style={{ color: 'var(--nexus-cyan)' }} />
        </h1>
        <p className="text-sm nexus-muted mt-1">
          Source-backed operating snapshot. Live counts remain in their connected modules.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard
          icon={MessageSquare}
          title="Communication"
          status="Partial"
          detail="Hermes, Operator Core, and approval surfaces exist. Live Showroom still needs deployment."
          tone="warning"
        />
        <StatusCard
          icon={CircleDollarSign}
          title="Monetization"
          status="Manual launch ready"
          detail="$97 review leads to $97, $197, or $297 monthly guided support."
          tone="success"
        />
        <StatusCard
          icon={Workflow}
          title="Automation"
          status="Approval-gated"
          detail="Creative scoring and local queues work. Unattended publishing remains off."
          tone="success"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="nexus-glass p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-black flex items-center gap-2">
                <Store className="w-4 h-4" style={{ color: 'var(--nexus-purple)' }} />
                Showroom approvals
              </h2>
              <p className="text-xs nexus-muted mt-1">
                {queuedApprovals.length} source-manifest items waiting for review.
              </p>
            </div>
            <button
              type="button"
              onClick={() => onNavigate('showroom')}
              className="px-3 py-2 rounded-lg text-xs font-bold text-white nexus-accent-grad"
            >
              Open Showroom
            </button>
          </div>
          <div className="mt-4 space-y-2">
            {queuedApprovals.slice(0, 3).map(item => (
              <div key={item.id} className="nexus-glass-strong p-3">
                <div className="text-xs font-bold">{item.title}</div>
                <div className="text-[11px] nexus-muted mt-1">
                  {item.queueItemId} · score {item.qualityScore ?? 'not scored'}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="nexus-glass p-5">
          <h2 className="text-sm font-black flex items-center gap-2">
            <Bot className="w-4 h-4" style={{ color: 'var(--nexus-blue)' }} />
            Hermes and control layer
          </h2>
          <p className="text-xs nexus-muted mt-1">
            Hermes Chat is connected as its own OS module. It does not execute outward actions by itself.
          </p>
          <div className="mt-4 grid gap-2">
            {[
              'What should I approve next?',
              'What did Nexus do today?',
              'Show social queue',
              'What is blocking monetization?',
            ].map(command => (
              <button
                key={command}
                type="button"
                onClick={() => onNavigate('hermes-chat')}
                className="nexus-glass-strong px-3 py-2 text-left text-xs font-semibold"
              >
                {command}
              </button>
            ))}
          </div>
        </section>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="nexus-glass p-5">
          <h2 className="text-sm font-black flex items-center gap-2">
            <Radio className="w-4 h-4" style={{ color: 'var(--nexus-success)' }} />
            Verified Facebook proof
          </h2>
          {publishedProof ? (
            <>
              <p className="text-xs nexus-muted mt-2">{publishedProof.title}</p>
              <a
                href={publishedProof.proofPermalink}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex items-center gap-1 text-xs font-bold"
                style={{ color: 'var(--nexus-cyan)' }}
              >
                Open published proof <ChevronRight className="w-3 h-3" />
              </a>
            </>
          ) : (
            <p className="text-xs nexus-muted mt-2">No source-backed publication receipt is registered.</p>
          )}
          <div className="mt-4 flex items-center gap-2 text-[11px] nexus-muted">
            <ShieldCheck className="w-3.5 h-3.5" />
            Future publishing remains exact-item approval gated.
          </div>
        </section>

        <section className="nexus-glass p-5">
          <h2 className="text-sm font-black flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" style={{ color: 'var(--nexus-warning)' }} />
            Next actions
          </h2>
          <ol className="mt-3 space-y-2 text-xs">
            <li>1. Deploy this preview branch so the restored OS is visible.</li>
            <li>2. Re-authenticate the expired Facebook Page token.</li>
            <li>3. Approve and dry-run one high-scoring social queue item.</li>
            <li>4. Connect secure lead capture before handling credit documents.</li>
          </ol>
        </section>
      </div>

      <div className="nexus-glass p-4 flex flex-wrap items-center gap-3 text-xs">
        <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--nexus-success)' }} />
        <span className="font-semibold">Direct routes:</span>
        <Link to="/app/showroom" className="font-bold" style={{ color: 'var(--nexus-blue)' }}>/app/showroom</Link>
        <Link to="/admin/showroom" className="font-bold" style={{ color: 'var(--nexus-blue)' }}>/admin/showroom</Link>
        <span className="nexus-muted">Operator evidence: reports/operator/nexus_operator_status.json</span>
      </div>
    </div>
  );
}

function StatusCard({
  icon: Icon,
  title,
  status,
  detail,
  tone,
}: {
  icon: React.ElementType;
  title: string;
  status: string;
  detail: string;
  tone: 'success' | 'warning';
}) {
  const color = tone === 'success' ? 'var(--nexus-success)' : 'var(--nexus-warning)';
  return (
    <section className="nexus-glass p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-black">
          <Icon className="w-4 h-4" style={{ color }} />
          {title}
        </div>
        <span className="text-[10px] font-black uppercase" style={{ color }}>{status}</span>
      </div>
      <p className="text-xs nexus-muted mt-3">{detail}</p>
    </section>
  );
}
