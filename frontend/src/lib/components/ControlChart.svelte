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
    height = 150,
  }: Props = $props();

  const PADDING = { top: 28, right: 40, bottom: 30, left: 50 };
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

  const Y_MIN = 0;
  const Y_MAX = 100;

  let plotW = $derived(width - PADDING.left - PADDING.right);
  let plotH = $derived(height - PADDING.top - PADDING.bottom);

  // Share the same time range as the temperature chart
  let maxTimeMs = $derived(
    history.length > 0
      ? Math.max(history[history.length - 1].timestamp_ms, 60000)
      : 60000,
  );
  let timeRangeMs = $derived(Math.ceil(maxTimeMs / 60000) * 60000);

  function xScale(timestamp_ms: number): number {
    return PADDING.left + (timestamp_ms / timeRangeMs) * plotW;
  }

  function yScale(val: number): number {
    return PADDING.top + plotH - ((val - Y_MIN) / (Y_MAX - Y_MIN)) * plotH;
  }

  // Build path for control values (from controlHistory)
  function buildControlPath(
    points: ControlPoint[],
    channel: string,
    ctrl: ControlConfig,
  ): string {
    if (points.length === 0) return "";
    return points
      .filter((p) => channel in p.values)
      .map((p, i) => {
        const x = xScale(p.timestamp_ms);
        const normalized =
          ctrl.max !== ctrl.min
            ? ((p.values[channel] - ctrl.min) / (ctrl.max - ctrl.min)) * 100
            : 0;
        const clamped = Math.max(Y_MIN, Math.min(Y_MAX, normalized));
        const y = yScale(clamped);
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  // Build path for extra channel values (0-100 scale)
  function buildExtraPath(
    points: ExtraChannelPoint[],
    channelName: string,
  ): string {
    if (points.length === 0) return "";
    return points
      .filter((p) => channelName in p.values)
      .map((p, i) => {
        const x = xScale(p.timestamp_ms);
        const clamped = Math.max(Y_MIN, Math.min(Y_MAX, p.values[channelName]));
        const y = yScale(clamped);
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  let timeGridLines = $derived(() => {
    const interval = timeRangeMs <= 120000 ? 30000 : 60000;
    const lines: number[] = [];
    for (let t = 0; t <= timeRangeMs; t += interval) {
      lines.push(t);
    }
    return lines;
  });

  // Filter out controls that have a matching extra channel
  let uniqueControls = $derived(
    controls.filter(
      (ctrl) => !extraChannels.some((ch) => ch.name === ctrl.name),
    ),
  );

  // Build control curves (only for controls without matching extra channels)
  let controlPaths = $derived(
    uniqueControls
      .filter((ctrl) => options.showControls[ctrl.channel])
      .map((ctrl) => ({
        path: buildControlPath(controlHistory, ctrl.channel, ctrl),
        color: CONTROL_COLORS[controls.indexOf(ctrl) % CONTROL_COLORS.length],
        label: ctrl.name,
      })),
  );

  // Build extra channel curves — use matching control color
  let extraChannelPaths = $derived(
    extraChannels
      .filter((ch) => options.showExtraChannels[ch.name])
      .map((ch) => {
        const matchingCtrl = controls.find((c) => c.name === ch.name);
        const color = matchingCtrl
          ? CONTROL_COLORS[
              controls.indexOf(matchingCtrl) % CONTROL_COLORS.length
            ]
          : EXTRA_CHANNEL_COLOR;
        return {
          path: buildExtraPath(extraChannelHistory, ch.name),
          color,
          label: ch.name,
        };
      }),
  );

  let allPaths = $derived([...controlPaths, ...extraChannelPaths]);
</script>

{#if allPaths.length > 0}
  <div class="chart-container">
    <svg {width} {height} viewBox="0 0 {width} {height}">
      <rect x="0" y="0" {width} {height} fill="#0d0d1a" rx="8" />

      <!-- Horizontal grid -->
      {#each [0, 25, 50, 75, 100] as val (val)}
        {@const y = yScale(val)}
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
          font-size="10"
          text-anchor="end">{val}</text
        >
      {/each}

      <!-- Vertical grid (time) -->
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
          y={height - PADDING.bottom + 16}
          fill={TEXT_COLOR}
          font-size="10"
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
        font-size="10"
        text-anchor="middle"
        transform="rotate(-90, 14, {height / 2})">%</text
      >

      <!-- Curves -->
      {#each allPaths as cp (cp.label)}
        {#if cp.path}
          <path
            d={cp.path}
            fill="none"
            stroke={cp.color}
            stroke-width="1.5"
            opacity="0.8"
          />
        {/if}
      {/each}

      <!-- Legend -->
      {#each allPaths as entry, i (entry.label)}
        {@const lx = PADDING.left + 10 + i * 65}
        <rect x={lx} y="8" width="10" height="3" fill={entry.color} rx="1" />
        <text x={lx + 14} y="13" fill={entry.color} font-size="9"
          >{entry.label}</text
        >
      {/each}
    </svg>
  </div>
{/if}

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
