import React, { useEffect, useState } from 'react';
import { Activity, Layers, Loader2, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Link } from 'react-router-dom';
import { scanService } from '../services/scanService';
import { Scan } from '../types';
import { getResultsUrl, getProjectUrl } from '../utils/routes';

export default function ScansList() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadScans() {
      setLoading(true);
      try {
        const data = await scanService.listScans({ page: 1, page_size: 50 });
        setScans(data.items);
      } catch {
        // Errors are handled by the API interceptor
      } finally {
        setLoading(false);
      }
    }
    loadScans();
  }, []);

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-foreground">Scans</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          History of all vulnerability and taint analysis scans executed in this workspace.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Scan Execution History</CardTitle>
          <CardDescription>
            Audit log of pipeline runs with real-time status and finding telemetry.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : scans.length === 0 ? (
            <div className="text-center py-16 px-4 text-muted-foreground">
              <Activity className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm font-medium text-foreground">No scans yet</p>
              <p className="text-sm mt-1">Upload code in a project to start a scan.</p>
              <Link to="/projects">
                <Button className="mt-4" variant="outline">
                  Go to Projects
                </Button>
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] font-semibold text-muted-foreground uppercase bg-muted/30 border-y border-border">
                  <tr>
                    <th className="px-5 py-3 font-medium">Scan ID</th>
                    <th className="px-5 py-3 font-medium">Project</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Progress</th>
                    <th className="px-5 py-3 font-medium">Started</th>
                    <th className="px-5 py-3 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {scans.map((scan) => (
                    <tr key={scan.id} className="hover:bg-hover transition-colors group">
                      <td className="px-5 py-3 font-medium text-foreground font-mono text-xs">
                        <span className="px-2 py-0.5 rounded bg-muted/60 text-foreground border border-border/40">
                          {scan.public_id || scan.id}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <Link
                          to={getProjectUrl(scan.project_public_id || scan.project_id)}
                          className="hover:text-primary font-medium text-foreground transition-colors"
                        >
                          {scan.project_name || scan.project_public_id || scan.project_id}
                        </Link>
                      </td>
                      <td className="px-5 py-3">
                        <Badge
                          variant={
                            scan.status === 'completed' ? 'safe' :
                            scan.status === 'failed' ? 'destructive' :
                            'warning'
                          }
                          className="text-[10px] capitalize"
                        >
                          {scan.status}
                        </Badge>
                      </td>
                      <td className="px-5 py-3 text-muted-foreground font-mono text-[11px]">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 rounded-full bg-muted/60 overflow-hidden">
                            <div
                              className={`h-full ${scan.status === 'completed' ? 'bg-emerald-500' : scan.status === 'failed' ? 'bg-destructive' : 'bg-primary'}`}
                              style={{ width: `${Math.min(100, Math.max(0, scan.progress))}%` }}
                            />
                          </div>
                          <span>{scan.progress}%</span>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-muted-foreground font-mono text-[11px]">
                        {new Date(scan.created_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <Link to={getResultsUrl(scan.project_public_id || scan.project_id, scan.public_id || scan.id)}>
                          <Button variant="ghost" size="sm" className="h-7 text-xs gap-1 group-hover:text-primary">
                            View Results <ArrowRight className="w-3 h-3 ml-0.5" />
                          </Button>
                        </Link>
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
