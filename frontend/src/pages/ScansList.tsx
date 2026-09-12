import React, { useEffect, useState } from 'react';
import { Activity, Layers, Loader2, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Link } from 'react-router-dom';
import { scanService } from '../services/scanService';
import { Scan } from '../types';

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
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Scans</h1>
        <p className="text-muted-foreground mt-1">Monitor all security scan executions across your projects.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Scans</CardTitle>
          <CardDescription>A global view of all analysis pipelines.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : scans.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Layers className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p className="font-medium">No scans yet</p>
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
                    <th className="px-6 py-4 font-medium">Status</th>
                    <th className="px-6 py-4 font-medium">Progress</th>
                    <th className="px-6 py-4 font-medium">Started</th>
                    <th className="px-6 py-4 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {scans.map((scan, i) => (
                    <tr key={scan.id} className={`border-b border-border/50 hover:bg-muted/30 transition-colors ${i === scans.length - 1 ? 'border-b-0' : ''}`}>
                      <td className="px-6 py-4 font-medium text-foreground font-mono text-xs">{scan.id.substring(0, 8)}...</td>
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
                        <Link to={`/projects/${scan.project_id}/results?scan_id=${scan.id}`}>
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
