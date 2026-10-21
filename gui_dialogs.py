"""Small brand-styled dialogs."""
import tkinter as tk
import customtkinter as ctk

from brand import BG, TEXT, ENTRY, BTN2, BrandButton


def ask_text(parent, title, prompt, initial="", ok="OK", cancel="Cancel"):
    """Modal text box. Returns the text (it may be empty) or None when the user cancels."""
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.configure(fg_color=BG)
    win.resizable(False, False)
    win.geometry(f"440x200+{parent.winfo_rootx() + 120}+{parent.winfo_rooty() + 120}")
    result = {"v": None}
    ctk.CTkLabel(win, text=prompt, text_color=TEXT, wraplength=400, justify="left").pack(anchor="w", padx=20, pady=(20, 8))
    var = tk.StringVar(master=win, value=initial)
    entry = ctk.CTkEntry(win, textvariable=var, **ENTRY)
    entry.pack(fill="x", padx=20)

    def done(accepted):
        result["v"] = var.get().strip() if accepted else None
        win.destroy()

    row = ctk.CTkFrame(win, fg_color="transparent")
    row.pack(fill="x", padx=20, pady=(18, 0))
    BrandButton(row, ok, lambda: done(True), width=110, height=34).pack(side="right")
    ctk.CTkButton(row, text=cancel, width=100, height=34, command=lambda: done(False), **BTN2).pack(side="right", padx=(0, 10))
    entry.bind("<Return>", lambda e: done(True))
    win.bind("<Escape>", lambda e: done(False))
    win.protocol("WM_DELETE_WINDOW", lambda: done(False))
    win._entry, win._ok = entry, lambda: done(True)  # handles for tests

    def focus():
        try:
            win.lift()
            win.grab_set()
            entry.focus_set()
        except tk.TclError:
            pass

    win.after(150, focus)
    parent.wait_window(win)
    return result["v"]
