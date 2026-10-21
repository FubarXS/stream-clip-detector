"""The clips window: one card per clip - thumbnail with play, texts per platform, hashtags, AI notes."""
import os
import importlib.util
import webbrowser
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from brand import TEXT, MUTED, ACCENT, ORANGE, BG, PANEL, BORDER, BORDER_H, CARD, ENTRY, BOX, BTN2, BTN_H, RADIUS_MD, SEG, SWITCH, BrandButton
from gui_widgets import Tip
from platforms import PLATFORMS

PIL_OK = importlib.util.find_spec("PIL") is not None
hms = lambda t: f"{int(t) // 3600}:{int(t) % 3600 // 60:02d}:{int(t) % 60:02d}"
TABS = [("General", None), ("TikTok", "tiktok"), ("YouTube Shorts", "shorts"), ("Reels", "reels")]
KEYS = dict(TABS)


def thumb_image(path, width=300):
    """Thumbnail with a play symbol drawn over it (like a video player); None if unavailable."""
    try:
        from PIL import Image, ImageDraw
        im = Image.open(path).convert("RGBA")
        size = (width, round(width * im.height / im.width))
        im = im.resize(size)
        ov = Image.new("RGBA", size, (0, 0, 0, 0))
        d, (cx, cy) = ImageDraw.Draw(ov), (size[0] // 2, size[1] // 2)
        d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(0, 0, 0, 150))
        d.polygon([(cx - 8, cy - 14), (cx - 8, cy + 14), (cx + 16, cy)], fill=(254, 85, 5, 255))
        return ctk.CTkImage(Image.alpha_composite(im, ov).convert("RGB"), size=size)
    except Exception:
        return None


def tag_words(box):
    return ["#" + w.lstrip("#") for w in box.get("1.0", "end").split() if w.strip("#")]


class CardState:
    """The editable texts of one clip card - one set per platform tab - and the widgets that show them."""

    def __init__(self, ai, saved=None):
        self.data = {"General": {"title": ai.get("title", ""), "description": ai.get("description") or ai.get("why", ""),
                                 "hashtags": " ".join(ai.get("hashtags", []))}}
        for name, key in TABS[1:]:
            p = (ai.get("platforms") or {}).get(key)
            if p:
                self.data[name] = {"title": p["title"], "description": p["description"], "hashtags": " ".join(p["hashtags"])}
        for name, d in (saved or {}).items():  # texts the user edited earlier
            if name in self.data:
                self.data[name].update(d)
        self.cur = "General"

    def save(self):
        self.data[self.cur] = {"title": self.title.get().strip(), "description": self.desc.get("1.0", "end").strip(),
                               "hashtags": " ".join(tag_words(self.tags))}

    def load(self, name):
        d = self.data[name]
        self.title.delete(0, "end")
        self.title.insert(0, d["title"])
        self.desc.delete("1.0", "end")
        self.desc.insert("1.0", d["description"])
        self.tags.delete("1.0", "end")
        self.tags.insert("1.0", d["hashtags"])
        self.cur = name

    def post(self, name=None):
        name = name or self.cur
        if name == self.cur:
            self.save()
        d = self.data[name]
        return "\n\n".join(x for x in (d["title"], d["description"], d["hashtags"]) if x)


class ClipsPanel(ctk.CTkFrame):
    """The Clips tab of the main window: one card per clip."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app, self.items, self.states = app, [], []
        self.fav_only = tk.BooleanVar(master=self, value=False)
        self.T = lambda s: app.tr(s)
        h = ctk.CTkFrame(self, fg_color="transparent")
        h.pack(fill="x", pady=(2, 6))
        self.title_lbl = ctk.CTkLabel(h, text="", text_color=TEXT, font=ctk.CTkFont(size=20, weight="bold"))
        self.title_lbl.pack(side="left")
        self.add_btn = BrandButton(h, "+  Add finished clip", app.add_finished, width=200, height=34)
        self.add_btn.pack(side="right")
        self.all_btn = ctk.CTkButton(h, text="Copy all posts", width=150, height=32, command=self.copy_all, **BTN2)
        self.all_btn.pack(side="right", padx=(0, 10))
        ctk.CTkButton(h, text="Open folder", width=110, height=32, command=app.open_out, **BTN2).pack(side="right", padx=(0, 8))
        ctk.CTkButton(h, text="Reload", width=90, height=32, command=app.load_clips, **BTN2).pack(side="right", padx=(0, 8))
        ctk.CTkSwitch(h, text="Favorites only", variable=self.fav_only, command=lambda: self.refresh(self.items),
                      **SWITCH).pack(side="right", padx=(0, 14))
        ctk.CTkLabel(self, text="Hashtags are ordered broad → niche (an AI estimate). You can edit any text, then copy. All texts are also saved in posts.txt.",
                     text_color=MUTED, anchor="w", font=ctk.CTkFont(size=11), wraplength=980, justify="left").pack(fill="x", pady=(0, 8))
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=BORDER,
                                           scrollbar_button_hover_color=BORDER_H)
        self.body.pack(fill="both", expand=True)
        self.refresh([])

    def relabel(self):
        self.add_btn.configure(text=self.T("+  Add finished clip"))
        self.title_lbl.configure(text=f"{self.T('Clips')} ({len(self.items)})")

    def collect(self):
        """Move the texts typed into the cards into their items (kept when the cards are rebuilt or saved)."""
        for st in self.states:
            try:
                st.save()
            except Exception:
                continue
            st.item["edits"] = st.data

    def refresh(self, items):
        """Rebuild the cards: favorites first; the 'Favorites only' switch filters."""
        self.collect()
        shown = sorted((it for it in items if it.get("favorite") or not self.fav_only.get()), key=lambda it: not it.get("favorite"))
        self.items, self.states = items, []
        for w in self.body.winfo_children():
            w.destroy()
        for i, it in enumerate(shown, 1):
            self.card(self.body, i, it)
        if not shown:
            msg = ("No favorites yet. Click ☆ Favorite on a clip." if items else
                   "No clips yet. Click '+ Add finished clip' to analyze a clip you already have "
                   "(for example exported from DaVinci Resolve), or run a stream analysis in the main window.")
            ctk.CTkLabel(self.body, text=self.T(msg), text_color=MUTED, justify="left", wraplength=800).pack(pady=60)
        self.relabel()

    def card(self, parent, i, it):
        T, a, small = self.T, it.get("ai") or {}, ctk.CTkFont(size=11)
        st = CardState(a, it.get("edits"))
        st.item = it
        self.states.append(st)
        f = ctk.CTkFrame(parent, **CARD)
        f.pack(fill="x", pady=(0, 12))
        f.grid_columnconfigure(1, weight=1)
        left = ctk.CTkFrame(f, fg_color="transparent")
        left.grid(row=0, column=0, sticky="n", padx=16, pady=(30, 16))
        pic = self.thumb(left, it.get("thumb", ""))
        pic.pack()
        pic.bind("<Button-1>", lambda e: self.play(it))
        ctk.CTkButton(left, text=T("▶  Play clip"), height=34, command=lambda: self.play(it), **BTN2).pack(fill="x", pady=(8, 0))
        fav = ctk.CTkButton(left, text=T("★ Favorite" if it.get("favorite") else "☆ Favorite"), height=30, **BTN2)
        fav.configure(command=lambda: self.toggle_fav(it, fav))
        fav.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(left, text=T("Delete"), height=30, command=lambda: self.delete(it), **BTN2).pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(left, text=f"{hms(it['start'])} - {hms(it['end'])}", text_color=MUTED, font=small).pack(pady=(6, 0))

        r = ctk.CTkFrame(f, fg_color="transparent")
        r.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=(30, 16))
        kind = {"marker": "MARKER", "finished": "FINISHED"}.get(it["kind"])
        badge = T(kind) if kind else (f"AI {a['funny']:g}/10" if a else f"score {it['score']}")
        ctk.CTkLabel(r, text=f"#{i}   {badge}", text_color=ACCENT, font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        if len(st.data) > 1:
            seg = ctk.CTkSegmentedButton(r, values=[n for n, _ in TABS if n in st.data], command=lambda n: self.switch(st, n), **SEG)
            seg.set("General")
            seg.pack(anchor="w", pady=(8, 0))
        st.tf = ctk.CTkFrame(r, fg_color="transparent")
        st.tf.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(st.tf, text=T("Title"), text_color=MUTED, font=small).pack(anchor="w")
        st.title = ctk.CTkEntry(st.tf, font=ctk.CTkFont(size=14, weight="bold"), **ENTRY)
        st.title.pack(fill="x")
        st.dlabel = ctk.CTkLabel(r, text=T("Description"), text_color=MUTED, font=small)
        st.dlabel.pack(anchor="w", pady=(8, 0))
        st.desc = ctk.CTkTextbox(r, height=58, wrap="word", **BOX)
        st.desc.pack(fill="x")
        th = ctk.CTkFrame(r, fg_color="transparent")
        th.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(th, text=T("Hashtags"), text_color=MUTED, font=small).pack(side="left")
        count = ctk.CTkLabel(th, text="", text_color=ACCENT, font=small)
        count.pack(side="right")
        st.tags = ctk.CTkTextbox(r, height=72, wrap="word", **BOX)
        st.tags.pack(fill="x")

        def upd(*_):
            n, key = len(tag_words(st.tags)), KEYS[st.cur]
            if key:
                p = PLATFORMS[key]
                count.configure(text=f"{n} {T('hashtags')} · {T('recommended')} {p['rec']}",
                                text_color=ORANGE if n > p["cap"] else ACCENT)
            else:
                count.configure(text=f"{n} {T('hashtags')}", text_color=ACCENT)

        st.upd = upd
        st.load("General")
        st.tags.bind("<KeyRelease>", upd)
        upd()
        row = ctk.CTkFrame(r, fg_color="transparent")
        row.pack(fill="x", pady=(6, 0))
        for label, n in (("Copy top 5", 5), ("Copy top 10", 10), ("Copy all tags", 0)):
            b = ctk.CTkButton(row, text=T(label), width=112, height=30, **BTN2)
            b.configure(command=lambda b=b, n=n: self.copy(" ".join(tag_words(st.tags)[: n or None]), b))
            b.pack(side="left", padx=(0, 6))
        b = ctk.CTkButton(row, text=T("Copy full post"), width=140, height=30, **BTN2)
        b.configure(command=lambda b=b: self.copy(st.post(), b))
        b.pack(side="left")

        notes = [f"{T('Why picked:')} {it['why']}"]
        if a:
            notes.insert(0, f"{T('AI rating:')} {a['funny']:g}/10 - {a['why']}")
        if a.get("evidence") and not a.get("evidence_ok"):
            notes.append(T("⚠ not found in the transcript - the AI may be wrong") + f"  ('{a['evidence']}')")
        ctk.CTkLabel(r, text="\n".join(notes), text_color=TEXT, justify="left", wraplength=560, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(10, 0))
        if it.get("links"):
            m = ctk.CTkFrame(r, fg_color="transparent")
            m.pack(anchor="w", pady=(6, 0))
            ctk.CTkLabel(m, text=T("Meme/GIF ideas:"), text_color=MUTED, font=small).pack(side="left", padx=(0, 6))
            for x in it["links"]:
                ctk.CTkLabel(m, text=f"\"{x['term']}\"", text_color=TEXT, font=small).pack(side="left", padx=(0, 4))
                for name, key in (("GIPHY", "giphy"), ("YouTube", "youtube")):
                    lk = ctk.CTkLabel(m, text=name, text_color=ACCENT, cursor="hand2", font=ctk.CTkFont(size=11, underline=True))
                    lk.pack(side="left", padx=(0, 6))
                    lk.bind("<Button-1>", lambda e, u=x[key]: webbrowser.open(u))
                ctk.CTkLabel(m, text="  ").pack(side="left")
        tb = ctk.CTkTextbox(r, height=90, wrap="word", **BOX)
        tb.insert("1.0", it.get("text", ""))
        tb.configure(state="disabled")
        tbtn = ctk.CTkButton(r, text=T("Show transcript"), width=160, height=28, **BTN2)

        def toggle():
            if tb.winfo_ismapped():
                tb.pack_forget()
                tbtn.configure(text=T("Show transcript"))
            else:
                tb.pack(fill="x", pady=(6, 0), after=tbtn)
                tbtn.configure(text=T("Hide transcript"))

        tbtn.configure(command=toggle)
        tbtn.pack(anchor="w", pady=(8, 0))
        xb = ctk.CTkButton(f, text="✕", width=24, height=24, fg_color="transparent", hover_color=BTN_H, text_color=MUTED,
                           corner_radius=RADIUS_MD, command=lambda: self.remove(it))
        xb.place(x=6, y=4)  # top-left corner: take the clip off the list
        Tip(xb, "Remove from the list (the files stay on disk)")

    def thumb(self, parent, path):
        img = thumb_image(path)
        if img:
            return ctk.CTkLabel(parent, text="", image=img, cursor="hand2")
        try:  # without Pillow, Tk can still show a PNG (just without the play symbol on top)
            photo = tk.PhotoImage(file=path)
            lbl = tk.Label(parent, image=photo, bd=0, bg=PANEL, cursor="hand2")
            lbl.image = photo
            return lbl
        except Exception:
            return ctk.CTkLabel(parent, text=self.T("(no preview)"), text_color=MUTED, cursor="hand2")

    def remove(self, it):
        """The cross in the corner: remove from the list only, never touches files."""
        self.items.remove(it)
        self.app.save_items()
        self.refresh(self.items)

    def toggle_fav(self, it, btn):
        it["favorite"] = not it.get("favorite")
        btn.configure(text=self.T("★ Favorite" if it["favorite"] else "☆ Favorite"))
        self.app.save_items()

    def delete(self, it):
        T, f = self.T, it.get("file") or ""
        msg = T("Remove this clip?") + (f"\n\n{f}" if f else "") + "\n\n" + T(
            "Yes = delete the file from disk and remove it from the list\nNo = only remove it from the list\nCancel = do nothing")
        ans = messagebox.askyesnocancel(T("Delete clip"), msg)
        if ans is None:
            return
        if ans:
            for p in (f, it.get("thumb")):
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except OSError as e:
                    messagebox.showerror(T("Delete clip"), str(e))
        self.items.remove(it)
        self.app.save_items()
        self.refresh(self.items)

    def switch(self, st, name):
        st.save()
        st.load(name)
        key = KEYS[name]
        if key and not PLATFORMS[key]["title"]:
            st.tf.pack_forget()
        elif not st.tf.winfo_ismapped():
            st.tf.pack(fill="x", pady=(6, 0), before=st.dlabel)
        st.upd()

    def copy(self, text, btn):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        old = btn.cget("text")
        btn.configure(text=self.T("Copied ✓"))
        self.after(1200, lambda: btn.winfo_exists() and btn.configure(text=old))

    def copy_all(self):
        self.copy("\n\n\n".join(s.post("General") for s in self.states), self.all_btn)

    def play(self, it):
        p = it.get("file")
        if p and os.path.exists(p):
            try:
                os.startfile(p)
            except AttributeError:
                webbrowser.open("file://" + p)
        else:
            messagebox.showinfo(self.T("No clip file"), self.T("This clip was not cut (the option 'Cut video clips' was off)."))
