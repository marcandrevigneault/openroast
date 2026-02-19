import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import MachineSettingsPanel from "./MachineSettingsPanel.svelte";
import type { SavedMachine } from "$lib/services/machine-api";

vi.mock("$lib/services/machine-api", () => ({
  getMachine: vi.fn(),
  updateMachine: vi.fn(),
}));

import { getMachine, updateMachine } from "$lib/services/machine-api";

const mockGetMachine = getMachine as ReturnType<typeof vi.fn>;
const mockUpdateMachine = updateMachine as ReturnType<typeof vi.fn>;

const MOCK_MACHINE: SavedMachine = {
  id: "m1",
  name: "Test Roaster",
  protocol: "modbus_tcp",
  connection: { type: "modbus_tcp", host: "192.168.1.10", port: 502 },
  sampling_interval_ms: 3000,
  controls: [
    {
      name: "Burner",
      channel: "burner",
      command: "writeSingle(1,10,{})",
      min: 0,
      max: 100,
      step: 5,
      unit: "%",
    },
  ],
  extra_channels: [
    {
      name: "Inlet",
      modbus: {
        address: 48,
        code: 3,
        device_id: 1,
        divisor: 1,
        mode: "C",
        is_float: false,
        is_bcd: false,
      },
    },
  ],
  et: {
    name: "ET",
    modbus: {
      address: 44,
      code: 3,
      device_id: 1,
      divisor: 1,
      mode: "C",
      is_float: false,
      is_bcd: false,
    },
  },
  bt: {
    name: "BT",
    modbus: {
      address: 43,
      code: 3,
      device_id: 1,
      divisor: 1,
      mode: "C",
      is_float: false,
      is_bcd: false,
    },
  },
};

describe("MachineSettingsPanel", () => {
  const onclose = vi.fn();
  const onsaved = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockGetMachine.mockResolvedValue({ ...MOCK_MACHINE });
  });

  function renderOpen() {
    return render(MachineSettingsPanel, {
      props: {
        machineId: "m1",
        open: true,
        onclose: onclose as unknown as () => void,
        onsaved: onsaved as unknown as (machine: SavedMachine) => void,
      },
    });
  }

  it("renders nothing when closed", () => {
    const { container } = render(MachineSettingsPanel, {
      props: {
        machineId: "m1",
        open: false,
        onclose: onclose as unknown as () => void,
        onsaved: onsaved as unknown as (machine: SavedMachine) => void,
      },
    });
    expect(container.querySelector(".overlay")).toBeNull();
  });

  it("shows loading state initially", () => {
    mockGetMachine.mockReturnValue(new Promise(() => {})); // Never resolves
    renderOpen();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("loads and displays machine settings", async () => {
    renderOpen();
    expect(await screen.findByText("Machine Settings")).toBeInTheDocument();
    expect(await screen.findByDisplayValue("Test Roaster")).toBeInTheDocument();
    expect(await screen.findByDisplayValue("192.168.1.10")).toBeInTheDocument();
  });

  it("shows General section with name and protocol", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    expect(screen.getByText("General")).toBeInTheDocument();
    // "Name" appears in multiple sections
    expect(screen.getAllByText("Name").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Protocol")).toBeInTheDocument();
  });

  it("shows Connection section", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    expect(screen.getByText("Connection")).toBeInTheDocument();
    expect(screen.getByText("Host")).toBeInTheDocument();
    expect(screen.getByText("Port")).toBeInTheDocument();
  });

  it("shows Sensors section with BT and ET", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    expect(screen.getByText("Sensors")).toBeInTheDocument();
    expect(screen.getByDisplayValue("BT")).toBeInTheDocument();
    expect(screen.getByDisplayValue("ET")).toBeInTheDocument();
  });

  it("shows BT modbus register config", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    // BT address=43, ET address=44
    expect(screen.getByDisplayValue("43")).toBeInTheDocument();
    expect(screen.getByDisplayValue("44")).toBeInTheDocument();
  });

  it("shows sensor register fields for modbus protocol", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    // "Address" labels (BT, ET, Inlet = 3 total)
    const addressLabels = screen.getAllByText("Address");
    expect(addressLabels.length).toBe(3);
    // "Fn Code" labels
    const fnCodeLabels = screen.getAllByText("Fn Code");
    expect(fnCodeLabels.length).toBe(3);
  });

  it("shows Controls section with existing controls", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    expect(screen.getByText("Controls")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Burner")).toBeInTheDocument();
    expect(screen.getByDisplayValue("burner")).toBeInTheDocument();
  });

  it("shows Extra Channels section with register config", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    expect(screen.getByText("Extra Channels")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Inlet")).toBeInTheDocument();
    // Inlet address=48
    expect(screen.getByDisplayValue("48")).toBeInTheDocument();
  });

  it("shows section dividers", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    const { container } = renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    const dividers = container.querySelectorAll(".section-divider");
    expect(dividers.length).toBeGreaterThanOrEqual(3);
  });

  it("calls updateMachine and onsaved on save", async () => {
    const updatedMachine = { ...MOCK_MACHINE, name: "Updated Roaster" };
    mockUpdateMachine.mockResolvedValue(updatedMachine);

    renderOpen();
    await screen.findByDisplayValue("Test Roaster");

    const nameInput = screen.getByDisplayValue("Test Roaster");
    await fireEvent.input(nameInput, { target: { value: "Updated Roaster" } });
    await fireEvent.click(screen.getByText("Save"));

    expect(mockUpdateMachine).toHaveBeenCalledWith("m1", expect.anything());
    expect(onsaved).toHaveBeenCalledWith(updatedMachine);
  });

  it("preserves extra channel register config on save", async () => {
    mockUpdateMachine.mockResolvedValue(MOCK_MACHINE);

    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    await fireEvent.click(screen.getByText("Save"));

    const savedMachine = mockUpdateMachine.mock.calls[0][1] as SavedMachine;
    const savedChannel = savedMachine.extra_channels[0] as Record<
      string,
      unknown
    >;
    expect(savedChannel.name).toBe("Inlet");
    expect(savedChannel.modbus).toEqual(
      expect.objectContaining({ address: 48, code: 3 }),
    );
  });

  it("preserves BT/ET sensor config on save", async () => {
    mockUpdateMachine.mockResolvedValue(MOCK_MACHINE);

    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    await fireEvent.click(screen.getByText("Save"));

    const savedMachine = mockUpdateMachine.mock.calls[0][1] as SavedMachine;
    const bt = savedMachine.bt as Record<string, unknown>;
    const et = savedMachine.et as Record<string, unknown>;
    expect(bt.name).toBe("BT");
    expect((bt.modbus as Record<string, unknown>).address).toBe(43);
    expect(et.name).toBe("ET");
    expect((et.modbus as Record<string, unknown>).address).toBe(44);
  });

  it("disables Save button when name is empty", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");

    const nameInput = screen.getByDisplayValue("Test Roaster");
    await fireEvent.input(nameInput, { target: { value: "" } });

    expect(screen.getByText("Save")).toBeDisabled();
  });

  it("calls onclose when Cancel clicked", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    await fireEvent.click(screen.getByText("Cancel"));
    expect(onclose).toHaveBeenCalledOnce();
  });

  it("calls onclose when X button clicked", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    // Multiple × characters (close button + control remove buttons)
    const closeBtns = screen.getAllByText("\u00d7");
    await fireEvent.click(closeBtns[0]); // First one is the dialog close button
    expect(onclose).toHaveBeenCalled();
  });

  it("shows error when load fails", async () => {
    mockGetMachine.mockRejectedValue(new Error("Not found"));
    renderOpen();
    expect(await screen.findByText("Not found")).toBeInTheDocument();
  });

  it("shows error when save fails", async () => {
    mockUpdateMachine.mockRejectedValue(new Error("Validation failed"));
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    await fireEvent.click(screen.getByText("Save"));
    expect(await screen.findByText("Validation failed")).toBeInTheDocument();
  });

  it("adds a new control when + Add clicked in Controls", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");

    const addButtons = screen.getAllByText("+ Add");
    // First "+ Add" is for Controls section
    await fireEvent.click(addButtons[0]);

    // Should now have 2 control cards — check for 2 "Channel" labels
    const channelLabels = screen.getAllByText("Channel");
    expect(channelLabels.length).toBe(2);
  });

  it("adds a new extra channel with register config for modbus", async () => {
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");

    const addButtons = screen.getAllByText("+ Add");
    // Second "+ Add" is for Extra Channels
    await fireEvent.click(addButtons[1]);

    // New modbus channel gets register config fields — now 4 Address labels (BT, ET, Inlet, new)
    const addressLabels = screen.getAllByText("Address");
    expect(addressLabels.length).toBe(4);
  });

  it("shows Serial Port / Baudrate for serial protocol", async () => {
    mockGetMachine.mockResolvedValue({
      ...MOCK_MACHINE,
      protocol: "serial",
      connection: { type: "serial", comport: "/dev/ttyUSB0", baudrate: 115200 },
      et: { name: "ET" },
      bt: { name: "BT" },
      extra_channels: [{ name: "Heater" }],
    });
    renderOpen();
    await screen.findByDisplayValue("/dev/ttyUSB0");
    expect(screen.getByText("Serial Port")).toBeInTheDocument();
    expect(screen.getByText("Baudrate")).toBeInTheDocument();
    // Should NOT show Address labels for serial protocol
    expect(screen.queryAllByText("Address")).toHaveLength(0);
  });

  it("shows S7 register fields for s7 protocol", async () => {
    mockGetMachine.mockResolvedValue({
      ...MOCK_MACHINE,
      protocol: "s7",
      connection: { type: "s7", host: "192.168.1.10", port: 102 },
      et: {
        name: "ET",
        s7: { area: 6, db_nr: 2, start: 36, type: 0, mode: 1, div: 0 },
      },
      bt: {
        name: "BT",
        s7: { area: 6, db_nr: 2, start: 38, type: 0, mode: 1, div: 0 },
      },
      extra_channels: [
        {
          name: "Exhaust",
          s7: { area: 6, db_nr: 2, start: 48, type: 0, mode: 0, div: 0 },
        },
      ],
    });
    renderOpen();
    await screen.findByDisplayValue("Test Roaster");
    // Should show S7 fields: DB Nr, Start, Area, Div
    expect(screen.getAllByText("DB Nr").length).toBe(3); // BT, ET, Exhaust
    expect(screen.getAllByText("Start").length).toBe(3);
    expect(screen.getAllByText("Area").length).toBe(3);
    // Should NOT show Modbus Address labels
    expect(screen.queryAllByText("Address")).toHaveLength(0);
  });
});
