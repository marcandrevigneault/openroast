"""Unit tests for the catalog loader."""

from __future__ import annotations

from openroast.catalog.loader import get_manufacturer, get_manufacturers, get_model, load_catalog


class TestLoadCatalog:
    def test_loads_successfully(self) -> None:
        catalog = load_catalog()
        assert catalog.version == 1
        assert len(catalog.manufacturers) > 0

    def test_has_known_manufacturers(self) -> None:
        catalog = load_catalog()
        ids = {m.id for m in catalog.manufacturers}
        assert "carmomaq" in ids
        assert "giesen" in ids
        assert "loring" in ids

    def test_all_models_have_valid_protocol(self) -> None:
        catalog = load_catalog()
        valid_protocols = {"modbus_rtu", "modbus_tcp", "serial", "s7"}
        for mfr in catalog.manufacturers:
            for model in mfr.models:
                assert model.protocol in valid_protocols, (
                    f"{mfr.id}/{model.id} has invalid protocol: {model.protocol}"
                )

    def test_all_models_have_connection(self) -> None:
        catalog = load_catalog()
        for mfr in catalog.manufacturers:
            for model in mfr.models:
                assert model.connection is not None, f"{mfr.id}/{model.id} missing connection"


class TestGetManufacturers:
    def test_returns_list(self) -> None:
        mfrs = get_manufacturers()
        assert isinstance(mfrs, list)
        assert len(mfrs) > 0

    def test_each_has_id_and_name(self) -> None:
        for mfr in get_manufacturers():
            assert mfr.id != ""
            assert mfr.name != ""


class TestGetManufacturer:
    def test_existing(self) -> None:
        mfr = get_manufacturer("carmomaq")
        assert mfr is not None
        assert mfr.name == "Carmomaq"

    def test_nonexistent(self) -> None:
        assert get_manufacturer("nonexistent") is None


class TestGetModel:
    def test_existing(self) -> None:
        model = get_model("carmomaq", "carmomaq-stratto-2.0")
        assert model is not None
        assert model.name == "Stratto 2.0"
        assert model.protocol == "modbus_tcp"

    def test_nonexistent_manufacturer(self) -> None:
        assert get_model("nonexistent", "any") is None

    def test_nonexistent_model(self) -> None:
        assert get_model("carmomaq", "nonexistent") is None

    def test_giesen_s7(self) -> None:
        model = get_model("giesen", "giesen-wxa")
        assert model is not None
        assert model.protocol == "s7"
        assert model.connection.type == "s7"
        assert model.et is not None
        assert model.et.s7 is not None

    def test_hottop_serial(self) -> None:
        model = get_model("hottop", "hottop-2k-plus")
        assert model is not None
        assert model.protocol == "serial"
        assert model.connection.type == "serial"
