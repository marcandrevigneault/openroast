/**
 * Temperature conversion and rate-of-rise calculations.
 */

/** Convert Celsius to Fahrenheit. */
export function celsiusToFahrenheit(c: number): number {
  return c * 1.8 + 32;
}

/** Convert Fahrenheit to Celsius. */
export function fahrenheitToCelsius(f: number): number {
  return (f - 32) / 1.8;
}

/**
 * Calculate Rate of Rise (RoR) in degrees per minute.
 *
 * @param current - Current temperature reading
 * @param previous - Previous temperature reading
 * @param intervalMs - Time between readings in milliseconds
 * @returns Rate of rise in °/min, or 0 if interval is zero
 */
export function rateOfRise(
  current: number,
  previous: number,
  intervalMs: number,
): number {
  if (intervalMs <= 0) return 0;
  const intervalMin = intervalMs / 60000;
  return (current - previous) / intervalMin;
}
