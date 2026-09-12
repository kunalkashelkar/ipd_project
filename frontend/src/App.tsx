import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ShieldAlert } from 'lucide-react';
import { AppShell, PublicLayout } from './layouts/AppShell';

// Lazy-loaded pages
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ProjectsList = lazy(() => import('./pages/projects/ProjectsList'));
const CreateProject = lazy(() => import('./pages/projects/CreateProject'));
const ProjectDetail = lazy(() => import('./pages/projects/ProjectDetail'));
const ScanConfig = lazy(() => import('./pages/projects/ScanConfig'));
const ScanProgress = lazy(() => import('./pages/projects/ScanProgress'));
const ScanResultsWorkspace = lazy(() => import('./pages/projects/ScanResultsWorkspace'));
const ScansList = lazy(() => import('./pages/ScansList'));
const ConnectRepo = lazy(() => import('./pages/projects/ConnectRepo'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Reports = lazy(() => import('./pages/Reports'));
const Settings = lazy(() => import('./pages/Settings'));
const Notifications = lazy(() => import('./pages/Notifications'));
const Upload = lazy(() => import('./pages/Upload'));
const AnalysisLegacy = lazy(() => import('./pages/Analysis'));
const GraphViewer = lazy(() => import('./pages/GraphViewer'));
const TaintReport = lazy(() => import('./pages/TaintReport'));
const Landing = lazy(() => import('./pages/Landing'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));

// Placeholder components
const Placeholder = ({ title }: { title: string }) => (
  <div className="flex items-center justify-center h-full">
    <div className="text-center space-y-4 max-w-md">
      <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">{title}</h2>
      <p className="text-muted-foreground">This feature is currently being implemented for the enterprise UI.</p>
    </div>
  </div>
);

function Spinner() {
  return (
    <div className="flex items-center justify-center h-64 text-primary animate-pulse-slow">
      <ShieldAlert className="w-8 h-8 opacity-50" />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'hsl(var(--card))',
            color: 'hsl(var(--foreground))',
            border: '1px solid hsl(var(--border))',
          }
        }}
      />
      <Suspense fallback={<div className="h-screen w-screen bg-background flex items-center justify-center"><Spinner /></div>}>
        <Routes>
          {/* Public routes */}
          <Route element={<PublicLayout />}>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
          </Route>

          {/* Authenticated routes */}
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<Dashboard />} />

            <Route path="/projects" element={<ProjectsList />} />
            <Route path="/projects/create" element={<CreateProject />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/projects/:id/connect" element={<ConnectRepo />} />
            <Route path="/projects/:id/scan-config" element={<ScanConfig />} />
            <Route path="/projects/:id/scan-progress" element={<ScanProgress />} />
            <Route path="/projects/:id/results" element={<ScanResultsWorkspace />} />

            <Route path="/scans" element={<ScansList />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/docs" element={<Placeholder title="Documentation" />} />
            <Route path="/settings" element={<Settings />} />

            {/* Legacy/Utility routes */}
            <Route path="/upload" element={<Upload />} />
            <Route path="/analysis/:jobId" element={<AnalysisLegacy />} />
            <Route path="/graph/:jobId" element={<GraphViewer />} />
            <Route path="/taint/:taintJobId" element={<TaintReport />} />
            <Route path="/graph/taint/:taintJobId" element={<GraphViewer taintMode />} />

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
