"""Unit tests for roast event detection algorithms."""

from __future__ import annotations

from openroast.core.detection import check_bt_break, find_turning_point


class TestCheckBtBreak:
    """Tests for the BT break detection algorithm."""

    def test_requires_exactly_6_samples(self) -> None:
        assert check_bt_break([1.0, 2.0, 3.0]) is False
        assert check_bt_break([]) is False
        assert check_bt_break([1.0] * 7) is False

    def test_no_break_flat_line(self) -> None:
        """Constant temperature has no break."""
        assert check_bt_break([200.0] * 6) is False

    def test_no_break_steady_rise(self) -> None:
        """Monotonically rising temperature has no break."""
        assert check_bt_break([150.0, 152.0, 154.0, 156.0, 158.0, 160.0]) is False

    def test_no_break_steady_fall(self) -> None:
        """Monotonically falling temperature has no break."""
        assert check_bt_break([200.0, 198.0, 196.0, 194.0, 192.0, 190.0]) is False

    def test_detects_fall_to_rise(self) -> None:
        """CHARGE break: temperature transitions from falling to rising."""
        # Falling: 200 → 190, then rising: 190 → 200
        samples = [200.0, 195.0, 190.0, 190.0, 195.0, 200.0]
        assert check_bt_break(samples) is True

    def test_detects_rise_to_fall(self) -> None:
        """DROP break: temperature transitions from rising to falling."""
        # Rising: 200 → 210, then falling: 210 → 200
        samples = [200.0, 205.0, 210.0, 210.0, 205.0, 200.0]
        assert check_bt_break(samples) is True

    def test_offset_raises_threshold(self) -> None:
        """Higher offset requires stronger gradient reversal."""
        # Mild reversal that passes with offset=0
        samples = [200.0, 198.0, 196.0, 196.0, 198.0, 200.0]
        assert check_bt_break(samples, d=0.5) is True
        # Same samples fail with high offset
        assert check_bt_break(samples, d=0.5, offset=5.0) is False

    def test_dpre_dpost_diff_filters_weak_reversals(self) -> None:
        """dpre_dpost_diff filters out weak gradient changes."""
        # Clear reversal with d=0
        samples = [200.0, 197.0, 194.0, 194.0, 197.0, 200.0]
        assert check_bt_break(samples, d=0) is True
        # Same samples filtered by requiring large gradient difference
        assert check_bt_break(samples, d=0, dpre_dpost_diff=10.0) is False


class TestFindTurningPoint:
    """Tests for turning point detection."""

    def test_finds_minimum_after_charge(self) -> None:
        """TP is the minimum BT value after CHARGE index."""
        bt = [210.0, 200.0, 190.0, 180.0, 170.0, 165.0, 168.0, 175.0, 185.0]
        #                                  charge^      tp^
        assert find_turning_point(bt, charge_index=3) == 5

    def test_returns_negative_for_invalid_charge(self) -> None:
        assert find_turning_point([200.0, 190.0], charge_index=-1) == -1
        assert find_turning_point([200.0, 190.0], charge_index=5) == -1

    def test_returns_negative_for_empty(self) -> None:
        assert find_turning_point([], charge_index=0) == -1

    def test_charge_at_start(self) -> None:
        """CHARGE at index 0 searches the entire array."""
        bt = [210.0, 195.0, 180.0, 170.0, 175.0, 185.0]
        assert find_turning_point(bt, charge_index=0) == 3

    def test_tp_at_charge_when_only_rising(self) -> None:
        """If BT only rises after charge, TP is at charge index."""
        bt = [210.0, 200.0, 190.0, 195.0, 200.0, 210.0]
        assert find_turning_point(bt, charge_index=2) == 2
