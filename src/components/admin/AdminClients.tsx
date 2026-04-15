import React from 'react';
import { 
  Users, 
  Search, 
  Filter, 
  MoreHorizontal, 
  ArrowUpRight, 
  TrendingUp, 
  ShieldCheck, 
  Briefcase,
  FileText,
  Zap,
  ChevronRight,
  Mail,
  Phone,
  Calendar
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AdminClients() {
  const clients = [
    { id: 1, name: 'Marcus Chen', email: 'marcus@example.com', phone: '(555) 123-4567', readiness: 68, fundingGoal: '$50,000', stage: 'Credit Repair', joined: '2024-01-15', status: 'active' },
    { id: 2, name: 'Sarah Jenkins', email: 'sarah.j@example.com', phone: '(555) 987-6543', readiness: 42, fundingGoal: '$15,000', stage: 'Entity Setup', joined: '2024-02-01', status: 'pending' },
    { id: 3, name: 'Robert Fox', email: 'robert@foxcorp.io', phone: '(555) 444-5555', readiness: 92, fundingGoal: '$100,000', stage: 'Funding Prep', joined: '2023-11-20', status: 'urgent' },
    { id: 4, name: 'Elena Rodriguez', email: 'elena@design.com', phone: '(555) 222-3333', readiness: 55, fundingGoal: '$30,000', stage: 'Bank Setup', joined: '2024-01-28', status: 'active' },
    { id: 5, name: 'David Kim', email: 'dkim@tech.net', phone: '(555) 777-8888', readiness: 74, fundingGoal: '$45,000', stage: 'Credit Repair', joined: '2024-02-10', status: 'active' },
    { id: 6, name: 'Jessica Taylor', email: 'jess@taylor.com', phone: '(555) 666-7777', readiness: 31, fundingGoal: '$10,000', stage: 'Initial Audit', joined: '2024-02-15', status: 'new' },
  ];

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Clients</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Manage all clients, monitor funding stages, and override progress.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-6 py-2 rounded-xl bg-white border border-slate-200 text-[#1A2244] text-xs font-black uppercase tracking-widest hover:bg-slate-50 transition-all shadow-sm">
            Export Data
          </button>
          <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
            Add New Client
          </button>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="flex items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-4 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search by name, email, or stage..." 
              className="w-full bg-slate-50 border border-slate-200 rounded-xl py-2 pl-10 pr-4 text-xs font-medium text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 transition-all"
            />
          </div>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-xs font-bold text-slate-500 hover:text-[#1A2244] transition-all">
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sort by:</span>
          <select className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-[10px] font-black text-slate-600 uppercase tracking-widest focus:outline-none focus:border-[#5B7CFA]/50">
            <option>Readiness Score</option>
            <option>Joined Date</option>
            <option>Funding Goal</option>
          </select>
        </div>
      </div>

      {/* Client List */}
      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/30">
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Client Details</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Current Stage</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Readiness</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Funding Goal</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Status</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {clients.map((client) => (
              <tr key={client.id} className="hover:bg-slate-50/50 transition-colors group">
                <td className="px-6 py-5">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-slate-100 border border-slate-200 overflow-hidden shrink-0">
                      <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${client.name}`} alt="" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-black text-[#1A2244] truncate">{client.name}</p>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-[9px] font-bold text-slate-400 flex items-center gap-1">
                          <Mail className="w-2.5 h-2.5" />
                          {client.email}
                        </span>
                        <span className="text-[9px] font-bold text-slate-400 flex items-center gap-1">
                          <Phone className="w-2.5 h-2.5" />
                          {client.phone}
                        </span>
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-5">
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      "w-1.5 h-1.5 rounded-full",
                      client.stage === 'Funding Prep' ? "bg-green-500" : "bg-[#5B7CFA]"
                    )} />
                    <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest">{client.stage}</span>
                  </div>
                  <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mt-1">Joined {client.joined}</p>
                </td>
                <td className="px-6 py-5">
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden w-24">
                      <div 
                        className={cn(
                          "h-full rounded-full",
                          client.readiness > 80 ? "bg-green-500" : client.readiness > 50 ? "bg-[#5B7CFA]" : "bg-amber-500"
                        )} 
                        style={{ width: `${client.readiness}%` }} 
                      />
                    </div>
                    <span className="text-[10px] font-black text-[#1A2244]">{client.readiness}%</span>
                  </div>
                </td>
                <td className="px-6 py-5">
                  <span className="text-sm font-black text-[#5B7CFA]">{client.fundingGoal}</span>
                </td>
                <td className="px-6 py-5">
                  <span className={cn(
                    "px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest",
                    client.status === 'urgent' ? "bg-red-50 text-red-600" :
                    client.status === 'active' ? "bg-green-50 text-green-600" :
                    client.status === 'pending' ? "bg-amber-50 text-amber-600" :
                    "bg-slate-100 text-slate-500"
                  )}>
                    {client.status}
                  </span>
                </td>
                <td className="px-6 py-5 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button className="p-2 text-slate-400 hover:text-[#5B7CFA] hover:bg-slate-50 rounded-lg transition-all">
                      <Mail className="w-4 h-4" />
                    </button>
                    <button className="px-4 py-2 bg-blue-50 text-[#5B7CFA] text-[10px] font-black uppercase tracking-widest rounded-lg hover:bg-[#5B7CFA] hover:text-white transition-all">
                      Manage
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="p-6 border-t border-slate-100 flex items-center justify-between bg-slate-50/30">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Showing 6 of 1,284 clients</p>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-400 text-[10px] font-black uppercase tracking-widest hover:text-[#1A2244] transition-all disabled:opacity-50" disabled>Previous</button>
            <button className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-400 text-[10px] font-black uppercase tracking-widest hover:text-[#1A2244] transition-all">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
