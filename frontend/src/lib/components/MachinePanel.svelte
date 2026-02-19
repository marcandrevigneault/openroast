<script lang="ts">
  import type { MachineState } from "$lib/stores/machine";
  import type { RoastEventType } from "$lib/types/ws-messages";
  import {
    createChartOptions,
    smoothRor,
    type ChartOptions,
  } from "$lib/stores/chart-options";
  import { addToast } from "$lib/stores/toast";
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
    onreset?: () => void;
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
    onreset,
    onremove,
    onretry,
    onsettingssaved,
    onsave,
  }: Props = $props();

  const CONTROL_COLORS = [
    "#e6c229",
    "#66bb6a",
    "#ab47bc",
    "#26c6da",
    "#ef5350",
    "#8d6e63",
  ];

  let sliderValues = $state<Record<string, number>>({});
  let saving = $state(false);
  let saved = $state(false);
  let settingsOpen = $state(false);
  let lastToastedError = $state<string | null>(null);

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

  let isConnected = $derived(machine.driverState === "connected");
  let showRetryButton = $derived(
    machine.driverState === "error" || machine.driverState === "disconnected",
  );

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

  // Dispatch machine errors as toast notifications
  $effect(() => {
    if (machine.error && machine.error !== lastToastedError) {
      addToast(machine.error, "error", machine.machineName);
      lastToastedError = machine.error;
    } else if (!machine.error) {
      lastToastedError = null;
    }
  });

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
      {#if showRetryButton && onretry}
        <button
          class="btn-retry-header"
          onclick={onretry}
          title="Retry connection">&#8635;</button
        >
      {/if}
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
      {#if onreset}
        <button class="btn-chart-reset" onclick={onreset} title="Reset chart"
          >&#8634;</button
        >
      {/if}
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
    <EventButtons disabled={true} events={machine.events} {onmark} />
  </div>

  <!-- Controls -->
  {#if machine.controls.length > 0}
    <div class="controls-section">
      <div class="controls-grid">
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

  .btn-retry-header {
    background: transparent;
    border: 1px solid #ff9800;
    color: #ff9800;
    font-size: 0.9rem;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    line-height: 1;
  }

  .btn-retry-header:hover {
    background: rgba(255, 152, 0, 0.15);
    color: #ffb74d;
    border-color: #ffb74d;
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
    display: flex;
    gap: 4px;
    align-items: center;
  }

  .btn-chart-reset {
    background: transparent;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    color: #888;
    font-size: 1rem;
    padding: 2px 6px;
    cursor: pointer;
    line-height: 1;
  }

  .btn-chart-reset:hover {
    color: #ccc;
    border-color: #444;
  }

  /* --- Actions row --- */
  .actions-row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }

  /* --- Controls --- */
  .controls-section {
    border-top: 1px solid #2a2a4a;
    padding-top: 4px;
  }

  .controls-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0 16px;
  }
</style>
