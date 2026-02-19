<script lang="ts">
  import type { MachineState } from "$lib/stores/machine";
  import type { RoastEventType } from "$lib/types/ws-messages";
  import {
    createChartOptions,
    type ChartOptions,
  } from "$lib/stores/chart-options";
  import TemperatureDisplay from "./TemperatureDisplay.svelte";
  import RoastChart from "./RoastChart.svelte";
  import ChartOptionsMenu from "./ChartOptionsMenu.svelte";
  import ControlSlider from "./ControlSlider.svelte";
  import EventButtons from "./EventButtons.svelte";
  import SessionControls from "./SessionControls.svelte";
  import ConnectionStatus from "./ConnectionStatus.svelte";
  import SaveProfileForm from "./SaveProfileForm.svelte";

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

  // Dynamic slider values keyed by channel name
  let sliderValues = $state<Record<string, number>>({});
  let saving = $state(false);
  let saved = $state(false);

  let localChartOptions = $state(
    createChartOptions(
      machine.controls.map((c: { channel: string }) => c.channel),
      machine.extraChannels.map((c: { name: string }) => c.name),
    ),
  );
  let effectiveOptions = $derived(chartOptions ?? localChartOptions);

  function handleChartOptionsChange(opts: ChartOptions) {
    localChartOptions = opts;
    onchartoptionschange?.(opts);
  }

  let isRecording = $derived(machine.sessionState === "recording");
  let isConnected = $derived(machine.driverState === "connected");
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
  <div class="panel-header">
    <h2 class="machine-name">{machine.machineName}</h2>
    <div class="header-right">
      <ConnectionStatus
        driverState={machine.driverState}
        sessionState={machine.sessionState}
      />
      {#if onremove}
        <button class="btn-remove" onclick={onremove} title="Remove machine"
          >✕</button
        >
      {/if}
    </div>
  </div>

  <div class="panel-body">
    <div class="left-column">
      <div class="temp-row">
        <TemperatureDisplay
          label="ET"
          value={machine.currentTemp?.et ?? null}
          ror={machine.currentTemp?.et_ror ?? null}
          color="#ff7043"
        />
        <TemperatureDisplay
          label="BT"
          value={machine.currentTemp?.bt ?? null}
          ror={machine.currentTemp?.bt_ror ?? null}
          color="#42a5f5"
        />
      </div>

      <div class="chart-row">
        <RoastChart
          history={machine.history}
          controlHistory={machine.controlHistory}
          controls={machine.controls}
          extraChannelHistory={machine.extraChannelHistory}
          extraChannels={machine.extraChannels}
          options={effectiveOptions}
        />
        <ChartOptionsMenu
          options={effectiveOptions}
          controls={machine.controls}
          extraChannels={machine.extraChannels}
          onchange={handleChartOptionsChange}
        />
      </div>

      <div class="controls-row">
        <SessionControls
          sessionState={machine.sessionState}
          {onstart}
          {onstop}
          {onrecord}
          {onstoprecord}
        />
        <EventButtons
          disabled={!isRecording}
          events={machine.events}
          {onmark}
        />
      </div>
    </div>

    <div class="right-column">
      <div class="sliders">
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
        {#if machine.controls.length === 0}
          <p class="no-controls">No controls configured</p>
        {/if}
      </div>

      {#if machine.error}
        <div class="error-banner">
          {machine.error}
        </div>
      {/if}

      {#if showSaveForm}
        <SaveProfileForm onsave={handleSave} {saving} {saved} />
      {/if}
    </div>
  </div>
</div>

<style>
  .machine-panel {
    background: #12122a;
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .machine-name {
    font-size: 1rem;
    font-weight: 600;
    color: #e0e0e0;
    margin: 0;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
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

  .panel-body {
    display: flex;
    gap: 16px;
  }

  .chart-row {
    display: flex;
    align-items: flex-start;
    gap: 4px;
  }

  .chart-row :global(.chart-container) {
    flex: 1;
    min-width: 0;
  }

  .left-column {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 0;
  }

  .temp-row {
    display: flex;
    gap: 12px;
  }

  .controls-row {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .right-column {
    width: 200px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .sliders {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .no-controls {
    color: #666;
    font-size: 0.75rem;
    text-align: center;
    margin: 8px 0;
  }

  .error-banner {
    background: #3e1111;
    border: 1px solid #f44336;
    border-radius: 6px;
    padding: 8px 12px;
    color: #ff8a80;
    font-size: 0.8rem;
  }
</style>
