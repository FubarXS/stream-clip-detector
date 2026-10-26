"""
FubarXS brand kit - generátor ikony rozšíření.

Použití:  python3 make_icon.py <výstupní_složka> [bone|heat]

  bone (výchozí) - černá dlaždice, horní půlkruh magma, dolní kostní bílá.
                   Hlavní logo doplňků.
  heat           - černá dlaždice, horní půlkruh žlutá→oranž, dolní červená
                   ("tón v tónu"). Alternativa, v malých velikostech slabší.

Pro nový doplněk vyměň jen funkci draw_glyph(): dlaždice, přechody a barvy
zůstávají stejné.
"""
import math
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 512
SIZES = [16, 32, 48, 96, 128]
TILE = "#0a0706"

VARIANTS = {
    "heat": {"top": ("#ffc233", "#ff5a0a"), "bottom": ("#c71d06", "#ee3a08")},
    "bone": {"top": ("#e32805", "#fe5505"), "bottom": ("#f4ede7", "#f4ede7")},
}
# tvar symbolu (zesílený kvůli čitelnosti v 16 px)
RADIUS, THICK, ARROW = 160, 54, 72


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hgradient(c1, c2):
    """Vodorovný přechod; teče ve směru šipky."""
    g = Image.new("RGB", (S, S))
    px = g.load()
    a, b = rgb(c1), rgb(c2)
    for x in range(S):
        t = x / (S - 1)
        col = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
        for y in range(S):
            px[x, y] = col
    return g


def arc_mask(start, end):
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    cx = cy = S / 2
    d.arc([cx - RADIUS, cy - RADIUS, cx + RADIUS, cy + RADIUS], start=start, end=end, fill=255, width=THICK)
    ang = math.radians(end)
    tip = (cx + RADIUS * math.cos(ang), cy + RADIUS * math.sin(ang))
    tan = ang + math.pi / 2
    back = (tip[0] - ARROW * 1.15 * math.cos(ang), tip[1] - ARROW * 1.15 * math.sin(ang))
    p1 = (tip[0] + ARROW * .55 * math.cos(tan) - ARROW * .15 * math.cos(ang),
          tip[1] + ARROW * .55 * math.sin(tan) - ARROW * .15 * math.sin(ang))
    p2 = (tip[0] - ARROW * .55 * math.cos(tan) - ARROW * .15 * math.cos(ang),
          tip[1] - ARROW * .55 * math.sin(tan) - ARROW * .15 * math.sin(ang))
    d.polygon([p1, back, p2], fill=255)
    return m


def glyph_masks():
    """Clapperboard: an open striped clapper stick over a striped bar (magma), the board below in bone white with a
    play triangle cut out of it. Returns (stripes_mask, board_mask) - the first gets the top gradient, the second the bottom."""
    dy = 34  # moves the whole glyph down a little so it sits in the middle of the tile
    hinge = (104, 206 + dy)

    def bar(y0, y1):  # a striped bar: rounded base minus slanted dark stripes
        base = Image.new("L", (S, S), 0)
        ImageDraw.Draw(base).rounded_rectangle([104, y0, 408, y1], radius=8, fill=255)
        cut = Image.new("L", (S, S), 0)
        d = ImageDraw.Draw(cut)
        for x in range(136, 420, 76):  # slanted gaps between the stripes
            d.polygon([(x, y0 - 4), (x + 18, y0 - 4), (x - 2, y1 + 4), (x - 20, y1 + 4)], fill=255)
        return ImageChops.subtract(base, cut)

    fixed = bar(206 + dy, 252 + dy)
    stick = bar(150 + dy, 196 + dy).rotate(11, center=hinge, resample=Image.BICUBIC)  # opened, hinged on the left
    board = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(board)
    d.rounded_rectangle([104, 262 + dy, 408, 404 + dy], radius=12, fill=255)
    play = Image.new("L", (S, S), 0)  # the play triangle, punched out of the board
    ImageDraw.Draw(play).polygon([(232, 290 + dy), (232, 378 + dy), (312, 334 + dy)], fill=255)
    play = play.filter(ImageFilter.GaussianBlur(5)).point(lambda p: 255 if p > 128 else 0)
    return ImageChops.lighter(fixed, stick), ImageChops.subtract(board, play)


def build(variant):
    v = VARIANTS[variant]
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    tile_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(tile_mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=96, fill=255)
    img.paste(Image.new("RGB", (S, S), rgb(TILE)), (0, 0), tile_mask)
    # glyph for Stream Clip Detector (the kit's sync symbol replaced; tile and colors unchanged)
    stripes, board = glyph_masks()
    img.paste(hgradient(*v["top"]), (0, 0), stripes)
    img.paste(hgradient(*v["bottom"]), (0, 0), board)
    return img


def main(out, variant="bone"):
    img = build(variant)
    for s in SIZES:
        img.resize((s, s), Image.LANCZOS).save(f"{out}/icon{s}.png")
    img.save(f"{out}/app.ico", sizes=[(16, 16), (32, 32), (48, 48), (128, 128), (256, 256)])
    print(f"ikony ({variant}) ->", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".", sys.argv[2] if len(sys.argv) > 2 else "bone")
