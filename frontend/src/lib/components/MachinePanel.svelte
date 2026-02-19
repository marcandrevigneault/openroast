<script lang="ts">
  import type { MachineState } from "$lib/stores/machine";
  import type { RoastEventType } from "$lib/types/ws-messages";
  import {
    createChartOptions,
    smoothRor,
    type ChartOptions,
  } from "$lib/stores/chart-options";
  import TemperatureDisplay from "./TemperatureDisplay.svelte";
  import RoastChart from "./RoastChart.svelte";
  import ChartOptionsMenu from "./ChartOptionsMenu.svelte";
  import ControlSlider from "./ControlSlider.svelte";
  import EventButtons from "./EventButtons.svelte";
  import SessionControls from "./SessionControls.svelte";
  import ConnectionStatus from "./ConnectionStatus.svelte";
  import ExtraChannelsBar from "./ExtraChannelsBar.svelte";
  import SaveProfileForm from "./SaveProfileForm.svelte";
  import MachineSettingsPanel from "./MachineSettingsPanel.svelte";
  import type { SavedMachine } from "$lib/services/machine-api";

  interface Props {
    machine: MachineState;
    chartOptions?: ChartOptions;
    onstart?: () => void;
    onstop?: () => void;
    onrecord?: () => void;
    onstoprecord?: () => void;
    onmark?: (eventType: RoastEventType) => void;
    oncontrol?: (channel: string, value: number) => void;
    onchartoptionschange?: (options: ChartOptions) => void;
    onremove?: () => void;
    onretry?: () => void;
    onsettingssaved?: (machine: SavedMachine) => void;
    onsave?: (data: {
      name: string;
      beanName: string;
      beanWeight: number;
    }) => void;
  }

  let {
    machine,
    chartOptions,
    onstart,
    onstop,
    onrecord,
    onstoprecord,
    onmark,
    oncontrol,
    onchartoptionschange,
    onremove,
    onretry,
    onsettingssaved,
    onsave,
  }: Props = $props();

  const CONTROL_COLORS = [
    "#ff7043",
    "#4fc3f7",
    "#81c784",
    "#ffab91",
    "#ce93d8",
    "#fff176",
  ];

  let sliderValues = $state<Record<string, number>>({});
  let saving = $state(false);
  let saved = $state(false);
  let controlsOpen = $state(false);
  let settingsOpen = $state(false);

  // svelte-ignore state_referenced_locally
  const initControlChannels = machine.controls.map(
    (c: { channel: string }) => c.channel,
  );
  // svelte-ignore state_referenced_locally
  const initExtraChannelNames = machine.extraChannels.map(
    (c: { name: string }) => c.name,
  );
  let localChartOptions = $state(
    createChartOptions(initControlChannels, initExtraChannelNames),
  );
  let effectiveOptions = $derived(chartOptions ?? localChartOptions);

  function handleChartOptionsChange(opts: ChartOptions) {
    localChartOptions = opts;
    onchartoptionschange?.(opts);
  }

  let isRecording = $derived(machine.sessionState === "recording");
  let isConnected = $derived(machine.driverState === "connected");

  // Smoothed RoR for the header temperature display
  let smoothedHeaderEtRor = $derived(() => {
    const w = effectiveOptions.rorSmoothing;
    if (w <= 1 || machine.history.length === 0)
      return machine.currentTemp?.et_ror ?? null;
    const rors = machine.history.map((p) => p.et_ror);
    const smoothed = smoothRor(rors, w);
    return smoothed[smoothed.length - 1] ?? null;
  });
  let smoothedHeaderBtRor = $derived(() => {
    const w = effectiveOptions.rorSmoothing;
    if (w <= 1 || machine.history.length === 0)
      return machine.currentTemp?.bt_ror ?? null;
    const rors = machine.history.map((p) => p.bt_ror);
    const smoothed = smoothRor(rors, w);
    return smoothed[smoothed.length - 1] ?? null;
  });
  let showSaveForm = $derived(
    machine.sessionState === "finished" && machine.history.length > 0 && !saved,
  );

  function handleSave(data: {
    name: string;
    beanName: string;
    beanWeight: number;
  }) {
    saving = true;
    onsave?.(data);
    saving = false;
    saved = true;
  }
</script>

<div class="machine-panel">
  <!-- Compact header: name, temps, status, remove -->
  <div class="panel-header">
    <div class="header-left">
      <h2 class="machine-name">{machine.machineName}</h2>
      <div class="header-temps">
        <TemperatureDisplay
          label="ET"
          value={machine.currentTemp?.et ?? null}
          ror={smoothedHeaderEtRor()}
          color="#ff7043"
          compact
        />
        <TemperatureDisplay
          label="BT"
          value={machine.currentTemp?.bt ?? null}
          ror={smoothedHeaderBtRor()}
          color="#42a5f5"
          compact
        />
      </div>
    </div>
    <div class="header-right">
      <ConnectionStatus
        driverState={machine.driverState}
        sessionState={machine.sessionState}
      />
      <button
        class="btn-settings"
        onclick={() => (settingsOpen = true)}
        title="Machine settings"
      >
        &#9881;
      </button>
      {#if onremove}
        <button class="btn-remove" onclick={onremove} title="Remove machine"
          >✕</button
        >
      {/if}
    </div>
  </div>

  <!-- Full-width chart -->
  <div class="chart-section">
    <RoastChart
      history={machine.history}
      controlHistory={machine.controlHistory}
      controls={machine.controls}
      extraChannelHistory={machine.extraChannelHistory}
      extraChannels={machine.extraChannels}
      options={effectiveOptions}
    />
    <div class="chart-toolbar">
      <ChartOptionsMenu
        options={effectiveOptions}
        controls={machine.controls}
        extraChannels={machine.extraChannels}
        onchange={handleChartOptionsChange}
      />
    </div>
  </div>

  <!-- Extra channels bar -->
  <ExtraChannelsBar
    channels={machine.extraChannels}
    values={machine.currentExtraChannels}
  />

  <!-- Session controls + event buttons in one compact row -->
  <div class="actions-row">
    <SessionControls
      sessionState={machine.sessionState}
      {onstart}
      {onstop}
      {onrecord}
      {onstoprecord}
    />
    <EventButtons disabled={!isRecording} events={machine.events} {onmark} />
  </div>

  <!-- Collapsible controls drawer -->
  {#if machine.controls.length > 0}
    <div class="controls-section">
      <button
        class="controls-toggle"
        onclick={() => (controlsOpen = !controlsOpen)}
        aria-label="Toggle controls"
      >
        Controls
        <span class="toggle-arrow" class:open={controlsOpen}>&#9662;</span>
      </button>

      {#if controlsOpen}
        <div class="controls-drawer">
          {#each machine.controls as ctrl (ctrl.channel)}
            <ControlSlider
              label={ctrl.name}
              value={sliderValues[ctrl.channel] ?? ctrl.min}
              min={ctrl.min}
              max={ctrl.max}
              step={ctrl.step}
              unit={ctrl.unit}
              color={CONTROL_COLORS[
                machine.controls.indexOf(ctrl) % CONTROL_COLORS.length
              ]}
              disabled={!isConnected}
              onchange={(v) => {
                sliderValues[ctrl.channel] = v;
                oncontrol?.(ctrl.channel, v);
              }}
            />
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  {#if machine.error}
    <div class="error-banner">
      <span>{machine.error}</span>
      {#if onretry}
        <button class="btn-retry" onclick={onretry}>Retry</button>
      {/if}
    </div>
  {/if}

  {#if showSaveForm}
    <SaveProfileForm onsave={handleSave} {saving} {saved} />
  {/if}

  <MachineSettingsPanel
    machineId={machine.machineId}
    open={settingsOpen}
    onclose={() => (settingsOpen = false)}
    onsaved={(m) => {
      settingsOpen = false;
      onsettingssaved?.(m);
    }}
  />
</div>

<style>
  .machine-panel {
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* --- Header --- */
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
    min-width: 0;
  }

  .machine-name {
    font-size: 0.9rem;
    font-weight: 600;
    color: #e0e0e0;
    margin: 0;
    white-space: nowrap;
  }

  .header-temps {
    display: flex;
    gap: 16px;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .btn-settings {
    background: transparent;
    border: 1px solid transparent;
    color: #666;
    font-size: 0.9rem;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    line-height: 1;
  }

  .btn-settings:hover {
    color: #4fc3f7;
    border-color: #4fc3f7;
    background: rgba(79, 195, 247, 0.1);
  }

  .btn-remove {
    background: transparent;
    border: 1px solid transparent;
    color: #666;
    font-size: 0.9rem;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    line-height: 1;
  }

  .btn-remove:hover {
    color: #f44336;
    border-color: #f44336;
    background: rgba(244, 67, 54, 0.1);
  }

  /* --- Chart --- */
  .chart-section {
    position: relative;
  }

  .chart-section :global(.chart-container) {
    width: 100%;
  }

  .chart-toolbar {
    position: absolute;
    top: 8px;
    right: 8px;
  }

  /* --- Actions row --- */
  .actions-row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }

  /* --- Controls drawer --- */
  .controls-section {
    border-top: 1px solid #2a2a4a;
    padding-top: 4px;
  }

  .controls-toggle {
    background: transparent;
    border: none;
    color: #888;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    cursor: pointer;
    padding: 4px 0;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .controls-toggle:hover {
    color: #ccc;
  }

  .toggle-arrow {
    display: inline-block;
    transition: transform 0.2s;
    font-size: 0.65rem;
  }

  .toggle-arrow.open {
    transform: rotate(180deg);
  }

  .controls-drawer {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0 16px;
    padding-top: 4px;
  }

  /* --- Error & misc --- */
  .error-banner {
    background: #3e1111;
    border: 1px solid #f44336;
    border-radius: 6px;
    padding: 8px 12px;
    color: #ff8a80;
    font-size: 0.8rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .btn-retry {
    background: #f44336;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    flex-shrink: 0;
  }

  .btn-retry:hover {
    background: #e53935;
  }
</style>
