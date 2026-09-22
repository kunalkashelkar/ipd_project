import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  LayoutDashboard,
  FolderOpen,
  Activity,
  ShieldCheck,
  FileText,
  BarChart2,
  Blocks,
  Users,
  Settings,
  BookOpen,
  Plus,
  ArrowRight,
  X,
  Command,
  CornerDownLeft,
  Key,
  Sliders,
  UserPlus,
} from 'lucide-react';
import { projectService } from '../services/projectService';
import { Project } from '../types';
import { getProjectUrl } from '../utils/routes';

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  category: 'Navigation' | 'Actions' | 'Projects';
  icon: React.ComponentType<{ className?: string }>;
  action: () => void;
  shortcut?: string;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [projects, setProjects] = useState<Project[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Fetch recent projects for quick jump
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      projectService
        .listProjects({ page: 1, page_size: 50 })
        .then((res) => setProjects(res.items || []))
        .catch(() => {});
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const baseItems: CommandItem[] = [
    // Navigation
    {
      id: 'nav-dashboard',
      label: 'Dashboard',
      description: 'Workspace security posture & health score',
      category: 'Navigation',
      icon: LayoutDashboard,
      action: () => navigate('/dashboard'),
    },
    {
      id: 'nav-projects',
      label: 'Projects',
      description: 'Browse repositories & source snapshots',
      category: 'Navigation',
      icon: FolderOpen,
      action: () => navigate('/projects'),
    },
    {
      id: 'nav-scans',
      label: 'Scans',
      description: 'Active pipelines & scan history',
      category: 'Navigation',
      icon: Activity,
      action: () => navigate('/scans'),
    },
    {
      id: 'nav-findings',
      label: 'Findings',
      description: 'Vulnerability triage & investigation',
      category: 'Navigation',
      icon: ShieldCheck,
      action: () => navigate('/findings'),
    },
    {
      id: 'nav-reports',
      label: 'Reports',
      description: 'Audit documents & compliance exports',
      category: 'Navigation',
      icon: FileText,
      action: () => navigate('/reports'),
    },
    {
      id: 'nav-analytics',
      label: 'Analytics',
      description: 'Security trends, MTTR & vulnerability density',
      category: 'Navigation',
      icon: BarChart2,
      action: () => navigate('/analytics'),
    },
    {
      id: 'nav-integrations',
      label: 'Integrations & Policy',
      description: 'GitHub apps, MinIO & security gates',
      category: 'Navigation',
      icon: Blocks,
      action: () => navigate('/integrations'),
    },
    {
      id: 'nav-team',
      label: 'Team & RBAC',
      description: 'Manage members, roles & permissions',
      category: 'Navigation',
      icon: Users,
      action: () => navigate('/team'),
    },
    {
      id: 'nav-settings',
      label: 'Settings',
      description: 'Workspace preferences & API keys',
      category: 'Navigation',
      icon: Settings,
      action: () => navigate('/settings'),
    },
    {
      id: 'nav-docs',
      label: 'Documentation',
      description: 'Technical manuals, API & CLI guides',
      category: 'Navigation',
      icon: BookOpen,
      action: () => navigate('/documentation'),
    },
    // Actions
    {
      id: 'action-create-project',
      label: 'Create New Project',
      description: 'Initialize a new repository target',
      category: 'Actions',
      icon: Plus,
      action: () => navigate('/projects/create'),
    },
    {
      id: 'action-invite-team',
      label: 'Invite Team Member',
      description: 'Add collaborators with RBAC permissions',
      category: 'Actions',
      icon: UserPlus,
      action: () => navigate('/team'),
    },
    {
      id: 'action-security-gate',
      label: 'Configure Security Gates',
      description: 'Set blocking thresholds for CI/CD PRs',
      category: 'Actions',
      icon: Sliders,
      action: () => navigate('/integrations'),
    },
    {
      id: 'action-api-keys',
      label: 'Manage API Keys',
      description: 'Generate or revoke programmatic tokens',
      category: 'Actions',
      icon: Key,
      action: () => navigate('/settings'),
    },
  ];

  const projectItems: CommandItem[] = projects.map((p) => ({
    id: `project-${p.id}`,
    label: p.name,
    description: p.public_id ? `Target: ${p.public_id}` : 'Repository target',
    category: 'Projects',
    icon: FolderOpen,
    action: () => navigate(getProjectUrl(p)),
  }));

  const allItems = [...projectItems, ...baseItems];

  const filteredItems = allItems.filter((item) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return (
      item.label.toLowerCase().includes(q) ||
      (item.description && item.description.toLowerCase().includes(q)) ||
      item.category.toLowerCase().includes(q)
    );
  });

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev < filteredItems.length - 1 ? prev + 1 : 0));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredItems.length - 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredItems[selectedIndex]) {
          filteredItems[selectedIndex].action();
          onClose();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filteredItems, selectedIndex, onClose]);

  // Keep selected element scrolled into view
  useEffect(() => {
    const el = listRef.current?.children[selectedIndex] as HTMLElement;
    if (el) {
      el.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Command Palette"
    >
      <div className="w-full max-w-xl bg-card border border-border rounded-card shadow-2xl overflow-hidden flex flex-col max-h-[70vh] animate-in zoom-in-95 duration-150">
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-sidebar shrink-0">
          <Search className="w-4 h-4 text-primary shrink-0" />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded="true"
            aria-controls="command-palette-results"
            aria-autocomplete="list"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a command, route, or search projects..."
            className="flex-1 bg-transparent border-none outline-none text-xs sm:text-sm text-foreground placeholder:text-muted-foreground font-sans"
          />
          {query ? (
            <button
              onClick={() => setQuery('')}
              className="text-muted-foreground hover:text-foreground p-1 rounded"
              aria-label="Clear query"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          ) : (
            <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground bg-muted border border-border/80 rounded">
              ESC
            </kbd>
          )}
        </div>

        {/* Results List */}
        <div id="command-palette-results" role="listbox" ref={listRef} className="overflow-y-auto p-2 space-y-1">
          {filteredItems.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">
              No matching commands or projects found for "{query}"
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => {
                    item.action();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2 rounded-btn cursor-pointer transition-colors text-xs ${
                    isSelected
                      ? 'bg-primary/10 text-primary border border-primary/20'
                      : 'text-foreground hover:bg-hover'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div
                      className={`w-6 h-6 rounded flex items-center justify-center shrink-0 ${
                        isSelected ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate">{item.label}</span>
                        <span className="text-[10px] font-mono text-muted-foreground px-1 py-0.2 bg-muted/60 rounded border border-border/40">
                          {item.category}
                        </span>
                      </div>
                      {item.description && (
                        <span className="text-[11px] text-muted-foreground truncate">
                          {item.description}
                        </span>
                      )}
                    </div>
                  </div>
                  {isSelected && (
                    <div className="flex items-center gap-1 text-[10px] text-primary font-mono shrink-0 pl-2">
                      <span>Jump</span>
                      <CornerDownLeft className="w-3 h-3" />
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Technical Footer */}
        <div className="px-4 py-2 bg-sidebar border-t border-border flex items-center justify-between text-[11px] text-muted-foreground font-mono shrink-0 select-none">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>Esc Close</span>
          </div>
          <div className="flex items-center gap-1 text-primary/80">
            <Command className="w-3 h-3" />
            <span>VulnScan Command</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
