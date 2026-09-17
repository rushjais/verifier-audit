"""Per-ROM eligibility (PREDICTIONS.md, Amendment 1)."""

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


def test_a_self_verifying_rom_adjudicates_itself():
    """Zero failed tests that a peer passes. The ROM decides, not my reference."""
    frames_by_rom = {
        "corax": {
            "good": _frame_with({(10, 10): "ok"}),
            "bad": _frame_with({(10, 10): "err"}),
        }
    }
    assert population_for(frames_by_rom, "corax") == ("good",)


def test_a_non_verifying_rom_requires_a_fully_clean_implementation():
    """Amendment 2 rule 2. Amendment 1 accepted agreement on the controls as a proxy here; it was
    withdrawn because it granted the largest population where the evidence was thinnest."""
    frames_by_rom = {
        "corax": {"clean": _frame_with({(10, 10): "ok"}), "buggy": _frame_with({(10, 10): "err"})},
        "ibm_logo": {"clean": A, "buggy": A},  # agreeing on the control is no longer enough
    }
    assert population_for(frames_by_rom, "ibm_logo") == ("clean",)


def test_a_timer_dependent_rom_admits_nobody():
    """Amendment 2 rule 3: timer semantics are not normalised across this population."""
    frames_by_rom = {
        "corax": {"clean": _frame_with({(10, 10): "ok"})},
        "quirks": {"clean": A},
    }
    assert population_for(frames_by_rom, "quirks") == ()
    basis = [e.basis for e in eligibility(frames_by_rom) if e.rom == "quirks"]
    assert basis == ["excluded: timer-dependent"]


def test_the_quirks_rom_is_marked_timer_dependent_and_out_of_the_study():
    """The confirmation Amendment 2 required before metrics: it does not qualify."""
    from vaudit.tasks.chip8.roms import BY_KEY, usable_roms

    quirks = BY_KEY["quirks"]
    assert quirks.timer_dependent
    assert not quirks.usable
    assert quirks not in usable_roms()


def test_every_record_carries_the_global_failure_count():
    """Amendment 1, obligation 1: the relaxation must not hide anything."""
    frames_by_rom = {
        "corax": {"good": _frame_with({(10, 10): "ok"}), "bad": _frame_with({(10, 10): "err"})},
        "flags": {"good": _frame_with({(20, 20): "ok"}), "bad": _frame_with({(20, 20): "err"})},
        "ibm_logo": {"good": A, "bad": B},
    }
    records = eligibility(frames_by_rom)
    for record in records:
        assert isinstance(record, Eligibility)
        assert record.global_failures == (2 if record.interpreter == "bad" else 0)


def test_the_basis_is_recorded_so_eligibility_is_never_mistaken_for_a_verdict():
    frames_by_rom = {
        "corax": {"a": _frame_with({(10, 10): "ok"})},
        "ibm_logo": {"a": A},
        "quirks": {"a": A},
    }
    basis = {r.rom: r.basis for r in eligibility(frames_by_rom)}
    assert basis["corax"] == "verdict"
    assert basis["ibm_logo"] == "fully-clean"
    assert basis["quirks"] == "excluded: timer-dependent"
