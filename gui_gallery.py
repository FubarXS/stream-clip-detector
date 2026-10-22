"""Gallery view of the Clips tab: compact cards side by side (thumbnail, rating, title, a few buttons).
'Edit' opens the full card of the list view in its own window."""
import customtkinter as ctk

from brand import CARD, BTN2, TEXT, MUTED, ACCENT, BG, window_icon
from gui_player import open_player

COL_W = 330  # width of one gallery card (including the gap)


def cols_for(panel):
    w = panel.winfo_width()
    return max(1, (w - 30) // COL_W) if w > 200 else 3


def post_text(it):
    """Title, description and hashtags of a clip as one text (the General tab, with the user's edits)."""
    a = it.get("ai") or {}
    d = {"title": a.get("title", ""), "description": a.get("description") or a.get("why", ""),
         "hashtags": " ".join(a.get("hashtags", []))}
    d.update(((it.get("edits") or {}).get("General")) or {})
    return "\n\n".join(x for x in (d["title"], d["description"], d["hashtags"]) if x), d["title"]


def build(panel, shown):
    """Lay the clips of 'shown' out in a grid inside panel.body."""
    T, body = panel.T, panel.body
    panel._cols = cols = cols_for(panel)
    for c in range(cols):
        body.grid_columnconfigure(c, weight=1, uniform="gal")
    for n, it in enumerate(shown):
        post, title = post_text(it)
        a = it.get("ai") or {}
        f = ctk.CTkFrame(body, **CARD)
        f.grid(row=n // cols, column=n % cols, padx=6, pady=6, sticky="nsew")
        pic = panel.thumb(f, it.get("thumb", ""), COL_W - 40)
        pic.pack(padx=12, pady=(12, 6))
        pic.bind("<Button-1>", lambda e, it=it: open_player(panel, it, T))
        kind = {"marker": "MARKER", "finished": "FINISHED"}.get(it.get("kind"))
        badge = T(kind) if kind else (f"AI {a['funny']:g}/10" if a else f"score {it['score']}")
        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", padx=12)
        ctk.CTkLabel(top, text=badge, text_color=ACCENT, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        fav = ctk.CTkButton(top, text="★" if it.get("favorite") else "☆", width=30, height=26, **BTN2)
        fav.configure(command=lambda it=it, b=fav: panel.toggle_fav(it, b, gallery=True))
        fav.pack(side="right")
        t0, t1 = it["start"], it["end"]
        ctk.CTkLabel(top, text=f"  {t0 // 3600}:{t0 % 3600 // 60:02d}:{t0 % 60:02d}", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).pack(side="left")
        ctk.CTkLabel(f, text=title or T("(no title)"), text_color=TEXT, wraplength=COL_W - 50, justify="left", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(fill="x", padx=12, pady=(4, 6))
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        for text, cmd in ((T("▶ Play"), lambda it=it: open_player(panel, it, T)),
                          (T("Copy post"), None), (T("Edit"), lambda it=it: open_details(panel, it)),
                          (T("Delete"), lambda it=it: panel.delete(it))):
            b = ctk.CTkButton(row, text=text, height=28, width=10, **BTN2)
            if cmd is None:
                b.configure(command=lambda b=b, p=post: panel.copy(p, b))
            else:
                b.configure(command=cmd)
            b.pack(side="left", expand=True, fill="x", padx=2)


def open_details(panel, it):
    """The full card (editable texts, copy buttons, transcript) in its own window; edits are kept when it closes."""
    close_details(panel)
    win = ctk.CTkToplevel(panel, fg_color=BG)
    win.title(panel.T("Edit"))
    window_icon(win)
    win.geometry("920x760")
    body = ctk.CTkScrollableFrame(win, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=10, pady=10)
    n0 = len(panel.states)
    panel.card(body, 1, it)
    mine = panel.states[n0:]

    def close():
        panel.collect()  # while the widgets still exist
        panel.states = [s for s in panel.states if s not in mine]
        win.destroy()
        panel.detail = None
        panel.refresh(panel.items)

    win.protocol("WM_DELETE_WINDOW", close)
    panel.detail = (win, close, it)
    win.after(100, win.lift)


def close_details(panel, only=None):
    d = getattr(panel, "detail", None)
    if d and d[0].winfo_exists() and (only is None or d[2] is only):
        d[1]()
