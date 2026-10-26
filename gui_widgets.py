"""Reusable widgets: hover tooltip and form-building helpers (cards, labeled rows, sliders...)."""
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

from brand import ACCENT, TEXT, MUTED, BORDER_H, CARD, ENTRY, BTN2, OPTION, SLIDER
from gui_config import DEFAULTS, WHY
from gui_strings import tr


class Tip:
    """Small hover tooltip (translated live through Tip.lang)."""
    lang = "en"

    def __init__(self, widget, text):
        self.w, self.text, self.tw = widget, text, None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        self.tw = tk.Toplevel(self.w)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{self.w.winfo_rootx() + 16}+{self.w.winfo_rooty() + 22}")
        tk.Label(self.tw, text=tr(self.text, Tip.lang), justify="left", wraplength=320, bg="#070504", fg=TEXT,
                 highlightbackground=BORDER_H, highlightthickness=1, bd=0, padx=10, pady=8).pack()

    def hide(self, _=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None


class FitButton(ctk.CTkButton):
    """A button that never clips its text: 'width' is only the minimum, the button grows with its text
    (longer words in another language, or the text changing later, e.g. 'Copied')."""
    PAD = 22

    def __init__(self, master, text="", width=140, **kw):
        self._min_w = width
        super().__init__(master, text=text, width=width, **kw)
        self._fit()

    def configure(self, require_redraw=False, **kw):
        super().configure(require_redraw=require_redraw, **kw)
        if "text" in kw:
            self._fit()

    def _fit(self):
        text = self.cget("text")
        if not text:  # icon only: back to the plain width
            if self.cget("width") != self._min_w:
                super().configure(width=self._min_w)
            return
        font = self.cget("font")
        font = font if isinstance(font, tkfont.Font) else tkfont.Font(font=font)
        img = self.cget("image")
        extra = (img.cget("size")[0] + 6) if img else 0
        need = max(self._min_w, font.measure(text) + self.PAD + extra)
        if need != self.cget("width"):
            super().configure(width=need)


class Blocks:
    """Mixin with the form-building helpers."""

    def info(self, parent, tip):
        l = ctk.CTkLabel(parent, text="ⓘ", text_color=MUTED, cursor="hand2", font=ctk.CTkFont(size=14))
        Tip(l, tip)
        l.bind("<Enter>", lambda e: l.configure(text_color=ACCENT))
        l.bind("<Leave>", lambda e: l.configure(text_color=MUTED))
        return l

    def card(self, parent, title, tip=None):
        f = ctk.CTkFrame(parent, **CARD)
        f.pack(fill="x", pady=(0, 12))
        h = ctk.CTkFrame(f, fg_color="transparent")
        h.pack(fill="x", padx=16, pady=(12, 2))
        ctk.CTkLabel(h, text=title, text_color=MUTED, font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        if tip:
            self.info(h, tip).pack(side="left", padx=6)
        return f

    def lab(self, parent, text, tip=None):
        r = ctk.CTkFrame(parent, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(8, 0))
        ctk.CTkLabel(r, text=text, text_color=TEXT).pack(side="left")
        if tip:
            self.info(r, tip).pack(side="left", padx=6)
        return r

    def entry(self, parent, text, key, browse=None, tip=None, clear=False):
        """Labeled text field. The field (and its Browse / clear buttons) is kept in self.fields[key] so it can be disabled."""
        self.lab(parent, text, tip)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(2, 4))
        e = ctk.CTkEntry(row, textvariable=self.vars[key], **ENTRY)
        e.pack(side="left", fill="x", expand=True)
        btns = []
        if clear:
            x = FitButton(row, text="✕", width=32, height=32, command=lambda: self.vars[key].set(""), **BTN2)
            x.pack(side="left", padx=(8, 0))
            Tip(x, "Clear")
            btns.append(x)
        if browse:
            b = FitButton(row, text="Browse", width=70, height=32, command=browse, **BTN2)
            b.pack(side="left", padx=(8, 0))
            btns.append(b)
        self.fields = getattr(self, "fields", {})
        self.fields[key] = (e, btns)

    def slider(self, parent, text, key, lo, hi, step, tip, unit="", dec=0):
        var, dflt = self.vars[key], float(DEFAULTS[key])
        full = tip + f"\n\nDefault: {dflt:.{dec}f}{unit}" + (f"\n\n{WHY[key]}" if key in WHY else "")
        r = self.lab(parent, text, full)
        val = ctk.CTkLabel(r, text="", text_color=ACCENT, font=ctk.CTkFont(weight="bold"))
        val.pack(side="right")
        rst = ctk.CTkLabel(r, text="↺", cursor="hand2", font=ctk.CTkFont(size=16))
        rst.pack(side="right", padx=(0, 10))
        Tip(rst, "Reset to default")

        def upd(*_):
            val.configure(text=f"{var.get():.{dec}f}{unit}")
            rst.configure(text_color=ACCENT if abs(var.get() - dflt) > 1e-9 else BORDER_H)

        rst.bind("<Button-1>", lambda e: (var.set(dflt), upd()))
        self.updaters.append(upd)
        ctk.CTkSlider(parent, from_=lo, to=hi, number_of_steps=int(round((hi - lo) / step)), variable=var,
                      command=upd, **SLIDER).pack(fill="x", padx=16, pady=(2, 4))
        upd()

    def option(self, parent, text, tip, var, values):
        """Dropdown. The variable keeps the English key (the program looks it up); the list shows it translated."""
        self.lab(parent, text, tip)
        keys = list(values)
        menu = ctk.CTkOptionMenu(parent, values=[self.tr(k) for k in keys], **OPTION)
        menu.configure(command=lambda shown: var.set(keys[[self.tr(k) for k in keys].index(shown)]))
        menu.pack(anchor="w", padx=16, pady=(2, 4))

        def show(*_):  # the variable or the language changed: show the current choice in the current language
            menu.configure(values=[self.tr(k) for k in keys])
            menu.set(self.tr(var.get()))

        var.trace_add("write", show)
        self.choices = getattr(self, "choices", [])
        self.choices.append(show)
        show()
