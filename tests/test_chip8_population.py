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
