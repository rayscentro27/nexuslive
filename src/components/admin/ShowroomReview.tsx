import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../../lib/supabase';

type AssetStatus = 'needs_review' | 'approved' | 'approved_with_notes' | 'revise' | 'revised' | 'ready_to_publish_pending_approval' | 'archived';
type PackageStatus = 'needs_review' | 'approved_for_manual_use_only' | 'needs_revision' | 'blocked' | 'ready_for_beta_manual_outreach';

interface Asset {
  asset_id: string;
  asset_type: string;
  title: string;
  status: AssetStatus;
  file_path: string;
  showroom_path: string;
  feedback: { at: string; status: string; note: string }[];
  lesson_memory: string;
  created_at: string;
  updated_at: string;
  preview?: string;
}

interface Package {
  package_id: string;
  title: string;
  count: number;
  status_summary: Record<string, number>;
  package_status: PackageStatus;
}

interface PackageDetail {
  package_id: string;
  meta: { status?: string; note?: string; updated_at?: string };
  assets: Asset[];
  count: number;
}

const STATUS_COLORS: Record<string, string> = {
  needs_review: '#f59e0b',
  approved: '#22c55e',
  approved_with_notes: '#16a34a',
  revise: '#ef4444',
  revised: '#3b82f6',
  ready_to_publish_pending_approval: '#8b5cf6',
  archived: '#6b7280',
};

const PACKAGE_STATUS_COLORS: Record<string, string> = {
  needs_review: '#f59e0b',
  approved_for_manual_use_only: '#22c55e',
  needs_revision: '#ef4444',
  blocked: '#dc2626',
  ready_for_beta_manual_outreach: '#8b5cf6',
};

const STYLES = {
  container: {
    padding: '24px',
    maxWidth: '1200px',
    margin: '0 auto',
    color: '#e2e8f0',
    fontFamily: "system-ui, -apple-system, sans-serif",
  },
  header: {
    fontSize: '24px',
    fontWeight: 700,
    marginBottom: '8px',
    color: '#f1f5f9',
  },
  subtitle: {
    fontSize: '14px',
    color: '#94a3b8',
    marginBottom: '24px',
  },
  backBtn: {
    background: 'rgba(255,255,255,0.08)',
    border: '1px solid rgba(255,255,255,0.15)',
    color: '#e2e8f0',
    padding: '8px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    marginBottom: '16px',
  },
  card: {
    background: 'rgba(15, 18, 50, 0.85)',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '12px',
  },
  badge: (color: string) => ({
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: '999px',
    fontSize: '11px',
    fontWeight: 600,
    background: `${color}22`,
    color: color,
    border: `1px solid ${color}44`,
  }),
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '12px',
  },
  pillBtn: (color: string) => ({
    padding: '6px 14px',
    borderRadius: '8px',
    border: `1px solid ${color}44`,
    background: `${color}18`,
    color: color,
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 600,
  }),
  textarea: {
    width: '100%',
    background: 'rgba(0,0,0,0.3)',
    border: '1px solid rgba(255,255,255,0.15)',
    borderRadius: '8px',
    padding: '10px',
    color: '#e2e8f0',
    fontSize: '13px',
    minHeight: '80px',
    resize: 'vertical' as const,
    fontFamily: 'inherit',
  },
  select: {
    background: 'rgba(0,0,0,0.3)',
    border: '1px solid rgba(255,255,255,0.15)',
    borderRadius: '8px',
    padding: '8px 12px',
    color: '#e2e8f0',
    fontSize: '13px',
  },
};

function statusBadge(status: string) {
  const color = STATUS_COLORS[status] || '#6b7280';
  return <span style={STYLES.badge(color)}>{status.replace(/_/g, ' ')}</span>;
}

function packageBadge(status: string) {
  const color = PACKAGE_STATUS_COLORS[status] || '#6b7280';
  return <span style={STYLES.badge(color)}>{status.replace(/_/g, ' ')}</span>;
}

function ErrorState({ message }: { message: string }) {
  const isServerOffline = message.includes('Failed to fetch') || message.includes('NetworkError');
  return (
    <div style={STYLES.card}>
      <p style={{ color: '#f87171', fontWeight: 600, margin: '0 0 8px' }}>
        ⚠️ {isServerOffline ? 'Backend server not running' : 'Error loading data'}
      </p>
      <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0 }}>
        {isServerOffline
          ? 'Start the Nexus control center: python3 control_center/control_center_server.py'
          : message}
      </p>
    </div>
  );
}

function LoadingState() {
  return (
    <div style={{ textAlign: 'center', padding: '48px', color: '#94a3b8' }}>
      <div style={{ fontSize: '32px', marginBottom: '12px' }}>⏳</div>
      <p>Loading showroom assets...</p>
    </div>
  );
}

function EmptyState({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div style={STYLES.card}>
      <p style={{ color: '#94a3b8', margin: '0 0 8px' }}>
        No reviewable assets found. Generate content first, then run build_results_showroom.py.
      </p>
      <button onClick={onRefresh} style={STYLES.backBtn}>Refresh</button>
    </div>
  );
}

function formatDate(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
  }
}

export function ShowroomReview() {
  const [view, setView] = useState<'packages' | 'package' | 'asset'>('packages');
  const [packages, setPackages] = useState<Package[]>([]);
  const [packageDetail, setPackageDetail] = useState<PackageDetail | null>(null);
  const [currentAsset, setCurrentAsset] = useState<Asset | null>(null);
  const [selectedPackageId, setSelectedPackageId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [pkgStatus, setPkgStatus] = useState<string>('needs_review');
  const [pkgStatusSaving, setPkgStatusSaving] = useState(false);

  const apiFetch = useCallback(async (apiPath: string, options?: RequestInit) => {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token ?? '';
    const url = `/.netlify/functions/nexus-api?path=${encodeURIComponent('/api/showroom' + apiPath)}`;
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...(options?.headers ?? {}),
      },
    });
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('text/html') || contentType.includes('text/plain')) {
      const text = await res.text();
      throw new Error(
        `Backend returned ${res.status} ${contentType} instead of JSON. ` +
        (res.status === 401 ? 'Session may have expired. Try refreshing the page.' :
         res.status === 403 ? 'Access denied by proxy.' :
         `First 120 chars: ${text.slice(0, 120)}`)
      );
    }
    if (!res.ok) {
      try {
        const body = await res.json();
        throw new Error(body.error || `HTTP ${res.status}`);
      } catch (parseErr: any) {
        if (parseErr.message && !parseErr.message.startsWith('HTTP')) throw parseErr;
        throw new Error(`HTTP ${res.status}`);
      }
    }
    try {
      return await res.json();
    } catch (parseErr: any) {
      const text = await res.text().catch(() => '(empty)');
      throw new Error(`Expected JSON but got: ${text.slice(0, 120)}`);
    }
  }, []);

  const loadPackages = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch('/packages');
      setPackages(data.packages || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);

  const loadPackageDetail = useCallback(async (pkgId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch(`/packages/${encodeURIComponent(pkgId)}`);
      setPackageDetail(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);

  const loadAsset = useCallback(async (assetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch(`/assets/${encodeURIComponent(assetId)}`);
      setCurrentAsset(data.asset);
      setFeedback('');
      setSaveMsg(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);

  useEffect(() => { loadPackages(); }, [loadPackages]);

  const handleReview = async (status: AssetStatus) => {
    if (!currentAsset) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      await apiFetch(`/assets/${encodeURIComponent(currentAsset.asset_id)}/review`, {
        method: 'POST',
        body: JSON.stringify({ status, feedback }),
      });
      setSaveMsg(`✓ Status updated to: ${status}`);
      setFeedback('');
      loadAsset(currentAsset.asset_id);
    } catch (e: any) {
      setSaveMsg(`✗ Error: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handlePackageStatus = async (status: string) => {
    if (!selectedPackageId) return;
    setPkgStatusSaving(true);
    try {
      await apiFetch(`/packages/${encodeURIComponent(selectedPackageId)}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status, note: feedback }),
      });
      setPkgStatus(status);
      setSaveMsg(`✓ Package status: ${status}`);
      setFeedback('');
      loadPackageDetail(selectedPackageId);
      loadPackages();
    } catch (e: any) {
      setSaveMsg(`✗ Error: ${e.message}`);
    } finally {
      setPkgStatusSaving(false);
    }
  };

  function openPackage(pkgId: string) {
    setSelectedPackageId(pkgId);
    setPackageDetail(null);
    setView('package');
    loadPackageDetail(pkgId);
  }

  function openAsset(asset: Asset) {
    setCurrentAsset(null);
    setView('asset');
    loadAsset(asset.asset_id);
  }

  function goBack() {
    if (view === 'asset') {
      if (selectedPackageId) {
        setView('package');
        loadPackageDetail(selectedPackageId);
      } else {
        setView('packages');
        loadPackages();
      }
    } else if (view === 'package') {
      setView('packages');
      setSelectedPackageId(null);
      loadPackages();
    }
  }

  if (loading && view === 'packages') return <LoadingState />;
  if (error && view === 'packages') return <ErrorState message={error} />;
  if (!loading && packages.length === 0 && view === 'packages') return <EmptyState onRefresh={loadPackages} />;

  return (
    <div style={{ minHeight: '100vh', background: '#0f1232' }}>
      <div style={STYLES.container}>
        {view === 'packages' && (
          <>
            <h1 style={STYLES.header}>📦 Showroom Review</h1>
            <p style={STYLES.subtitle}>
              {packages.length} asset types · {packages.reduce((s, p) => s + p.count, 0)} total assets
            </p>
            {error && <ErrorState message={error} />}
            <div style={STYLES.grid}>
              {packages.map(pkg => (
                <div key={pkg.package_id} style={STYLES.card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#f1f5f9' }}>{pkg.title}</h3>
                    <span style={{ fontSize: '12px', color: '#94a3b8' }}>{pkg.count}</span>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: 12 }}>
                    {Object.entries(pkg.status_summary).map(([s, c]) => (
                      <span key={s} style={{ fontSize: '11px', color: '#94a3b8' }}>
                        {statusBadge(s)} {c}
                      </span>
                    ))}
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    Package: {packageBadge(pkg.package_status || 'needs_review')}
                  </div>
                  <button
                    onClick={() => openPackage(pkg.package_id)}
                    style={{ ...STYLES.backBtn, marginBottom: 0, fontSize: '12px' }}
                  >
                    View assets →
                  </button>
                </div>
              ))}
            </div>
          </>
        )}

        {view === 'package' && (
          <>
            <button onClick={goBack} style={STYLES.backBtn}>← Back to packages</button>
            {loading ? <LoadingState /> : error ? <ErrorState message={error} /> : packageDetail && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <h1 style={{ ...STYLES.header, marginBottom: 0 }}>
                    📂 {packageDetail.package_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </h1>
                  <span style={{ fontSize: '14px', color: '#94a3b8' }}>{packageDetail.count} assets</span>
                </div>

                <div style={STYLES.card}>
                  <h4 style={{ margin: '0 0 8px', color: '#94a3b8', fontSize: '13px' }}>Package Status</h4>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: 8 }}>
                    {(['needs_review', 'approved_for_manual_use_only', 'needs_revision', 'blocked', 'ready_for_beta_manual_outreach'] as PackageStatus[]).map(s => (
                      <button
                        key={s}
                        onClick={() => { setFeedback(''); handlePackageStatus(s); }}
                        disabled={pkgStatusSaving}
                        style={{
                          ...STYLES.pillBtn(PACKAGE_STATUS_COLORS[s] || '#6b7280'),
                          opacity: (packageDetail.meta?.status || 'needs_review') === s ? 1 : 0.5,
                        }}
                      >
                        {s.replace(/_/g, ' ')}
                      </button>
                    ))}
                  </div>
                  {packageDetail.meta?.note && (
                    <p style={{ fontSize: '12px', color: '#94a3b8', margin: '4px 0 0', fontStyle: 'italic' }}>
                      Note: {packageDetail.meta.note}
                    </p>
                  )}
                  {packageDetail.meta?.updated_at && (
                    <p style={{ fontSize: '11px', color: '#64748b', margin: '4px 0 0' }}>
                      Updated: {formatDate(packageDetail.meta.updated_at)}
                    </p>
                  )}
                </div>

                {saveMsg && (
                  <p style={{ fontSize: '13px', color: saveMsg.startsWith('✓') ? '#22c55e' : '#f87171', margin: '8px 0' }}>
                    {saveMsg}
                  </p>
                )}

                <div style={{ marginTop: 16 }}>
                  {packageDetail.assets.map(a => (
                    <div key={a.asset_id} style={STYLES.card}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: '14px', color: '#f1f5f9' }}>{a.title}</span>
                        {statusBadge(a.status)}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b', marginBottom: 8 }}>
                        ID: {a.asset_id} · {a.asset_type}
                      </div>
                      {a.feedback && a.feedback.length > 0 && (
                        <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: 8 }}>
                          <strong>Last feedback:</strong> {a.feedback[a.feedback.length - 1].note}
                        </div>
                      )}
                      <button
                        onClick={() => openAsset(a)}
                        style={{ ...STYLES.backBtn, marginBottom: 0, fontSize: '12px', padding: '4px 12px' }}
                      >
                        Review →
                      </button>
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}

        {view === 'asset' && (
          <>
            <button onClick={goBack} style={STYLES.backBtn}>← Back to package</button>
            {loading ? <LoadingState /> : error ? <ErrorState message={error} /> : currentAsset && (
              <>
                <h1 style={STYLES.header}>{currentAsset.title}</h1>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: 16 }}>
                  {statusBadge(currentAsset.status)}
                  <span style={{ fontSize: '12px', color: '#64748b' }}>ID: {currentAsset.asset_id}</span>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>Type: {currentAsset.asset_type}</span>
                </div>

                <div style={STYLES.card}>
                  <h4 style={{ margin: '0 0 12px', color: '#94a3b8', fontSize: '13px' }}>Actions</h4>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: 12 }}>
                    <button onClick={() => handleReview('approved')} disabled={saving} style={STYLES.pillBtn('#22c55e')}>
                      ✅ Approve
                    </button>
                    <button onClick={() => handleReview('approved_with_notes')} disabled={saving} style={STYLES.pillBtn('#16a34a')}>
                      📝 Approve with notes
                    </button>
                    <button onClick={() => handleReview('revise')} disabled={saving} style={STYLES.pillBtn('#ef4444')}>
                      🔄 Request revision
                    </button>
                    <button onClick={() => handleReview('needs_review')} disabled={saving} style={STYLES.pillBtn('#f59e0b')}>
                      🔍 Needs review
                    </button>
                  </div>

                  <h4 style={{ margin: '0 0 8px', color: '#94a3b8', fontSize: '13px' }}>Feedback</h4>
                  <textarea
                    value={feedback}
                    onChange={e => setFeedback(e.target.value)}
                    placeholder="Enter feedback for this asset..."
                    style={STYLES.textarea}
                    disabled={saving}
                  />

                  {saveMsg && (
                    <p style={{ fontSize: '13px', color: saveMsg.startsWith('✓') ? '#22c55e' : '#f87171', margin: '8px 0' }}>
                      {saveMsg}
                    </p>
                  )}
                </div>

                <div style={STYLES.card}>
                  <h4 style={{ margin: '0 0 8px', color: '#94a3b8', fontSize: '13px' }}>Details</h4>
                  <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                    <tbody>
                      {[
                        ['Created', formatDate(currentAsset.created_at)],
                        ['Updated', formatDate(currentAsset.updated_at)],
                        ['File path', currentAsset.file_path],
                        ['Showroom path', currentAsset.showroom_path],
                        ['Lesson memory', currentAsset.lesson_memory],
                      ].map(([k, v]) => (
                        <tr key={k}>
                          <td style={{ padding: '4px 8px', color: '#64748b', width: '120px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{k}</td>
                          <td style={{ padding: '4px 8px', color: '#e2e8f0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{v}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {currentAsset.feedback && currentAsset.feedback.length > 0 && (
                  <div style={STYLES.card}>
                    <h4 style={{ margin: '0 0 8px', color: '#94a3b8', fontSize: '13px' }}>
                      Feedback History ({currentAsset.feedback.length})
                    </h4>
                    {currentAsset.feedback.map((fb, i) => (
                      <div key={i} style={{
                        padding: '8px 0',
                        borderBottom: i < currentAsset.feedback.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
                      }}>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: 4 }}>
                          {statusBadge(fb.status)}
                          <span style={{ fontSize: '11px', color: '#64748b' }}>{formatDate(fb.at)}</span>
                        </div>
                        <p style={{ margin: 0, fontSize: '13px', color: '#cbd5e1' }}>{fb.note}</p>
                      </div>
                    ))}
                  </div>
                )}

                {currentAsset.preview && (
                  <div style={STYLES.card}>
                    <h4 style={{ margin: '0 0 8px', color: '#94a3b8', fontSize: '13px' }}>Preview</h4>
                    <pre style={{
                      fontSize: '12px',
                      color: '#cbd5e1',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      margin: 0,
                      fontFamily: "'SF Mono', 'Fira Code', monospace",
                      lineHeight: 1.5,
                      maxHeight: '400px',
                      overflowY: 'auto',
                      background: 'rgba(0,0,0,0.2)',
                      padding: '12px',
                      borderRadius: '8px',
                    }}>
                      {currentAsset.preview}
                    </pre>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
