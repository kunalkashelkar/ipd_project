import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';
import { Bell, ShieldAlert, CheckCircle, Info, RefreshCw, CheckCheck } from 'lucide-react';
import { notificationService } from '../services/notificationService';
import { Notification } from '../types';
import toast from 'react-hot-toast';

export default function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMarkingAll, setIsMarkingAll] = useState(false);

  const fetchNotifications = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await notificationService.getNotifications({ page: 1, page_size: 50 });
      setNotifications(data?.items || []);
    } catch (err: any) {
      setError(
        err?.response?.data?.message ||
        err?.message ||
        'Failed to load notifications'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleMarkAsRead = async (id: string) => {
    try {
      await notificationService.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
      toast.success('Marked as read');
    } catch {
      toast.error('Failed to mark notification as read');
    }
  };

  const handleMarkAllRead = async () => {
    setIsMarkingAll(true);
    try {
      await notificationService.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      toast.success('All notifications marked as read');
    } catch {
      toast.error('Failed to mark all as read');
    } finally {
      setIsMarkingAll(false);
    }
  };

  const hasUnread = notifications.some((n) => !n.read);

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight flex items-center gap-2.5">
            <Bell className="w-8 h-8 text-primary" /> Notifications
          </h1>
          <p className="text-muted-foreground mt-1">
            Real-time security scan events, organization updates, and access logs.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchNotifications}
            disabled={isLoading}
            className="gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
          {notifications.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleMarkAllRead}
              disabled={isMarkingAll || !hasUnread}
              className="gap-1.5"
            >
              <CheckCheck className="w-4 h-4" /> Mark All as Read
            </Button>
          )}
        </div>
      </div>

      {isLoading ? (
        <Card className="p-16 text-center">
          <div className="flex flex-col items-center justify-center gap-3">
            <Spinner size="lg" />
            <p className="text-sm font-medium text-foreground">Loading notifications...</p>
            <p className="text-xs text-muted-foreground">Retrieving persistent activity alerts</p>
          </div>
        </Card>
      ) : error ? (
        <Card className="p-12 text-center border-destructive/30 bg-destructive/5">
          <div className="flex flex-col items-center justify-center gap-3 max-w-md mx-auto">
            <ShieldAlert className="w-8 h-8 text-destructive" />
            <div>
              <h3 className="text-sm font-semibold text-foreground">Failed to load notifications</h3>
              <p className="text-xs text-muted-foreground mt-1">{error}</p>
            </div>
            <Button size="sm" variant="outline" onClick={fetchNotifications} className="gap-2 mt-2">
              <RefreshCw className="w-3.5 h-3.5" /> Retry
            </Button>
          </div>
        </Card>
      ) : notifications.length === 0 ? (
        <Card className="p-16 text-center">
          <div className="flex flex-col items-center justify-center gap-3 max-w-sm mx-auto">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Bell className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-foreground">You're all caught up.</h3>
            <p className="text-xs text-muted-foreground">
              No notifications at this time. Activity from security scans and workspace invitations will appear here.
            </p>
          </div>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {notifications.map((notif) => (
                <div
                  key={notif.id}
                  className={`p-4 flex gap-4 ${
                    !notif.read ? 'bg-primary/5' : 'hover:bg-muted/10'
                  } transition-colors`}
                >
                  <div className="mt-1 flex-shrink-0">
                    {notif.type === 'warning' && <ShieldAlert className="w-5 h-5 text-warning" />}
                    {notif.type === 'info' && <Info className="w-5 h-5 text-primary" />}
                    {notif.type === 'success' && <CheckCircle className="w-5 h-5 text-emerald-500" />}
                    {notif.type === 'error' && <ShieldAlert className="w-5 h-5 text-destructive" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start mb-1">
                      <h3
                        className={`font-medium text-sm ${
                          !notif.read ? 'text-foreground font-semibold' : 'text-foreground/80'
                        }`}
                      >
                        {notif.title}
                      </h3>
                      <span className="text-xs text-muted-foreground shrink-0 ml-2">
                        {notif.timestamp ? new Date(notif.timestamp).toLocaleString() : ''}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">{notif.message}</p>
                    {!notif.read && (
                      <div className="mt-2 flex items-center gap-2">
                        <button
                          onClick={() => handleMarkAsRead(notif.id)}
                          className="text-[11px] text-primary hover:underline font-medium"
                        >
                          Mark as read
                        </button>
                      </div>
                    )}
                  </div>
                  {!notif.read && (
                    <div className="w-2 h-2 rounded-full bg-primary mt-2 flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
