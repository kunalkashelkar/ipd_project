import React, { useEffect, useState, useCallback } from 'react';
import {
  FileText,
  Download,
  RotateCcw,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Filter,
  Plus,
  Shield,
  Layers,
  FileSpreadsheet,
  Code2,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { projectService } from '../services/projectService';
import { scanService } from '../services/scanService';
import { reportService } from '../services/reportService';
import { Project, Scan, Report } from '../types';
import toast from 'react-hot-toast';

export default function Reports() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [completedScans, setCompletedScans] = useState<Scan[]>([]);
  const [selectedScanId, setSelectedScanId] = useState<string>('');

  const [reportType, setReportType] = useState<'developer' | 'security' | 'executive'>('security');
  const [format, setFormat] = useState<'pdf' | 'html' | 'json' | 'csv'>('pdf');

  const [reports, setReports] = useState<Report[]>([]);
  const [isLoadingReports, setIsLoadingReports] = useState<boolean>(true);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  // 1. Fetch Projects
  useEffect(() => {
    projectService
      .listProjects({ page_size: 100 })
      .then((res) => {
        const items = res.items || [];
        setProjects(items);
        if (items.length > 0) {
          setSelectedProjectId(items[0].public_id || items[0].id);
        }
      })
      .catch((err) => {
        toast.error('Failed to load projects');
      });
  }, []);

  // 2. Fetch Scans for Selected Project
  useEffect(() => {
    if (!selectedProjectId) {
      setCompletedScans([]);
      return;
    }
    scanService
      .listScans({ project_id: selectedProjectId, page_size: 50 })
      .then((res) => {
        const scans = (res.items || []).filter((s) => s.status === 'completed');
        setCompletedScans(scans);
        if (scans.length > 0) {
          setSelectedScanId(scans[0].public_id || scans[0].id);
        } else {
          setSelectedScanId('');
        }
      })
      .catch(() => {
        setCompletedScans([]);
      });
  }, [selectedProjectId]);

  // 3. Fetch Reports
  const fetchReports = useCallback(async () => {
    try {
      const res = await reportService.getReports({ page_size: 50 });
      setReports(res.items || []);
    } catch (err: any) {
      // Don't show toast on background poll
    } finally {
      setIsLoadingReports(false);
    }
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // 4. Polling for in-flight reports
  useEffect(() => {
    const hasActiveReports = reports.some(
      (r) => r.status === 'queued' || r.status === 'generating'
    );
    if (!hasActiveReports) return;

    const interval = setInterval(() => {
      fetchReports();
    }, 3000);
    return () => clearInterval(interval);
  }, [reports, fetchReports]);

  // 5. Request Report
  const handleRequestReport = async () => {
    if (!selectedScanId) {
      toast.error('Please select a completed scan to generate a report');
      return;
    }
    setIsGenerating(true);
    try {
      const newReport = await reportService.requestReport({
        scan_id: selectedScanId,
        report_type: reportType,
        format: format,
      });
      toast.success(`Report ${newReport.public_id} queued for generation`);
      await fetchReports();
    } catch (err: any) {
      toast.error(err?.response?.data?.message || 'Failed to request report generation');
    } finally {
      setIsGenerating(false);
    }
  };

  // 6. Download Report
  const handleDownload = async (report: Report) => {
    setDownloadingId(report.id);
    try {
      const ext = report.format.toLowerCase();
      const filename = `${report.report_type}-report-${report.public_id}.${ext}`;
      await reportService.downloadReport(report.id, filename);
      toast.success(`Report ${filename} downloaded`);
    } catch (err: any) {
      toast.error('Failed to download report artifact');
    } finally {
      setDownloadingId(null);
    }
  };

  // 7. Retry Report
  const handleRetry = async (reportId: string) => {
    try {
      await reportService.retryReport(reportId);
      toast.success('Report generation re-queued');
      await fetchReports();
    } catch (err: any) {
      toast.error('Failed to retry report');
    }
  };

  const getFormatIcon = (fmt: string) => {
    switch (fmt.toLowerCase()) {
      case 'pdf':
        return <FileText className="w-4 h-4 text-rose-500" />;
      case 'html':
        return <Layers className="w-4 h-4 text-amber-500" />;
      case 'json':
        return <Code2 className="w-4 h-4 text-sky-500" />;
      case 'csv':
        return <FileSpreadsheet className="w-4 h-4 text-emerald-500" />;
      default:
        return <FileText className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 gap-1">
            <CheckCircle2 className="w-3 h-3" /> Completed
          </Badge>
        );
      case 'generating':
        return (
          <Badge variant="outline" className="bg-sky-500/10 text-sky-500 border-sky-500/20 gap-1">
            <Loader2 className="w-3 h-3 animate-spin" /> Generating
          </Badge>
        );
      case 'queued':
        return (
          <Badge variant="outline" className="bg-amber-500/10 text-amber-500 border-amber-500/20 gap-1">
            <Clock className="w-3 h-3" /> Queued
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="outline" className="bg-rose-500/10 text-rose-500 border-rose-500/20 gap-1">
            <AlertCircle className="w-3 h-3" /> Failed
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-display tracking-tight text-foreground">
            Compliance & Security Reports
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Generate and export authoritative audit, developer, and executive security reports.
          </p>
        </div>
      </div>

      {/* Report Generation Configuration Card */}
      <Card className="border-border/80">
        <CardHeader className="pb-3 border-b border-border/40">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Plus className="w-4 h-4 text-primary" /> Request New Report
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Project Select */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                Target Project
              </label>
              <select
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.public_id || p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Scan Select */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                Completed Scan
              </label>
              <select
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
                value={selectedScanId}
                onChange={(e) => setSelectedScanId(e.target.value)}
                disabled={completedScans.length === 0}
              >
                {completedScans.length === 0 ? (
                  <option value="">No completed scans found</option>
                ) : (
                  completedScans.map((s) => (
                    <option key={s.id} value={s.public_id || s.id}>
                      {s.public_id} (
                      {s.completed_at
                        ? new Date(s.completed_at).toLocaleDateString()
                        : 'Completed'}
                      )
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* Report Type */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                Report Type
              </label>
              <select
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                value={reportType}
                onChange={(e) => setReportType(e.target.value as any)}
              >
                <option value="developer">Developer (Remediation & Evidence)</option>
                <option value="security">Security (Findings & CWE Analysis)</option>
                <option value="executive">Executive (Posture & Health Score)</option>
              </select>
            </div>

            {/* Format */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                Output Format
              </label>
              <select
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                value={format}
                onChange={(e) => setFormat(e.target.value as any)}
              >
                <option value="pdf">PDF (Printable Report)</option>
                <option value="html">HTML (Standalone Webpage)</option>
                <option value="json">JSON (Machine-Readable v1.0.0)</option>
                <option value="csv">CSV (Spreadsheet RFC-4180)</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Button
              onClick={handleRequestReport}
              disabled={isGenerating || !selectedScanId}
              className="gap-2 text-xs font-medium"
            >
              {isGenerating ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Shield className="w-3.5 h-3.5" />
              )}
              Generate Report
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Generated Reports List */}
      <Card className="border-border/80">
        <CardHeader className="pb-3 border-b border-border/40 flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <FileText className="w-4 h-4 text-primary" /> Generated Report Artifacts
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchReports}
            className="text-xs h-7 text-muted-foreground"
          >
            Refresh
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {isLoadingReports ? (
            <div className="py-16 text-center">
              <Loader2 className="w-6 h-6 animate-spin mx-auto text-primary" />
              <p className="text-xs text-muted-foreground mt-2">Loading reports...</p>
            </div>
          ) : reports.length === 0 ? (
            <div className="py-16 text-center px-4">
              <div className="w-10 h-10 rounded-full bg-muted/60 flex items-center justify-center mx-auto mb-2">
                <FileText className="w-5 h-5 text-muted-foreground/60" />
              </div>
              <h3 className="text-sm font-semibold text-foreground">No reports generated yet</h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                Select a completed scan above and click "Generate Report" to produce PDF, HTML, JSON, or CSV compliance artifacts.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-border/60 bg-muted/30 text-muted-foreground font-medium">
                    <th className="py-2.5 px-4">Report ID</th>
                    <th className="py-2.5 px-4">Type</th>
                    <th className="py-2.5 px-4">Format</th>
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4">Requested</th>
                    <th className="py-2.5 px-4">Completed</th>
                    <th className="py-2.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30 text-foreground">
                  {reports.map((report) => (
                    <tr key={report.id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-xs">
                        {report.public_id}
                      </td>
                      <td className="py-3 px-4 capitalize font-medium">
                        {report.report_type} Report
                      </td>
                      <td className="py-3 px-4">
                        <span className="flex items-center gap-1.5 uppercase font-medium">
                          {getFormatIcon(report.format)}
                          {report.format}
                        </span>
                      </td>
                      <td className="py-3 px-4">{getStatusBadge(report.status)}</td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {report.created_at
                          ? new Date(report.created_at).toLocaleString()
                          : '—'}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {report.generated_at
                          ? new Date(report.generated_at).toLocaleString()
                          : report.error_message ? (
                            <span className="text-rose-500 truncate max-w-xs block" title={report.error_message}>
                              {report.error_message}
                            </span>
                          ) : (
                            '—'
                          )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {report.status === 'completed' ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDownload(report)}
                            disabled={downloadingId === report.id}
                            className="gap-1.5 text-xs h-7"
                          >
                            {downloadingId === report.id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Download className="w-3 h-3" />
                            )}
                            Download
                          </Button>
                        ) : report.status === 'failed' ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleRetry(report.id)}
                            className="gap-1 text-xs h-7 text-amber-500 hover:text-amber-600"
                          >
                            <RotateCcw className="w-3 h-3" /> Retry
                          </Button>
                        ) : (
                          <span className="text-xs text-muted-foreground flex items-center justify-end gap-1">
                            <Loader2 className="w-3 h-3 animate-spin" /> Processing
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
