<script lang="ts">
  interface Props {
    label: string;
    value: number;
    min?: number;
    max?: number;
    step?: number;
    color?: string;
    unit?: string;
    disabled?: boolean;
    onchange?: (value: number) => void;
  }

  let {
    label,
    value = $bindable(),
    min = 0,
    max = 100,
    step = 1,
    color = "#4fc3f7",
    unit = "",
    disabled = false,
    onchange,
  }: Props = $props();

  let percentage = $derived(((value - min) / (max - min)) * 100);

  function handleInput(e: Event) {
    const target = e.target as HTMLInputElement;
    value = parseFloat(target.value);
    onchange?.(value);
  }
</script>

<div class="slider-control" class:disabled>
  <div class="slider-header">
    <span class="slider-label">{label}</span>
    <span class="slider-value" style="color: {color}"
      >{value}{#if unit}<span class="slider-unit">{unit}</span>{/if}</span
    >
  </div>
  <input
    type="range"
    {min}
    {max}
    {step}
    {value}
    {disabled}
    oninput={handleInput}
    class="slider"
    style="--slider-color: {color}; --fill-pct: {percentage}%"
  />
</div>

<style>
  .slider-control {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 0;
  }

  .slider-control.disabled {
    opacity: 0.4;
  }

  .slider-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .slider-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #999;
  }

  .slider-value {
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 0.85rem;
    font-weight: 600;
  }

  .slider-unit {
    font-size: 0.65rem;
    opacity: 0.6;
    margin-left: 2px;
  }

  .slider {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: linear-gradient(
      to right,
      var(--slider-color) 0%,
      var(--slider-color) var(--fill-pct),
      #2a2a4a var(--fill-pct),
      #2a2a4a 100%
    );
    outline: none;
    cursor: pointer;
  }

  .slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--slider-color);
    cursor: pointer;
    border: 2px solid #0d0d1a;
  }

  .slider::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--slider-color);
    cursor: pointer;
    border: 2px solid #0d0d1a;
  }

  .slider:disabled {
    cursor: not-allowed;
  }
</style>
