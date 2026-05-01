import React, { useEffect, useRef, useState } from 'react';
import {
  Plus,
  Search,
  FileText,
  Briefcase,
  Wallet,
  Upload,
  Eye,
  Trash2,
  Download,
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  FolderOpen,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from './AuthProvider';
import { getDocuments, Document } from '../lib/db';
import { supabase } from '../lib/supabase';

const categoryConfig = [
  { id: 'all',      label: 'All',             icon: FileText },
  { id: 'credit',   label: 'Credit Reports',  icon: FileText },
  { id: 'business', label: 'Business Docs',   icon: Briefcase },
  { id: 'tax',      label: 'Tax Returns',     icon: Wallet },
  { id: 'bank',     label: 'Bank Statements', icon: Wallet },
  { id: 'funding',  label: 'Agreements',      icon: FileText },
];

const statusBadge = {
  verified:  { label: 'Verified',  icon: CheckCircle2, color: '#22c55e' },
  pending:   { label: 'Pending',   icon: Clock,        color: '#f59e0b' },
  attention: { label: 'Attention', icon: AlertCircle,  color: '#ef4444' },
};

function formatBytes(bytes: number | null) {
  if (!bytes) return '—';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function timeAgo(ts: string) {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const requiredDocs = [
  { label: 'Business Bank Statements (3 mo.)', urgent: true },
  { label: 'EIN / Formation Documents', urgent: true },
  { label: 'Business Tax Return (2023)', urgent: false },
  { label: "Driver's License / ID", urgent: false },
];

export function Documents() {
  const { user } = useAuth();
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!user) return;
    (async () => {
      const { data } = await getDocuments(user.id);
      setDocs(data);
      setLoading(false);
    })();
  }, [user]);

  const handleUpload = async (files: FileList | null) => {
    if (!files || !user) return;
    setUploading(true);

    for (const file of Array.from(files)) {
      const path = `${user.id}/${Date.now()}_${file.name}`;
      const { data: storageData, error: storageError } = await supabase.storage
        .from('documents')
        .upload(path, file);

      if (storageError) {
        console.error('Upload error:', storageError);
        continue;
      }

      const { data: { publicUrl } } = supabase.storage
        .from('documents')
        .getPublicUrl(path);

      const { error: dbError } = await supabase
        .from('documents')
        .insert({
          user_id: user.id,
          filename: file.name,
          file_url: publicUrl,
          file_size: file.size,
          mime_type: file.type,
          category: 'general',
          status: 'pending',
          uploaded_by: 'client',
        });

      if (!dbError) {
        const { data } = await getDocuments(user.id);
        setDocs(data);
      }
    }

    setUploading(false);
  };

  const handleDelete = async (docId: string) => {
    await supabase.from('documents').delete().eq('id', docId);
    setDocs(prev => prev.filter(d => d.id !== docId));
  };

  const filtered = docs.filter(d => {
    if (search && !d.filename.toLowerCase().includes(search.toLowerCase())) return false;
    if (activeCategory && activeCategory !== 'all' && d.category !== activeCategory) return false;
    return true;
  });

  const categoryCounts = (catId: string) => ({
    count: docs.filter(d => d.category === catId).length,
    verified: docs.filter(d => d.category === catId && d.status === 'verified').length,
  });

  const attentionCount = docs.filter(d => d.status === 'attention').length;
  const verifiedCount = docs.filter(d => d.status === 'verified').length;
  const reviewCount = docs.filter(d => d.status === 'pending').length;

  // Storage estimate: sum file sizes in bytes → convert to GB
  const totalBytes = docs.reduce((sum, d) => sum + (d.file_size ?? 0), 0);
  const usedGB = parseFloat((totalBytes / (1024 ** 3)).toFixed(2));
  const totalGB = 10;
  const storageUsedPct = Math.min((usedGB / totalGB) * 100, 100);

  return (
    <div className="p-6 max-w-6xl mx-auto h-full flex flex-col overflow-y-auto no-scrollbar" style={{ gap: 24 }}>
      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexShrink: 0 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Documents</h1>
          <p style={{ fontSize: 13, color: '#8b8fa8', marginTop: 4 }}>
            {docs.length} uploaded{attentionCount > 0 ? ` · ${attentionCount} need attention` : ''}
          </p>
        </div>
        <button
          className="nexus-button-primary"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 18px', fontSize: 13, opacity: uploading ? 0.6 : 1 }}
        >
          {uploading ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
          Upload Document
        </button>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
        className="hidden"
        onChange={e => handleUpload(e.target.files)}
      />

      {/* ── Stat Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, flexShrink: 0 }}>
        {[
          { label: 'Total Documents', value: docs.length, iconBg: '#eef0fd', iconColor: '#3d5af1', Icon: FileText },
          { label: 'Verified', value: verifiedCount, iconBg: '#f0fdf4', iconColor: '#22c55e', Icon: CheckCircle2 },
          { label: 'Under Review', value: reviewCount, iconBg: '#fff7ed', iconColor: '#f59e0b', Icon: Clock },
          { label: 'Need Attention', value: attentionCount, iconBg: '#fef2f2', iconColor: '#ef4444', Icon: AlertCircle },
        ].map(({ label, value, iconBg, iconColor, Icon }) => (
          <div key={label} className="glass-card" style={{ padding: '18px 16px', display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ width: 42, height: 42, borderRadius: 12, background: iconBg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Icon size={18} color={iconColor} />
            </div>
            <div>
              <div style={{ fontSize: 22, fontWeight: 800, color: '#1a1c3a', lineHeight: 1 }}>{value}</div>
              <div style={{ fontSize: 12, color: '#8b8fa8', marginTop: 3 }}>{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Two-Column Body ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: 20, flex: 1, minHeight: 0 }}>
        {/* Left main column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Drag-and-drop upload zone */}
          <div
            className="glass-card"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); handleUpload(e.dataTransfer.files); }}
            style={{
              padding: 32,
              border: '2px dashed #e8e9f2',
              borderRadius: 14,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              gap: 12,
              cursor: 'pointer',
              transition: 'border-color 0.15s, background 0.15s',
              background: '#fafbff',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = '#3d5af1'; (e.currentTarget as HTMLElement).style.background = '#eef0fd'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = '#e8e9f2'; (e.currentTarget as HTMLElement).style.background = '#fafbff'; }}
          >
            <div style={{ fontSize: 36 }}>📂</div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a' }}>Drag & drop files here</div>
              <div style={{ fontSize: 12, color: '#8b8fa8', marginTop: 4 }}>PDF, JPG, PNG, DOC up to 50MB each</div>
            </div>
            <button
              className="nexus-button-primary"
              style={{ fontSize: 13, padding: '8px 20px' }}
              onClick={e => { e.stopPropagation(); fileInputRef.current?.click(); }}
            >
              {uploading ? 'Uploading…' : 'Browse Files'}
            </button>
          </div>

          {/* Search bar */}
          <div style={{ position: 'relative', flexShrink: 0 }}>
            <Search size={15} color="#8b8fa8" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search documents..."
              style={{
                width: '100%',
                background: '#fff',
                border: '1px solid #e8e9f2',
                borderRadius: 10,
                padding: '10px 12px 10px 36px',
                fontSize: 13,
                color: '#1a1c3a',
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Category pill tabs */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', flexShrink: 0 }}>
            {categoryConfig.map(cat => {
              const isActive = (cat.id === 'all' && !activeCategory) || activeCategory === cat.id;
              const count = cat.id === 'all' ? docs.length : categoryCounts(cat.id).count;
              return (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id === 'all' ? null : (isActive ? null : cat.id))}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '6px 14px',
                    borderRadius: 20,
                    fontSize: 13,
                    fontWeight: 600,
                    border: '1px solid',
                    borderColor: isActive ? '#3d5af1' : '#e8e9f2',
                    background: isActive ? '#eef0fd' : '#fff',
                    color: isActive ? '#3d5af1' : '#8b8fa8',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  {cat.label}
                  <span style={{
                    background: isActive ? '#3d5af1' : '#eaebf6',
                    color: isActive ? '#fff' : '#8b8fa8',
                    borderRadius: 10,
                    padding: '0 6px',
                    fontSize: 11,
                    fontWeight: 700,
                  }}>{count}</span>
                </button>
              );
            })}
          </div>

          {/* Document table card */}
          <div className="glass-card" style={{ padding: 20, flex: 1 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1c3a', marginBottom: 14 }}>
              {activeCategory
                ? categoryConfig.find(c => c.id === activeCategory)?.label ?? 'Documents'
                : 'All Documents'}
            </h3>

            {/* Table header */}
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 0.8fr 0.7fr 0.8fr 80px', gap: 8, padding: '8px 12px', background: '#eaebf6', borderRadius: 8, marginBottom: 8 }}>
              {['Document', 'Category', 'Date', 'Size', 'Status', ''].map((col, i) => (
                <span key={i} style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{col}</span>
              ))}
            </div>

            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 48 }}>
                <Loader2 size={24} color="#8b8fa8" className="animate-spin" />
              </div>
            ) : filtered.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: '#8b8fa8' }}>
                <FileText size={32} style={{ margin: '0 auto 10px', opacity: 0.4 }} />
                <p style={{ fontSize: 14, fontWeight: 600 }}>No documents yet</p>
                <p style={{ fontSize: 12, marginTop: 4 }}>Upload your first document to get started</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {filtered.map((doc) => {
                  const badge = statusBadge[doc.status as keyof typeof statusBadge] ?? statusBadge.pending;
                  const BadgeIcon = badge.icon;
                  return (
                    <div
                      key={doc.id}
                      style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 0.8fr 0.7fr 0.8fr 80px', gap: 8, padding: '10px 12px', borderRadius: 8, alignItems: 'center', transition: 'background 0.15s' }}
                      onMouseEnter={e => (e.currentTarget.style.background = '#eaebf6')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                      {/* Document name + icon */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                        <div style={{ width: 32, height: 32, borderRadius: 8, background: '#eef0fd', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <FileText size={15} color="#3d5af1" />
                        </div>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1c3a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.filename}</span>
                      </div>

                      <span style={{ fontSize: 12, color: '#8b8fa8', textTransform: 'capitalize' }}>{doc.category}</span>
                      <span style={{ fontSize: 12, color: '#8b8fa8' }}>{timeAgo(doc.created_at)}</span>
                      <span style={{ fontSize: 12, color: '#8b8fa8' }}>{formatBytes(doc.file_size)}</span>

                      {/* Status badge */}
                      <span style={{ background: badge.color + '18', color: badge.color, borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <BadgeIcon size={11} /> {badge.label}
                      </span>

                      {/* Action buttons */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <a href={doc.file_url} target="_blank" rel="noopener noreferrer">
                          <button style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 5, borderRadius: 6, color: '#8b8fa8', transition: 'color 0.15s' }}
                            onMouseEnter={e => ((e.currentTarget as HTMLElement).style.color = '#3d5af1')}
                            onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = '#8b8fa8')}
                          >
                            <Eye size={14} />
                          </button>
                        </a>
                        <a href={doc.file_url} download={doc.filename}>
                          <button style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 5, borderRadius: 6, color: '#8b8fa8', transition: 'color 0.15s' }}
                            onMouseEnter={e => ((e.currentTarget as HTMLElement).style.color = '#3d5af1')}
                            onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = '#8b8fa8')}
                          >
                            <Download size={14} />
                          </button>
                        </a>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 5, borderRadius: 6, color: '#8b8fa8', transition: 'color 0.15s' }}
                          onMouseEnter={e => ((e.currentTarget as HTMLElement).style.color = '#ef4444')}
                          onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = '#8b8fa8')}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* ── Right Sidebar ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Documents Required */}
          <div className="glass-card" style={{ padding: 18 }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', marginBottom: 14 }}>Documents Required</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {requiredDocs.map(({ label, urgent }) => (
                <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '10px 12px', borderRadius: 10, background: urgent ? '#fef2f2' : '#eaebf6', border: `1px solid ${urgent ? '#ef444422' : '#e8e9f2'}` }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                    <AlertCircle size={14} color={urgent ? '#ef4444' : '#8b8fa8'} style={{ flexShrink: 0, marginTop: 1 }} />
                    <span style={{ fontSize: 12, fontWeight: 600, color: urgent ? '#ef4444' : '#1a1c3a', lineHeight: 1.4 }}>{label}</span>
                  </div>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    style={{ background: 'none', border: `1px solid ${urgent ? '#ef4444' : '#e8e9f2'}`, borderRadius: 7, padding: '4px 10px', fontSize: 11, fontWeight: 600, color: urgent ? '#ef4444' : '#8b8fa8', cursor: 'pointer', alignSelf: 'flex-start', transition: 'all 0.15s' }}
                  >
                    Upload Now
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Storage Used */}
          <div className="glass-card" style={{ padding: 18 }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', marginBottom: 6 }}>Storage Used</h3>
            <p style={{ fontSize: 12, color: '#8b8fa8', marginBottom: 10 }}>{usedGB} GB used / {totalGB} GB total</p>
            <div style={{ height: 6, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ width: `${storageUsedPct}%`, height: '100%', background: storageUsedPct > 80 ? '#ef4444' : '#3d5af1', borderRadius: 10 }} />
            </div>
            <p style={{ fontSize: 11, color: '#8b8fa8', marginTop: 6 }}>{(totalGB - usedGB).toFixed(2)} GB remaining</p>
          </div>

          {/* Pro Tip */}
          <div style={{ padding: 18, borderRadius: 14, background: 'linear-gradient(135deg, #3d5af1, #6b82f5)', color: '#fff' }}>
            <div style={{ fontSize: 18, marginBottom: 8 }}>💡</div>
            <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Pro Tip</h3>
            <p style={{ fontSize: 12, lineHeight: 1.6, opacity: 0.9 }}>
              Upload bank statements from the last 3 months to unlock lenders with higher approval rates. Recent, consistent revenue data boosts your funding range.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
