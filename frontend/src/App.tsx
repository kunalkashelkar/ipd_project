import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AppShell, PublicLayout } from './layouts/AppShell';
import { Spinner } from './components/ui';

// Lazy-loaded pages
const Landing = lazy(() => import('./pages/Landing'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Documentation = lazy(() => import('./pages/Documentation'));

const Dashboard = lazy(() => import('./pages/Dashboard'));
const ProjectsList = lazy(() => import('./pages/projects/ProjectsList'));
const CreateProject = lazy(() => import('./pages/projects/CreateProject'));
const ProjectDetail = lazy(() => import('./pages/projects/ProjectDetail'));
const ConnectRepo = lazy(() => import('./pages/projects/ConnectRepo'));
const ScanConfig = lazy(() => import('./pages/projects/ScanConfig'));
const ScanProgress = lazy(() => import('./pages/projects/ScanProgress'));
const ScanResultsWorkspace = lazy(() => import('./pages/projects/ScanResultsWorkspace'));
const SnapshotDetail = lazy(() => import('./pages/projects/SnapshotDetail'));
const { ProjectScans, ProjectFindings, ProjectReports, ProjectSettings } = {
  ProjectScans: lazy(() => import('./pages/projects/ProjectSubPages').then(m => ({ default: m.ProjectScans }))),
  ProjectFindings: lazy(() => import('./pages/projects/ProjectSubPages').then(m => ({ default: m.ProjectFindings }))),
  ProjectReports: lazy(() => import('./pages/projects/ProjectSubPages').then(m => ({ default: m.ProjectReports }))),
  ProjectSettings: lazy(() => import('./pages/projects/ProjectSubPages').then(m => ({ default: m.ProjectSettings }))),
};

const ScansList = lazy(() => import('./pages/ScansList'));
const FindingsList = lazy(() => import('./pages/FindingsList'));
const Reports = lazy(() => import('./pages/Reports'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Integrations = lazy(() => import('./pages/Integrations'));
const Team = lazy(() => import('./pages/Team'));
const Notifications = lazy(() => import('./pages/Notifications'));
const Settings = lazy(() => import('./pages/Settings'));

const AcceptInvitation = lazy(() => import('./pages/AcceptInvitation'));
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));

function PageFallback() {
  return (
    <div className="h-[60vh] w-full flex items-center justify-center">
      <Spinner size="lg" />
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
          },
        }}
      />
      <Suspense fallback={<div className="h-screen w-screen bg-background flex items-center justify-center"><Spinner size="lg" /></div>}>
        <Routes>
          {/* Public Routes */}
          <Route element={<PublicLayout />}>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/invitations/accept" element={<AcceptInvitation />} />
            <Route path="/invite" element={<AcceptInvitation />} />
            <Route path="/documentation" element={<Documentation />} />
            <Route path="/docs" element={<Navigate to="/documentation" replace />} />
          </Route>

          {/* Authenticated Application Routes */}
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<Dashboard />} />

            {/* Project Context Routes */}
            <Route path="/projects" element={<ProjectsList />} />
            <Route path="/projects/create" element={<CreateProject />} />
            <Route path="/projects/:projectId" element={<ProjectDetail />} />
            <Route path="/projects/:projectId/repository" element={<ConnectRepo />} />
            <Route path="/projects/:projectId/connect" element={<Navigate to="repository" replace />} />
            <Route path="/projects/:projectId/snapshots/:snapshotId" element={<SnapshotDetail />} />
            <Route path="/projects/:projectId/scan-config" element={<ScanConfig />} />
            <Route path="/projects/:projectId/scan-progress/:scanId" element={<ScanProgress />} />
            <Route path="/projects/:projectId/scan-progress" element={<ScanProgress />} />
            <Route path="/projects/:projectId/scans" element={<ProjectScans />} />
            <Route path="/projects/:projectId/scans/:scanId" element={<ScanResultsWorkspace />} />
            <Route path="/projects/:projectId/scans/:scanId/results" element={<ScanResultsWorkspace />} />
            <Route path="/projects/:projectId/findings" element={<ProjectFindings />} />
            <Route path="/projects/:projectId/reports" element={<ProjectReports />} />
            <Route path="/projects/:projectId/settings" element={<ProjectSettings />} />
            <Route path="/projects/:projectId/results" element={<ScanResultsWorkspace />} />

            {/* Global Domain Routes */}
            <Route path="/scans" element={<ScansList />} />
            <Route path="/findings" element={<FindingsList />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/team" element={<Team />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/settings" element={<Settings />} />

            {/* Catch-all redirect */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
