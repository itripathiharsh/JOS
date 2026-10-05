import React from 'react';
import { LayoutDashboard, Briefcase, FileText, User, Settings, Database, Activity, Landmark } from 'lucide-react';
import type { HealthResponse } from '../api/client';

export type PageId = 'dashboard' | 'jobs' | 'applications' | 'profile' | 'government' | 'settings';

interface NavigationProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  health: HealthResponse | null;
  loadingHealth: boolean;
}

export const Navigation: React.FC<NavigationProps> = ({
  currentPage,
  onSelectPage,
  health,
  loadingHealth,
}) => {
  const navItems = [
    { id: 'dashboard' as PageId, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'jobs' as PageId, label: 'Jobs', icon: Briefcase },
    { id: 'government' as PageId, label: 'Government', icon: Landmark },
    { id: 'applications' as PageId, label: 'Applications', icon: FileText },
    { id: 'profile' as PageId, label: 'My Profile', icon: User },
    { id: 'settings' as PageId, label: 'Settings', icon: Settings },
  ];

  const isDbConnected = health?.database === 'connected';

  return (
    <aside className="w-64 border-r border-slate-800 bg-[#0d131f] flex flex-col justify-between shrink-0 h-screen sticky top-0">
      <div>
        {/* Brand */}
        <div className="p-5 border-b border-slate-800/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-mono font-bold text-white shadow-sm shadow-indigo-500/20">
              OS
            </div>
            <div>
              <div className="font-semibold text-sm tracking-tight text-slate-100 leading-none">Job Operating System</div>
              <div className="text-[11px] text-cyan-400 font-mono mt-1">Controlled Autonomy • Step 12</div>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = currentPage === item.id;
            return (
              <button
                key={item.id}
                id={`nav-${item.id}`}
                onClick={() => onSelectPage(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-xs font-medium transition-colors ${
                  active
                    ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-indigo-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* System Status Footer */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-900/40">
        <div className="text-[11px] font-mono text-slate-400 mb-2 uppercase tracking-wider font-semibold">
          System State
        </div>
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Activity className="w-3.5 h-3.5 text-slate-500" />
              API Server
            </span>
            <span className={`inline-flex items-center gap-1 font-mono text-[11px] ${health?.status === 'ok' ? 'text-emerald-400' : 'text-amber-400'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${health?.status === 'ok' ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`} />
              {loadingHealth ? 'Checking...' : health?.status === 'ok' ? 'Healthy' : 'Offline'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Database className="w-3.5 h-3.5 text-slate-500" />
              PostgreSQL
            </span>
            <span className={`inline-flex items-center gap-1 font-mono text-[11px] ${isDbConnected ? 'text-emerald-400' : 'text-rose-400'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isDbConnected ? 'bg-emerald-400' : 'bg-rose-400'}`} />
              {loadingHealth ? 'Checking...' : isDbConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};
