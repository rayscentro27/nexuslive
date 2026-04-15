import React, { useEffect, useState, useMemo } from 'react';
import { FileText, Search, Filter, Download, Eye, CheckCircle2, Clock, AlertCircle, FolderOpen, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { getAllDocuments, updateDocumentStatus, Document } from '../../lib/db';

export function AdminDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    getAllDocuments().then(({ data }) => {
      setDocuments(data);
      setLoading(false);
    });
  }, []);

  const handleVerify = async (doc: Document) => {
    const newStatus = doc.status === 'verified' ? 'pending' : 'verified';
    const { data } = await updateDocumentStatus(doc.id, newStatus as any);
    if (data) setDocuments(prev => prev.map(d => d.id === doc.id ? data : d));
  };

  const filtered = useMemo(() => {
    return documents.filter(d => {
      const matchSearch = !search || d.filename.toLowerCase().includes(search.toLowerCase()) || d.category.toLowerCase().includes(search.toLowerCase());
      const matchStatus = statusFilter === 'all' || d.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [documents, search, statusFilter]);

  const total = documents.length;
  const verified = documents.filter(d => d.status === 'verified').length;
  const pending = documents.filter(d => d.status === 'pending').length;
  const attention = documents.filter(d => d.status === 'attention').length;

  const statusBadge = (status: string) => {
    switch (status) {
      case 'verified': return 'bg-green-50 text-green-600';
      case 'attention': return 'bg-red-50 text-red-600';
      default: return 'bg-amber-50 text-amber-600';
    }
  };

  const statusLabel = (status: string) => {
    if (status === 'attention') return 'Needs Attention';
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Document Management</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Review, verify, and manage all client-uploaded documentation.</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Total Files', value: total, icon: FolderOpen, color: 'blue' },
          { label: 'Verified', value: verified, icon: CheckCircle2, color: 'green' },
          { label: 'Pending Review', value: pending, icon: Clock, color: 'amber' },
          { label: 'Needs Attention', value: attention, icon: AlertCircle, color: 'red' },
        ].map((stat, i) => (
          <div key={i} className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm">
            <div className="flex items-center gap-4">
              <div className={cn(
                "w-12 h-12 rounded-2xl flex items-center justify-center",
                stat.color === 'blue' ? "bg-blue-50 text-[#5B7CFA]" :
                stat.color === 'green' ? "bg-green-50 text-green-600" :
                stat.color === 'red' ? "bg-red-50 text-red-600" :
                "bg-amber-50 text-amber-600"
              )}>
                <stat.icon className="w-6 h-6" />
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</p>
                <h3 className="text-xl font-black text-[#1A2244] mt-0.5">
                  {loading ? '—' : stat.value}
                </h3>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Documents Table */}
      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <FileText className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">All Documents</h3>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search documents..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-xl py-1.5 pl-9 pr-4 text-[10px] font-bold text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 w-48"
              />
            </div>
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-[10px] font-bold text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="verified">Verified</option>
              <option value="attention">Needs Attention</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-slate-300 animate-spin" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-50">
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">File Name</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Category</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Uploaded By</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Date</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Status</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filtered.length > 0 ? filtered.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/50 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-[#1A2244]">
                          <FileText className="w-4 h-4" />
                        </div>
                        <span className="text-xs font-bold text-[#1A2244] max-w-[200px] truncate">{doc.filename}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{doc.category}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{doc.uploaded_by}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-bold text-slate-400">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn("px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest", statusBadge(doc.status))}>
                        {statusLabel(doc.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <a
                          href={doc.file_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 text-slate-400 hover:text-[#5B7CFA] transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                        </a>
                        <a
                          href={doc.file_url}
                          download
                          className="p-2 text-slate-400 hover:text-[#5B7CFA] transition-colors"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                        <button
                          onClick={() => handleVerify(doc)}
                          className={cn(
                            "px-3 py-1.5 text-[9px] font-black uppercase tracking-widest rounded-lg transition-all",
                            doc.status === 'verified'
                              ? "bg-slate-100 text-slate-500 hover:bg-slate-200"
                              : "bg-green-50 text-green-600 hover:bg-green-500 hover:text-white"
                          )}
                        >
                          {doc.status === 'verified' ? 'Unverify' : 'Verify'}
                        </button>
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                        {search || statusFilter !== 'all' ? 'No documents match your filters' : 'No documents uploaded yet'}
                      </p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <div className="p-6 border-t border-slate-100 bg-slate-50/30">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                Showing {filtered.length} of {total} documents
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
