<script lang="ts">
  import type { RoastEventType } from "$lib/types/ws-messages";
  import { formatTime } from "$lib/stores/machine";
  import type { RoastEvent } from "$lib/stores/machine";

  interface Props {
    disabled?: boolean;
    events?: RoastEvent[];
    onmark?: (eventType: RoastEventType) => void;
  }

  let { disabled = false, events = [], onmark }: Props = $props();

  const EVENT_BUTTONS: {
    type: RoastEventType;
    label: string;
    color: string;
  }[] = [
    { type: "CHARGE", label: "CHARGE", color: "#66bb6a" },
    { type: "DRY_END", label: "DRY", color: "#ffa726" },
    { type: "FCs", label: "FCs", color: "#ef5350" },
    { type: "FCe", label: "FCe", color: "#ec407a" },
    { type: "SCs", label: "SCs", color: "#ab47bc" },
    { type: "DROP", label: "DROP", color: "#42a5f5" },
    { type: "COOL", label: "COOL", color: "#26c6da" },
  ];

  function isMarked(eventType: RoastEventType): boolean {
    return events.some((e) => e.event_type === eventType);
  }

  function getEventTime(eventType: RoastEventType): string | null {
    const evt = events.find((e) => e.event_type === eventType);
    return evt ? formatTime(evt.timestamp_ms) : null;
  }
</script>

<div class="event-buttons">
  {#each EVENT_BUTTONS as btn (btn.type)}
    {@const marked = isMarked(btn.type)}
    {@const time = getEventTime(btn.type)}
    <button
      class="event-btn"
      class:marked
      disabled={disabled || marked}
      style="--btn-color: {btn.color}"
      onclick={() => onmark?.(btn.type)}
    >
      <span class="btn-label">{btn.label}</span>
      {#if time}
        <span class="btn-time">{time}</span>
      {/if}
    </button>
  {/each}
</div>

<style>
  .event-buttons {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .event-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 14px;
    border: 1px solid var(--btn-color);
    border-radius: 6px;
    background: transparent;
    color: var(--btn-color);
    cursor: pointer;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    transition:
      background-color 0.15s,
      opacity 0.15s;
    min-width: 60px;
  }

  .event-btn:hover:not(:disabled) {
    background: color-mix(in srgb, var(--btn-color) 15%, transparent);
  }

  .event-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .event-btn.marked {
    background: color-mix(in srgb, var(--btn-color) 20%, transparent);
    opacity: 0.8;
  }

  .btn-label {
    font-size: 0.7rem;
    text-transform: uppercase;
  }

  .btn-time {
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 0.7rem;
    margin-top: 2px;
    opacity: 0.7;
  }
</style>
