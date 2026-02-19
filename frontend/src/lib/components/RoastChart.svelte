<script lang="ts">
	import type { TemperaturePoint } from '$lib/stores/machine';
	import { formatTime } from '$lib/stores/machine';

	interface Props {
		history: TemperaturePoint[];
		width?: number;
		height?: number;
	}

	let { history, width = 800, height = 350 }: Props = $props();

	// Chart configuration
	const PADDING = { top: 20, right: 60, bottom: 40, left: 50 };
	const ET_COLOR = '#ff7043';
	const BT_COLOR = '#42a5f5';
	const GRID_COLOR = '#1e1e3a';
	const AXIS_COLOR = '#444';
	const TEXT_COLOR = '#888';

	// Temperature range
	const T_MIN = 50;
	const T_MAX = 300;
	const T_STEP = 50;

	// Derived dimensions
	let plotW = $derived(width - PADDING.left - PADDING.right);
	let plotH = $derived(height - PADDING.top - PADDING.bottom);

	// Time range: show up to 15 minutes, auto-expand
	let maxTimeMs = $derived(
		history.length > 0 ? Math.max(history[history.length - 1].timestamp_ms, 60000) : 60000
	);

	// Rounding to nice intervals
	let timeRangeMs = $derived(Math.ceil(maxTimeMs / 60000) * 60000);

	// Scale functions
	function xScale(timestamp_ms: number): number {
		return PADDING.left + (timestamp_ms / timeRangeMs) * plotW;
	}

	function yScale(temp: number): number {
		return PADDING.top + plotH - ((temp - T_MIN) / (T_MAX - T_MIN)) * plotH;
	}

	// Build SVG path from points
	function buildPath(points: TemperaturePoint[], accessor: (p: TemperaturePoint) => number): string {
		if (points.length === 0) return '';
		return points
			.map((p, i) => {
				const x = xScale(p.timestamp_ms);
				const y = yScale(accessor(p));
				return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
			})
			.join(' ');
	}

	// Grid lines
	let tempGridLines = $derived(
		Array.from({ length: Math.floor((T_MAX - T_MIN) / T_STEP) + 1 }, (_, i) => T_MIN + i * T_STEP)
	);

	let timeGridLines = $derived(() => {
		const interval = timeRangeMs <= 120000 ? 30000 : 60000;
		const lines: number[] = [];
		for (let t = 0; t <= timeRangeMs; t += interval) {
			lines.push(t);
		}
		return lines;
	});

	let etPath = $derived(buildPath(history, (p) => p.et));
	let btPath = $derived(buildPath(history, (p) => p.bt));

	// Current values for readout
	let lastPoint = $derived(history.length > 0 ? history[history.length - 1] : null);
</script>

<div class="chart-container">
	<svg {width} {height} viewBox="0 0 {width} {height}">
		<!-- Background -->
		<rect x="0" y="0" {width} {height} fill="#0d0d1a" rx="8" />

		<!-- Grid: horizontal (temperature) -->
		{#each tempGridLines as temp (temp)}
			{@const y = yScale(temp)}
			<line x1={PADDING.left} y1={y} x2={width - PADDING.right} y2={y} stroke={GRID_COLOR} stroke-width="1" />
			<text x={PADDING.left - 8} y={y + 4} fill={TEXT_COLOR} font-size="11" text-anchor="end">{temp}</text>
		{/each}

		<!-- Grid: vertical (time) -->
		{#each timeGridLines() as t (t)}
			{@const x = xScale(t)}
			<line x1={x} y1={PADDING.top} x2={x} y2={height - PADDING.bottom} stroke={GRID_COLOR} stroke-width="1" />
			<text x={x} y={height - PADDING.bottom + 20} fill={TEXT_COLOR} font-size="11" text-anchor="middle">{formatTime(t)}</text>
		{/each}

		<!-- Axes -->
		<line x1={PADDING.left} y1={PADDING.top} x2={PADDING.left} y2={height - PADDING.bottom} stroke={AXIS_COLOR} stroke-width="1" />
		<line x1={PADDING.left} y1={height - PADDING.bottom} x2={width - PADDING.right} y2={height - PADDING.bottom} stroke={AXIS_COLOR} stroke-width="1" />

		<!-- Y-axis label -->
		<text x="14" y={height / 2} fill={TEXT_COLOR} font-size="11" text-anchor="middle" transform="rotate(-90, 14, {height / 2})">°C</text>

		<!-- ET curve -->
		{#if etPath}
			<path d={etPath} fill="none" stroke={ET_COLOR} stroke-width="2" stroke-linejoin="round" />
		{/if}

		<!-- BT curve -->
		{#if btPath}
			<path d={btPath} fill="none" stroke={BT_COLOR} stroke-width="2" stroke-linejoin="round" />
		{/if}

		<!-- Current value markers -->
		{#if lastPoint}
			{@const etX = xScale(lastPoint.timestamp_ms)}
			{@const etY = yScale(lastPoint.et)}
			{@const btY = yScale(lastPoint.bt)}

			<!-- ET marker -->
			<circle cx={etX} cy={etY} r="4" fill={ET_COLOR} />
			<text x={width - PADDING.right + 8} y={etY + 4} fill={ET_COLOR} font-size="12" font-weight="600">
				ET {lastPoint.et.toFixed(1)}
			</text>

			<!-- BT marker -->
			<circle cx={etX} cy={btY} r="4" fill={BT_COLOR} />
			<text x={width - PADDING.right + 8} y={btY + 4} fill={BT_COLOR} font-size="12" font-weight="600">
				BT {lastPoint.bt.toFixed(1)}
			</text>
		{/if}

		<!-- Legend -->
		<rect x={PADDING.left + 10} y={PADDING.top + 5} width="10" height="3" fill={ET_COLOR} rx="1" />
		<text x={PADDING.left + 24} y={PADDING.top + 10} fill={ET_COLOR} font-size="11">ET</text>
		<rect x={PADDING.left + 50} y={PADDING.top + 5} width="10" height="3" fill={BT_COLOR} rx="1" />
		<text x={PADDING.left + 64} y={PADDING.top + 10} fill={BT_COLOR} font-size="11">BT</text>
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
