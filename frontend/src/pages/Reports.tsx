import React from 'react';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { FileText, FolderOpen } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Reports() {
  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight">Compliance & Reports</h1>
          <p className="text-muted-foreground mt-1">Export executive vulnerability summaries and audit reports.</p>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="text-center py-16 px-4">
            <div className="w-12 h-12 rounded-full bg-muted/60 flex items-center justify-center mx-auto mb-3">
              <FileText className="w-6 h-6 text-muted-foreground/60" />
            </div>
            <h3 className="text-base font-semibold text-foreground">Analytics & Reporting (Phase 7)</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
              Automated compliance audit summaries, PDF reports, and JSON exports will be available in Phase 7. Currently, you can investigate individual findings within your project's Results Workspace.
            </p>
            <div className="mt-5 flex justify-center gap-3">
              <Link to="/projects">
                <Button variant="outline" size="sm" className="gap-1.5">
                  <FolderOpen className="w-4 h-4" /> Go to Projects
                </Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
