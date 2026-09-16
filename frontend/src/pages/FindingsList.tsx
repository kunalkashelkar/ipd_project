import React from 'react';
import { ShieldAlert, FolderOpen } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  PageHeader,
  EmptyState,
  Button,
} from '../components/ui';

export default function FindingsList() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Global Security Findings"
        description="Consolidated vulnerability findings, severity classifications, and explainability records across your workspace."
      />

      <EmptyState
        icon={<ShieldAlert className="w-8 h-8 text-muted-foreground/60" />}
        title="No Security Findings Recorded"
        description="Vulnerability findings are evaluated per project scan. Once code property graph extraction and ML classification run on your project repositories (Phases 4 & 5), detected vulnerabilities will be cataloged here."
        action={
          <Button onClick={() => navigate('/projects')} className="gap-2">
            <FolderOpen className="w-4 h-4" /> Go to Projects
          </Button>
        }
      />
    </div>
  );
}
