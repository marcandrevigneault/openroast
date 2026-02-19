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
}

export const DEFAULT_CHART_OPTIONS: ChartOptions = {
  showET: true,
  showBT: true,
  showETRor: false,
  showBTRor: false,
  showControls: {},
  showExtraChannels: {},
};

/**
 * Create chart options with all controls and extra channels defaulting to hidden.
 */
export function createChartOptions(
  controlChannels: string[] = [],
  extraChannelNames: string[] = [],
): ChartOptions {
  const showControls: Record<string, boolean> = {};
  for (const ch of controlChannels) {
    showControls[ch] = false;
  }
  const showExtraChannels: Record<string, boolean> = {};
  for (const ch of extraChannelNames) {
    showExtraChannels[ch] = false;
  }
  return {
    showET: true,
    showBT: true,
    showETRor: false,
    showBTRor: false,
    showControls,
    showExtraChannels,
  };
}
