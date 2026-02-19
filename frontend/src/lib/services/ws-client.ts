/**
 * WebSocket client for real-time machine data.
 *
 * Manages a single connection to /ws/live/{machineId}, handles
 * reconnection with exponential backoff, and provides methods
 * to send control/session commands.
 */

import type { ClientMessage, ServerMessage } from "$lib/types/ws-messages";

export type WSClientState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

export interface WSClientCallbacks {
  onMessage: (msg: ServerMessage) => void;
  onStateChange: (state: WSClientState) => void;
}

const MIN_RECONNECT_MS = 1000;
const MAX_RECONNECT_MS = 30000;
const JITTER_FACTOR = 0.3;

export class WSClient {
  private ws: WebSocket | null = null;
  private machineId: string;
  private callbacks: WSClientCallbacks;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = MIN_RECONNECT_MS;
  private intentionalClose = false;
  private _state: WSClientState = "disconnected";
  private lastTimestampMs = 0;

  constructor(machineId: string, callbacks: WSClientCallbacks) {
    this.machineId = machineId;
    this.callbacks = callbacks;
  }

  get state(): WSClientState {
    return this._state;
  }

  connect(): void {
    if (this.ws) return;
    this.intentionalClose = false;
    this.setState("connecting");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/live/${this.machineId}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.setState("connected");
      this.reconnectDelay = MIN_RECONNECT_MS;

      // If we have history, request sync
      if (this.lastTimestampMs > 0) {
        this.send({
          type: "command",
          action: "sync",
          last_timestamp_ms: this.lastTimestampMs,
        });
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as ServerMessage;

        // Track last timestamp for reconnect sync
        if (msg.type === "temperature") {
          this.lastTimestampMs = msg.timestamp_ms;
        }

        this.callbacks.onMessage(msg);
      } catch {
        // Ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      if (!this.intentionalClose) {
        this.setState("disconnected");
        this.scheduleReconnect();
      } else {
        this.setState("disconnected");
      }
    };

    this.ws.onerror = () => {
      this.setState("error");
    };
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.cancelReconnect();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setState("disconnected");
  }

  send(msg: ClientMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  private setState(state: WSClientState): void {
    this._state = state;
    this.callbacks.onStateChange(state);
  }

  private scheduleReconnect(): void {
    this.cancelReconnect();

    const jitter = 1 + (Math.random() * 2 - 1) * JITTER_FACTOR;
    const delay = Math.min(this.reconnectDelay * jitter, MAX_RECONNECT_MS);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.ws = null;
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_MS);
      this.connect();
    }, delay);
  }

  private cancelReconnect(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
