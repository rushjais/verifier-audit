"""M1c — a CHIP-8 differential-grading study. See PREDICTIONS.md, registered before any metric."""

from .cheats import BlankScreen, FrozenFirstFrame, InvertedPalette, OneFrameLate, all_cheats
from .core import CHIP48, COSMAC_VIP, HEIGHT, WIDTH, Chip8, Quirks
from .harness import BLANK, Frame, Interpreter, NativeInterpreter, lit, render

__all__ = [
    "BLANK",
    "CHIP48",
    "COSMAC_VIP",
    "HEIGHT",
    "WIDTH",
    "BlankScreen",
    "Chip8",
    "Frame",
    "FrozenFirstFrame",
    "Interpreter",
    "InvertedPalette",
    "NativeInterpreter",
    "OneFrameLate",
    "Quirks",
    "all_cheats",
    "lit",
    "render",
]
