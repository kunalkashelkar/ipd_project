import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Link, NavLink } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { FiUpload, FiGrid, FiBarChart2, FiFileText, FiSettings, FiCpu } from 'react-icons/fi';

// Lazy-loaded pages
const Dashboard   = lazy(() => import('./pages/Dashboard'));
const Upload      = lazy(() => import('./pages/Upload'));
const Analysis    = lazy(() => import('./pages/Analysis'));
const GraphViewer = lazy(() => import('./pages/GraphViewer'));
const TaintReport = lazy(() => import('./pages/TaintReport'));
const Reports     = lazy(() => import('./pages/Reports'));
const Settings    = lazy(() => import('./pages/Settings'));

// Placeholder pages for Phase 1 stubs
const Dashboard_  = () => <div className="p-8 animate-slide-up"><h2 className="text-2xl font-bold text-surface-800">Dashboard Overview</h2><p className="text-surface-500 mt-2 text-sm">Phase 1 placeholder. Upload a file to get started.</p></div>;
const Reports_    = () => <div className="p-8 animate-slide-up"><h2 className="text-2xl font-bold text-surface-800">Reports</h2><p className="text-surface-500 mt-2 text-sm">No reports yet.</p></div>;
const Settings_   = () => <div className="p-8 animate-slide-up"><h2 className="text-2xl font-bold text-surface-800">Settings</h2></div>;

const navItems = [
  { to: '/',        label: 'Dashboard',   icon: <FiGrid className="w-4 h-4" /> },
  { to: '/upload',  label: 'Upload',      icon: <FiUpload className="w-4 h-4" /> },
  { to: '/reports', label: 'Reports',     icon: <FiFileText className="w-4 h-4" /> },
  { to: '/settings',label: 'Settings',   icon: <FiSettings className="w-4 h-4" /> },
];

function Spinner() {
  return <div className="flex items-center justify-center h-64 text-primary-500 animate-pulse-slow"><FiCpu className="w-8 h-8" /></div>;
}

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
      <div className="min-h-screen bg-gradient-to-br from-surface-50 via-white to-primary-50 flex flex-col">

        {/* Top nav */}
        <header className="sticky top-0 z-20 glass-panel mx-4 mt-4 rounded-2xl px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-glow">
              <FiCpu className="text-white w-4 h-4" />
            </div>
            <span className="font-bold text-primary-800 text-sm tracking-tight">XAI Vuln Detector</span>
          </div>
          <nav className="flex gap-1">
            {navItems.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900'
                  }`
                }
              >
                {item.icon}
                {item.label}
              </NavLink>
            ))}
          </nav>
        </header>

        {/* Main content */}
        <main className="flex-1 px-4 pb-8 mt-6 container mx-auto max-w-7xl">
          <div className="glass-panel p-6 min-h-[600px]">
            <Suspense fallback={<Spinner />}>
              <Routes>
                <Route path="/"                      element={<Dashboard_ />} />
                <Route path="/upload"                element={<Upload />} />
                <Route path="/analysis/:jobId"       element={<Analysis />} />
                <Route path="/graph/:jobId"          element={<GraphViewer />} />
                <Route path="/taint/:taintJobId"     element={<TaintReport />} />
                <Route path="/graph/taint/:taintJobId" element={<GraphViewer taintMode />} />
                <Route path="/reports"               element={<Reports_ />} />
                <Route path="/settings"              element={<Settings_ />} />
              </Routes>
            </Suspense>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
