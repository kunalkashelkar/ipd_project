import React, { useEffect, useState } from 'react';
import { Search, Bell, Building2, ChevronDown, Check, Plus, ChevronRight } from 'lucide-react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store';
import { organizationService } from '../services/organizationService';
import { notificationService } from '../services/notificationService';
import { projectService } from '../services/projectService';
import { Organization } from '../types';
import toast from 'react-hot-toast';

const isUuid = (val: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(val);

export function TopBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { activeOrganization, organizations, setActiveOrganization, setOrganizations } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [unreadCount, setUnreadCount] = useState(0);
  const [projectNames, setProjectNames] = useState<Record<string, string>>({});

  const paths = location.pathname.split('/').filter(Boolean);

  // Fetch human-readable project name for breadcrumb when navigating project routes
  useEffect(() => {
    if (paths[0] === 'projects' && paths[1] && isUuid(paths[1])) {
      const projectId = paths[1];
      if (!projectNames[projectId]) {
        projectService
          .getProject(projectId)
          .then((p) => {
            if (p?.name) {
              setProjectNames((prev) => ({ ...prev, [projectId]: p.name }));
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

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    navigate(`/projects?search=${encodeURIComponent(searchQuery.trim())}`);
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
              const isProjectId = paths[0] === 'projects' && idx === 1 && isUuid(p);
              const displayName = isProjectId && projectNames[p] ? projectNames[p] : p.replace(/-/g, ' ');
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
      <div className="flex items-center gap-3">
        <form onSubmit={handleSearchSubmit} className="relative hidden sm:block">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search projects by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 w-56 bg-muted/40 border border-border rounded-md pl-8 pr-3 text-xs focus:outline-none focus:ring-1 focus:ring-primary transition-all placeholder:text-muted-foreground/60 text-foreground"
          />
        </form>

        <button
          onClick={() => navigate('/notifications')}
          aria-label="View notifications"
          className="relative w-8 h-8 flex items-center justify-center rounded-md hover:bg-hover transition-colors text-muted-foreground hover:text-foreground border border-border/50"
        >
          <Bell className="w-4 h-4" />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full ring-2 ring-background" />
          )}
        </button>
      </div>
    </header>
  );
}
