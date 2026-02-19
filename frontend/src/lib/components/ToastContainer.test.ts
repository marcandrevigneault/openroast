import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import ToastContainer from "./ToastContainer.svelte";
import { addToast, clearToasts } from "$lib/stores/toast";

describe("ToastContainer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    clearToasts();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders nothing when no toasts", () => {
    const { container } = render(ToastContainer);
    expect(container.querySelector(".toast-container")).toBeNull();
  });

  it("renders a toast message", async () => {
    render(ToastContainer);
    addToast("Something went wrong");
    // Need to wait for effect to propagate
    await vi.advanceTimersByTimeAsync(0);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders machine label when provided", async () => {
    render(ToastContainer);
    addToast("Lost connection", "error", "Stratto 2.0");
    await vi.advanceTimersByTimeAsync(0);
    expect(screen.getByText("Stratto 2.0")).toBeInTheDocument();
    expect(screen.getByText("Lost connection")).toBeInTheDocument();
  });

  it("applies error class for error type", async () => {
    const { container } = render(ToastContainer);
    addToast("Error!", "error");
    await vi.advanceTimersByTimeAsync(0);
    expect(container.querySelector(".toast-error")).not.toBeNull();
  });

  it("applies warning class for warning type", async () => {
    const { container } = render(ToastContainer);
    addToast("Warning!", "warning");
    await vi.advanceTimersByTimeAsync(0);
    expect(container.querySelector(".toast-warning")).not.toBeNull();
  });

  it("dismisses toast when X clicked", async () => {
    render(ToastContainer);
    addToast("Temp error");
    await vi.advanceTimersByTimeAsync(0);
    expect(screen.getByText("Temp error")).toBeInTheDocument();

    await fireEvent.click(screen.getByLabelText("Dismiss"));
    await vi.advanceTimersByTimeAsync(0);
    expect(screen.queryByText("Temp error")).not.toBeInTheDocument();
  });

  it("renders multiple toasts", async () => {
    render(ToastContainer);
    addToast("Error 1");
    addToast("Error 2");
    await vi.advanceTimersByTimeAsync(0);
    expect(screen.getByText("Error 1")).toBeInTheDocument();
    expect(screen.getByText("Error 2")).toBeInTheDocument();
  });
});
