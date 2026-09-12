import React from 'react';
import { Search, Bell } from 'lucide-react';
import { useLocation } from 'react-router-dom';

export function TopBar() {
  const location = useLocation();

  // Create breadcrumb from pathname
  const paths = location.pathname.split('/').filter(Boolean);

  return (
    <header className="h-16 px-8 flex items-center justify-between border-b border-border bg-background/50 backdrop-blur-md sticky top-0 z-30">
      <div className="flex items-center gap-2 font-bold text-foreground opacity-50 hidden md:flex">
        <span>XAI</span>
        <span className="text-primary font-black">/</span>
        {paths.map((path, index) => (
          <React.Fragment key={path}>
            <span>/</span>
            <span className={index === paths.length - 1 ? "text-foreground font-semibold" : ""}>
              {path.replace(/-/g, ' ')}
            </span>
          </React.Fragment>
        ))}
      </div>

      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search projects, vulnerabilities (⌘K)..."
            className="h-9 w-64 bg-muted/50 border border-border rounded-lg pl-9 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary transition-all placeholder:text-muted-foreground/70"
          />
        </div>

        <button className="relative w-9 h-9 flex items-center justify-center rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-primary rounded-full ring-2 ring-background line-pulse" />
        </button>
      </div>
    </header>
  );
}
