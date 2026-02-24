import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import ControlSlider from "./ControlSlider.svelte";

describe("ControlSlider", () => {
  it("renders label", () => {
    render(ControlSlider, { props: { label: "Burner", value: 50 } });
    expect(screen.getByText("Burner")).toBeInTheDocument();
  });

  it("shows current value in a button", () => {
    render(ControlSlider, { props: { label: "Burner", value: 75 } });
    const btn = screen.getByTitle("Click to edit");
    expect(btn.textContent).toContain("75");
  });

  it("renders range input with correct attributes", () => {
    render(ControlSlider, {
      props: { label: "Air", value: 50, min: 0, max: 100, step: 5 },
    });
    const input = screen.getByRole("slider");
    expect(input).toHaveAttribute("min", "0");
    expect(input).toHaveAttribute("max", "100");
    expect(input).toHaveAttribute("step", "5");
  });

  it("is disabled when disabled prop is true", () => {
    render(ControlSlider, {
      props: { label: "Burner", value: 50, disabled: true },
    });
    const input = screen.getByRole("slider");
    expect(input).toBeDisabled();
  });

  it("calls onchange when slider moves", async () => {
    const onchange = vi.fn();
    render(ControlSlider, {
      props: { label: "Burner", value: 50, onchange },
    });
    const input = screen.getByRole("slider");
    await fireEvent.input(input, { target: { value: "75" } });
    expect(onchange).toHaveBeenCalledWith(75);
  });

  // --- Drag events ---

  it("calls ondragstart on pointerdown", async () => {
    const ondragstart = vi.fn();
    render(ControlSlider, {
      props: { label: "Burner", value: 50, ondragstart },
    });
    const input = screen.getByRole("slider");
    await fireEvent.pointerDown(input);
    expect(ondragstart).toHaveBeenCalledOnce();
  });

  it("calls ondragend on pointerup after drag", async () => {
    const ondragend = vi.fn();
    render(ControlSlider, {
      props: { label: "Burner", value: 50, ondragend },
    });
    const input = screen.getByRole("slider");
    await fireEvent.pointerDown(input);
    await fireEvent.pointerUp(window);
    expect(ondragend).toHaveBeenCalledOnce();
  });

  // --- Editable value ---

  it("enters edit mode on value click", async () => {
    render(ControlSlider, {
      props: { label: "Burner", value: 50 },
    });
    const btn = screen.getByTitle("Click to edit");
    await fireEvent.click(btn);
    const input = screen.getByRole("spinbutton");
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue(50);
  });

  it("commits valid value on Enter", async () => {
    const onchange = vi.fn();
    render(ControlSlider, {
      props: { label: "Burner", value: 50, onchange },
    });
    await fireEvent.click(screen.getByTitle("Click to edit"));
    const input = screen.getByRole("spinbutton");
    await fireEvent.input(input, { target: { value: "80" } });
    await fireEvent.keyDown(input, { key: "Enter" });
    expect(onchange).toHaveBeenCalledWith(80);
  });

  it("cancels edit on Escape", async () => {
    const onchange = vi.fn();
    render(ControlSlider, {
      props: { label: "Burner", value: 50, onchange },
    });
    await fireEvent.click(screen.getByTitle("Click to edit"));
    const input = screen.getByRole("spinbutton");
    await fireEvent.input(input, { target: { value: "99" } });
    await fireEvent.keyDown(input, { key: "Escape" });
    // Should not have called onchange and should show button again
    expect(onchange).not.toHaveBeenCalled();
    expect(screen.getByTitle("Click to edit")).toBeInTheDocument();
  });

  it("clamps value to min/max on commit", async () => {
    const onchange = vi.fn();
    render(ControlSlider, {
      props: { label: "Burner", value: 50, min: 0, max: 100, onchange },
    });
    await fireEvent.click(screen.getByTitle("Click to edit"));
    const input = screen.getByRole("spinbutton");
    await fireEvent.input(input, { target: { value: "150" } });
    await fireEvent.keyDown(input, { key: "Enter" });
    expect(onchange).toHaveBeenCalledWith(100);
  });

  it("snaps value to step on commit", async () => {
    const onchange = vi.fn();
    render(ControlSlider, {
      props: {
        label: "Burner",
        value: 50,
        min: 0,
        max: 100,
        step: 5,
        onchange,
      },
    });
    await fireEvent.click(screen.getByTitle("Click to edit"));
    const input = screen.getByRole("spinbutton");
    await fireEvent.input(input, { target: { value: "73" } });
    await fireEvent.keyDown(input, { key: "Enter" });
    expect(onchange).toHaveBeenCalledWith(75);
  });

  it("commits value on blur", async () => {
    const onchange = vi.fn();
    render(ControlSlider, {
      props: { label: "Burner", value: 50, onchange },
    });
    await fireEvent.click(screen.getByTitle("Click to edit"));
    const input = screen.getByRole("spinbutton");
    await fireEvent.input(input, { target: { value: "60" } });
    await fireEvent.blur(input);
    expect(onchange).toHaveBeenCalledWith(60);
  });

  it("does not enter edit mode when disabled", async () => {
    render(ControlSlider, {
      props: { label: "Burner", value: 50, disabled: true },
    });
    const btn = screen.getByTitle("Click to edit");
    await fireEvent.click(btn);
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  });

  it("discards non-numeric input on commit", async () => {
    const onchange = vi.fn();
    render(ControlSlider, {
      props: { label: "Burner", value: 50, onchange },
    });
    await fireEvent.click(screen.getByTitle("Click to edit"));
    const input = screen.getByRole("spinbutton");
    await fireEvent.input(input, { target: { value: "abc" } });
    await fireEvent.keyDown(input, { key: "Enter" });
    expect(onchange).not.toHaveBeenCalled();
  });
});
