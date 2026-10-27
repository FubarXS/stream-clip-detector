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
import io
import math
import struct
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 512
SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128]  # 20, 24, 40 = what Windows asks for at 125 / 150 / 250 % scaling
BOLD_UP_TO = 48  # up to this size the simple, fat glyph is used - the detailed one turns to mush
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
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


def bold_masks():
    """The same clapperboard for 16-48 px: bigger in the tile, fewer and fatter stripes (4 instead of 5), thicker bars
    and a bigger play triangle. Brand rule: the stroke is deliberately thick so the icon holds in 16 px."""
    x0, x1, bt, yf = 70, 442, 66, 230
    hinge = (x0, yf - 4)

    def bar(y0):
        y1 = y0 + bt
        base = Image.new("L", (S, S), 0)
        ImageDraw.Draw(base).rounded_rectangle([x0, y0, x1, y1], radius=10, fill=255)
        cut = Image.new("L", (S, S), 0)
        d = ImageDraw.Draw(cut)
        for x in (163, 256, 349):  # three slanted gaps = four fat stripes
            d.polygon([(x - 13, y0 - 4), (x + 13, y0 - 4), (x - 15, y1 + 4), (x - 41, y1 + 4)], fill=255)
        return ImageChops.subtract(base, cut)

    fixed = bar(yf)
    stick = bar(yf - bt - 12).rotate(11, center=hinge, resample=Image.BICUBIC)
    board = Image.new("L", (S, S), 0)
    ImageDraw.Draw(board).rounded_rectangle([x0, yf + bt + 12, x1, yf + bt + 12 + 160], radius=14, fill=255)
    mid = yf + bt + 12 + 80
    play = Image.new("L", (S, S), 0)
    ImageDraw.Draw(play).polygon([(218, mid - 60), (218, mid + 60), (322, mid)], fill=255)
    play = play.filter(ImageFilter.GaussianBlur(6)).point(lambda p: 255 if p > 128 else 0)  # softly rounded corners
    stripes, board = ImageChops.lighter(fixed, stick), ImageChops.subtract(board, play)
    box = ImageChops.lighter(stripes, board).getbbox()  # centre the whole glyph in the tile
    dy = round(S / 2 - (box[1] + box[3]) / 2)
    return ImageChops.offset(stripes, 0, dy), ImageChops.offset(board, 0, dy)


def build(variant, bold=False):
    v = VARIANTS[variant]
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    tile_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(tile_mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=96, fill=255)
    img.paste(Image.new("RGB", (S, S), rgb(TILE)), (0, 0), tile_mask)
    # glyph for Stream Clip Detector (the kit's sync symbol replaced; tile and colors unchanged)
    stripes, board = bold_masks() if bold else glyph_masks()
    img.paste(hgradient(*v["top"]), (0, 0), stripes)
    img.paste(hgradient(*v["bottom"]), (0, 0), board)
    return img


def frame(detailed, bold, s):
    """One size: the fat glyph up to BOLD_UP_TO px, the detailed one above. LANCZOS overshoots next to a hard edge
    (a bright ring inside the white board at 20-32 px), so the small sizes use HAMMING: just as sharp, no ring."""
    small = s <= BOLD_UP_TO
    return (bold if small else detailed).resize((s, s), Image.HAMMING if small else Image.LANCZOS)


def write_ico(path, frames):
    """An .ico with one PNG picture per size. Pillow would scale ONE big picture to every size, and Windows then
    shows a soft 20/24 px icon at 125/150 % scaling; here every size is made on purpose."""
    pngs = []
    for s, im in sorted(frames.items()):
        b = io.BytesIO()
        im.save(b, "PNG")
        pngs.append((s, b.getvalue()))
    offset, head, body = 6 + 16 * len(pngs), struct.pack("<HHH", 0, 1, len(pngs)), b""
    for s, data in pngs:
        head += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(data), offset + len(body))
        body += data
    with open(path, "wb") as f:
        f.write(head + body)


def main(out, variant="bone"):
    detailed, bold = build(variant), build(variant, bold=True)
    for s in SIZES:
        frame(detailed, bold, s).save(f"{out}/icon{s}.png")
    write_ico(f"{out}/app.ico", {s: frame(detailed, bold, s) for s in ICO_SIZES})
    print(f"ikony ({variant}) ->", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".", sys.argv[2] if len(sys.argv) > 2 else "bone")
