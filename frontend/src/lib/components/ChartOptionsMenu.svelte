<script lang="ts">
  import type { ChartOptions } from "$lib/stores/chart-options";
  import type { ControlConfig, ExtraChannelConfig } from "$lib/stores/machine";

  interface Props {
    options: ChartOptions;
    controls?: ControlConfig[];
    extraChannels?: ExtraChannelConfig[];
    onchange: (options: ChartOptions) => void;
  }

  let {
    options,
    controls = [],
    extraChannels = [],
    onchange,
  }: Props = $props();
  let open = $state(false);

  // Filter out controls that already have a matching extra channel (same name = read-back exists)
  let uniqueControls = $derived(
    controls.filter(
      (ctrl) => !extraChannels.some((ch) => ch.name === ctrl.name),
    ),
  );

  const CONTROL_COLORS = [
    "#e6c229",
    "#66bb6a",
    "#ab47bc",
    "#26c6da",
    "#ef5350",
    "#8d6e63",
  ];
  const EXTRA_CHANNEL_COLOR = "#a5d6a7";

  function toggleBase(key: "showET" | "showBT" | "showETRor" | "showBTRor") {
    onchange({ ...options, [key]: !options[key] });
  }

  function toggleControl(channel: string) {
    onchange({
      ...options,
      showControls: {
        ...options.showControls,
        [channel]: !options.showControls[channel],
      },
    });
  }

  const ROR_SMOOTHING_OPTIONS = [1, 3, 5, 7, 9];

  function setRorSmoothing(value: number) {
    onchange({ ...options, rorSmoothing: value });
  }

  function toggleExtraChannel(name: string) {
    onchange({
      ...options,
      showExtraChannels: {
        ...options.showExtraChannels,
        [name]: !options.showExtraChannels[name],
      },
    });
  }

  function handleClickOutside(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (!target.closest(".chart-options-menu")) {
      open = false;
    }
  }

  const BASE_ITEMS: {
    key: "showET" | "showBT" | "showETRor" | "showBTRor";
    label: string;
    color: string;
  }[] = [
    { key: "showET", label: "ET", color: "#ff7043" },
    { key: "showBT", label: "BT", color: "#42a5f5" },
    { key: "showETRor", label: "ET RoR", color: "#ffab91" },
    { key: "showBTRor", label: "BT RoR", color: "#90caf9" },
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
      {#each BASE_ITEMS as item (item.key)}
        <label class="option-row">
          <input
            type="checkbox"
            checked={options[item.key]}
            onchange={() => toggleBase(item.key)}
          />
          <span class="color-dot" style="background: {item.color}"></span>
          <span class="option-label">{item.label}</span>
        </label>
      {/each}

      {#if options.showETRor || options.showBTRor}
        <div class="section-divider"></div>
        <div class="smoothing-row">
          <span class="option-label">RoR Avg</span>
          <select
            class="smoothing-select"
            value={options.rorSmoothing}
            onchange={(e) =>
              setRorSmoothing(Number((e.target as HTMLSelectElement).value))}
          >
            {#each ROR_SMOOTHING_OPTIONS as n (n)}
              <option value={n}>{n === 1 ? "Off" : String(n)}</option>
            {/each}
          </select>
        </div>
      {/if}

      {#if uniqueControls.length > 0}
        <div class="section-divider"></div>
        {#each uniqueControls as ctrl (ctrl.channel)}
          <label class="option-row">
            <input
              type="checkbox"
              checked={options.showControls[ctrl.channel] ?? false}
              onchange={() => toggleControl(ctrl.channel)}
            />
            <span
              class="color-dot"
              style="background: {CONTROL_COLORS[
                controls.indexOf(ctrl) % CONTROL_COLORS.length
              ]}"
            ></span>
            <span class="option-label">{ctrl.name}</span>
          </label>
        {/each}
      {/if}

      {#if extraChannels.length > 0}
        <div class="section-divider"></div>
        {#each extraChannels as ch (ch.name)}
          <label class="option-row">
            <input
              type="checkbox"
              checked={options.showExtraChannels[ch.name] ?? false}
              onchange={() => toggleExtraChannel(ch.name)}
            />
            <span class="color-dot" style="background: {EXTRA_CHANNEL_COLOR}"
            ></span>
            <span class="option-label">{ch.name}</span>
          </label>
        {/each}
      {/if}
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

  .section-divider {
    height: 1px;
    background: #2a2a4a;
    margin: 4px 0;
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

  .smoothing-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 3px 4px;
    font-size: 0.8rem;
    color: #ccc;
  }

  .smoothing-select {
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 3px;
    color: #ccc;
    font-size: 0.75rem;
    padding: 2px 4px;
    cursor: pointer;
  }
</style>
