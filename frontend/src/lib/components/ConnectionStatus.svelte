<script lang="ts">
  import type { DriverState, SessionState } from "$lib/types/ws-messages";

  interface Props {
    driverState: DriverState;
    sessionState: SessionState;
  }

  let { driverState, sessionState }: Props = $props();

  let statusColor = $derived(
    driverState === "connected"
      ? "#4caf50"
      : driverState === "connecting"
        ? "#ff9800"
        : driverState === "error"
          ? "#f44336"
          : "#666",
  );

  let statusLabel = $derived(
    driverState === "connected"
      ? sessionState === "recording"
        ? "Recording"
        : sessionState === "monitoring"
          ? "Monitoring"
          : "Connected"
      : driverState === "connecting"
        ? "Connecting..."
        : driverState === "error"
          ? "Error"
          : "Disconnected",
  );
</script>

<div class="connection-status">
  <span class="dot" style="background-color: {statusColor}"></span>
  <span class="label">{statusLabel}</span>
</div>

<style>
  .connection-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 12px;
    border-radius: 12px;
    background: #1a1a2e;
    font-size: 0.8rem;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .label {
    color: #ccc;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.75rem;
  }
</style>
