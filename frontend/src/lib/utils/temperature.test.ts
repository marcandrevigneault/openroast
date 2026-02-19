import { describe, it, expect } from "vitest";
import {
  celsiusToFahrenheit,
  fahrenheitToCelsius,
  rateOfRise,
} from "./temperature";

describe("celsiusToFahrenheit", () => {
  it("converts freezing point", () => {
    expect(celsiusToFahrenheit(0)).toBe(32);
  });

  it("converts boiling point", () => {
    expect(celsiusToFahrenheit(100)).toBe(212);
  });

  it("converts typical roasting temperature", () => {
    expect(celsiusToFahrenheit(200)).toBeCloseTo(392);
  });
});

describe("fahrenheitToCelsius", () => {
  it("converts freezing point", () => {
    expect(fahrenheitToCelsius(32)).toBe(0);
  });

  it("converts boiling point", () => {
    expect(fahrenheitToCelsius(212)).toBe(100);
  });

  it("roundtrips with celsiusToFahrenheit", () => {
    const original = 185.5;
    expect(fahrenheitToCelsius(celsiusToFahrenheit(original))).toBeCloseTo(
      original,
    );
  });
});

describe("rateOfRise", () => {
  it("calculates positive RoR", () => {
    // 3°C rise in 3 seconds = 60°C/min
    expect(rateOfRise(153, 150, 3000)).toBeCloseTo(60);
  });

  it("calculates negative RoR (cooling)", () => {
    // 3°C drop in 3 seconds = -60°C/min
    expect(rateOfRise(147, 150, 3000)).toBeCloseTo(-60);
  });

  it("returns zero for zero interval", () => {
    expect(rateOfRise(200, 190, 0)).toBe(0);
  });

  it("returns zero for equal temps", () => {
    expect(rateOfRise(200, 200, 3000)).toBe(0);
  });

  it("handles typical roasting scenario", () => {
    // 1.5°C rise in 3 seconds = 30°C/min (typical mid-roast RoR)
    expect(rateOfRise(181.5, 180, 3000)).toBeCloseTo(30);
  });
});
