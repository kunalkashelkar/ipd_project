import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { BarChart3, TrendingUp, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function Analytics() {
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold font-display tracking-tight">Security Analytics</h1>
        <p className="text-muted-foreground mt-1">Platform-wide vulnerability trends and risk metrics.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Total Scans</p>
                <div className="text-3xl font-bold text-foreground">1,284</div>
              </div>
              <div className="p-2 bg-primary/10 rounded-lg">
                <BarChart3 className="w-5 h-5 text-primary" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm text-emerald-500">
              <TrendingUp className="w-4 h-4 mr-1" />
              <span>12% from last month</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Critical Issues</p>
                <div className="text-3xl font-bold text-foreground">42</div>
              </div>
              <div className="p-2 bg-destructive/10 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-destructive" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm text-destructive">
              <TrendingUp className="w-4 h-4 mr-1" />
              <span>+5 this week</span>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Avg Risk Score</p>
                <div className="text-3xl font-bold text-foreground">A-</div>
              </div>
              <div className="p-2 bg-emerald-500/10 rounded-lg">
                <ShieldCheck className="w-5 h-5 text-emerald-500" />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm text-muted-foreground">
              <span>Platform wide</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="min-h-[400px] flex items-center justify-center border-dashed">
          <div className="text-center text-muted-foreground">
            <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p>Vulnerability Trends Over Time</p>
            <p className="text-xs mt-2">D3.js / Recharts visualization component loads here</p>
          </div>
        </Card>
        <Card className="min-h-[400px] flex items-center justify-center border-dashed">
          <div className="text-center text-muted-foreground">
            <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p>Issues by CWE Category</p>
            <p className="text-xs mt-2">Pie/Donut chart component loads here</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
