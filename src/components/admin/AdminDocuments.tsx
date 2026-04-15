import React from 'react';
import { 
  FileText, 
  Search, 
  Filter, 
  Download, 
  Eye, 
  Trash2, 
  Upload, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  FolderOpen
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AdminDocuments() {
  const documents = [
    { id: 1, name: 'Articles of Incorporation.pdf', client: 'Robert Fox', type: 'Legal', date: '2024-03-15', status: 'Verified' },
    { id: 2, name: 'Tax Return 2023.pdf', client: 'Marcus Chen', type: 'Financial', date: '2024-03-14', status: 'Pending Review' },
    { id: 3, name: 'Business Plan.docx', client: 'Elena Rodriguez', type: 'Strategy', date: '2024-03-12', status: 'Verified' },
    { id: 4, name: 'Credit Report.pdf', client: 'Sarah Jenkins', type: 'Credit', date: '2024-03-10', status: 'Rejected' },
  ];

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Document Management</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Review, verify, and manage all client-uploaded documentation.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-6 py-2 rounded-xl bg-white border border-slate-200 text-[#1A2244] text-xs font-black uppercase tracking-widest hover:bg-slate-50 transition-all shadow-sm">
            Folder Settings
          </button>
          <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
            <Upload className="w-4 h-4" />
            Upload File
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Total Files', value: '1,248', icon: FolderOpen, color: 'blue' },
          { label: 'Verified', value: '982', icon: CheckCircle2, color: 'green' },
          { label: 'Pending Review', value: '42', icon: Clock, color: 'amber' },
          { label: 'Rejected', value: '12', icon: AlertCircle, color: 'red' },
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
                <h3 className="text-xl font-black text-[#1A2244] mt-0.5">{stat.value}</h3>
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
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Recent Uploads</h3>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search documents..." 
                className="bg-slate-50 border border-slate-200 rounded-xl py-1.5 pl-9 pr-4 text-[10px] font-bold text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 w-48"
              />
            </div>
            <button className="p-2 text-slate-400 hover:text-[#1A2244] transition-colors">
              <Filter className="w-5 h-5" />
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-50">
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">File Name</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Client</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Type</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Date</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Status</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-[#1A2244]">
                        <FileText className="w-4 h-4" />
                      </div>
                      <span className="text-xs font-bold text-[#1A2244]">{doc.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs font-bold text-slate-500">{doc.client}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{doc.type}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs font-bold text-slate-400">{doc.date}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      "px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest",
                      doc.status === 'Verified' ? "bg-green-50 text-green-600" :
                      doc.status === 'Rejected' ? "bg-red-50 text-red-600" :
                      "bg-amber-50 text-amber-600"
                    )}>
                      {doc.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button className="p-2 text-slate-400 hover:text-[#5B7CFA] transition-colors">
                        <Eye className="w-4 h-4" />
                      </button>
                      <button className="p-2 text-slate-400 hover:text-[#5B7CFA] transition-colors">
                        <Download className="w-4 h-4" />
                      </button>
                      <button className="p-2 text-slate-400 hover:text-red-500 transition-colors">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
