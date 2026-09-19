import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Spinner } from '../components/ui/Spinner';
import {
  Bell,
  ShieldAlert,
  CheckCircle,
  Info,
  RefreshCw,
  CheckCheck,
  ExternalLink,
  AtSign,
  AlertOctagon,
  FileText,
} from 'lucide-react';
import { notificationService } from '../services/notificationService';
import { Notification } from '../types';
import toast from 'react-hot-toast';

export default function Notifications() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMarkingAll, setIsMarkingAll] = useState(false);
  const [filterType, setFilterType] = useState<string>('all');

  const fetchNotifications = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await notificationService.getNotifications({
        page: 1,
        page_size: 50,
      });
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

  const handleNavigate = (notif: Notification) => {
    const url = notif.link_url || notif.link;
    if (url) {
      if (!notif.read) {
        handleMarkAsRead(notif.id);
      }
      navigate(url);
    }
  };

  const filteredNotifications = notifications.filter((n) => {
    if (filterType === 'all') return true;
    if (filterType === 'unread') return !n.read;
    return n.type === filterType;
  });

  const hasUnread = notifications.some((n) => !n.read);

  const getEventIcon = (type: string, severity?: string) => {
    if (type === 'critical_finding' || severity === 'critical') {
      return <AlertOctagon className="w-5 h-5 text-rose-500" />;
    }
    if (type === 'user_mentioned' || type === 'finding_assigned') {
      return <AtSign className="w-5 h-5 text-sky-500" />;
    }
    if (type === 'report_ready') {
      return <FileText className="w-5 h-5 text-amber-500" />;
    }
    if (type === 'fix_validated' || type === 'fix_ready') {
      return <CheckCircle className="w-5 h-5 text-emerald-500" />;
    }
    if (type === 'scan_completed') {
      return <CheckCircle className="w-5 h-5 text-emerald-500" />;
    }
    return <Info className="w-5 h-5 text-primary" />;
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-display tracking-tight flex items-center gap-2.5">
            <Bell className="w-7 h-7 text-primary" /> Notifications
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Authoritative security events, scan completions, finding assignments, and collaboration mentions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchNotifications}
            disabled={isLoading}
            className="gap-1.5 h-8 text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
          {notifications.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleMarkAllRead}
              disabled={isMarkingAll || !hasUnread}
              className="gap-1.5 h-8 text-xs"
            >
              <CheckCheck className="w-3.5 h-3.5" /> Mark All Read
            </Button>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-border/40 pb-2 text-xs">
        <button
          onClick={() => setFilterType('all')}
          className={`px-3 py-1 rounded-md transition-colors ${
            filterType === 'all'
              ? 'bg-primary text-primary-foreground font-medium'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          All ({notifications.length})
        </button>
        <button
          onClick={() => setFilterType('unread')}
          className={`px-3 py-1 rounded-md transition-colors ${
            filterType === 'unread'
              ? 'bg-primary text-primary-foreground font-medium'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Unread ({notifications.filter((n) => !n.read).length})
        </button>
        <button
          onClick={() => setFilterType('critical_finding')}
          className={`px-3 py-1 rounded-md transition-colors ${
            filterType === 'critical_finding'
              ? 'bg-primary text-primary-foreground font-medium'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Critical
        </button>
        <button
          onClick={() => setFilterType('scan_completed')}
          className={`px-3 py-1 rounded-md transition-colors ${
            filterType === 'scan_completed'
              ? 'bg-primary text-primary-foreground font-medium'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Scans
        </button>
        <button
          onClick={() => setFilterType('user_mentioned')}
          className={`px-3 py-1 rounded-md transition-colors ${
            filterType === 'user_mentioned'
              ? 'bg-primary text-primary-foreground font-medium'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Mentions
        </button>
      </div>

      {isLoading ? (
        <Card className="p-16 text-center">
          <div className="flex flex-col items-center justify-center gap-3">
            <Spinner size="lg" />
            <p className="text-xs text-muted-foreground">Retrieving persistent activity notifications...</p>
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
      ) : filteredNotifications.length === 0 ? (
        <Card className="p-16 text-center">
          <div className="flex flex-col items-center justify-center gap-3 max-w-sm mx-auto">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Bell className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">You're all caught up</h3>
            <p className="text-xs text-muted-foreground">
              No notifications matching the selected filter. Real-time events from security scans, PR gates, and mentions will appear here.
            </p>
          </div>
        </Card>
      ) : (
        <Card className="border-border/80">
          <CardContent className="p-0">
            <div className="divide-y divide-border/40">
              {filteredNotifications.map((notif) => {
                const targetUrl = notif.link_url || notif.link;
                return (
                  <div
                    key={notif.id}
                    className={`p-4 flex gap-4 ${
                      !notif.read ? 'bg-primary/[0.04]' : 'hover:bg-muted/10'
                    } transition-colors`}
                  >
                    <div className="mt-0.5 flex-shrink-0">
                      {getEventIcon(notif.type, notif.severity)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start mb-1">
                        <h3
                          onClick={() => targetUrl && handleNavigate(notif)}
                          className={`text-xs font-semibold ${
                            targetUrl ? 'cursor-pointer hover:underline text-foreground' : 'text-foreground'
                          } ${!notif.read ? 'font-bold' : ''}`}
                        >
                          {notif.title}
                        </h3>
                        <span className="text-[11px] text-muted-foreground shrink-0 ml-2">
                          {notif.created_at || notif.timestamp
                            ? new Date(notif.created_at || notif.timestamp!).toLocaleString()
                            : ''}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {notif.body || notif.message}
                      </p>

                      <div className="mt-2 flex items-center gap-3">
                        {targetUrl && (
                          <button
                            onClick={() => handleNavigate(notif)}
                            className="text-[11px] text-primary hover:underline font-medium inline-flex items-center gap-1"
                          >
                            Open Resource <ExternalLink className="w-2.5 h-2.5" />
                          </button>
                        )}
                        {!notif.read && (
                          <button
                            onClick={() => handleMarkAsRead(notif.id)}
                            className="text-[11px] text-muted-foreground hover:text-foreground font-medium"
                          >
                            Mark as read
                          </button>
                        )}
                      </div>
                    </div>
                    {!notif.read && (
                      <div className="w-2 h-2 rounded-full bg-primary mt-1.5 flex-shrink-0" />
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
