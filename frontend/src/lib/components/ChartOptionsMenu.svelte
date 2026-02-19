<script lang="ts">
  import type { ChartOptions } from "$lib/stores/chart-options";

  interface Props {
    options: ChartOptions;
    onchange: (options: ChartOptions) => void;
  }

  let { options, onchange }: Props = $props();
  let open = $state(false);

  function toggle(key: keyof ChartOptions) {
    onchange({ ...options, [key]: !options[key] });
  }

  function handleClickOutside(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (!target.closest(".chart-options-menu")) {
      open = false;
    }
  }

  const ITEMS: { key: keyof ChartOptions; label: string; color: string }[] = [
    { key: "showET", label: "ET", color: "#ff7043" },
    { key: "showBT", label: "BT", color: "#42a5f5" },
    { key: "showETRor", label: "ET RoR", color: "#ffab91" },
    { key: "showBTRor", label: "BT RoR", color: "#90caf9" },
    { key: "showBurner", label: "Burner", color: "#ff7043" },
    { key: "showAirflow", label: "Airflow", color: "#4fc3f7" },
    { key: "showDrum", label: "Drum", color: "#81c784" },
  ];
</script>

<svelte:window onclick={handleClickOutside} />

<div class="chart-options-menu">
  <button
    class="gear-btn"
    onclick={() => (open = !open)}
    aria-label="Chart options"
  >
    &#9881;
  </button>

  {#if open}
    <div class="popover">
      {#each ITEMS as item (item.key)}
        <label class="option-row">
          <input
            type="checkbox"
            checked={options[item.key]}
            onchange={() => toggle(item.key)}
          />
          <span class="color-dot" style="background: {item.color}"></span>
          <span class="option-label">{item.label}</span>
        </label>
      {/each}
    </div>
  {/if}
</div>

<style>
  .chart-options-menu {
    position: relative;
  }

  .gear-btn {
    background: transparent;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    color: #888;
    font-size: 1rem;
    padding: 2px 6px;
    cursor: pointer;
    line-height: 1;
  }

  .gear-btn:hover {
    color: #ccc;
    border-color: #444;
  }

  .popover {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 4px;
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 8px;
    z-index: 10;
    min-width: 140px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .option-row {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    padding: 3px 4px;
    border-radius: 3px;
    font-size: 0.8rem;
    color: #ccc;
  }

  .option-row:hover {
    background: #2a2a4a;
  }

  .color-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .option-label {
    user-select: none;
  }

  input[type="checkbox"] {
    accent-color: #4fc3f7;
  }
</style>
