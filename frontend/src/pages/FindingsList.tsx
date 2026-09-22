import React, { useEffect, useState } from 'react';
import { ShieldAlert, Layers, Loader2, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  PageHeader,
  EmptyState,
  Button,
} from '../components/ui';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { findingService } from '../services/findingService';
import { FindingListItem } from '../types';

import { getResultsUrl } from '../utils/routes';

export default function FindingsList() {
  const [findings, setFindings] = useState<FindingListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadFindings() {
      setLoading(true);
      try {
        const data = await findingService.getGlobalFindings({ page: 1, page_size: 50 });
        setFindings(data.items);
      } catch {
        // Errors are handled by the API interceptor
      } finally {
        setLoading(false);
      }
    }
    loadFindings();
  }, []);

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      <PageHeader
        title="Global Security Findings"
        description="Consolidated vulnerability findings, severity classifications, and explainability records across your workspace."
      />

      <Card>
        <CardHeader>
          <CardTitle>All Findings</CardTitle>
          <CardDescription>A global view of all security vulnerabilities across projects.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : findings.length === 0 ? (
            <EmptyState
              icon={<ShieldAlert className="w-8 h-8 text-muted-foreground/60" />}
              title="No Security Findings Recorded"
              description="No vulnerabilities have been found yet across your project scans."
              action={
                <Link to="/projects">
                  <Button className="gap-2">
                    <Layers className="w-4 h-4" /> Go to Projects
                  </Button>
                </Link>
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] font-semibold text-muted-foreground uppercase bg-muted/30 border-y border-border">
                  <tr>
                    <th className="px-5 py-3 font-medium">Severity</th>
                    <th className="px-5 py-3 font-medium">Finding Title & Location</th>
                    <th className="px-5 py-3 font-medium">CWE</th>
                    <th className="px-5 py-3 font-medium">Project</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {findings.map((finding) => {
                    const findingDisplayId = finding.public_id || finding.id;
                    const projectDisplay = finding.project_name || finding.project_public_id || finding.project_id;
                    const resultsUrl = getResultsUrl(
                      finding.project_public_id || finding.project_id,
                      finding.latest_scan_public_id || finding.latest_scan_id,
                      finding.public_id || finding.id
                    );

                    const severityColor =
                      finding.severity === 'critical'
                        ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                        : finding.severity === 'high'
                        ? 'bg-orange-500/10 text-orange-400 border-orange-500/30'
                        : finding.severity === 'medium'
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                        : 'bg-sky-500/10 text-sky-400 border-sky-500/30';

                    return (
                      <tr key={finding.id} className="hover:bg-hover transition-colors group">
                        <td className="px-5 py-3">
                          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-semibold uppercase border ${severityColor}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${
                              finding.severity === 'critical' ? 'bg-rose-500' :
                              finding.severity === 'high' ? 'bg-orange-500' :
                              finding.severity === 'medium' ? 'bg-amber-500' : 'bg-sky-500'
                            }`} />
                            {finding.severity}
                          </span>
                        </td>
                        <td className="px-5 py-3">
                          <div className="font-medium text-foreground text-xs group-hover:text-primary transition-colors line-clamp-1" title={finding.title}>
                            {finding.title}
                          </div>
                          <div className="text-[11px] text-muted-foreground font-mono mt-0.5 flex items-center gap-2">
                            <span>{findingDisplayId}</span>
                            {finding.latest_file_path && (
                              <>
                                <span>•</span>
                                <span className="truncate max-w-[280px]">
                                  {finding.latest_file_path}{finding.latest_line_number ? `:${finding.latest_line_number}` : ''}
                                </span>
                              </>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          {finding.cwe_id ? (
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted/60 text-muted-foreground border border-border/40">
                              {finding.cwe_id}
                            </span>
                          ) : (
                            <span className="text-muted-foreground/50">—</span>
                          )}
                        </td>
                        <td className="px-5 py-3 font-medium text-foreground">
                          {projectDisplay}
                        </td>
                        <td className="px-5 py-3">
                          <Badge variant={finding.status === 'open' ? 'destructive' : 'safe'} className="text-[10px] capitalize">
                            {finding.status}
                          </Badge>
                        </td>
                        <td className="px-5 py-3 text-right">
                          <Link to={resultsUrl}>
                            <Button variant="ghost" size="sm" className="h-7 text-xs gap-1 group-hover:text-primary">
                              Investigate <ArrowRight className="w-3 h-3 ml-0.5" />
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
