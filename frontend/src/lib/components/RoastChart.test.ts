import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import RoastChart from './RoastChart.svelte';
import type { TemperaturePoint } from '$lib/stores/machine';

function makePoints(count: number): TemperaturePoint[] {
	return Array.from({ length: count }, (_, i) => ({
		timestamp_ms: i * 1000,
		et: 200 + i * 0.5,
		bt: 160 + i * 0.8,
		et_ror: 5,
		bt_ror: 8
	}));
}

describe('RoastChart', () => {
	it('renders SVG element', () => {
		const { container } = render(RoastChart, { props: { history: [] } });
		const svg = container.querySelector('svg');
		expect(svg).toBeTruthy();
	});

	it('renders background rect', () => {
		const { container } = render(RoastChart, { props: { history: [] } });
		const rects = container.querySelectorAll('rect');
		expect(rects.length).toBeGreaterThan(0);
	});

	it('renders temperature grid lines', () => {
		const { container } = render(RoastChart, { props: { history: [] } });
		const lines = container.querySelectorAll('line');
		// Should have horizontal grid lines (temp) + vertical (time) + axis lines
		expect(lines.length).toBeGreaterThan(2);
	});

	it('renders ET path with data', () => {
		const { container } = render(RoastChart, {
			props: { history: makePoints(20) }
		});
		const paths = container.querySelectorAll('path');
		// Should have ET and BT paths
		expect(paths.length).toBe(2);
	});

	it('renders no paths when history is empty', () => {
		const { container } = render(RoastChart, { props: { history: [] } });
		const paths = container.querySelectorAll('path');
		expect(paths.length).toBe(0);
	});

	it('renders current value markers with data', () => {
		const { container } = render(RoastChart, {
			props: { history: makePoints(5) }
		});
		const circles = container.querySelectorAll('circle');
		// Should have ET and BT endpoint markers
		expect(circles.length).toBe(2);
	});

	it('renders legend items', () => {
		const { container } = render(RoastChart, { props: { history: [] } });
		const texts = container.querySelectorAll('text');
		const textContent = Array.from(texts).map((t) => t.textContent);
		expect(textContent).toContain('ET');
		expect(textContent).toContain('BT');
	});

	it('respects custom width and height', () => {
		const { container } = render(RoastChart, {
			props: { history: [], width: 600, height: 250 }
		});
		const svg = container.querySelector('svg');
		expect(svg?.getAttribute('width')).toBe('600');
		expect(svg?.getAttribute('height')).toBe('250');
	});

	it('shows latest ET and BT values', () => {
		const points = makePoints(10);
		const lastPoint = points[points.length - 1];
		const { container } = render(RoastChart, { props: { history: points } });
		const texts = container.querySelectorAll('text');
		const textContent = Array.from(texts).map((t) => t.textContent?.trim());
		// Should show "ET <value>" and "BT <value>"
		expect(textContent.some((t) => t?.includes(`ET ${lastPoint.et.toFixed(1)}`))).toBe(true);
		expect(textContent.some((t) => t?.includes(`BT ${lastPoint.bt.toFixed(1)}`))).toBe(true);
	});
});
