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
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted-foreground uppercase bg-background border-y border-border">
                  <tr>
                    <th className="px-6 py-4 font-medium">Scan ID</th>
                    <th className="px-6 py-4 font-medium">Project</th>
                    <th className="px-6 py-4 font-medium">Status</th>
                    <th className="px-6 py-4 font-medium">Progress</th>
                    <th className="px-6 py-4 font-medium">Started</th>
                    <th className="px-6 py-4 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {scans.map((scan, i) => (
                    <tr key={scan.id} className={`border-b border-border/50 hover:bg-muted/30 transition-colors ${i === scans.length - 1 ? 'border-b-0' : ''}`}>
                      <td className="px-6 py-4 font-medium text-foreground font-mono text-xs">{scan.public_id || scan.id}</td>
                      <td className="px-6 py-4">
                        <Link
                          to={getProjectUrl(scan.project_public_id || scan.project_id)}
                          className="hover:underline text-primary font-medium"
                        >
                          {scan.project_name || scan.project_public_id || scan.project_id}
                        </Link>
                      </td>
                      <td className="px-6 py-4">
                        <Badge
                          variant={
                            scan.status === 'completed' ? 'safe' :
                            scan.status === 'failed' ? 'destructive' :
                            'warning'
                          }
                        >
                          {scan.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-muted-foreground">
                        {scan.progress}%
                      </td>
                      <td className="px-6 py-4 text-muted-foreground">
                        {new Date(scan.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4">
                        <Link to={getResultsUrl(scan.project_public_id || scan.project_id, scan.public_id || scan.id)}>
                          <Button variant="outline" size="sm">
                            View <ArrowRight className="w-3 h-3 ml-1" />
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
