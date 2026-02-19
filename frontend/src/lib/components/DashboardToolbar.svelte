<script lang="ts">
  import type { LayoutConfig, LayoutMode } from "$lib/stores/dashboard";

  interface Props {
    layout: LayoutConfig;
    machineCount: number;
    onaddmachine: () => void;
    onlayoutchange: (layout: Partial<LayoutConfig>) => void;
  }

  let { layout, machineCount, onaddmachine, onlayoutchange }: Props = $props();

  const MODES: { mode: LayoutMode; icon: string; label: string }[] = [
    { mode: "grid", icon: "⊞", label: "Grid" },
    { mode: "horizontal", icon: "⊟", label: "Side by side" },
    { mode: "vertical", icon: "☰", label: "Stacked" },
  ];
</script>

<div class="toolbar">
  <button class="btn-add" onclick={onaddmachine}>+ Add Machine</button>

  <div class="layout-controls">
    {#each MODES as m (m.mode)}
      <button
        class="layout-btn"
        class:active={layout.mode === m.mode}
        onclick={() => onlayoutchange({ mode: m.mode })}
        title={m.label}
      >
        {m.icon}
      </button>
    {/each}

    {#if layout.mode === "grid"}
      <select
        class="col-select"
        value={layout.columns}
        onchange={(e) =>
          onlayoutchange({
            columns: parseInt((e.target as HTMLSelectElement).value),
          })}
      >
        {#each [1, 2, 3, 4] as n (n)}
          <option value={n}>{n} col{n > 1 ? "s" : ""}</option>
        {/each}
      </select>
    {/if}
  </div>

  <span class="machine-count"
    >{machineCount} machine{machineCount !== 1 ? "s" : ""}</span
  >
</div>

<style>
  .toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 0;
  }

  .btn-add {
    background: #2e7d32;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-add:hover {
    background: #388e3c;
  }

  .layout-controls {
    display: flex;
    align-items: center;
    gap: 4px;
    background: #1a1a2e;
    border-radius: 6px;
    padding: 2px;
  }

  .layout-btn {
    background: transparent;
    border: none;
    color: #888;
    font-size: 1rem;
    padding: 4px 8px;
    cursor: pointer;
    border-radius: 4px;
  }

  .layout-btn:hover {
    color: #ccc;
  }

  .layout-btn.active {
    background: #2a2a4a;
    color: #4fc3f7;
  }

  .col-select {
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    color: #ccc;
    font-size: 0.75rem;
    padding: 4px 6px;
    margin-left: 4px;
  }

  .machine-count {
    margin-left: auto;
    color: #666;
    font-size: 0.75rem;
  }
</style>
