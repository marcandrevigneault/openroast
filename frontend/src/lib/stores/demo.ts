/**
 * Demo data generator — simulates a roasting machine producing
 * temperature readings so the UI can be previewed without a backend.
 */

import type { TemperaturePoint } from './machine';

export interface DemoConfig {
	/** Sampling interval in milliseconds */
	intervalMs: number;
	/** Initial ET temperature */
	etStart: number;
	/** Initial BT temperature (after charge) */
	btStart: number;
	/** Burner power 0-1 */
	burnerPower: number;
}

const DEFAULT_CONFIG: DemoConfig = {
	intervalMs: 1000,
	etStart: 210,
	btStart: 155,
	burnerPower: 0.7
};

/**
 * Generate a sequence of demo temperature points simulating a roast.
 * Pure function, deterministic for a given config.
 */
export function generateDemoPoints(
	count: number,
	config: Partial<DemoConfig> = {}
): TemperaturePoint[] {
	const cfg = { ...DEFAULT_CONFIG, ...config };
	const points: TemperaturePoint[] = [];

	let et = cfg.etStart;
	let bt = cfg.btStart;
	let prevEt = et;
	let prevBt = bt;

	for (let i = 0; i < count; i++) {
		const t = i * cfg.intervalMs;
		const seconds = t / 1000;

		// BT: starts low (charge), dips slightly, then rises in an S-curve
		const btTarget = 220 + cfg.burnerPower * 30;
		const btRate = 0.15 * cfg.burnerPower;
		// Turning point dip in first 30 seconds
		const dipFactor = seconds < 30 ? -0.3 * (1 - seconds / 30) : 0;
		bt = bt + (btTarget - bt) * btRate * (cfg.intervalMs / 1000) + dipFactor;

		// ET: rises gradually from start temp
		const etTarget = 240 + cfg.burnerPower * 40;
		const etRate = 0.08 * cfg.burnerPower;
		et = et + (etTarget - et) * etRate * (cfg.intervalMs / 1000);

		// Add slight noise for realism
		const noiseEt = Math.sin(i * 0.7) * 0.3;
		const noiseBt = Math.sin(i * 1.1 + 0.5) * 0.2;

		const etVal = Math.round((et + noiseEt) * 10) / 10;
		const btVal = Math.round((bt + noiseBt) * 10) / 10;

		// RoR in °C/min
		const etRor =
			i > 0 ? Math.round(((etVal - prevEt) / (cfg.intervalMs / 60000)) * 10) / 10 : 0;
		const btRor =
			i > 0 ? Math.round(((btVal - prevBt) / (cfg.intervalMs / 60000)) * 10) / 10 : 0;

		points.push({
			timestamp_ms: t,
			et: etVal,
			bt: btVal,
			et_ror: etRor,
			bt_ror: btRor
		});

		prevEt = etVal;
		prevBt = btVal;
	}

	return points;
}
