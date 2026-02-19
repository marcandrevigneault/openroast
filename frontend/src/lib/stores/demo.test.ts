import { describe, it, expect } from 'vitest';
import { generateDemoPoints, type DemoConfig } from './demo';

describe('generateDemoPoints', () => {
	it('generates requested number of points', () => {
		const points = generateDemoPoints(100);
		expect(points).toHaveLength(100);
	});

	it('generates zero points when count is 0', () => {
		expect(generateDemoPoints(0)).toEqual([]);
	});

	it('starts at timestamp 0', () => {
		const points = generateDemoPoints(5);
		expect(points[0].timestamp_ms).toBe(0);
	});

	it('timestamps increase by intervalMs', () => {
		const points = generateDemoPoints(5, { intervalMs: 2000 });
		for (let i = 0; i < points.length; i++) {
			expect(points[i].timestamp_ms).toBe(i * 2000);
		}
	});

	it('uses default interval of 1000ms', () => {
		const points = generateDemoPoints(3);
		expect(points[0].timestamp_ms).toBe(0);
		expect(points[1].timestamp_ms).toBe(1000);
		expect(points[2].timestamp_ms).toBe(2000);
	});

	it('starts ET near configured value', () => {
		const points = generateDemoPoints(1, { etStart: 220 });
		// First point applies model dynamics + noise, so allow wider tolerance
		expect(points[0].et).toBeGreaterThan(210);
		expect(points[0].et).toBeLessThan(230);
	});

	it('starts BT near configured value', () => {
		const points = generateDemoPoints(1, { btStart: 160 });
		// First point applies model dynamics + noise, so allow wider tolerance
		expect(points[0].bt).toBeGreaterThan(150);
		expect(points[0].bt).toBeLessThan(180);
	});

	it('BT rises over time', () => {
		const points = generateDemoPoints(300);
		const firstBt = points[0].bt;
		const lastBt = points[points.length - 1].bt;
		expect(lastBt).toBeGreaterThan(firstBt);
	});

	it('ET rises over time', () => {
		const points = generateDemoPoints(300);
		const firstEt = points[0].et;
		const lastEt = points[points.length - 1].et;
		expect(lastEt).toBeGreaterThan(firstEt);
	});

	it('BT stays below ET after initial period', () => {
		const points = generateDemoPoints(300);
		// After warmup, BT should be below ET
		for (let i = 60; i < points.length; i++) {
			expect(points[i].bt).toBeLessThan(points[i].et);
		}
	});

	it('first point has zero RoR', () => {
		const points = generateDemoPoints(5);
		expect(points[0].et_ror).toBe(0);
		expect(points[0].bt_ror).toBe(0);
	});

	it('subsequent points have non-zero RoR', () => {
		const points = generateDemoPoints(10);
		// At least some of the non-first points should have non-zero RoR
		const nonZeroRor = points.slice(1).filter((p) => p.bt_ror !== 0);
		expect(nonZeroRor.length).toBeGreaterThan(0);
	});

	it('is deterministic for same config', () => {
		const a = generateDemoPoints(50);
		const b = generateDemoPoints(50);
		expect(a).toEqual(b);
	});

	it('higher burner power produces higher final temperatures', () => {
		const lowPower = generateDemoPoints(200, { burnerPower: 0.3 });
		const highPower = generateDemoPoints(200, { burnerPower: 1.0 });
		const lowFinal = lowPower[lowPower.length - 1].bt;
		const highFinal = highPower[highPower.length - 1].bt;
		expect(highFinal).toBeGreaterThan(lowFinal);
	});

	it('all points have valid numeric fields', () => {
		const points = generateDemoPoints(100);
		for (const p of points) {
			expect(typeof p.timestamp_ms).toBe('number');
			expect(typeof p.et).toBe('number');
			expect(typeof p.bt).toBe('number');
			expect(typeof p.et_ror).toBe('number');
			expect(typeof p.bt_ror).toBe('number');
			expect(Number.isFinite(p.et)).toBe(true);
			expect(Number.isFinite(p.bt)).toBe(true);
		}
	});

	it('temperatures stay in reasonable range', () => {
		const points = generateDemoPoints(600);
		for (const p of points) {
			expect(p.et).toBeGreaterThan(50);
			expect(p.et).toBeLessThan(350);
			expect(p.bt).toBeGreaterThan(50);
			expect(p.bt).toBeLessThan(350);
		}
	});
});
