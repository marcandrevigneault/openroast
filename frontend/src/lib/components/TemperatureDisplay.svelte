<script lang="ts">
  interface Props {
    label: string;
    value: number | null;
    ror: number | null;
    unit?: string;
    color?: string;
    compact?: boolean;
  }

  let {
    label,
    value,
    ror,
    unit = "°C",
    color = "#e0e0e0",
    compact = false,
  }: Props = $props();

  let displayValue = $derived(value !== null ? value.toFixed(1) : "---");
  let displayRor = $derived(
    ror !== null ? (ror >= 0 ? `+${ror.toFixed(1)}` : ror.toFixed(1)) : "---",
  );
</script>

{#if compact}
  <div class="temp-compact" style="--accent-color: {color}">
    <span class="compact-label">{label}</span>
    <span class="compact-value">{displayValue}</span>
    <span class="compact-ror">{displayRor}/min</span>
  </div>
{:else}
  <div class="temp-display" style="--accent-color: {color}">
    <span class="label">{label}</span>
    <span class="value">{displayValue}</span>
    <span class="unit">{unit}</span>
    <span class="ror">{displayRor} /min</span>
  </div>
{/if}

<style>
  /* --- Compact (inline) mode --- */
  .temp-compact {
    display: flex;
    align-items: baseline;
    gap: 6px;
  }

  .compact-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent-color);
    opacity: 0.7;
  }

  .compact-value {
    font-size: 1.3rem;
    font-weight: 700;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    color: var(--accent-color);
    line-height: 1;
  }

  .compact-ror {
    font-size: 0.7rem;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    color: #888;
  }

  /* --- Full (card) mode --- */
  .temp-display {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 12px 20px;
    background: #1a1a2e;
    border-radius: 8px;
    border: 1px solid #2a2a4a;
    min-width: 140px;
  }

  .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent-color);
    opacity: 0.8;
    margin-bottom: 4px;
  }

  .value {
    font-size: 2.2rem;
    font-weight: 700;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    color: var(--accent-color);
    line-height: 1;
  }

  .unit {
    font-size: 0.8rem;
    color: #888;
    margin-top: 2px;
  }

  .ror {
    font-size: 0.85rem;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    color: #aaa;
    margin-top: 6px;
  }

  @media (max-width: 480px) {
    .compact-value {
      font-size: 1.1rem;
    }

    .compact-ror {
      font-size: 0.65rem;
    }

    .temp-display {
      min-width: 110px;
      padding: 10px 14px;
    }

    .value {
      font-size: 1.8rem;
    }
  }
</style>
