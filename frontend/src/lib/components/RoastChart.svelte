<script lang="ts">
  import type { TemperaturePoint } from "$lib/stores/machine";
  import { formatTime } from "$lib/stores/machine";
  import {
    DEFAULT_CHART_OPTIONS,
    smoothRor,
    type ChartOptions,
  } from "$lib/stores/chart-options";

  interface Props {
    history: TemperaturePoint[];
    options?: ChartOptions;
    width?: number;
    height?: number;
  }

  let {
    history,
    options = DEFAULT_CHART_OPTIONS,
    width = 800,
    height = 350,
  }: Props = $props();

  // Chart configuration
  const PADDING = { top: 20, right: 60, bottom: 40, left: 50 };
  const ET_COLOR = "#ff7043";
  const BT_COLOR = "#42a5f5";
  const ET_DELTA_COLOR = "#ffab91";
  const BT_DELTA_COLOR = "#90caf9";
  const GRID_COLOR = "#1e1e3a";
  const AXIS_COLOR = "#444";
  const TEXT_COLOR = "#888";

  // Delta range (right Y-axis)
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

  // Build SVG path for delta (clamped to right Y-axis range)
  function buildDeltaPath(
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

  // Smoothed delta values
  let smoothedEtDelta = $derived(
    smoothRor(
      history.map((p) => p.et_ror),
      options.rorSmoothing,
    ),
  );
  let smoothedBtDelta = $derived(
    smoothRor(
      history.map((p) => p.bt_ror),
      options.rorSmoothing,
    ),
  );

  // Delta curves
  let etDeltaPath = $derived(
    options.showETRor ? buildDeltaPath(history, smoothedEtDelta) : "",
  );
  let btDeltaPath = $derived(
    options.showBTRor ? buildDeltaPath(history, smoothedBtDelta) : "",
  );

  // Whether the right Y-axis is needed
  let showRightAxis = $derived(options.showETRor || options.showBTRor);

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
      entries.push({ label: "\u0394 ET", color: ET_DELTA_COLOR });
    if (options.showBTRor)
      entries.push({ label: "\u0394 BT", color: BT_DELTA_COLOR });
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

    <!-- Right Y-axis (Delta °C/min) -->
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

    <!-- Delta curves -->
    {#if etDeltaPath}
      <path
        d={etDeltaPath}
        fill="none"
        stroke={ET_DELTA_COLOR}
        stroke-width="1.5"
        stroke-dasharray="4,3"
      />
    {/if}
    {#if btDeltaPath}
      <path
        d={btDeltaPath}
        fill="none"
        stroke={BT_DELTA_COLOR}
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
