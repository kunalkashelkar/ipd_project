// ============================================================
// useScanProgress — Live scan progress via WebSocket + polling
// ============================================================

import { useCallback, useEffect, useRef, useState } from 'react';
import { ScanStatus } from '../types';
import { scanService } from '../services/scanService';
import { authStorage } from '../services/authStorage';

interface ScanProgressState {
  status: ScanStatus;
  progress: number;
  currentStage: string | null;
  errorMessage: string | null;
  isConnected: boolean;
}

const POLL_INTERVAL = 3000; // 3 seconds

export function useScanProgress(scanId: string | null) {
  const [state, setState] = useState<ScanProgressState>({
    status: 'queued',
    progress: 0,
    currentStage: null,
    errorMessage: null,
    isConnected: false,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  // ── HTTP Polling Fallback ────────────────────────────────

  const pollStatus = useCallback(async () => {
    if (!scanId || !mountedRef.current) return;

    try {
      const data = await scanService.getScanStatus(scanId);
      if (!mountedRef.current) return;

      setState((prev) => ({
        ...prev,
        status: data.status,
        progress: data.progress ?? prev.progress,
        currentStage: data.current_stage ?? prev.currentStage,
        errorMessage: data.error_message ?? null,
      }));

      // Stop polling if scan is terminal
      if (['completed', 'failed', 'cancelled', 'timed_out'].includes(data.status)) {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }
    } catch {
      // Silently ignore polling errors — will retry next interval
    }
  }, [scanId]);

  // ── WebSocket Connection ─────────────────────────────────

  const connectWebSocket = useCallback(() => {
    if (!scanId) return;

    // Read token via authStorage abstraction
    const token = authStorage.getAccessToken();

    if (!token) {
      // No token — rely on polling
      startPolling();
      return;
    }

    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

    try {
      const ws = new WebSocket(`${wsUrl}/ws?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setState((prev) => ({ ...prev, isConnected: true }));
        // Note: Polling is intentionally kept active as a reliable background heartbeat
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const msg = JSON.parse(event.data);
          // Only process messages for our scan
          if (msg.scan_id === scanId || msg.type === 'scan_progress') {
            setState((prev) => ({
              ...prev,
              status: msg.status ?? prev.status,
              progress: msg.progress ?? prev.progress,
              currentStage: msg.current_stage ?? msg.stage ?? prev.currentStage,
              errorMessage: msg.error_message ?? prev.errorMessage,
            }));
            if (['completed', 'failed', 'cancelled', 'timed_out'].includes(msg.status)) {
              if (pollRef.current) {
                clearInterval(pollRef.current);
                pollRef.current = null;
              }
            }
          }
        } catch {
          // Not JSON — ignore
        }
      };

      ws.onerror = () => {
        if (mountedRef.current) {
          setState((prev) => ({ ...prev, isConnected: false }));
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setState((prev) => ({ ...prev, isConnected: false }));
      };
    } catch {
      // WebSocket creation failed — polling is already active
    }
  }, [scanId]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  function startPolling() {
    if (pollRef.current) return; // Already polling
    pollStatus(); // Immediate first poll
    pollRef.current = setInterval(pollStatus, POLL_INTERVAL);
  }

  // ── Lifecycle ────────────────────────────────────────────

  useEffect(() => {
    mountedRef.current = true;

    if (scanId) {
      // Start polling immediately as reliable primary progress mechanism
      startPolling();
      // Connect WebSocket for low-latency live event stream
      connectWebSocket();
    }

    return () => {
      mountedRef.current = false;
      if (wsRef.current) {
        const wsToClose = wsRef.current;
        wsRef.current = null;
        if (wsToClose.readyState === WebSocket.OPEN) {
          wsToClose.close(1000, 'Component unmounted');
        } else if (wsToClose.readyState === WebSocket.CONNECTING) {
          wsToClose.onopen = () => {
            wsToClose.close(1000, 'Component unmounted');
          };
        }
      }
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [scanId, connectWebSocket]);

  return state;
}
