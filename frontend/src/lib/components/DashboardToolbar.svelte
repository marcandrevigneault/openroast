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
    { mode: "vertical", icon: "☰", label: "Stacked" },
    { mode: "side-by-side", icon: "⊟", label: "Side by side" },
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

  .machine-count {
    margin-left: auto;
    color: #666;
    font-size: 0.75rem;
  }

  @media (max-width: 480px) {
    .btn-add {
      padding: 8px 12px;
    }

    .layout-controls {
      display: none;
    }
  }
</style>
