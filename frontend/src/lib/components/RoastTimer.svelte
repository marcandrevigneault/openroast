<script lang="ts">
  import type { SessionState } from "$lib/types/ws-messages";

  interface Props {
    sessionState: SessionState;
  }

  let { sessionState }: Props = $props();

  // Wall-clock time the current recording started, or null when not recording.
  let startedAt = $state<number | null>(null);
  // Seconds shown to the user. Driven by setInterval while recording, or
  // frozen at the last value when recording stops, or 0 when reset.
  let elapsed = $state(0);

  // React to session-state transitions:
  //   → recording  : reset to 0 and start ticking
  //   → monitoring : reset to 0 (timer hidden / showing 0:00)
  //   → idle       : reset to 0
  //   → finished   : freeze at current value
  $effect(() => {
    const state = sessionState;
    if (state === "recording") {
      startedAt = Date.now();
      elapsed = 0;
      const id = window.setInterval(() => {
        if (startedAt !== null) {
          elapsed = Math.floor((Date.now() - startedAt) / 1000);
        }
      }, 250);
      return () => {
        window.clearInterval(id);
        startedAt = null;
      };
    }
    if (state === "monitoring" || state === "idle") {
      startedAt = null;
      elapsed = 0;
    }
    // For "finished", do nothing — keep the last elapsed value frozen.
  });

  function format(s: number): string {
    const mm = Math.floor(s / 60);
    const ss = s % 60;
    return `${mm.toString().padStart(2, "0")}:${ss.toString().padStart(2, "0")}`;
  }

  let display = $derived(format(elapsed));
  let active = $derived(sessionState === "recording");
</script>

<div class="timer" class:active aria-label="Roast timer">
  <span class="timer-label">TIME</span>
  <span class="timer-value">{display}</span>
</div>

<style>
  .timer {
    display: flex;
    align-items: baseline;
    gap: 6px;
  }

  .timer-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #888;
    opacity: 0.8;
  }

  .timer-value {
    font-size: 1.3rem;
    font-weight: 700;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-variant-numeric: tabular-nums;
    color: #cfcfcf;
    line-height: 1;
  }

  .timer.active .timer-value {
    color: #ef5350;
  }

  .timer.active .timer-label {
    color: #ef5350;
    opacity: 1;
  }

  @media (max-width: 480px) {
    .timer-value {
      font-size: 1.1rem;
    }
  }
</style>
