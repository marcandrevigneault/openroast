/**
 * Chart display options — controls which curves are visible on the roast chart.
 */

export interface ChartOptions {
  showET: boolean;
  showBT: boolean;
  showETRor: boolean;
  showBTRor: boolean;
  showControls: Record<string, boolean>;
  showExtraChannels: Record<string, boolean>;
  rorSmoothing: number;
}

export const DEFAULT_CHART_OPTIONS: ChartOptions = {
  showET: true,
  showBT: true,
  showETRor: false,
  showBTRor: false,
  showControls: {},
  showExtraChannels: {},
  rorSmoothing: 1,
};

/**
 * Apply a trailing moving average to an array of RoR values.
 * Returns a new array of the same length with smoothed values.
 * windowSize=1 returns the original values unchanged.
 */
export function smoothRor(values: number[], windowSize: number): number[] {
  if (windowSize <= 1) return values;
  return values.map((_, i) => {
    const start = Math.max(0, i - windowSize + 1);
    const window = values.slice(start, i + 1);
    return window.reduce((sum, v) => sum + v, 0) / window.length;
  });
}

/**
 * Create chart options with all controls and extra channels defaulting to visible.
 */
export function createChartOptions(
  controlChannels: string[] = [],
  extraChannelNames: string[] = [],
): ChartOptions {
  const showControls: Record<string, boolean> = {};
  for (const ch of controlChannels) {
    showControls[ch] = true;
  }
  const showExtraChannels: Record<string, boolean> = {};
  for (const ch of extraChannelNames) {
    showExtraChannels[ch] = true;
  }
  return {
    showET: true,
    showBT: true,
    showETRor: false,
    showBTRor: false,
    showControls,
    showExtraChannels,
    rorSmoothing: 1,
  };
}
