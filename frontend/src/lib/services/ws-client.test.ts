import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WSClient, type WSClientCallbacks } from "./ws-client";

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  url: string;
  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }

  // Test helpers
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateError() {
    this.onerror?.();
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }
}

describe("WSClient", () => {
  let callbacks: WSClientCallbacks;
  let onMessage: ReturnType<typeof vi.fn>;
  let onStateChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);
    // Mock window.location for URL construction
    vi.stubGlobal("location", { protocol: "http:", host: "localhost:8000" });

    onMessage = vi.fn();
    onStateChange = vi.fn();
    callbacks = {
      onMessage: onMessage as unknown as WSClientCallbacks["onMessage"],
      onStateChange:
        onStateChange as unknown as WSClientCallbacks["onStateChange"],
    };
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("starts in disconnected state", () => {
    const client = new WSClient("machine-1", callbacks);
    expect(client.state).toBe("disconnected");
  });

  it("connects to correct WebSocket URL", () => {
    const client = new WSClient("machine-1", callbacks);
    client.connect();

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toBe(
      "ws://localhost:8000/ws/live/machine-1",
    );
  });

  it("transitions to connecting then connected", () => {
    const client = new WSClient("machine-1", callbacks);
    client.connect();

    expect(onStateChange).toHaveBeenCalledWith("connecting");

    MockWebSocket.instances[0].simulateOpen();
    expect(onStateChange).toHaveBeenCalledWith("connected");
    expect(client.state).toBe("connected");
  });

  it("passes received messages to callback", () => {
    const client = new WSClient("machine-1", callbacks);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();

    const msg = {
      type: "temperature",
      timestamp_ms: 1000,
      et: 210,
      bt: 180,
      et_ror: 5,
      bt_ror: 8,
      extra_channels: {},
    };
    MockWebSocket.instances[0].simulateMessage(msg);

    expect(onMessage).toHaveBeenCalledWith(msg);
  });

  it("sends messages as JSON", () => {
    const client = new WSClient("machine-1", callbacks);
    client.connect();
    const ws = MockWebSocket.instances[0];
    ws.simulateOpen();

    client.send({ type: "control", channel: "burner", value: 0.8 });

    expect(ws.sentMessages).toHaveLength(1);
    expect(JSON.parse(ws.sentMessages[0])).toEqual({
      type: "control",
      channel: "burner",
      value: 0.8,
    });
  });

  it("does not send when not connected", () => {
    const client = new WSClient("machine-1", callbacks);
    client.send({ type: "control", channel: "burner", value: 0.5 });
    // No error thrown, message just dropped
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it("disconnects cleanly", () => {
    const client = new WSClient("machine-1", callbacks);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();

    client.disconnect();

    expect(client.state).toBe("disconnected");
    expect(onStateChange).toHaveBeenLastCalledWith("disconnected");
  });

  it("does not reconnect after intentional disconnect", () => {
    const client = new WSClient("machine-1", callbacks);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();

    client.disconnect();

    // Fast-forward timers — should not reconnect
    vi.advanceTimersByTime(60000);
    expect(MockWebSocket.instances).toHaveLength(1); // Only the original
  });

  it("attempts reconnect on unexpected close", () => {
    const client = new WSClient("machine-1", callbacks);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();

    // Simulate unexpected close
    MockWebSocket.instances[0].simulateClose();
    expect(client.state).toBe("disconnected");

    // Should reconnect after delay
    vi.advanceTimersByTime(2000);
    expect(MockWebSocket.instances.length).toBeGreaterThan(1);
  });

  it("sends sync on reconnect with last timestamp", () => {
    const client = new WSClient("machine-1", callbacks);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();

    // Receive a temperature message to set lastTimestampMs
    MockWebSocket.instances[0].simulateMessage({
      type: "temperature",
      timestamp_ms: 5000,
      et: 200,
      bt: 180,
      et_ror: 0,
      bt_ror: 0,
      extra_channels: {},
    });

    // Simulate unexpected close
    MockWebSocket.instances[0].simulateClose();

    // Reconnect
    vi.advanceTimersByTime(2000);
    const newWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];
    newWs.simulateOpen();

    // Should have sent sync command
    expect(newWs.sentMessages).toHaveLength(1);
    const syncMsg = JSON.parse(newWs.sentMessages[0]);
    expect(syncMsg.action).toBe("sync");
    expect(syncMsg.last_timestamp_ms).toBe(5000);
  });

  it("reports error state on WebSocket error", () => {
    const client = new WSClient("machine-1", callbacks);
    client.connect();
    MockWebSocket.instances[0].simulateError();

    expect(onStateChange).toHaveBeenCalledWith("error");
  });

  it("ignores malformed messages", () => {
    const client = new WSClient("machine-1", callbacks);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();

    // Send invalid JSON
    MockWebSocket.instances[0].onmessage?.({ data: "not json" });

    // Should not crash, no message callback
    expect(onMessage).not.toHaveBeenCalled();
  });

  it("retryNow forces immediate reconnect and resets backoff", () => {
    const client = new WSClient("machine-1", callbacks);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();

    // Simulate error state
    MockWebSocket.instances[0].simulateClose();
    const countBefore = MockWebSocket.instances.length;

    // Retry now — should create a new WebSocket immediately
    client.retryNow();
    expect(MockWebSocket.instances.length).toBe(countBefore + 1);
    expect(client.state).toBe("connecting");
  });
});
