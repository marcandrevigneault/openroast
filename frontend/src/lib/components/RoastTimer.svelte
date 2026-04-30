<script lang="ts">
  import type { SessionState } from "$lib/types/ws-messages";
  import { onDestroy } from "svelte";

  interface Props {
    sessionState: SessionState;
  }

  let { sessionState }: Props = $props();

  // Seconds shown to the user. Driven by setInterval while recording, or
  // frozen at the last value when recording stops, or 0 when reset.
  let elapsed = $state(0);

  // Plain (non-reactive) lifecycle state. Stored outside `$state` so that
  // (a) reading them inside the effect does not register a dependency that
  //     would re-fire the effect, and
  // (b) the parent re-rendering with the SAME sessionState value does not
  //     accidentally reset the timer — we explicitly compare to prevState
  //     and bail out when nothing has changed.
  //
  // Earlier implementation reset the timer on every parent re-render
  // because each new TemperatureMessage caused MachinePanel to re-render
  // and Svelte 5's $effect re-fired even though sessionState had not
  // actually transitioned.
  let prevState: SessionState | null = null;
  let startedAt: number | null = null;
  let intervalId: ReturnType<typeof setInterval> | null = null;

  function clearTick(): void {
    if (intervalId !== null) {
      clearInterval(intervalId);
      intervalId = null;
    }
  }

  $effect(() => {
    const state = sessionState;
    if (state === prevState) return; // Not a real transition — leave timer alone.
    prevState = state;

    clearTick();

    if (state === "recording") {
      startedAt = Date.now();
      elapsed = 0;
      intervalId = setInterval(() => {
        if (startedAt !== null) {
          elapsed = Math.floor((Date.now() - startedAt) / 1000);
        }
      }, 250);
      return;
    }

    if (state === "monitoring" || state === "idle") {
      startedAt = null;
      elapsed = 0;
      return;
    }

    // For "finished", do nothing — keep the last elapsed value frozen.
  });

  onDestroy(clearTick);

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
