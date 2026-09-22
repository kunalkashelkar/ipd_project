import React from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderOpen,
  Activity,
  ShieldCheck,
  FileText,
  BarChart2,
  Blocks,
  Users,
  Bell,
  Settings,
  LogOut,
  BookOpen,
  Shield,
} from 'lucide-react';
import { cn } from './ui/Button';
import { useAuthStore } from '../store';
import { authService } from '../services/authService';
import { authStorage } from '../services/authStorage';

interface NavSection {
  title: string;
  items: Array<{
    to: string;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
  }>;
}

const navSections: NavSection[] = [
  {
    title: 'Platform',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Security & Code',
    items: [
      { to: '/projects', label: 'Projects', icon: FolderOpen },
      { to: '/scans', label: 'Scans', icon: Activity },
      { to: '/findings', label: 'Findings', icon: ShieldCheck },
      { to: '/reports', label: 'Reports', icon: FileText },
    ],
  },
  {
    title: 'Analysis & Reference',
    items: [
      { to: '/analytics', label: 'Analytics', icon: BarChart2 },
      { to: '/integrations', label: 'Integrations', icon: Blocks },
      { to: '/documentation', label: 'Documentation', icon: BookOpen },
    ],
  },
  {
    title: 'Workspace',
    items: [
      { to: '/team', label: 'Team & Access', icon: Users },
      { to: '/notifications', label: 'Notifications', icon: Bell },
      { to: '/settings', label: 'Settings', icon: Settings },
    ],
  },
];

import { VulnScanLogo } from './VulnScanLogo';

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, activeMemberRole, activeOrganization, logout } = useAuthStore();

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch {
      // Ignore network errors during logout
    } finally {
      logout();
      authStorage.clearSession();
      navigate('/login', { replace: true });
    }
  };

  const displayName = user?.name || 'Authenticated User';
  const displayEmail = user?.email || '';
  const rawRole = activeMemberRole || activeOrganization?.current_user_role;
  const displayRole = rawRole ? rawRole.replace('_', ' ') : (user?.role ? user.role.replace('_', ' ') : 'Member');

  return (
    <aside className="w-64 border-r border-border bg-sidebar flex flex-col h-screen fixed left-0 top-0 z-40 select-none shadow-soft">
      {/* Platform Branding */}
      <div className="h-16 px-4 flex items-center border-b border-border shrink-0 bg-sidebar/80">
        <VulnScanLogo
          variant="full"
          size="md"
          showSubtitle={true}
          subtitle="Security Intelligence"
          linkTo="/dashboard"
          className="hover:opacity-95 transition-opacity"
        />
      </div>

      {/* Semantic Grouped Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto scrollbar-thin scrollbar-thumb-border">
        {navSections.map((section) => (
          <div key={section.title} className="space-y-1">
            <div className="px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
              {section.title}
            </div>
            {section.items.map((item) => {
              const isActive =
                item.to === '/dashboard'
                  ? location.pathname === '/dashboard'
                  : location.pathname.startsWith(item.to);

              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={cn(
                    'flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors group relative',
                    isActive
                      ? 'bg-primary/10 text-primary font-semibold'
                      : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'
                  )}
                >
                  <item.icon
                    className={cn(
                      'w-4 h-4 shrink-0 transition-colors',
                      isActive
                        ? 'text-primary'
                        : 'text-muted-foreground group-hover:text-foreground'
                    )}
                  />
                  <span className="truncate">{item.label}</span>
                  {isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-3.5 bg-primary rounded-r" />
                  )}
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Account / User Area */}
      <div className="p-3 border-t border-border/50 shrink-0 space-y-2 bg-sidebar/50">
        <div className="p-2.5 rounded-md bg-card/60 border border-border/50 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-full bg-primary/20 text-primary font-semibold flex items-center justify-center text-xs shrink-0 uppercase">
              {displayName.slice(0, 2)}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-medium text-foreground truncate leading-tight">
                {displayName}
              </span>
              <span className="text-[10px] text-muted-foreground truncate leading-tight mt-0.5">
                {displayEmail}
              </span>
            </div>
          </div>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono uppercase tracking-wider shrink-0">
            {displayRole}
          </span>
        </div>

        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors border border-transparent hover:border-destructive/20"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}
