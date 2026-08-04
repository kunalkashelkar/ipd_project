import React from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FolderOpen, 
  Activity, 
  FileText, 
  BarChart, 
  Bell, 
  Settings, 
  LogOut,
  ShieldAlert
} from 'lucide-react';
import { cn } from './ui/Button';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/projects', label: 'Projects', icon: FolderOpen },
  { to: '/scans', label: 'Scans', icon: Activity },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/analytics', label: 'Analytics', icon: BarChart },
  { to: '/notifications', label: 'Notifications', icon: Bell, badge: 3 },
  { to: '/docs', label: 'Documentation', icon: ShieldAlert },
];

export function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    navigate('/login');
  };

  return (
    <aside className="w-64 border-r border-border bg-sidebar flex flex-col h-screen fixed left-0 top-0 z-40">
      <div className="p-6 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-soft">
          <ShieldAlert className="w-5 h-5 text-primary-foreground" />
        </div>
        <span className="font-bold text-lg tracking-tight text-foreground">Aegis Kinetic</span>
      </div>

      <nav className="flex-1 px-4 space-y-1 overflow-y-auto mt-4 scrollbar-thin scrollbar-thumb-border">
        {navItems.map((item) => {
          const isActive = location.pathname.startsWith(item.to);
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group relative",
                isActive 
                  ? "bg-primary/10 text-primary" 
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className={cn("w-5 h-5", isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
              {item.label}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-primary rounded-r-full" />
              )}
              {item.badge && (
                <span className="ml-auto bg-primary text-primary-foreground text-[10px] font-bold px-2 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>

      <div className="p-4 mt-auto border-t border-border/50">
        <NavLink
            to="/settings"
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
              isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted"
            )}
          >
            <Settings className="w-5 h-5" />
            Settings
        </NavLink>
        <button 
          onClick={handleLogout}
          className="w-full mt-1 flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all"
        >
          <LogOut className="w-5 h-5" />
          Logout
        </button>

        <div className="mt-4 flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-secondary overflow-hidden">
            <img src="https://ui-avatars.com/api/?name=Admin&background=0D8ABC&color=fff" alt="User" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium">Administrator</span>
            <span className="text-xs text-muted-foreground">admin@aegis.io</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
