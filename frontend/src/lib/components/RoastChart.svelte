<script lang="ts">
  import type {
    TemperaturePoint,
    ControlPoint,
    ControlConfig,
    ExtraChannelConfig,
    ExtraChannelPoint,
  } from "$lib/stores/machine";
  import { formatTime } from "$lib/stores/machine";
  import {
    DEFAULT_CHART_OPTIONS,
    smoothRor,
    type ChartOptions,
  } from "$lib/stores/chart-options";

  interface Props {
    history: TemperaturePoint[];
    controlHistory?: ControlPoint[];
    controls?: ControlConfig[];
    extraChannelHistory?: ExtraChannelPoint[];
    extraChannels?: ExtraChannelConfig[];
    options?: ChartOptions;
    width?: number;
    height?: number;
  }

  let {
    history,
    controlHistory = [],
    controls = [],
    extraChannelHistory = [],
    extraChannels = [],
    options = DEFAULT_CHART_OPTIONS,
    width = 800,
    height = 350,
  }: Props = $props();

  // Chart configuration
  const PADDING = { top: 20, right: 60, bottom: 40, left: 50 };
  const ET_COLOR = "#ff7043";
  const BT_COLOR = "#42a5f5";
  const ET_ROR_COLOR = "#ffab91";
  const BT_ROR_COLOR = "#90caf9";
  const CONTROL_COLORS = [
    "#e6c229",
    "#66bb6a",
    "#ab47bc",
    "#26c6da",
    "#ef5350",
    "#8d6e63",
  ];
  const EXTRA_CHANNEL_COLOR = "#a5d6a7";
  const GRID_COLOR = "#1e1e3a";
  const AXIS_COLOR = "#444";
  const TEXT_COLOR = "#888";

  // RoR / Control range (right Y-axis)
  const R_MIN = 0;
  const R_MAX = 100;

  // Derived dimensions
  let plotW = $derived(width - PADDING.left - PADDING.right);
  let plotH = $derived(height - PADDING.top - PADDING.bottom);

  // Dynamic temperature range (left Y-axis) — fits to data
  let tempRange = $derived(() => {
    const temps: number[] = [];
    for (const p of history) {
      if (options.showET) temps.push(p.et);
      if (options.showBT) temps.push(p.bt);
    }
    // Include visible extra channels
    for (const ep of extraChannelHistory) {
      for (const ch of extraChannels) {
        if (options.showExtraChannels[ch.name] && ch.name in ep.values) {
          temps.push(ep.values[ch.name]);
        }
      }
    }
    if (temps.length === 0) return { min: 0, max: 300, step: 50 };

    const rawMin = Math.min(...temps);
    const rawMax = Math.max(...temps);
    const padding = Math.max(25, (rawMax - rawMin) * 0.1);
    const min = Math.max(0, Math.floor((rawMin - padding) / 25) * 25);
    const max = Math.max(min + 50, Math.ceil((rawMax + padding) / 25) * 25);
    const range = max - min;
    const step = range <= 150 ? 25 : range <= 300 ? 50 : 100;
    return { min, max, step };
  });

  // Time range: auto-expand
  let maxTimeMs = $derived(
    history.length > 0
      ? Math.max(history[history.length - 1].timestamp_ms, 60000)
      : 60000,
  );
  let timeRangeMs = $derived(Math.ceil(maxTimeMs / 60000) * 60000);

  // Scale functions
  function xScale(timestamp_ms: number): number {
    return PADDING.left + (timestamp_ms / timeRangeMs) * plotW;
  }

  function yScale(temp: number): number {
    const { min, max } = tempRange();
    return PADDING.top + plotH - ((temp - min) / (max - min)) * plotH;
  }

  function yScaleRight(val: number): number {
    return PADDING.top + plotH - ((val - R_MIN) / (R_MAX - R_MIN)) * plotH;
  }

  // Build SVG path from temperature points
  function buildTempPath(
    points: TemperaturePoint[],
    accessor: (p: TemperaturePoint) => number,
  ): string {
    if (points.length === 0) return "";
    return points
      .map((p, i) => {
        const x = xScale(p.timestamp_ms);
        const y = yScale(accessor(p));
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  // Build SVG path for RoR (clamped to right Y-axis range), using pre-smoothed values
  function buildRorPath(
    points: TemperaturePoint[],
    smoothedValues: number[],
  ): string {
    if (points.length < 2) return "";
    return points
      .slice(1)
      .map((p, i) => {
        const x = xScale(p.timestamp_ms);
        const val = Math.max(R_MIN, Math.min(R_MAX, smoothedValues[i + 1]));
        const y = yScaleRight(val);
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  // Build SVG path for dynamic control values
  function buildDynamicControlPath(
    points: ControlPoint[],
    channel: string,
    ctrl: ControlConfig,
  ): string {
    if (points.length === 0) return "";
    return points
      .filter((p) => channel in p.values)
      .map((p, i) => {
        const x = xScale(p.timestamp_ms);
        // Normalize from native range to 0-100 for the right axis
        const normalized =
          ctrl.max !== ctrl.min
            ? ((p.values[channel] - ctrl.min) / (ctrl.max - ctrl.min)) * 100
            : 0;
        const clamped = Math.max(R_MIN, Math.min(R_MAX, normalized));
        const y = yScaleRight(clamped);
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  // Build SVG path for extra channel values (scaled to right axis as raw values)
  function buildExtraChannelPath(
    points: ExtraChannelPoint[],
    channelName: string,
  ): string {
    if (points.length === 0) return "";
    return points
      .filter((p) => channelName in p.values)
      .map((p, i) => {
        const x = xScale(p.timestamp_ms);
        // Extra channels are temperature-like — use left Y-axis
        const { min: tMin, max: tMax } = tempRange();
        const y = yScale(Math.max(tMin, Math.min(tMax, p.values[channelName])));
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  // Grid lines
  let tempGridLines = $derived(() => {
    const { min, max, step } = tempRange();
    return Array.from(
      { length: Math.floor((max - min) / step) + 1 },
      (_, i) => min + i * step,
    );
  });

  let timeGridLines = $derived(() => {
    const interval = timeRangeMs <= 120000 ? 30000 : 60000;
    const lines: number[] = [];
    for (let t = 0; t <= timeRangeMs; t += interval) {
      lines.push(t);
    }
    return lines;
  });

  // Temperature curves
  let etPath = $derived(
    options.showET ? buildTempPath(history, (p) => p.et) : "",
  );
  let btPath = $derived(
    options.showBT ? buildTempPath(history, (p) => p.bt) : "",
  );

  // Smoothed RoR values
  let smoothedEtRor = $derived(
    smoothRor(
      history.map((p) => p.et_ror),
      options.rorSmoothing,
    ),
  );
  let smoothedBtRor = $derived(
    smoothRor(
      history.map((p) => p.bt_ror),
      options.rorSmoothing,
    ),
  );

  // RoR curves
  let etRorPath = $derived(
    options.showETRor ? buildRorPath(history, smoothedEtRor) : "",
  );
  let btRorPath = $derived(
    options.showBTRor ? buildRorPath(history, smoothedBtRor) : "",
  );

  // Filter out controls that have a matching extra channel (read-back already exists)
  let uniqueControls = $derived(
    controls.filter(
      (ctrl) => !extraChannels.some((ch) => ch.name === ctrl.name),
    ),
  );

  // Dynamic control curves (only for controls without a matching extra channel)
  let controlPaths = $derived(
    uniqueControls
      .filter((ctrl) => options.showControls[ctrl.channel])
      .map((ctrl) => ({
        path: buildDynamicControlPath(controlHistory, ctrl.channel, ctrl),
        color: CONTROL_COLORS[controls.indexOf(ctrl) % CONTROL_COLORS.length],
        label: ctrl.name,
      })),
  );

  // Dynamic extra channel curves
  let extraChannelPaths = $derived(
    extraChannels
      .filter((ch) => options.showExtraChannels[ch.name])
      .map((ch) => ({
        path: buildExtraChannelPath(extraChannelHistory, ch.name),
        color: EXTRA_CHANNEL_COLOR,
        label: ch.name,
      })),
  );

  // Whether the right Y-axis is needed
  let showRightAxis = $derived(
    options.showETRor || options.showBTRor || controlPaths.length > 0,
  );

  // Current values for readout
  let lastPoint = $derived(
    history.length > 0 ? history[history.length - 1] : null,
  );

  // Dynamic legend entries
  let legendEntries = $derived(() => {
    const entries: { label: string; color: string }[] = [];
    if (options.showET) entries.push({ label: "ET", color: ET_COLOR });
    if (options.showBT) entries.push({ label: "BT", color: BT_COLOR });
    if (options.showETRor)
      entries.push({ label: "ET RoR", color: ET_ROR_COLOR });
    if (options.showBTRor)
      entries.push({ label: "BT RoR", color: BT_ROR_COLOR });
    for (const cp of controlPaths) {
      entries.push({ label: cp.label, color: cp.color });
    }
    for (const ep of extraChannelPaths) {
      entries.push({ label: ep.label, color: ep.color });
    }
    return entries;
  });
</script>

<div class="chart-container">
  <svg {width} {height} viewBox="0 0 {width} {height}">
    <!-- Background -->
    <rect x="0" y="0" {width} {height} fill="#0d0d1a" rx="8" />

    <!-- Grid: horizontal (temperature) -->
    {#each tempGridLines() as temp (temp)}
      {@const y = yScale(temp)}
      <line
        x1={PADDING.left}
        y1={y}
        x2={width - PADDING.right}
        y2={y}
        stroke={GRID_COLOR}
        stroke-width="1"
      />
      <text
        x={PADDING.left - 8}
        y={y + 4}
        fill={TEXT_COLOR}
        font-size="11"
        text-anchor="end">{temp}</text
      >
    {/each}

    <!-- Grid: vertical (time) -->
    {#each timeGridLines() as t (t)}
      {@const x = xScale(t)}
      <line
        x1={x}
        y1={PADDING.top}
        x2={x}
        y2={height - PADDING.bottom}
        stroke={GRID_COLOR}
        stroke-width="1"
      />
      <text
        {x}
        y={height - PADDING.bottom + 20}
        fill={TEXT_COLOR}
        font-size="11"
        text-anchor="middle">{formatTime(t)}</text
      >
    {/each}

    <!-- Axes -->
    <line
      x1={PADDING.left}
      y1={PADDING.top}
      x2={PADDING.left}
      y2={height - PADDING.bottom}
      stroke={AXIS_COLOR}
      stroke-width="1"
    />
    <line
      x1={PADDING.left}
      y1={height - PADDING.bottom}
      x2={width - PADDING.right}
      y2={height - PADDING.bottom}
      stroke={AXIS_COLOR}
      stroke-width="1"
    />

    <!-- Left Y-axis label -->
    <text
      x="14"
      y={height / 2}
      fill={TEXT_COLOR}
      font-size="11"
      text-anchor="middle"
      transform="rotate(-90, 14, {height / 2})">°C</text
    >

    <!-- Right Y-axis (RoR / Controls %) -->
    {#if showRightAxis}
      <line
        x1={width - PADDING.right}
        y1={PADDING.top}
        x2={width - PADDING.right}
        y2={height - PADDING.bottom}
        stroke={AXIS_COLOR}
        stroke-width="1"
      />
      {#each [0, 25, 50, 75, 100] as val (val)}
        {@const y = yScaleRight(val)}
        <text
          x={width - PADDING.right + 8}
          y={y + 4}
          fill={TEXT_COLOR}
          font-size="9"
          text-anchor="start"
          opacity="0.6">{val}</text
        >
      {/each}
    {/if}

    <!-- Dynamic control curves (behind temperature curves) -->
    {#each controlPaths as cp (cp.label)}
      {#if cp.path}
        <path
          d={cp.path}
          fill="none"
          stroke={cp.color}
          stroke-width="1.5"
          opacity="0.7"
        />
      {/if}
    {/each}

    <!-- Dynamic extra channel curves -->
    {#each extraChannelPaths as ep (ep.label)}
      {#if ep.path}
        <path
          d={ep.path}
          fill="none"
          stroke={ep.color}
          stroke-width="1.5"
          stroke-dasharray="6,3"
          opacity="0.6"
        />
      {/if}
    {/each}

    <!-- RoR curves -->
    {#if etRorPath}
      <path
        d={etRorPath}
        fill="none"
        stroke={ET_ROR_COLOR}
        stroke-width="1.5"
        stroke-dasharray="4,3"
      />
    {/if}
    {#if btRorPath}
      <path
        d={btRorPath}
        fill="none"
        stroke={BT_ROR_COLOR}
        stroke-width="1.5"
        stroke-dasharray="4,3"
      />
    {/if}

    <!-- ET curve -->
    {#if etPath}
      <path
        d={etPath}
        fill="none"
        stroke={ET_COLOR}
        stroke-width="2"
        stroke-linejoin="round"
      />
    {/if}

    <!-- BT curve -->
    {#if btPath}
      <path
        d={btPath}
        fill="none"
        stroke={BT_COLOR}
        stroke-width="2"
        stroke-linejoin="round"
      />
    {/if}

    <!-- Current value markers -->
    {#if lastPoint && options.showET}
      {@const etX = xScale(lastPoint.timestamp_ms)}
      {@const etY = yScale(lastPoint.et)}
      <circle cx={etX} cy={etY} r="4" fill={ET_COLOR} />
    {/if}
    {#if lastPoint && options.showBT}
      {@const btX = xScale(lastPoint.timestamp_ms)}
      {@const btY = yScale(lastPoint.bt)}
      <circle cx={btX} cy={btY} r="4" fill={BT_COLOR} />
    {/if}

    <!-- Dynamic legend -->
    {#each legendEntries() as entry, i (entry.label)}
      {@const lx = PADDING.left + 10 + i * 55}
      <rect
        x={lx}
        y={PADDING.top + 5}
        width="10"
        height="3"
        fill={entry.color}
        rx="1"
      />
      <text x={lx + 14} y={PADDING.top + 10} fill={entry.color} font-size="10"
        >{entry.label}</text
      >
    {/each}
  </svg>
</div>

<style>
  .chart-container {
    border-radius: 8px;
    overflow: hidden;
    background: #0d0d1a;
  }

  svg {
    display: block;
    width: 100%;
    height: auto;
  }
</style>
