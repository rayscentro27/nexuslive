import React from 'react';
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
  Clock
} from 'lucide-react';
import { cn } from '../lib/utils';

const categories = [
  { id: 'credit', label: 'Credit Documents', icon: FileText, count: 3, verified: 1, pending: 1 },
  { id: 'business', label: 'Business Documents', icon: Briefcase, count: 2, verified: 2, pending: 0 },
  { id: 'funding', label: 'Funding Documents', icon: Wallet, count: 3, verified: 2, pending: 1 },
];

const recentUploads = [
  { id: 1, name: 'Experian-Report.pdf', size: '1.3 MB', time: '2 days ago', status: 'verified', type: 'credit' },
  { id: 2, name: 'Articles Of Incorporation.pdf', size: '2.4 MB', time: '4 hours ago', status: 'pending', type: 'business' },
  { id: 3, name: 'Business-ID.pdf', size: '0.8 MB', time: '5 days ago', status: 'attention', type: 'business' },
];

export function Documents() {
  return (
    <div className="p-4 space-y-4 max-w-7xl mx-auto h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="flex items-center justify-between shrink-0">
        <div className="space-y-0.5">
          <h2 className="text-xl font-black text-[#1A2244]">Documents</h2>
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">8 uploaded • 2 need attention</p>
        </div>
        <button className="bg-[#5B7CFA] text-white px-5 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Upload
        </button>
      </div>

      <div className="flex-1 space-y-4">
        {/* Categories Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 shrink-0">
          {categories.map((cat) => {
            const Icon = cat.icon;
            return (
              <div key={cat.id} className="glass-card p-4 flex flex-col items-center text-center space-y-3 group hover:border-[#5B7CFA]/30 transition-all">
                <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm">
                  <Icon className="w-5 h-5 text-[#5B7CFA]" />
                </div>
                <div className="space-y-0.5">
                  <h3 className="text-xs font-black text-[#1A2244]">{cat.label}</h3>
                  <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">{cat.count} Docs</p>
                </div>
                <div className="w-full space-y-1">
                  <div className="flex items-center justify-center gap-1.5 text-[7px] font-black text-green-600 uppercase tracking-widest">
                    <CheckCircle2 className="w-2.5 h-2.5" />
                    {cat.verified} Verified
                  </div>
                </div>
                <button className="w-full py-1.5 bg-slate-50 border border-slate-100 text-[#1A2244] text-[9px] font-black uppercase tracking-widest rounded-lg hover:bg-slate-100 transition-all">View</button>
              </div>
            );
          })}
        </div>

        {/* Recent Uploads */}
        <div className="space-y-4 shrink-0">
          <h3 className="text-lg font-bold text-[#1A2244]">Recent Uploads</h3>
          <div className="space-y-2">
            {recentUploads.map((doc) => (
              <div key={doc.id} className="glass-card p-3 flex items-center gap-4 group hover:border-[#5B7CFA]/10 transition-all">
                <div className={cn(
                  "w-10 h-10 rounded-lg flex items-center justify-center shrink-0 shadow-sm",
                  doc.type === 'credit' ? "bg-blue-50 border border-blue-100" : "bg-amber-50 border border-amber-100"
                )}>
                  <FileText className={cn("w-5 h-5", doc.type === 'credit' ? "text-[#5B7CFA]" : "text-amber-600")} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-[#1A2244] group-hover:text-[#5B7CFA] transition-colors truncate">{doc.name}</p>
                  <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">Uploaded {doc.time} • {doc.size}</p>
                </div>
                
                <div className="flex items-center gap-4">
                  {doc.status === 'verified' && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-green-50 text-green-600 text-[8px] font-bold uppercase tracking-widest">
                      <CheckCircle2 className="w-3 h-3" /> Verified
                    </span>
                  )}
                  {doc.status === 'pending' && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-50 text-amber-600 text-[8px] font-bold uppercase tracking-widest">
                      <Clock className="w-3 h-3" /> Pending
                    </span>
                  )}
                  {doc.status === 'attention' && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-red-50 text-red-600 text-[8px] font-bold uppercase tracking-widest">
                      <AlertCircle className="w-3 h-3" /> Attention
                    </span>
                  )}
                  
                  <div className="flex items-center gap-1.5 border-l border-slate-100 pl-4">
                    <button className="p-1.5 text-slate-400 hover:text-[#5B7CFA] hover:bg-slate-50 rounded-lg transition-all"><Eye className="w-3.5 h-3.5" /></button>
                    <button className="p-1.5 text-slate-400 hover:text-[#5B7CFA] hover:bg-slate-50 rounded-lg transition-all"><Download className="w-3.5 h-3.5" /></button>
                    <button className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Upload Area */}
        <div className="glass-card p-8 border-2 border-dashed border-slate-200 bg-slate-50/50 flex flex-col items-center justify-center text-center space-y-4 group hover:border-[#5B7CFA]/30 hover:bg-white transition-all cursor-pointer shadow-inner shrink-0">
          <div className="w-16 h-16 rounded-2xl bg-white border border-slate-100 flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm">
            <Upload className="w-8 h-8 text-[#5B7CFA]" />
          </div>
          <div className="space-y-1">
            <h3 className="text-xl font-black text-[#1A2244]">Drag & drop files here</h3>
            <p className="text-xs text-slate-500 font-medium">or click to browse your computer</p>
          </div>
          <div className="flex gap-3">
            <span className="px-3 py-1 rounded-lg bg-white border border-slate-100 text-[8px] font-bold text-slate-400 uppercase tracking-widest shadow-sm">PDF</span>
            <span className="px-3 py-1 rounded-lg bg-white border border-slate-100 text-[8px] font-bold text-slate-400 uppercase tracking-widest shadow-sm">JPG</span>
            <span className="px-3 py-1 rounded-lg bg-white border border-slate-100 text-[8px] font-bold text-slate-400 uppercase tracking-widest shadow-sm">PNG</span>
          </div>
        </div>
      </div>
    </div>
  );
}
