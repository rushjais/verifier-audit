"""Per-ROM eligibility (PREDICTIONS.md, Amendment 1)."""

import pytest

from vaudit.tasks.chip8.adjudicate import Eligibility, eligibility, population_for

A = bytes([1] + [0] * 2047)
B = bytes([0, 1] + [0] * 2046)


def _frame_with(marks):
    """A frame with an ok or err mark at each given position."""
    from vaudit.tasks.chip8.adjudicate import ERR_MARK, OK_MARK
    from vaudit.tasks.chip8.harness import HEIGHT, WIDTH

    pixels = bytearray(WIDTH * HEIGHT)
    for (x, y), kind in marks.items():
        for dy, row in enumerate(OK_MARK if kind == "ok" else ERR_MARK):
            for dx, on in enumerate(row):
                pixels[(y + dy) * WIDTH + (x + dx)] = on
    return bytes(pixels)


def test_a_self_reporting_rom_adjudicates_itself():
    """Zero failed tests that a peer passes. The ROM decides, not my reference."""
    frames_by_rom = {
        "corax": {
            "good": _frame_with({(10, 10): "ok"}),
            "bad": _frame_with({(10, 10): "err"}),
        }
    }
    assert population_for(frames_by_rom, "corax") == ("good",)


def test_a_rom_with_no_marks_falls_back_to_agreement_on_the_controls():
    consensus = _frame_with({(10, 10): "ok"})
    odd = _frame_with({(20, 20): "ok"})
    frames_by_rom = {
        "ibm_logo": {"a": consensus, "b": consensus, "c": odd},
        "quirks": {"a": A, "b": B, "c": A},  # disagreement here must not decide eligibility
    }
    assert set(population_for(frames_by_rom, "quirks")) == {"a", "b"}
    assert "c" not in population_for(frames_by_rom, "quirks")


def test_disagreeing_on_a_control_excludes_you_from_every_proxy_rom():
    """A control ROM is quirk-free: disagreement there is a broken interpreter, not a choice."""
    consensus = _frame_with({(10, 10): "ok"})
    frames_by_rom = {
        "ibm_logo": {"a": consensus, "b": consensus, "broken": A},
        "chip8_logo": {"a": consensus, "b": consensus, "broken": consensus},
        "quirks": {"a": A, "b": B, "broken": A},
    }
    assert "broken" not in population_for(frames_by_rom, "quirks")


def test_no_majority_on_a_control_excludes_everyone_rather_than_guessing():
    frames_by_rom = {
        "ibm_logo": {"a": A, "b": B},  # a tie is not a consensus
        "quirks": {"a": A, "b": B},
    }
    assert population_for(frames_by_rom, "quirks") == ()


def test_every_record_carries_the_global_failure_count():
    """Amendment 1, obligation 1: the relaxation must not hide anything."""
    frames_by_rom = {
        "corax": {"good": _frame_with({(10, 10): "ok"}), "bad": _frame_with({(10, 10): "err"})},
        "flags": {"good": _frame_with({(20, 20): "ok"}), "bad": _frame_with({(20, 20): "err"})},
        "quirks": {"good": A, "bad": B},
    }
    records = eligibility(frames_by_rom)
    for record in records:
        assert isinstance(record, Eligibility)
        assert record.global_failures == (2 if record.interpreter == "bad" else 0)
    # and the count follows an interpreter onto ROMs it IS eligible for
    quirks_bad = [r for r in records if r.rom == "quirks" and r.interpreter == "bad"]
    assert quirks_bad and quirks_bad[0].global_failures == 2


def test_the_basis_is_recorded_so_proxy_eligibility_is_never_mistaken_for_a_verdict():
    frames_by_rom = {
        "corax": {"a": _frame_with({(10, 10): "ok"})},
        "quirks": {"a": A},
        "ibm_logo": {"a": A},
    }
    basis = {r.rom: r.basis for r in eligibility(frames_by_rom)}
    assert basis["corax"] == "verdict"
    assert basis["quirks"] == "proxy"


@pytest.mark.parametrize("rom", ["corax", "flags"])
def test_self_reporting_roms_are_adjudicated_not_proxied(rom):
    from vaudit.tasks.chip8.adjudicate import SELF_REPORTING

    assert rom in SELF_REPORTING
