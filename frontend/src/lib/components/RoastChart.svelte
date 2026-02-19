<script lang="ts">
  import type { TemperaturePoint } from "$lib/stores/machine";
  import { formatTime } from "$lib/stores/machine";
  import {
    DEFAULT_CHART_OPTIONS,
    type ChartOptions,
    type ControlPoint,
  } from "$lib/stores/chart-options";

  interface Props {
    history: TemperaturePoint[];
    controlHistory?: ControlPoint[];
    options?: ChartOptions;
    width?: number;
    height?: number;
  }

  let {
    history,
    controlHistory = [],
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
  const BURNER_COLOR = "#ff7043";
  const AIRFLOW_COLOR = "#4fc3f7";
  const DRUM_COLOR = "#81c784";
  const GRID_COLOR = "#1e1e3a";
  const AXIS_COLOR = "#444";
  const TEXT_COLOR = "#888";

  // Temperature range (left Y-axis)
  const T_MIN = 50;
  const T_MAX = 300;
  const T_STEP = 50;

  // RoR / Control range (right Y-axis)
  const R_MIN = 0;
  const R_MAX = 100;

  // Derived dimensions
  let plotW = $derived(width - PADDING.left - PADDING.right);
  let plotH = $derived(height - PADDING.top - PADDING.bottom);

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
    return PADDING.top + plotH - ((temp - T_MIN) / (T_MAX - T_MIN)) * plotH;
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

  // Build SVG path for RoR (clamped to right Y-axis range)
  function buildRorPath(
    points: TemperaturePoint[],
    accessor: (p: TemperaturePoint) => number,
  ): string {
    if (points.length < 2) return "";
    return points
      .slice(1)
      .map((p, i) => {
        const x = xScale(p.timestamp_ms);
        const val = Math.max(R_MIN, Math.min(R_MAX, accessor(p)));
        const y = yScaleRight(val);
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  // Build SVG path for control values
  function buildControlPath(
    points: ControlPoint[],
    accessor: (p: ControlPoint) => number,
  ): string {
    if (points.length === 0) return "";
    return points
      .map((p, i) => {
        const x = xScale(p.timestamp_ms);
        const val = Math.max(R_MIN, Math.min(R_MAX, accessor(p)));
        const y = yScaleRight(val);
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  // Grid lines
  let tempGridLines = $derived(
    Array.from(
      { length: Math.floor((T_MAX - T_MIN) / T_STEP) + 1 },
      (_, i) => T_MIN + i * T_STEP,
    ),
  );

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

  // RoR curves
  let etRorPath = $derived(
    options.showETRor ? buildRorPath(history, (p) => p.et_ror) : "",
  );
  let btRorPath = $derived(
    options.showBTRor ? buildRorPath(history, (p) => p.bt_ror) : "",
  );

  // Control curves
  let burnerPath = $derived(
    options.showBurner ? buildControlPath(controlHistory, (p) => p.burner) : "",
  );
  let airflowPath = $derived(
    options.showAirflow
      ? buildControlPath(controlHistory, (p) => p.airflow)
      : "",
  );
  let drumPath = $derived(
    options.showDrum ? buildControlPath(controlHistory, (p) => p.drum) : "",
  );

  // Whether the right Y-axis is needed
  let showRightAxis = $derived(
    options.showETRor ||
      options.showBTRor ||
      options.showBurner ||
      options.showAirflow ||
      options.showDrum,
  );

  // Current values for readout
  let lastPoint = $derived(
    history.length > 0 ? history[history.length - 1] : null,
  );

  // Dynamic legend entries
  let legendEntries = $derived(
    (
      [
        options.showET && { label: "ET", color: ET_COLOR },
        options.showBT && { label: "BT", color: BT_COLOR },
        options.showETRor && { label: "ET RoR", color: ET_ROR_COLOR },
        options.showBTRor && { label: "BT RoR", color: BT_ROR_COLOR },
        options.showBurner && { label: "Burner", color: BURNER_COLOR },
        options.showAirflow && { label: "Airflow", color: AIRFLOW_COLOR },
        options.showDrum && { label: "Drum", color: DRUM_COLOR },
      ] as ({ label: string; color: string } | false)[]
    ).filter(Boolean) as { label: string; color: string }[],
  );
</script>

<div class="chart-container">
  <svg {width} {height} viewBox="0 0 {width} {height}">
    <!-- Background -->
    <rect x="0" y="0" {width} {height} fill="#0d0d1a" rx="8" />

    <!-- Grid: horizontal (temperature) -->
    {#each tempGridLines as temp (temp)}
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

    <!-- Control curves (behind temperature curves) -->
    {#if burnerPath}
      <path
        d={burnerPath}
        fill="none"
        stroke={BURNER_COLOR}
        stroke-width="1"
        stroke-dasharray="none"
        opacity="0.4"
      />
    {/if}
    {#if airflowPath}
      <path
        d={airflowPath}
        fill="none"
        stroke={AIRFLOW_COLOR}
        stroke-width="1"
        stroke-dasharray="none"
        opacity="0.4"
      />
    {/if}
    {#if drumPath}
      <path
        d={drumPath}
        fill="none"
        stroke={DRUM_COLOR}
        stroke-width="1"
        stroke-dasharray="none"
        opacity="0.4"
      />
    {/if}

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
    {#each legendEntries as entry, i (entry.label)}
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
