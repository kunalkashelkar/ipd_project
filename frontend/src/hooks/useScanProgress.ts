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
      if (['completed', 'failed', 'cancelled'].includes(data.status)) {
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
      // No token — fall back to polling
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
        // Stop polling if WS connects
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
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
          }
        } catch {
          // Not JSON — ignore
        }
      };

      ws.onerror = () => {
        // WS failed — fall back to polling
        if (mountedRef.current) {
          setState((prev) => ({ ...prev, isConnected: false }));
          startPolling();
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setState((prev) => ({ ...prev, isConnected: false }));
        // Fall back to polling on close
        startPolling();
      };
    } catch {
      // WebSocket creation failed — fall back to polling
      startPolling();
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
      // Try WebSocket first, falls back to polling internally
      connectWebSocket();
      // Also start polling as a safety net (WS may take time to connect)
      startPolling();
    }

    return () => {
      mountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [scanId, connectWebSocket]);

  return state;
}
