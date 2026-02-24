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
    ondragstart?: () => void;
    ondragend?: () => void;
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
    ondragstart,
    ondragend,
  }: Props = $props();

  let percentage = $derived(((value - min) / (max - min)) * 100);

  // --- Drag tracking ---
  let dragging = $state(false);

  function handlePointerDown() {
    dragging = true;
    ondragstart?.();
  }

  $effect(() => {
    if (!dragging) return;
    const handleUp = () => {
      dragging = false;
      ondragend?.();
    };
    window.addEventListener("pointerup", handleUp);
    window.addEventListener("pointercancel", handleUp);
    return () => {
      window.removeEventListener("pointerup", handleUp);
      window.removeEventListener("pointercancel", handleUp);
    };
  });

  function handleInput(e: Event) {
    const target = e.target as HTMLInputElement;
    value = parseFloat(target.value);
    onchange?.(value);
  }

  // --- Editable value ---
  let editing = $state(false);
  let editValue = $state("");
  let inputRef = $state<HTMLInputElement | null>(null);

  function startEdit() {
    if (disabled) return;
    editing = true;
    editValue = String(value);
  }

  function commitEdit() {
    if (!editing) return;
    editing = false;
    const parsed = parseFloat(editValue);
    if (isNaN(parsed)) return;
    const clamped = Math.min(max, Math.max(min, parsed));
    const snapped = Math.round((clamped - min) / step) * step + min;
    const rounded = parseFloat(snapped.toFixed(10));
    value = rounded;
    onchange?.(value);
  }

  function cancelEdit() {
    editing = false;
  }

  function handleEditKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      commitEdit();
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelEdit();
    }
  }

  $effect(() => {
    if (editing && inputRef) {
      inputRef.focus();
      inputRef.select();
    }
  });
</script>

<div class="slider-control" class:disabled>
  <div class="slider-header">
    <span class="slider-label">{label}</span>
    {#if editing}
      <input
        bind:this={inputRef}
        type="number"
        class="slider-value-input"
        style="color: {color}"
        {min}
        {max}
        {step}
        bind:value={editValue}
        onblur={commitEdit}
        onkeydown={handleEditKeydown}
      />
    {:else}
      <button
        class="slider-value"
        style="color: {color}"
        onclick={startEdit}
        {disabled}
        type="button"
        title="Click to edit"
      >
        {value}{#if unit}<span class="slider-unit">{unit}</span>{/if}
      </button>
    {/if}
  </div>
  <input
    type="range"
    {min}
    {max}
    {step}
    {value}
    {disabled}
    oninput={handleInput}
    onpointerdown={handlePointerDown}
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
    background: none;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 1px 4px;
    cursor: pointer;
  }

  .slider-value:hover:not(:disabled) {
    border-color: #4fc3f7;
    background: rgba(79, 195, 247, 0.05);
  }

  .slider-value:disabled {
    cursor: default;
  }

  .slider-value-input {
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 0.85rem;
    font-weight: 600;
    background: #0d0d1a;
    border: 1px solid #4fc3f7;
    border-radius: 3px;
    padding: 1px 4px;
    width: 60px;
    text-align: right;
    outline: none;
    -moz-appearance: textfield;
  }

  .slider-value-input::-webkit-inner-spin-button,
  .slider-value-input::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
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
