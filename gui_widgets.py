"""Reusable widgets: hover tooltip and form-building helpers (cards, labeled rows, sliders...)."""
import tkinter as tk
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

    def entry(self, parent, text, key, browse=None, tip=None):
        self.lab(parent, text, tip)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(2, 4))
        ctk.CTkEntry(row, textvariable=self.vars[key], **ENTRY).pack(side="left", fill="x", expand=True)
        if browse:
            ctk.CTkButton(row, text="Browse", width=70, height=32, command=browse, **BTN2).pack(side="left", padx=(8, 0))

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
        self.lab(parent, text, tip)
        ctk.CTkOptionMenu(parent, values=list(values), variable=var, **OPTION).pack(anchor="w", padx=16, pady=(2, 4))
