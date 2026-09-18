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
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted-foreground uppercase bg-background border-y border-border">
                  <tr>
                    <th className="px-6 py-4 font-medium">Finding ID</th>
                    <th className="px-6 py-4 font-medium">Project</th>
                    <th className="px-6 py-4 font-medium">Severity</th>
                    <th className="px-6 py-4 font-medium">Title</th>
                    <th className="px-6 py-4 font-medium">Status</th>
                    <th className="px-6 py-4 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {findings.map((finding, i) => {
                    const findingDisplayId = finding.public_id || finding.id;
                    const projectDisplay = finding.project_name || finding.project_public_id || finding.project_id;
                    const resultsUrl = getResultsUrl(
                      finding.project_public_id || finding.project_id,
                      finding.latest_scan_public_id || finding.latest_scan_id,
                      finding.public_id || finding.id
                    );

                    return (
                      <tr key={finding.id} className={`border-b border-border/50 hover:bg-muted/30 transition-colors ${i === findings.length - 1 ? 'border-b-0' : ''}`}>
                        <td className="px-6 py-4 font-medium text-foreground font-mono text-xs" title={finding.id}>
                          {findingDisplayId}
                        </td>
                        <td className="px-6 py-4">{projectDisplay}</td>
                        <td className="px-6 py-4">
                          <Badge
                            variant={
                              finding.severity === 'critical' || finding.severity === 'high' ? 'destructive' :
                              finding.severity === 'medium' ? 'warning' : 'secondary'
                            }
                          >
                            {finding.severity}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 text-muted-foreground truncate max-w-xs" title={finding.title}>
                          {finding.title}
                        </td>
                        <td className="px-6 py-4">
                          <Badge variant={finding.status === 'open' ? 'destructive' : 'safe'}>{finding.status}</Badge>
                        </td>
                        <td className="px-6 py-4">
                          <Link to={resultsUrl}>
                            <Button variant="outline" size="sm">
                              View <ArrowRight className="w-3 h-3 ml-1" />
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
