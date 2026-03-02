"""Tests for simulator register map builder."""

from __future__ import annotations

import struct

from openroast.models.catalog import (
    CatalogModel,
    ChannelConfig,
    ControlConfig,
    ModbusConnectionConfig,
    ModbusRegisterConfig,
    ProtocolType,
)
from openroast.simulator.register_map import (
    _int_to_bcd,
    build_server_context,
    encode_value,
    read_register_raw,
    write_channel,
)

# ── encode_value ──────────────────────────────────────────────────────


class TestEncodeValue:
    """Tests for encode_value."""

    def test_signed_int16_celsius(self) -> None:
        config = ModbusRegisterConfig(address=0, divisor=1, mode="C")
        result = encode_value(200.0, config)
        assert result == [2000]  # 200 * 10

    def test_signed_int16_no_divisor(self) -> None:
        config = ModbusRegisterConfig(address=0, divisor=0, mode="")
        result = encode_value(50.0, config)
        assert result == [50]

    def test_signed_int16_divisor_2(self) -> None:
        config = ModbusRegisterConfig(address=0, divisor=2, mode="C")
        result = encode_value(123.45, config)
        assert result == [12345]  # 123.45 * 100

    def test_signed_int16_negative(self) -> None:
        config = ModbusRegisterConfig(address=0, divisor=0, mode="")
        result = encode_value(-10.0, config)
        # -10 as unsigned 16-bit: 65526
        assert result == [0x10000 - 10]

    def test_fahrenheit_mode(self) -> None:
        config = ModbusRegisterConfig(address=0, divisor=1, mode="F")
        # 200°C = 392°F → * 10 = 3920
        result = encode_value(200.0, config)
        assert result == [3920]

    def test_bcd_encoding(self) -> None:
        config = ModbusRegisterConfig(
            address=0, divisor=1, mode="F", is_bcd=True,
        )
        # 200°C = 392°F → * 10 = 3920 → BCD 0x3920
        result = encode_value(200.0, config)
        assert result == [0x3920]

    def test_float32_big_endian(self) -> None:
        config = ModbusRegisterConfig(
            address=0, divisor=0, mode="F", is_float=True,
        )
        # 200°C = 392°F
        result = encode_value(200.0, config, word_order_little=False)
        packed = struct.pack(">HH", result[0], result[1])
        value = struct.unpack(">f", packed)[0]
        assert abs(value - 392.0) < 0.1

    def test_float32_little_endian(self) -> None:
        config = ModbusRegisterConfig(
            address=0, divisor=0, mode="F", is_float=True,
        )
        result = encode_value(200.0, config, word_order_little=True)
        # little endian: [low, high]
        packed = struct.pack(">HH", result[1], result[0])
        value = struct.unpack(">f", packed)[0]
        assert abs(value - 392.0) < 0.1

    def test_clamp_int16_overflow(self) -> None:
        config = ModbusRegisterConfig(address=0, divisor=0, mode="")
        result = encode_value(40000.0, config)
        assert result == [32767]  # clamped to max int16

    def test_clamp_int16_underflow(self) -> None:
        config = ModbusRegisterConfig(address=0, divisor=0, mode="")
        result = encode_value(-40000.0, config)
        # -32768 as unsigned: 32768
        assert result == [32768]


class TestIntToBcd:
    """Tests for BCD encoding."""

    def test_zero(self) -> None:
        assert _int_to_bcd(0) == 0

    def test_simple(self) -> None:
        assert _int_to_bcd(215) == 0x0215

    def test_round_number(self) -> None:
        assert _int_to_bcd(3920) == 0x3920

    def test_negative_clamps_to_zero(self) -> None:
        assert _int_to_bcd(-5) == 0


# ── build_server_context ──────────────────────────────────────────────


def _make_model(
    bt_addr: int = 43,
    et_addr: int = 44,
    bt_code: int = 3,
    et_code: int = 3,
    device_id: int = 1,
    divisor: int = 1,
    mode: str = "C",
    is_float: bool = False,
    is_bcd: bool = False,
    word_order_little: bool = True,
    extra_channels: list[ChannelConfig] | None = None,
    controls: list[ControlConfig] | None = None,
) -> CatalogModel:
    """Helper to create a CatalogModel for testing."""
    return CatalogModel(
        id="test-model",
        name="Test Model",
        protocol=ProtocolType.MODBUS_TCP,
        sampling_interval_ms=1000,
        connection=ModbusConnectionConfig(
            type="modbus_tcp",
            host="127.0.0.1",
            port=502,
            word_order_little=word_order_little,
        ),
        bt=ChannelConfig(
            name="BT",
            modbus=ModbusRegisterConfig(
                address=bt_addr, code=bt_code, device_id=device_id,
                divisor=divisor, mode=mode, is_float=is_float, is_bcd=is_bcd,
            ),
        ),
        et=ChannelConfig(
            name="ET",
            modbus=ModbusRegisterConfig(
                address=et_addr, code=et_code, device_id=device_id,
                divisor=divisor, mode=mode, is_float=is_float, is_bcd=is_bcd,
            ),
        ),
        extra_channels=extra_channels or [],
        controls=controls or [],
    )


class TestBuildServerContext:
    """Tests for build_server_context."""

    def test_basic_int16_registers(self) -> None:
        model = _make_model()
        ctx = build_server_context(model, initial_bt=200.0, initial_et=220.0)

        bt_raw = read_register_raw(ctx, device_id=1, address=43, code=3)
        et_raw = read_register_raw(ctx, device_id=1, address=44, code=3)
        assert bt_raw == 2000  # 200 * 10
        assert et_raw == 2200  # 220 * 10

    def test_input_registers_fc4(self) -> None:
        model = _make_model(bt_code=4, et_code=4)
        ctx = build_server_context(model, initial_bt=100.0, initial_et=150.0)

        bt_raw = read_register_raw(ctx, device_id=1, address=43, code=4)
        et_raw = read_register_raw(ctx, device_id=1, address=44, code=4)
        assert bt_raw == 1000
        assert et_raw == 1500

    def test_multiple_device_ids(self) -> None:
        """Test machines like Coffed that use different device_ids."""
        model = CatalogModel(
            id="multi-device",
            name="Multi Device",
            protocol=ProtocolType.MODBUS_TCP,
            sampling_interval_ms=1000,
            connection=ModbusConnectionConfig(type="modbus_tcp"),
            bt=ChannelConfig(
                name="BT",
                modbus=ModbusRegisterConfig(
                    address=52, code=3, device_id=4, divisor=1, mode="C",
                ),
            ),
            et=ChannelConfig(
                name="ET",
                modbus=ModbusRegisterConfig(
                    address=52, code=3, device_id=3, divisor=1, mode="C",
                ),
            ),
        )
        ctx = build_server_context(model, initial_bt=180.0, initial_et=200.0)

        bt_raw = read_register_raw(ctx, device_id=4, address=52, code=3)
        et_raw = read_register_raw(ctx, device_id=3, address=52, code=3)
        assert bt_raw == 1800
        assert et_raw == 2000

    def test_extra_channels(self) -> None:
        model = _make_model(
            extra_channels=[
                ChannelConfig(
                    name="Burner",
                    modbus=ModbusRegisterConfig(
                        address=45, code=3, device_id=1, divisor=0, mode="",
                    ),
                ),
            ],
        )
        ctx = build_server_context(model)
        burner_raw = read_register_raw(ctx, device_id=1, address=45, code=3)
        assert burner_raw == 0

    def test_control_addresses_created(self) -> None:
        model = _make_model(
            controls=[
                ControlConfig(
                    name="Burner", channel="burner",
                    command="writeSingle(1,45,{})",
                    min=0, max=100, step=1,
                ),
            ],
        )
        ctx = build_server_context(model)
        # Control address should exist and be 0
        raw = read_register_raw(ctx, device_id=1, address=45, code=3)
        assert raw == 0

    def test_compound_command_address(self) -> None:
        """Test Probat-style compound commands."""
        model = _make_model(
            controls=[
                ControlConfig(
                    name="Burner", channel="burner",
                    command="writeSingle(1,12290,{});mwrite(1,12318,65531,4)",
                    min=0, max=100, step=1,
                ),
            ],
        )
        ctx = build_server_context(model)
        raw = read_register_raw(ctx, device_id=1, address=12290, code=3)
        assert raw == 0

    def test_bracket_command_syntax(self) -> None:
        """Test Coffed-style bracket command syntax."""
        model = _make_model(
            controls=[
                ControlConfig(
                    name="Slider 1", channel="slider1",
                    command="writeSingle([1,1,{}])",
                    min=0, max=100, step=1,
                ),
            ],
        )
        ctx = build_server_context(model)
        raw = read_register_raw(ctx, device_id=1, address=1, code=3)
        assert raw == 0

    def test_toggle_control_address(self) -> None:
        """Toggle controls allocate registers like sliders."""
        model = _make_model(
            controls=[
                ControlConfig(
                    name="Machine ON/OFF", channel="machine_onoff",
                    type="toggle",
                    command="writeSingle(1,50,{})",
                    on_value=1, off_value=2,
                ),
            ],
        )
        ctx = build_server_context(model)
        raw = read_register_raw(ctx, device_id=1, address=50, code=3)
        assert raw == 0

    def test_mixed_slider_and_toggle_controls(self) -> None:
        """Both slider and toggle controls create registers."""
        model = _make_model(
            controls=[
                ControlConfig(
                    name="Burner", channel="burner",
                    command="writeSingle(1,45,{})",
                    min=0, max=100, step=1,
                ),
                ControlConfig(
                    name="Machine ON/OFF", channel="machine_onoff",
                    type="toggle",
                    command="writeSingle(1,50,{})",
                    on_value=1, off_value=2,
                ),
                ControlConfig(
                    name="Cooling", channel="cooling",
                    type="toggle",
                    command="writeSingle(1,58,{})",
                    on_value=1, off_value=2,
                ),
            ],
        )
        ctx = build_server_context(model)
        assert read_register_raw(ctx, device_id=1, address=45, code=3) == 0
        assert read_register_raw(ctx, device_id=1, address=50, code=3) == 0
        assert read_register_raw(ctx, device_id=1, address=58, code=3) == 0


# ── write_channel / read_register_raw ────────────────────────────────


class TestWriteReadChannel:
    """Tests for write_channel and read_register_raw."""

    def test_write_and_read_back(self) -> None:
        model = _make_model()
        ctx = build_server_context(model, initial_bt=25.0, initial_et=25.0)

        write_channel(ctx, model.bt.modbus, 185.5)
        raw = read_register_raw(ctx, device_id=1, address=43, code=3)
        assert raw == 1855

    def test_write_float_and_read_back(self) -> None:
        model = _make_model(
            is_float=True, mode="F", divisor=0,
            word_order_little=True,
        )
        ctx = build_server_context(model, initial_bt=200.0, initial_et=220.0)

        write_channel(ctx, model.bt.modbus, 200.0)
        r0 = read_register_raw(ctx, device_id=1, address=43, code=3)
        r1 = read_register_raw(ctx, device_id=1, address=44, code=3)

        # Decode float (little endian word order: [low, high])
        packed = struct.pack(">HH", r1, r0)
        value = struct.unpack(">f", packed)[0]
        assert abs(value - 392.0) < 0.1  # 200C = 392F


# ── Real catalog models ──────────────────────────────────────────────


class TestRealCatalogModels:
    """Integration tests with actual catalog machine definitions."""

    def test_stratto(self) -> None:
        from openroast.catalog.loader import get_model

        model = get_model("carmomaq", "carmomaq-stratto-2.0")
        assert model is not None
        ctx = build_server_context(model, initial_bt=200.0, initial_et=220.0)

        bt = read_register_raw(ctx, device_id=1, address=43, code=3)
        et = read_register_raw(ctx, device_id=1, address=44, code=3)
        assert bt == 2000
        assert et == 2200

    def test_loring_bcd(self) -> None:
        from openroast.catalog.loader import get_model

        model = get_model("loring", "loring-smart-roast")
        assert model is not None
        ctx = build_server_context(model, initial_bt=200.0, initial_et=220.0)

        bt = read_register_raw(ctx, device_id=1, address=768, code=3)
        assert bt == 0x3920  # 200C → 392F → *10 → 3920 → BCD

    def test_diedrich_float(self) -> None:
        from openroast.catalog.loader import get_model

        model = get_model("diedrich", "diedrich-cr")
        assert model is not None
        ctx = build_server_context(model, initial_bt=200.0, initial_et=220.0)

        r0 = read_register_raw(ctx, device_id=1, address=0, code=3)
        r1 = read_register_raw(ctx, device_id=1, address=1, code=3)
        packed = struct.pack(">HH", r1, r0)
        value = struct.unpack(">f", packed)[0]
        assert abs(value - 392.0) < 0.1

    def test_coffed_multi_device(self) -> None:
        from openroast.catalog.loader import get_model

        model = get_model("coffed", "coffed-sr5")
        assert model is not None
        ctx = build_server_context(model, initial_bt=180.0, initial_et=200.0)

        bt = read_register_raw(ctx, device_id=4, address=52, code=3)
        et = read_register_raw(ctx, device_id=3, address=52, code=3)
        assert bt == 1800
        assert et == 2000

    def test_san_franciscan_fc4(self) -> None:
        from openroast.catalog.loader import get_model

        model = get_model("san-franciscan", "sf-eurotherm")
        assert model is not None
        ctx = build_server_context(model, initial_bt=200.0, initial_et=220.0)

        # FC4 input registers, F mode, divisor 1
        bt = read_register_raw(ctx, device_id=1, address=289, code=4)
        et = read_register_raw(ctx, device_id=1, address=290, code=4)
        assert bt == 3920  # 200C → 392F → *10
        assert et == 4280  # 220C → 428F → *10

    def test_stratto_toggle_controls(self) -> None:
        """Stratto 2.0 has 7 controls: 3 sliders with embedded toggles + 4 standalone toggles."""
        from openroast.catalog.loader import get_model

        model = get_model("carmomaq", "carmomaq-stratto-2.0")
        assert model is not None
        assert len(model.controls) == 7

        # Sliders have embedded toggle sub-configs
        air = next(c for c in model.controls if c.channel == "air")
        assert air.toggle is not None
        assert air.toggle.channel == "air_onoff"

        burner = next(c for c in model.controls if c.channel == "burner")
        assert burner.toggle is not None
        assert burner.toggle.channel == "burner_onoff"

        ctx = build_server_context(model, initial_bt=200.0, initial_et=220.0)

        # Slider registers
        assert read_register_raw(ctx, device_id=1, address=45, code=3) == 0  # Burner
        assert read_register_raw(ctx, device_id=1, address=46, code=3) == 0  # Drum
        assert read_register_raw(ctx, device_id=1, address=47, code=3) == 0  # Air

        # Embedded toggle registers (via toggle sub-config)
        assert read_register_raw(ctx, device_id=1, address=55, code=3) == 0  # Burner ON/OFF
        assert read_register_raw(ctx, device_id=1, address=56, code=3) == 0  # Drum ON/OFF
        assert read_register_raw(ctx, device_id=1, address=57, code=3) == 0  # Air ON/OFF

        # Standalone toggle registers
        assert read_register_raw(ctx, device_id=1, address=50, code=3) == 0  # Machine
        assert read_register_raw(ctx, device_id=1, address=52, code=3) == 0  # Ignition
        assert read_register_raw(ctx, device_id=1, address=58, code=3) == 0  # Cooling

        # Extra channel register
        assert read_register_raw(ctx, device_id=1, address=49, code=3) == 0

    def test_stratto_lab(self) -> None:
        """Stratto Lab loads and builds context correctly."""
        from openroast.catalog.loader import get_model

        model = get_model("carmomaq", "carmomaq-stratto-lab")
        assert model is not None
        assert model.sampling_interval_ms == 2000
        ctx = build_server_context(model, initial_bt=200.0, initial_et=220.0)

        bt = read_register_raw(ctx, device_id=1, address=43, code=3)
        et = read_register_raw(ctx, device_id=1, address=44, code=3)
        assert bt == 2000
        assert et == 2200

    def test_caloratto_materatto_legacy(self) -> None:
        """Caloratto/Materatto Legacy with registers 8000/8001."""
        from openroast.catalog.loader import get_model

        model = get_model("carmomaq", "carmomaq-caloratto-materatto-legacy")
        assert model is not None
        ctx = build_server_context(model, initial_bt=200.0, initial_et=220.0)

        bt = read_register_raw(ctx, device_id=0, address=8000, code=3)
        et = read_register_raw(ctx, device_id=0, address=8001, code=3)
        assert bt == 2000
        assert et == 2200

    def test_masteratto_slider3(self) -> None:
        """Masteratto 2.0 has slider 3 (reg 59) visible."""
        from openroast.catalog.loader import get_model

        model = get_model("carmomaq", "carmomaq-masteratto-2.0")
        assert model is not None

        # Find the slider3 control
        slider3 = next(
            (c for c in model.controls if c.channel == "slider3"),
            None,
        )
        assert slider3 is not None
        assert slider3.type == "slider"
        assert slider3.max == 100

        ctx = build_server_context(model, initial_bt=200.0, initial_et=220.0)
        assert read_register_raw(ctx, device_id=1, address=59, code=3) == 0

    def test_coffed_sr5_factor_offset(self) -> None:
        """Coffed SR5 sliders have factor/offset scaling."""
        from openroast.catalog.loader import get_model

        model = get_model("coffed", "coffed-sr5")
        assert model is not None

        air = next(c for c in model.controls if c.channel == "slider1")
        assert air.factor == 21.0
        assert air.offset == 2700.0

        burner = next(c for c in model.controls if c.channel == "slider4")
        assert burner.factor == 100.0
        assert burner.offset == 0.0

    def test_probat_burner_factor(self) -> None:
        """Probat Probatone burner has factor=100 scaling."""
        from openroast.catalog.loader import get_model

        model = get_model("probat", "probat-probatone")
        assert model is not None

        burner = next(c for c in model.controls if c.channel == "burner")
        assert burner.factor == 100.0
        assert burner.offset == 0.0
        assert burner.unit == "%"

    def test_mill_city_factor_offset(self) -> None:
        """Mill City Digital has different factors per slider."""
        from openroast.catalog.loader import get_model

        model = get_model("mill-city", "mill-city-digital")
        assert model is not None

        gas1 = next(c for c in model.controls if c.channel == "gas1")
        assert gas1.factor == 100.0
        assert gas1.unit == "Hz"

        pressure = next(c for c in model.controls if c.channel == "pressure")
        assert pressure.factor == 10.0
        assert pressure.unit == "daPa"

    def test_besca_bsc_auto_controls(self) -> None:
        """Besca BSC Auto has sliders with factor/offset and embedded toggles."""
        from openroast.catalog.loader import get_model

        model = get_model("besca", "besca-bsc-auto")
        assert model is not None
        assert len(model.controls) == 6

        # Sliders with factor/offset
        air = next(c for c in model.controls if c.channel == "air")
        assert air.type == "slider"
        assert air.factor == 2.57
        assert air.offset == 100.0
        assert air.toggle is None  # No ON/OFF for air

        # Drum has embedded toggle with on_command/off_command
        drum = next(c for c in model.controls if c.channel == "drum")
        assert drum.factor == 4.0
        assert drum.offset == 100.0
        assert drum.toggle is not None
        assert drum.toggle.channel == "drum_onoff"
        assert drum.toggle.on_command != ""
        assert drum.toggle.off_command != ""

        # Burner has embedded toggle
        burner = next(c for c in model.controls if c.channel == "burner")
        assert burner.factor == 45.0
        assert burner.toggle is not None
        assert burner.toggle.channel == "burner_onoff"

        # Simple standalone toggles
        cooler = next(c for c in model.controls if c.channel == "cooler_onoff")
        assert cooler.type == "toggle"
        assert cooler.command == "wcoil(1,2005,{})"

        # Button type
        reset = next(c for c in model.controls if c.channel == "reset_burner")
        assert reset.type == "button"
