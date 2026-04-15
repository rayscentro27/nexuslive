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
  Loader2
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from './AuthProvider';
import { getDocuments, Document } from '../lib/db';
import { supabase } from '../lib/supabase';

const categoryConfig = [
  { id: 'credit',   label: 'Credit Documents',   icon: FileText },
  { id: 'business', label: 'Business Documents',  icon: Briefcase },
  { id: 'funding',  label: 'Funding Documents',   icon: Wallet },
];

const statusBadge = {
  verified:  { label: 'Verified',  icon: CheckCircle2, cls: 'bg-green-50 text-green-600 border-green-100' },
  pending:   { label: 'Pending',   icon: Clock,        cls: 'bg-amber-50 text-amber-600 border-amber-100' },
  attention: { label: 'Attention', icon: AlertCircle,  cls: 'bg-red-50 text-red-600 border-red-100' },
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
    if (activeCategory && d.category !== activeCategory) return false;
    return true;
  });

  const categoryCounts = (catId: string) => ({
    count: docs.filter(d => d.category === catId).length,
    verified: docs.filter(d => d.category === catId && d.status === 'verified').length,
  });

  const attentionCount = docs.filter(d => d.status === 'attention').length;

  return (
    <div className="p-4 space-y-4 max-w-7xl mx-auto h-full flex flex-col overflow-y-auto no-scrollbar">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="space-y-0.5">
          <h2 className="text-xl font-black text-[#1A2244]">Documents</h2>
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
            {docs.length} uploaded{attentionCount > 0 ? ` • ${attentionCount} need attention` : ''}
          </p>
        </div>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="bg-[#5B7CFA] text-white px-5 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2 disabled:opacity-60"
        >
          {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Upload
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
          className="hidden"
          onChange={e => handleUpload(e.target.files)}
        />
      </div>

      <div className="flex-1 space-y-4">
        {/* Search */}
        <div className="relative shrink-0">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search documents..."
            className="w-full bg-white border border-slate-100 rounded-xl py-2.5 pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 transition-all shadow-sm"
          />
        </div>

        {/* Categories Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 shrink-0">
          {categoryConfig.map((cat) => {
            const Icon = cat.icon;
            const { count, verified } = categoryCounts(cat.id);
            const isActive = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(isActive ? null : cat.id)}
                className={cn(
                  "glass-card p-4 flex flex-col items-center text-center space-y-3 group hover:border-[#5B7CFA]/30 transition-all text-left",
                  isActive && "border-[#5B7CFA]/40 bg-blue-50/20"
                )}
              >
                <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm">
                  <Icon className="w-5 h-5 text-[#5B7CFA]" />
                </div>
                <div className="space-y-0.5">
                  <h3 className="text-xs font-black text-[#1A2244]">{cat.label}</h3>
                  <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">{count} Docs</p>
                </div>
                {count > 0 && (
                  <div className="flex items-center justify-center gap-1.5 text-[7px] font-black text-green-600 uppercase tracking-widest">
                    <CheckCircle2 className="w-2.5 h-2.5" />
                    {verified} Verified
                  </div>
                )}
              </button>
            );
          })}
        </div>

        {/* Document List */}
        <div className="space-y-4 shrink-0">
          <h3 className="text-lg font-bold text-[#1A2244]">
            {activeCategory
              ? categoryConfig.find(c => c.id === activeCategory)?.label
              : 'All Documents'}
          </h3>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-[#5B7CFA]" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="glass-card p-8 text-center text-slate-400 space-y-2">
              <FileText className="w-8 h-8 mx-auto" />
              <p className="text-sm font-bold">No documents yet</p>
              <p className="text-xs">Upload your first document to get started</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((doc) => {
                const badge = statusBadge[doc.status as keyof typeof statusBadge] ?? statusBadge.pending;
                const BadgeIcon = badge.icon;
                return (
                  <div key={doc.id} className="glass-card p-3 flex items-center gap-4 group hover:border-[#5B7CFA]/10 transition-all">
                    <div className={cn(
                      "w-10 h-10 rounded-lg flex items-center justify-center shrink-0 shadow-sm",
                      doc.category === 'credit' ? "bg-blue-50 border border-blue-100" : "bg-amber-50 border border-amber-100"
                    )}>
                      <FileText className={cn("w-5 h-5", doc.category === 'credit' ? "text-[#5B7CFA]" : "text-amber-600")} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold text-[#1A2244] group-hover:text-[#5B7CFA] transition-colors truncate">{doc.filename}</p>
                      <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">
                        Uploaded {timeAgo(doc.created_at)} • {formatBytes(doc.file_size)}
                      </p>
                    </div>

                    <div className="flex items-center gap-4">
                      <span className={cn(
                        "flex items-center gap-1 px-2 py-0.5 rounded-md border text-[8px] font-bold uppercase tracking-widest",
                        badge.cls
                      )}>
                        <BadgeIcon className="w-3 h-3" /> {badge.label}
                      </span>

                      <div className="flex items-center gap-1.5 border-l border-slate-100 pl-4">
                        <a href={doc.file_url} target="_blank" rel="noopener noreferrer">
                          <button className="p-1.5 text-slate-400 hover:text-[#5B7CFA] hover:bg-slate-50 rounded-lg transition-all">
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        </a>
                        <a href={doc.file_url} download={doc.filename}>
                          <button className="p-1.5 text-slate-400 hover:text-[#5B7CFA] hover:bg-slate-50 rounded-lg transition-all">
                            <Download className="w-3.5 h-3.5" />
                          </button>
                        </a>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Upload Area */}
        <div
          className="glass-card p-8 border-2 border-dashed border-slate-200 bg-slate-50/50 flex flex-col items-center justify-center text-center space-y-4 group hover:border-[#5B7CFA]/30 hover:bg-white transition-all cursor-pointer shadow-inner shrink-0"
          onClick={() => fileInputRef.current?.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => { e.preventDefault(); handleUpload(e.dataTransfer.files); }}
        >
          <div className="w-16 h-16 rounded-2xl bg-white border border-slate-100 flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm">
            {uploading
              ? <Loader2 className="w-8 h-8 text-[#5B7CFA] animate-spin" />
              : <Upload className="w-8 h-8 text-[#5B7CFA]" />
            }
          </div>
          <div className="space-y-1">
            <h3 className="text-xl font-black text-[#1A2244]">Drag & drop files here</h3>
            <p className="text-xs text-slate-500 font-medium">or click to browse your computer</p>
          </div>
          <div className="flex gap-3">
            {['PDF', 'JPG', 'PNG', 'DOC'].map(ext => (
              <span key={ext} className="px-3 py-1 rounded-lg bg-white border border-slate-100 text-[8px] font-bold text-slate-400 uppercase tracking-widest shadow-sm">{ext}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
