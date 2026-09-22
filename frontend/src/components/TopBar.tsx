import React, { useEffect, useState } from 'react';
import { Search, Bell, Building2, ChevronDown, Check, Plus, ChevronRight } from 'lucide-react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store';
import { organizationService } from '../services/organizationService';
import { notificationService } from '../services/notificationService';
import { projectService } from '../services/projectService';
import { Organization } from '../types';
import toast from 'react-hot-toast';
import { VulnScanLogo } from './VulnScanLogo';
import { CommandPalette } from './CommandPalette';

const isUuid = (val: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(val);

export function TopBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { activeOrganization, organizations, setActiveOrganization, setOrganizations } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [projectNames, setProjectNames] = useState<Record<string, string>>({});

  // Global shortcut for Cmd/Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const paths = location.pathname.split('/').filter(Boolean);

  // Fetch human-readable project name for breadcrumb when navigating project routes
  useEffect(() => {
    if (paths[0] === 'projects' && paths[1] && paths[1] !== 'create') {
      const projectSlug = paths[1];
      if (!projectNames[projectSlug]) {
        projectService
          .getProject(projectSlug)
          .then((p) => {
            if (p?.name) {
              setProjectNames((prev) => ({
                ...prev,
                [projectSlug]: p.name,
                [p.id]: p.name,
                ...(p.public_id ? { [p.public_id]: p.name } : {}),
              }));
            }
          })
          .catch(() => {});
      }
    }
  }, [location.pathname]);

  useEffect(() => {
    const fetchOrgs = async () => {
      try {
        const orgs = await organizationService.listOrganizations();
        setOrganizations(orgs);
        if (!activeOrganization && orgs.length > 0) {
          setActiveOrganization(orgs[0]);
        }
      } catch {
        // Fallback silently if unauthenticated
      }
    };
    fetchOrgs();
  }, []);

  // Check real unread notification count
  useEffect(() => {
    let isMounted = true;
    const checkNotifications = async () => {
      try {
        const res = await notificationService.getNotifications({ page: 1, page_size: 20 });
        if (isMounted) {
          const unread = (res?.items || []).filter((n) => !n.read).length;
          setUnreadCount(unread);
        }
      } catch {
        // Silently ignore
      }
    };
    checkNotifications();
    return () => {
      isMounted = false;
    };
  }, [location.pathname]);

  const handleSelectOrg = (org: Organization) => {
    setActiveOrganization(org);
    setIsOpen(false);
    toast.success(`Switched to workspace: ${org.name}`);
    window.location.reload();
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName.trim()) return;
    try {
      const created = await organizationService.createOrganization(newOrgName.trim());
      setOrganizations([...organizations, created]);
      setActiveOrganization(created);
      setIsCreating(false);
      setNewOrgName('');
      setIsOpen(false);
      toast.success(`Workspace "${created.name}" created!`);
      window.location.reload();
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Failed to create workspace');
    }
  };



  return (
    <header className="h-16 px-6 flex items-center justify-between border-b border-border bg-background/90 backdrop-blur-sm sticky top-0 z-30">
      <div className="flex items-center gap-4 min-w-0">
        {/* Workspace / Tenant Selector */}
        <div className="relative">
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-card border border-border hover:bg-hover transition-colors text-xs font-medium text-foreground"
            title="Switch Workspace"
          >
            <Building2 className="w-3.5 h-3.5 text-primary shrink-0" />
            <span className="max-w-[150px] truncate">
              {activeOrganization?.name || 'Select Workspace'}
            </span>
            <ChevronDown className="w-3 h-3 text-muted-foreground shrink-0" />
          </button>

          {isOpen && (
            <div className="absolute left-0 mt-2 w-64 bg-card border border-border rounded-lg shadow-lg py-2 z-50 animate-in fade-in zoom-in-95">
              <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Workspaces
              </div>
              <div className="max-h-48 overflow-y-auto">
                {organizations.map((org) => (
                  <button
                    key={org.id}
                    onClick={() => handleSelectOrg(org)}
                    className="w-full flex items-center justify-between px-3 py-2 text-xs text-left hover:bg-hover transition-colors text-foreground"
                  >
                    <span className="truncate">{org.name}</span>
                    {activeOrganization?.id === org.id && (
                      <Check className="w-3.5 h-3.5 text-primary shrink-0" />
                    )}
                  </button>
                ))}
              </div>

              <div className="border-t border-border mt-1 pt-1">
                {isCreating ? (
                  <form onSubmit={handleCreateOrg} className="p-2 space-y-2">
                    <input
                      type="text"
                      placeholder="Workspace name..."
                      value={newOrgName}
                      onChange={(e) => setNewOrgName(e.target.value)}
                      className="w-full text-xs px-2.5 py-1.5 rounded-md border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      autoFocus
                    />
                    <div className="flex gap-1 justify-end">
                      <button
                        type="button"
                        onClick={() => setIsCreating(false)}
                        className="text-xs px-2 py-1 text-muted-foreground hover:text-foreground"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="text-xs px-2.5 py-1 bg-primary text-primary-foreground rounded-md font-medium"
                      >
                        Create
                      </button>
                    </div>
                  </form>
                ) : (
                  <button
                    onClick={() => setIsCreating(true)}
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-primary hover:bg-muted font-medium transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Create New Workspace
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Clean Breadcrumb */}
        <div className="hidden md:flex items-center gap-1.5 text-xs text-muted-foreground truncate">
          <ChevronRight className="w-3 h-3 text-muted-foreground/60 shrink-0" />
          {paths.length === 0 ? (
            <span className="text-foreground font-medium">Dashboard</span>
          ) : (
            paths.map((p, idx) => {
              const isLast = idx === paths.length - 1;
              const isProjectId = paths[0] === 'projects' && idx === 1;
              let displayName: string;
              if (isProjectId) {
                displayName = projectNames[p] || (isUuid(p) ? 'Project' : p);
              } else if (paths[0] === 'projects' && paths[2] === 'snapshots' && idx === 3) {
                displayName = isUuid(p) ? `Snapshot ${p.slice(0, 8)}` : p;
              } else if (paths[0] === 'projects' && paths[2] === 'scans' && idx === 3) {
                displayName = isUuid(p) ? `Scan ${p.slice(0, 8)}` : p;
              } else {
                displayName = p.replace(/-/g, ' ');
              }
              const targetUrl = '/' + paths.slice(0, idx + 1).join('/');

              return (
                <React.Fragment key={`${p}-${idx}`}>
                  {idx > 0 && <ChevronRight className="w-3 h-3 text-muted-foreground/40 shrink-0" />}
                  {isLast ? (
                    <span className="text-foreground font-medium truncate max-w-[200px]" title={displayName}>
                      {displayName}
                    </span>
                  ) : (
                    <Link
                      to={targetUrl}
                      className="hover:text-foreground capitalize truncate max-w-[150px] transition-colors"
                      title={displayName}
                    >
                      {displayName}
                    </Link>
                  )}
                </React.Fragment>
              );
            })
          )}
        </div>
      </div>

      {/* Right Action Area */}
      <div className="flex items-center gap-2.5">
        {/* Command Palette Trigger Button */}
        <button
          type="button"
          onClick={() => setIsCommandPaletteOpen(true)}
          className="flex items-center gap-2 px-2.5 py-1.5 h-8 bg-card hover:bg-card-hover border border-border rounded-btn text-xs text-muted-foreground hover:text-foreground transition-all shadow-soft group"
          title="Open Command Palette (Cmd/Ctrl + K)"
        >
          <Search className="w-3.5 h-3.5 text-primary shrink-0 group-hover:text-primary transition-colors" />
          <span className="hidden sm:inline font-sans text-muted-foreground/90">Search platform...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground bg-sidebar border border-border/80 rounded">
            ⌘K
          </kbd>
        </button>

        {/* Notifications Icon with unread badge */}
        <button
          onClick={() => navigate('/notifications')}
          aria-label="View notifications"
          className="relative w-8 h-8 flex items-center justify-center rounded-btn hover:bg-card-hover transition-colors text-muted-foreground hover:text-foreground border border-border/70"
          title="Notifications"
        >
          <Bell className="w-3.5 h-3.5" />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-brand-orange rounded-full ring-2 ring-background animate-pulse" />
          )}
        </button>
      </div>

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
    </header>
  );
}
