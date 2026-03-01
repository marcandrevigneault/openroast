<script lang="ts">
  import type { SessionState } from "$lib/types/ws-messages";

  interface Props {
    sessionState: SessionState;
    onstart?: () => void;
    onstop?: () => void;
    onrecord?: () => void;
    onstoprecord?: () => void;
  }

  let { sessionState, onstart, onstop, onrecord, onstoprecord }: Props =
    $props();
</script>

<div class="session-controls">
  {#if sessionState === "idle"}
    <button class="btn btn-monitor" onclick={onstart}>
      <span class="icon">&#9654;</span> Monitor
    </button>
  {:else if sessionState === "monitoring"}
    <button class="btn btn-record" onclick={onrecord}>
      <span class="icon record-dot">&#9679;</span> Record
    </button>
    <button class="btn btn-stop" onclick={onstop}>
      <span class="icon">&#9632;</span> Stop
    </button>
  {:else if sessionState === "recording"}
    <button class="btn btn-stop-record" onclick={onstoprecord}>
      <span class="icon recording-dot">&#9679;</span> Stop Recording
    </button>
  {:else}
    <button class="btn btn-monitor" onclick={onstart}>
      <span class="icon">&#9654;</span> New Session
    </button>
  {/if}
</div>

<style>
  .session-controls {
    display: flex;
    gap: 8px;
  }

  .btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 18px;
    border: none;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition:
      background-color 0.15s,
      transform 0.1s;
  }

  .btn:hover {
    transform: scale(1.02);
  }

  .btn:active {
    transform: scale(0.98);
  }

  .icon {
    font-size: 0.7rem;
  }

  .btn-monitor {
    background: #2e7d32;
    color: white;
  }

  .btn-monitor:hover {
    background: #388e3c;
  }

  .btn-record {
    background: rgba(79, 195, 247, 0.15);
    border: 1px solid #4fc3f7;
    color: #4fc3f7;
  }

  .btn-record:hover {
    background: rgba(79, 195, 247, 0.25);
  }

  .record-dot {
    color: #4fc3f7;
  }

  .btn-stop {
    background: #424242;
    color: #ccc;
  }

  .btn-stop:hover {
    background: #555;
  }

  .btn-stop-record {
    background: #c62828;
    color: white;
    animation: rec-glow 3s ease-in-out infinite;
  }

  .btn-stop-record:hover {
    background: #d32f2f;
    animation: none;
  }

  .recording-dot {
    animation: pulse 3s ease-in-out infinite;
  }

  @keyframes rec-glow {
    0%,
    100% {
      background: #c62828;
    }
    50% {
      background: #8e1c1c;
    }
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.4;
    }
  }

  @media (max-width: 480px) {
    .btn {
      padding: 10px 14px;
      font-size: 0.8rem;
    }
  }
</style>
