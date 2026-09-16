import React from 'react';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { FileText, Download, FolderOpen } from 'lucide-react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';

export default function Reports() {
  const reports: any[] = []; // Scan-specific reports loaded when scans exist

  const handleGenerateReportClick = () => {
    toast('Report generation requires completed scans. Go to Projects, upload code, and run a security scan first.', {
      icon: 'ℹ️',
      duration: 5000,
    });
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight">Compliance & Reports</h1>
          <p className="text-muted-foreground mt-1">Export executive vulnerability summaries and audit reports.</p>
        </div>
        <Button onClick={handleGenerateReportClick} className="gap-2">
          <Download className="w-4 h-4" /> Generate New Report
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {reports.length === 0 ? (
            <div className="text-center py-16 px-4">
              <div className="w-12 h-12 rounded-full bg-muted/60 flex items-center justify-center mx-auto mb-3">
                <FileText className="w-6 h-6 text-muted-foreground/60" />
              </div>
              <h3 className="text-base font-semibold text-foreground">No reports generated yet</h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                Compliance audit summaries, PDF reports, and JSON exports are generated against completed scans. Run your first project scan to enable export.
              </p>
              <div className="mt-5 flex justify-center gap-3">
                <Link to="/projects">
                  <Button variant="outline" size="sm" className="gap-1.5">
                    <FolderOpen className="w-4 h-4" /> Go to Projects
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {reports.map((report) => (
                <div key={report.id} className="p-4 flex items-center justify-between hover:bg-muted/10 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <FileText className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-medium text-foreground">{report.title}</h3>
                      <p className="text-sm text-muted-foreground">Generated on {new Date(report.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-code text-muted-foreground uppercase">{report.format}</span>
                    <Button variant="ghost" size="sm">Download</Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
