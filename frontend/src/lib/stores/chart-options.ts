/**
 * Chart display options — controls which curves are visible on the roast chart.
 */

export interface ChartOptions {
  showET: boolean;
  showBT: boolean;
  showETRor: boolean;
  showBTRor: boolean;
  showBurner: boolean;
  showAirflow: boolean;
  showDrum: boolean;
}

export const DEFAULT_CHART_OPTIONS: ChartOptions = {
  showET: true,
  showBT: true,
  showETRor: false,
  showBTRor: false,
  showBurner: false,
  showAirflow: false,
  showDrum: false,
};

export interface ControlPoint {
  timestamp_ms: number;
  burner: number;
  airflow: number;
  drum: number;
}
