import React from 'react';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Bell, ShieldAlert, CheckCircle, Info } from 'lucide-react';

export default function Notifications() {
  const notifications = [
    { id: 1, title: 'Scan Completed', message: 'Project "Authentication Service" scan finished. 4 new vulnerabilities found.', type: 'alert', time: '10 min ago', isNew: true },
    { id: 2, title: 'System Update', message: 'Hybrid XAI model weights updated to version 2.4.1.', type: 'info', time: '2 hours ago', isNew: true },
    { id: 3, title: 'Risk Score Improved', message: 'Project "Payment Gateway" risk score improved to A after recent fixes.', type: 'success', time: '1 day ago', isNew: false },
    { id: 4, title: 'Scan Failed', message: 'Unable to parse CPG for repository "Legacy App". Verify permissions.', type: 'error', time: '2 days ago', isNew: false },
  ];

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight flex items-center gap-2">
            <Bell className="w-8 h-8" /> Notifications
          </h1>
          <p className="text-muted-foreground mt-1">Updates on your scans, system alerts, and platform news.</p>
        </div>
        <Button variant="outline">Mark All as Read</Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="divide-y divide-border">
            {notifications.map((notif) => (
              <div key={notif.id} className={`p-4 flex gap-4 ${notif.isNew ? 'bg-primary/5' : 'hover:bg-muted/10'} transition-colors`}>
                <div className="mt-1 flex-shrink-0">
                  {notif.type === 'alert' && <ShieldAlert className="w-5 h-5 text-warning" />}
                  {notif.type === 'info' && <Info className="w-5 h-5 text-primary" />}
                  {notif.type === 'success' && <CheckCircle className="w-5 h-5 text-emerald-500" />}
                  {notif.type === 'error' && <ShieldAlert className="w-5 h-5 text-destructive" />}
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start mb-1">
                    <h3 className={`font-medium ${notif.isNew ? 'text-foreground' : 'text-foreground/80'}`}>{notif.title}</h3>
                    <span className="text-xs text-muted-foreground">{notif.time}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{notif.message}</p>
                </div>
                {notif.isNew && (
                  <div className="w-2 h-2 rounded-full bg-primary mt-2 flex-shrink-0" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
