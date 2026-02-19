<script lang="ts">
  interface Props {
    label: string;
    value: number | null;
    ror: number | null;
    unit?: string;
    color?: string;
  }

  let { label, value, ror, unit = "°C", color = "#e0e0e0" }: Props = $props();

  let displayValue = $derived(value !== null ? value.toFixed(1) : "---");
  let displayRor = $derived(
    ror !== null ? (ror >= 0 ? `+${ror.toFixed(1)}` : ror.toFixed(1)) : "---",
  );
</script>

<div class="temp-display" style="--accent-color: {color}">
  <span class="label">{label}</span>
  <span class="value">{displayValue}</span>
  <span class="unit">{unit}</span>
  <span class="ror">{displayRor} /min</span>
</div>

<style>
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
</style>
