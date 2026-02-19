import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import CatalogSelector from "./CatalogSelector.svelte";
import type { SavedMachine } from "$lib/services/machine-api";

vi.mock("$lib/services/machine-api", () => ({
  listManufacturers: vi.fn(),
  listModels: vi.fn(),
  createFromCatalog: vi.fn(),
  createCustomMachine: vi.fn(),
}));

import {
  listManufacturers,
  listModels,
  createFromCatalog,
  createCustomMachine,
} from "$lib/services/machine-api";

const mockListManufacturers = listManufacturers as ReturnType<typeof vi.fn>;
const mockListModels = listModels as ReturnType<typeof vi.fn>;
const mockCreateFromCatalog = createFromCatalog as ReturnType<typeof vi.fn>;
const mockCreateCustomMachine = createCustomMachine as ReturnType<typeof vi.fn>;

describe("CatalogSelector", () => {
  const onadd = vi.fn();
  const onclose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  function renderOpen() {
    return render(CatalogSelector, {
      props: {
        open: true,
        onadd: onadd as unknown as (machine: SavedMachine) => void,
        onclose: onclose as unknown as () => void,
      },
    });
  }

  it("renders nothing when closed", () => {
    const { container } = render(CatalogSelector, {
      props: {
        open: false,
        onadd: onadd as unknown as (machine: SavedMachine) => void,
        onclose: onclose as unknown as () => void,
      },
    });
    expect(container.querySelector(".overlay")).toBeNull();
  });

  it("shows choice step when open", () => {
    renderOpen();
    expect(screen.getByText("Add Machine")).toBeInTheDocument();
    expect(screen.getByText("From Catalog")).toBeInTheDocument();
    expect(screen.getByText("Custom Machine")).toBeInTheDocument();
  });

  it("Custom Machine button is not disabled", () => {
    renderOpen();
    const btn = screen.getByText("Custom Machine").closest("button");
    expect(btn).not.toBeDisabled();
  });

  // --- Catalog flow ---

  it("loads manufacturers when From Catalog clicked", async () => {
    mockListManufacturers.mockResolvedValue([
      { id: "carmomaq", name: "Carmomaq", country: "BR", model_count: 4 },
    ]);
    renderOpen();
    await fireEvent.click(screen.getByText("From Catalog"));
    expect(mockListManufacturers).toHaveBeenCalledOnce();
    expect(await screen.findByText("Select Manufacturer")).toBeInTheDocument();
    expect(screen.getByText("Carmomaq")).toBeInTheDocument();
  });

  it("loads models when manufacturer selected", async () => {
    mockListManufacturers.mockResolvedValue([
      { id: "carmomaq", name: "Carmomaq", country: "BR", model_count: 1 },
    ]);
    mockListModels.mockResolvedValue([
      {
        id: "stratto-2.0",
        name: "Stratto 2.0",
        protocol: "modbus_tcp",
        controls: [{ name: "Air" }],
      },
    ]);
    renderOpen();
    await fireEvent.click(screen.getByText("From Catalog"));
    await screen.findByText("Carmomaq");
    await fireEvent.click(screen.getByText("Carmomaq"));
    expect(mockListModels).toHaveBeenCalledWith("carmomaq");
    expect(await screen.findByText("Stratto 2.0")).toBeInTheDocument();
  });

  it("shows confirm step and creates machine from catalog", async () => {
    mockListManufacturers.mockResolvedValue([
      { id: "carmomaq", name: "Carmomaq", country: "BR", model_count: 1 },
    ]);
    mockListModels.mockResolvedValue([
      {
        id: "stratto-2.0",
        name: "Stratto 2.0",
        protocol: "modbus_tcp",
        controls: [{ name: "Air" }],
        extra_channels: [],
      },
    ]);
    const machine = { id: "m1", name: "Stratto 2.0", protocol: "modbus_tcp" };
    mockCreateFromCatalog.mockResolvedValue({ id: "m1", machine });

    renderOpen();
    await fireEvent.click(screen.getByText("From Catalog"));
    await screen.findByText("Carmomaq");
    await fireEvent.click(screen.getByText("Carmomaq"));
    await screen.findByText("Stratto 2.0");
    await fireEvent.click(screen.getByText("Stratto 2.0"));

    expect(screen.getByText("Confirm")).toBeInTheDocument();
    await fireEvent.click(screen.getByText("Add Machine"));

    expect(mockCreateFromCatalog).toHaveBeenCalledWith(
      "carmomaq",
      "stratto-2.0",
      "Stratto 2.0",
    );
    expect(onadd).toHaveBeenCalledWith(machine);
  });

  // --- Custom flow ---

  it("shows custom form when Custom Machine clicked", async () => {
    renderOpen();
    await fireEvent.click(screen.getByText("Custom Machine"));
    expect(
      screen.getByText("Custom Machine", { selector: "h3" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Machine Name")).toBeInTheDocument();
    expect(screen.getByText("Protocol")).toBeInTheDocument();
    expect(screen.getByText("Host")).toBeInTheDocument();
    expect(screen.getByText("Port")).toBeInTheDocument();
  });

  it("shows Serial Port / Baudrate labels for serial protocol", async () => {
    renderOpen();
    await fireEvent.click(screen.getByText("Custom Machine"));
    const select = screen.getByDisplayValue("Modbus TCP");
    await fireEvent.change(select, { target: { value: "serial" } });
    expect(screen.getByText("Serial Port")).toBeInTheDocument();
    expect(screen.getByText("Baudrate")).toBeInTheDocument();
  });

  it("creates custom machine on submit", async () => {
    const machine = {
      id: "m2",
      name: "My Roaster",
      protocol: "modbus_tcp",
      connection: { type: "modbus_tcp", host: "10.0.0.1", port: 502 },
      sampling_interval_ms: 3000,
      controls: [],
      extra_channels: [],
    };
    mockCreateCustomMachine.mockResolvedValue({ id: "m2", machine });

    renderOpen();
    await fireEvent.click(screen.getByText("Custom Machine"));

    const nameInput = screen.getByPlaceholderText("My Roaster");
    await fireEvent.input(nameInput, { target: { value: "My Roaster" } });

    await fireEvent.click(screen.getByText("Create Machine"));

    expect(mockCreateCustomMachine).toHaveBeenCalledWith({
      name: "My Roaster",
      protocol: "modbus_tcp",
      connection: { type: "modbus_tcp", host: "192.168.1.1", port: 502 },
    });
    expect(onadd).toHaveBeenCalledWith(machine);
  });

  it("disables Create Machine when name is empty", async () => {
    renderOpen();
    await fireEvent.click(screen.getByText("Custom Machine"));
    const submitBtn = screen.getByText("Create Machine");
    expect(submitBtn).toBeDisabled();
  });

  // --- Navigation ---

  it("back from custom goes to choose", async () => {
    renderOpen();
    await fireEvent.click(screen.getByText("Custom Machine"));
    expect(
      screen.getByText("Custom Machine", { selector: "h3" }),
    ).toBeInTheDocument();
    const backBtn = screen.getByText("\u2190");
    await fireEvent.click(backBtn);
    expect(screen.getByText("Add Machine")).toBeInTheDocument();
  });

  it("shows error when catalog load fails", async () => {
    mockListManufacturers.mockRejectedValue(new Error("Network error"));
    renderOpen();
    await fireEvent.click(screen.getByText("From Catalog"));
    expect(await screen.findByText("Network error")).toBeInTheDocument();
  });

  it("calls onclose when Cancel clicked", async () => {
    renderOpen();
    await fireEvent.click(screen.getByText("Cancel"));
    expect(onclose).toHaveBeenCalledOnce();
  });
});
