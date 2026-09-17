"""The population: third-party interpreters, their manifest, and their adapters.

Manifest tests always run. Adapter tests need the population fetched
(`python -m vaudit.tasks.chip8.fetch`) and skip cleanly when it is not — a suite that silently
passed without the population would be claiming a study that never ran.
"""

import pytest

from vaudit.tasks.chip8 import COSMAC_VIP, NativeInterpreter, lit, render
from vaudit.tasks.chip8.adapters import HeadlessScreen, build
from vaudit.tasks.chip8.fetch import is_fetched, path_for
from vaudit.tasks.chip8.manifest import POPULATION, Entry, report, usable_population

# Portable: FX29 asks the interpreter for ITS OWN font address. Hardcoding one would only test
# implementations that happen to share my convention — craigthomas puts the font at 0x000, I put
# it at 0x050, and both are defensible.
DRAW_ZERO = bytes([0x60, 0x00, 0xF0, 0x29, 0x61, 0x00, 0x62, 0x00, 0xD1, 0x25, 0x12, 0x0A])


def test_every_listed_entry_is_permissively_licensed_and_pinned():
    for entry in POPULATION:
        assert entry.permissive, f"{entry.key}: {entry.licence} is not on the permissive list"
        assert entry.pinned, f"{entry.key}: commit not pinned"


def test_an_unpinned_or_copyleft_entry_can_never_enter_the_population():
    assert not Entry("x", "a/b", "HEAD", "MIT", "adapter").usable
    assert not Entry("x", "a/b", "abc123", "GPL-3.0", "adapter").usable
    assert Entry("x", "a/b", "abc123", "MIT", "adapter").usable


def test_the_manifest_reports_blockers_rather_than_hiding_them():
    text = report()
    assert "usable of" in text
    assert all(e.repo in text and e.licence in text for e in POPULATION)


def test_every_entry_names_an_adapter_that_exists():
    from vaudit.tasks.chip8.adapters import ADAPTERS

    for entry in POPULATION:
        assert entry.adapter in ADAPTERS, f"{entry.key} names a missing adapter"


def test_the_headless_screen_satisfies_the_api_interpreters_draw_through():
    screen = HeadlessScreen()
    assert (screen.get_width(), screen.get_height()) == (64, 32)
    screen.draw_pixel(3, 4, True)
    assert screen.get_pixel(3, 4) == 1
    screen.draw_pixel(3, 4, False)
    assert screen.get_pixel(3, 4) == 0
    screen.draw_pixel(70, 40, True)  # out of range must wrap, never raise
    screen.clear_screen()
    assert sum(screen.pixels) == 0


# --- adapter tests: need the population on disk ------------------------------------------------

_fetched = [e for e in usable_population() if is_fetched(e)]
needs_population = pytest.mark.skipif(
    not _fetched, reason="population not fetched: python -m vaudit.tasks.chip8.fetch"
)


@needs_population
@pytest.mark.parametrize("entry", _fetched, ids=lambda e: e.key)
def test_a_third_party_interpreter_draws_the_same_glyph_as_the_reference(entry):
    """The population and the reference must agree on something before disagreement means
    anything. If a third-party interpreter cannot draw a font glyph, the adapter is wrong and
    any later 'difference' would be my bug wearing their name."""
    theirs = build(entry, path_for(entry)).frames(DRAW_ZERO, 4)[-1]
    mine = NativeInterpreter("reference", COSMAC_VIP).frames(DRAW_ZERO, 4)[-1]

    assert lit(theirs) == 14, f"{entry.key} did not draw the glyph:\n{render(theirs)}"
    assert theirs == mine, f"{entry.key} disagrees with the reference on a quirk-free ROM"


@needs_population
@pytest.mark.parametrize("entry", _fetched, ids=lambda e: e.key)
def test_a_third_party_interpreter_is_deterministic_across_runs(entry):
    first = build(entry, path_for(entry)).frames(DRAW_ZERO, 3)
    second = build(entry, path_for(entry)).frames(DRAW_ZERO, 3)
    assert first == second


@needs_population
def test_the_population_is_reported_honestly_not_padded():
    """n is whatever it is. Quirk profiles of my own reference are NOT population members."""
    assert len(_fetched) == len(usable_population())
    assert all(not e.key.startswith("cheat") for e in _fetched)


@needs_population
def test_adapters_leave_no_modules_or_path_behind():
    """Several of these projects ship a top-level package called `chip8`."""
    import sys

    before_path = list(sys.path)
    for entry in _fetched:
        build(entry, path_for(entry)).frames(DRAW_ZERO, 1)
        leaked = [m for m in ("chip8", "emu", "ui") if m in sys.modules]
        assert not leaked, f"{entry.key} left {leaked} in sys.modules"
    assert sys.path == before_path


@needs_population
@pytest.mark.skipif(len(_fetched) < 2, reason="needs two interpreters to interleave")
def test_running_one_interpreter_cannot_change_another_s_output():
    """The failure this guards against is silent and total: if importing one project hands
    another its code, two implementations agree perfectly because they ARE the same code —
    honest_pass reads 1.00 and the study concludes the opposite of the truth."""
    first, second = _fetched[0], _fetched[1]

    alone = build(first, path_for(first)).frames(DRAW_ZERO, 3)
    build(second, path_for(second)).frames(DRAW_ZERO, 3)
    after = build(first, path_for(first)).frames(DRAW_ZERO, 3)

    assert alone == after, f"{second.key} changed what {first.key} produced"


@needs_population
def test_the_key_stub_models_pygames_actual_contract():
    """get_pressed() returns an indexable sequence, not a dict. Returning {} raised KeyError the
    moment an interpreter executed EX9E, which read as "this implementation crashes" and nearly
    got a working one excluded from the population as broken."""
    from vaudit.tasks.chip8.adapters import _stub_pygame

    _stub_pygame()
    import pygame

    pressed = pygame.key.get_pressed()
    assert pressed[0] is False
    assert pressed[pygame.K_x] is False
    assert len({getattr(pygame, n) for n in ("K_x", "K_1", "K_2", "K_q")}) == 4, (
        "key constants must be distinct or sixteen keys collapse into one"
    )


@needs_population
def test_no_test_rom_uses_cxnn_so_rng_cannot_affect_any_comparison():
    """CXNN is CHIP-8's only nondeterminism. If a ROM used it, every interpreter would need an
    identically seeded PRNG or the comparison would be measuring luck. None of them do, and this
    test fails loudly if that ever changes."""
    from vaudit.tasks.chip8.roms import ROM_DIR, usable_roms

    for rom in usable_roms():
        source = ROM_DIR / "src" / "tests" / rom.filename.replace(".ch8", ".8o")
        if source.exists():
            assert "random" not in source.read_text().lower(), f"{rom.key} now uses CXNN"


@needs_population
def test_the_correctness_gate_decides_eligibility_by_the_roms_verdict_not_by_agreement():
    """Differing from my reference is not being wrong; the ROM's own marks decide."""
    from vaudit.tasks.chip8.adjudicate import failures_against_peers
    from vaudit.tasks.chip8.roms import BY_KEY

    interps = {"reference": NativeInterpreter("r", COSMAC_VIP)}
    interps.update({e.key: build(e, path_for(e)) for e in _fetched})

    failures = {}
    for rom_key in ("corax", "flags"):
        rom = BY_KEY[rom_key]
        frames = {n: i.frames(rom.load(), 90)[-1] for n, i in interps.items()}
        for name, count in failures_against_peers(frames).items():
            failures[name] = failures.get(name, 0) + count

    # The reference must itself be clean, or the study is built on a broken yardstick.
    assert failures["reference"] == 0, f"the reference fails the suite: {failures}"
    # And the gate must actually discriminate, or it is not a gate.
    assert any(v > 0 for k, v in failures.items() if k != "reference"), (
        "no interpreter failed anything; the gate is not doing its job"
    )
