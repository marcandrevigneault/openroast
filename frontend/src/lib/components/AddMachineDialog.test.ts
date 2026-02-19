import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import AddMachineDialog from "./AddMachineDialog.svelte";

describe("AddMachineDialog", () => {
  it("does not render when closed", () => {
    const { container } = render(AddMachineDialog, {
      props: { open: false, onadd: () => {}, onclose: () => {} },
    });
    expect(container.querySelector(".overlay")).toBeFalsy();
  });

  it("renders when open", () => {
    render(AddMachineDialog, {
      props: { open: true, onadd: () => {}, onclose: () => {} },
    });
    expect(screen.getByText("Add Machine")).toBeInTheDocument();
  });

  it("renders name input", () => {
    render(AddMachineDialog, {
      props: { open: true, onadd: () => {}, onclose: () => {} },
    });
    expect(
      screen.getByPlaceholderText("e.g. Stratto Pro 300"),
    ).toBeInTheDocument();
  });

  it("disables Add button when name is empty", () => {
    render(AddMachineDialog, {
      props: { open: true, onadd: () => {}, onclose: () => {} },
    });
    const addBtn = screen.getByText("Add");
    expect(addBtn).toBeDisabled();
  });

  it("enables Add button when name is entered", async () => {
    render(AddMachineDialog, {
      props: { open: true, onadd: () => {}, onclose: () => {} },
    });
    const input = screen.getByPlaceholderText("e.g. Stratto Pro 300");
    await fireEvent.input(input, { target: { value: "My Roaster" } });
    const addBtn = screen.getByText("Add");
    expect(addBtn).not.toBeDisabled();
  });

  it("calls onadd with trimmed name on submit", async () => {
    const onadd = vi.fn();
    const onclose = vi.fn();
    render(AddMachineDialog, {
      props: { open: true, onadd, onclose },
    });
    const input = screen.getByPlaceholderText("e.g. Stratto Pro 300");
    await fireEvent.input(input, { target: { value: "  My Roaster  " } });
    await fireEvent.submit(screen.getByText("Add").closest("form")!);
    expect(onadd).toHaveBeenCalledWith("My Roaster");
    expect(onclose).toHaveBeenCalled();
  });

  it("calls onclose when Cancel clicked", async () => {
    const onclose = vi.fn();
    render(AddMachineDialog, {
      props: { open: true, onadd: () => {}, onclose },
    });
    await fireEvent.click(screen.getByText("Cancel"));
    expect(onclose).toHaveBeenCalledOnce();
  });

  it("calls onclose on Escape key", async () => {
    const onclose = vi.fn();
    const { container } = render(AddMachineDialog, {
      props: { open: true, onadd: () => {}, onclose },
    });
    const overlay = container.querySelector(".overlay")!;
    await fireEvent.keyDown(overlay, { key: "Escape" });
    expect(onclose).toHaveBeenCalledOnce();
  });
});
