"""OG card, 1200x630. Frames come from quirk_roms.py + harness.py so the card cannot drift.

Not part of the package or the test suite; Pillow is not a project dependency. Run it with:

    uv run --with pillow python tools/make_og_card.py

Writes docs/img/og-card.png, which the write-up references as its og:image.
"""

from PIL import Image, ImageDraw, ImageFont

from vaudit.tasks.chip8.core import CHIP48, COSMAC_VIP
from vaudit.tasks.chip8.harness import HEIGHT, WIDTH, NativeInterpreter
from vaudit.tasks.chip8.quirk_roms import SHIFT_ROM
from vaudit.tasks.chip8.strategies import STRATEGIES

W, H = 1200, 630
GROUND, LIT, SCREEN, EDGE = (
    (0x12, 0x15, 0x1C),
    (0xF0, 0xA8, 0x30),
    (0x09, 0x0B, 0x0F),
    (0x39, 0x42, 0x55),
)
INK, MUTED, FAIL, REF = (
    (0xE7, 0xE3, 0xDA),
    (0x9A, 0xA3, 0xB4),
    (0xE0, 0x57, 0x4F),
    (0x6F, 0xB3, 0xA8),
)

ref = NativeInterpreter("r", COSMAC_VIP).frames(SHIFT_ROM, 30)[-1]
div = NativeInterpreter("d", CHIP48).frames(SHIFT_ROM, 30)[-1]
blank = bytes(len(ref))
ssim = STRATEGIES["SSIM"]
panels = [
    (ref, "REFERENCE", ssim(ref, ref), REF),
    (div, "ALSO CORRECT", ssim(ref, div), FAIL),
    (blank, "DRAWS NOTHING", ssim(ref, blank), LIT),
]
print("scores from source:", [f"{p[2]:.4f}" for p in panels])

img = Image.new("RGB", (W, H), GROUND)
d = ImageDraw.Draw(img)
serif = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia Bold.ttf", 46)
mono = ImageFont.truetype("/System/Library/Menlo.ttc", 19)
monob = ImageFont.truetype("/System/Library/Menlo.ttc", 36)

# The headline and its scope, because the short form overclaims on its own: the failure is real
# and it is confined to a regime the page then derives.
HEAD = "A correct emulator scored below a blank screen."
QUAL = "Here is exactly when."
while d.textlength(HEAD, font=serif) > W - 120 and serif.size > 28:
    serif = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf", serif.size - 2
    )
qual_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", serif.size - 10)
d.text(((W - d.textlength(HEAD, font=serif)) / 2, 78), HEAD, font=serif, fill=INK)
d.text(((W - d.textlength(QUAL, font=qual_font)) / 2, 142), QUAL, font=qual_font, fill=MUTED)

S, PW, PH, GAP = 5, WIDTH * 5, HEIGHT * 5, 40
x0 = (W - (3 * PW + 2 * GAP)) // 2
sy = 286
for i, (frame, cap, score, col) in enumerate(panels):
    px = x0 + i * (PW + GAP)
    d.rectangle([px - 1, sy - 1, px + PW, sy + PH], fill=SCREEN, outline=EDGE)
    for y in range(HEIGHT):
        row = frame[y * WIDTH : (y + 1) * WIDTH]
        x = 0
        while x < WIDTH:
            if row[x]:
                run = 1
                while x + run < WIDTH and row[x + run]:
                    run += 1
                d.rectangle(
                    [px + x * S, sy + y * S, px + (x + run) * S - 1, sy + (y + 1) * S - 1], fill=LIT
                )
                x += run
            else:
                x += 1
    d.text((px, sy - 34), cap, font=mono, fill=MUTED)
    txt = f"{score:.4f}"
    d.text((px + (PW - d.textlength(txt, font=monob)) / 2, sy + PH + 26), txt, font=monob, fill=col)

out = "docs/img/og-card.png"
img.save(out, optimize=True)
print("wrote", out, img.size)
