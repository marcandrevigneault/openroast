import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";
import ConnectionStatus from "./ConnectionStatus.svelte";

describe("ConnectionStatus", () => {
  it("shows Connected when driver connected and idle", () => {
    render(ConnectionStatus, {
      props: { driverState: "connected", sessionState: "idle" },
    });
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("shows Monitoring when connected and monitoring", () => {
    render(ConnectionStatus, {
      props: { driverState: "connected", sessionState: "monitoring" },
    });
    expect(screen.getByText("Monitoring")).toBeInTheDocument();
  });

  it("shows Recording when connected and recording", () => {
    render(ConnectionStatus, {
      props: { driverState: "connected", sessionState: "recording" },
    });
    expect(screen.getByText("Recording")).toBeInTheDocument();
  });

  it("shows Connecting when driver connecting", () => {
    render(ConnectionStatus, {
      props: { driverState: "connecting", sessionState: "idle" },
    });
    expect(screen.getByText("Connecting...")).toBeInTheDocument();
  });

  it("shows Error when driver in error state", () => {
    render(ConnectionStatus, {
      props: { driverState: "error", sessionState: "idle" },
    });
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("shows Disconnected when driver disconnected", () => {
    render(ConnectionStatus, {
      props: { driverState: "disconnected", sessionState: "idle" },
    });
    expect(screen.getByText("Disconnected")).toBeInTheDocument();
  });
});
