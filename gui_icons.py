"""Small line icons for the clips window (trash, edit, copy, list, gallery), drawn with Pillow at run time in the brand
text color - no extra files to ship. Without Pillow every icon button falls back to a short translated word."""
import customtkinter as ctk

from brand import TEXT, BTN, BTN_H, SEL, SEL_H, BORDER, RADIUS_MD
from gui_widgets import FitButton, Tip

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None

K = 8  # drawing scale: icons are drawn on a 24 x 24 grid at 8x and shrunk (smooth edges)
_cache = {}


def _lines(d, pts, c, w):
    d.line([(x * K, y * K) for x, y in pts], fill=c, width=w, joint="curve")
    for x, y in (pts[0], pts[-1]):  # round caps
        d.ellipse([x * K - w / 2, y * K - w / 2, x * K + w / 2, y * K + w / 2], fill=c)


def _box(d, r, c, w, radius=2.0, fill=None):
    d.rounded_rectangle([v * K for v in r], radius=radius * K, outline=c, width=w, fill=fill)


def _trash(d, c, w):
    _lines(d, [(4, 6.5), (20, 6.5)], c, w)
    _lines(d, [(9, 6.5), (9, 4), (15, 4), (15, 6.5)], c, w)
    d.polygon([(x * K, y * K) for x, y in ((6, 9), (18, 9), (17, 20.5), (7, 20.5))], outline=c, width=w)
    _lines(d, [(10.2, 11.5), (10.4, 17.5)], c, w)
    _lines(d, [(13.8, 11.5), (13.6, 17.5)], c, w)


def _edit(d, c, w):  # a notepad with a pencil
    _box(d, (3, 3.5, 16, 21), c, w, 2.2)
    _lines(d, [(6.5, 8), (12.5, 8)], c, w)
    _lines(d, [(6.5, 12), (10.5, 12)], c, w)
    pencil = [(21.2, 8.2), (22.8, 9.8), (14.2, 18.4), (11.4, 19.4), (12.4, 16.6)]
    d.polygon([(x * K, y * K) for x, y in ((20.3, 6.3), (24.1, 10.1), (14.6, 19.6), (10.2, 20.8), (11.4, 16.4))],
              fill=(0, 0, 0, 0))  # clear the notepad border around the pencil
    d.polygon([(x * K, y * K) for x, y in pencil], outline=c, width=w)
    _lines(d, [(19.4, 9.4), (21.2, 11.2)], c, w)


def _copy(d, c, w):  # two sheets of paper
    _box(d, (9, 3, 20.5, 15.5), c, w, 2.2)
    _box(d, (3.5, 8.5, 15, 21), c, w, 2.2, fill=(0, 0, 0, 0))


# The two view icons are laid out in units of 4/3 of the 24 grid = exactly 1 pixel at the usual 18 px size, so at 100 %
# their edges fall on whole pixels (crisp) and the ink is centred: list 3..15 px, grid 3..15 px of 18.
P = 24 / 18


def _list(d, c, w):  # bullet list: a 3 px dot and a 2 px line, three times (rows at 4, 9 and 14 px)
    for y in (4, 9, 14):
        d.ellipse([3 * P * K, (y - 1.5) * P * K, 6 * P * K, (y + 1.5) * P * K], fill=c)
        d.rectangle([8 * P * K, (y - 1) * P * K, 15 * P * K - 1, (y + 1) * P * K - 1], fill=c)


def _grid(d, c, w):  # four rounded squares, 5 px each with a 2 px gap
    for x, y in ((3, 3), (10, 3), (3, 10), (10, 10)):
        d.rounded_rectangle([x * P * K, y * P * K, (x + 5) * P * K - 1, (y + 5) * P * K - 1], radius=1.3 * P * K, fill=c)


DRAW = {"trash": _trash, "edit": _edit, "copy": _copy, "list": _list, "grid": _grid}


def centered(im):
    """The same picture with its ink (not its drawing grid) exactly in the middle of the canvas."""
    box = im.getbbox()
    if not box:
        return im
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(im.crop(box), ((im.width - (box[2] - box[0])) // 2, (im.height - (box[3] - box[1])) // 2))
    return out


def icon(name, size=18, color=TEXT):
    """CTkImage of a named icon, or None without Pillow. The big drawing goes to CTk as it is, so it is shrunk only
    once, straight to the real pixel size of the screen (an extra step in between made the edges soft)."""
    if Image is None:
        return None
    key = (name, size, color)
    if key not in _cache:
        im = Image.new("RGBA", (24 * K, 24 * K), (0, 0, 0, 0))
        DRAW[name](ImageDraw.Draw(im), color, round(1.9 * K))
        _cache[key] = ctk.CTkImage(centered(im), size=(size, size))
    return _cache[key]


def icon_button(parent, name, tip, command, T, width=34, height=28):
    """Square-ish button with an icon and a hover tooltip (the English key of the tooltip is translated live).
    Without Pillow it shows the translated word instead, and still grows to fit it."""
    img = icon(name)
    b = FitButton(parent, text="" if img else T(tip), image=img, width=width, height=height, command=command,
                  fg_color=BTN, hover_color=BTN_H, border_width=1, border_color=BORDER, text_color=TEXT,
                  corner_radius=RADIUS_MD)
    Tip(b, tip)
    return b


class ViewToggle(ctk.CTkFrame):
    """Two icon buttons - list and gallery - the chosen one is filled like a selected tab."""
    MODES = (("list", "list", "List"), ("gallery", "grid", "Gallery"))

    def __init__(self, master, command):
        super().__init__(master, fg_color="transparent")
        self.command, self.btns, self.icons = command, {}, icon("list") is not None
        for i, (mode, ico, tip) in enumerate(self.MODES):
            b = FitButton(self, text="", image=icon(ico), width=44, height=30, corner_radius=RADIUS_MD,
                          command=lambda m=mode: self.command(m))
            b.pack(side="left", padx=(0 if i == 0 else 4, 0))
            Tip(b, tip)
            self.btns[mode] = b

    def set(self, mode):
        for m, b in self.btns.items():
            on = m == mode
            b.configure(fg_color=SEL if on else BTN, hover_color=SEL_H if on else BTN_H)

    def relabel(self, T):
        """Only matters without Pillow: the buttons then show the words 'List' / 'Gallery'."""
        if not self.icons:
            for mode, _, tip in self.MODES:
                self.btns[mode].configure(text=T(tip))
