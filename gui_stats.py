"""The Stats tab: hashtag settings, the imported YouTube data (kept between starts), which hashtags work - overall and
per game - and a small overview of the channel. The numbers come from hashtag_stats.py (no window code there)."""
import datetime
import tkinter as tk
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

import hashtag_stats as hs
from brand import ACCENT, BORDER, BORDER_H, BOX, BTN2, COMBO, INPUT, MUTED, OPTION, SWITCH, TEXT
from gui_config import STATS
from gui_widgets import FitButton

SCRIPT_URL = "https://github.com/FubarXS/stream-clip-detector/blob/main/tools/yt-studio-export.user.js"
ALL = "All games"  # English key of the "no game filter" choice
BEST = 20          # how many hashtags "Use as proven hashtags" copies
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
SOURCE_NAMES = {"feed": "Shorts feed", "search": "search", "browse": "browsing", "hashtag": "hashtags"}


def fmt(n):
    return f"{int(n):,}".replace(",", " ")


class StatsPanel(ctk.CTkFrame):
    """The Stats tab of the main window (shown instead of the Analysis tab)."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app, self.T = app, app.tr
        self.store, self.meta = hs.load_all(STATS)
        self.view_game = tk.StringVar(master=self, value="")  # "" = all games
        self.bulk = tk.StringVar(master=self, value="")
        self.dirty = True  # the video list is built when the tab is opened
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        scroll = dict(fg_color="transparent", scrollbar_button_color=BORDER, scrollbar_button_hover_color=BORDER_H)
        left = ctk.CTkScrollableFrame(self, width=430, **scroll)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 6))
        right = ctk.CTkScrollableFrame(self, **scroll)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.build_left(left)
        self.build_right(right)

    # ---------- layout ----------
    def label(self, parent, size=11, color=MUTED, wrap=380, **pack):
        lbl = ctk.CTkLabel(parent, text="", text_color=color, font=ctk.CTkFont(size=size), justify="left", wraplength=wrap, anchor="w")
        lbl.pack(anchor="w", padx=16, **({"pady": (2, 6)} | pack))
        return lbl

    def build_left(self, left):
        a = self.app
        data = a.card(left, "YouTube data",
                      "Your videos from YouTube Studio. Made by the Tampermonkey script in the tools folder of the project. "
                      "The import is saved, so the program remembers it the next time you start it.")
        row = ctk.CTkFrame(data, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(8, 2))
        FitButton(row, text="Import YouTube export", width=150, height=30, command=a.import_stats, **BTN2).pack(side="left")
        FitButton(row, text="Get the export script", width=140, height=30, command=lambda: webbrowser.open(SCRIPT_URL),
                  **BTN2).pack(side="left", padx=(8, 0))
        self.data_lbl = self.label(data, pady=(6, 12))

        tags = a.card(left, "Hashtags")
        a.entry(tags, "Always add these hashtags", "extra_tags", None,
                "Your own hashtags for every clip, e.g. #yourchannel. Separate with spaces. They are added at the end of the list.")
        a.entry(tags, "Proven hashtags", "proven_tags", None,
                "Hashtags that worked well for you, e.g. #funny #fail. Separate with spaces. TikTok, YouTube Shorts and "
                "Reels use them right after the game hashtag, up to two thirds of each post; the rest comes fresh from "
                "the AI so you keep learning what works. Needs the AI switch in the Analysis tab.")
        a.slider(tags, "Hashtag pool size", "tag_pool", 15, 50, 5,
                 "How many hashtags the AI collects in the General tab - a big list to pick from. TikTok and Reels use "
                 "5 of them, YouTube Shorts up to 30 (YouTube ignores hashtags above 60).")
        ctk.CTkSwitch(tags, text="Add the best hashtags for the game automatically", variable=a.vars["auto_tags"],
                      command=a.update_game_hint, **SWITCH).pack(anchor="w", padx=16, pady=(10, 0))
        ctk.CTkLabel(tags, text="When you start an analysis, the hashtags that did best for the game in the Analysis tab (and "
                                "the strong general ones) are added to your proven hashtags. Hashtags of other games are left "
                                "out. Needs the AI switch in the Analysis tab. Off by default.", text_color=MUTED,
                     font=ctk.CTkFont(size=11), justify="left", wraplength=380, anchor="w").pack(anchor="w", padx=16, pady=(2, 14))

    def build_right(self, right):
        a = self.app
        top = a.card(right, "Strongest hashtags",
                     "Videos with a hashtag are compared with videos without it. Pick a game to see only its videos.")
        top.pack_configure(pady=(0, 12))
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(8, 0))
        ctk.CTkLabel(row, text="Game", text_color=TEXT).pack(side="left")
        self.menu = ctk.CTkOptionMenu(row, values=[""], width=220, command=self.pick_game, dynamic_resizing=False, **OPTION)
        self.menu.pack(side="left", padx=(10, 0))
        self.count_lbl = self.label(top, wrap=500, pady=(8, 2))
        self.prog = ctk.CTkProgressBar(top, mode="determinate", progress_color=ACCENT, fg_color=BORDER, height=8)
        self.prog.pack(fill="x", padx=16, pady=(0, 8))
        self.best_lbl = self.label(top, size=13, color=TEXT, wrap=500, pady=(0, 6))
        brow = ctk.CTkFrame(top, fg_color="transparent")
        brow.pack(fill="x", padx=16, pady=(0, 14))
        self.use_btn = FitButton(brow, text="Use as proven hashtags", width=190, height=32, command=self.use_best, **BTN2)
        self.use_btn.pack(side="left")

        rk = a.card(right, "Ranking")
        self.box = ctk.CTkTextbox(rk, height=250, font=("Consolas", 12), wrap="none", **BOX)
        self.box.pack(fill="x", padx=16, pady=(6, 6))
        self.note_lbl = self.label(rk, wrap=500, pady=(0, 12))

        ov = a.card(right, "Overview of the channel",
                    "Uses the other columns of the export: where the views come from, which weekday and which length did better.")
        self.ov_lbl = self.label(ov, size=12, color=TEXT, wrap=500, pady=(6, 12))

        vd = a.card(right, "Videos and games",
                    "Give every video its game, so the statistics and the automatic hashtags can tell the games apart. The game is "
                    "guessed from the title and hashtags; you can type it yourself. Hashtags that almost only appear on one game "
                    "are marked as game hashtags and are not used for other games.")
        brow = ctk.CTkFrame(vd, fg_color="transparent")
        brow.pack(fill="x", padx=16, pady=(8, 2))
        FitButton(brow, text="Guess the games", width=130, height=30, command=self.guess_click, **BTN2).pack(side="left")
        self.bulk_box = ctk.CTkComboBox(brow, variable=self.bulk, width=190, height=30, values=[""], **COMBO)
        self.bulk_box.pack(side="left", padx=(14, 0))
        FitButton(brow, text="Set for videos without a game", width=190, height=30, command=self.bulk_click,
                  **BTN2).pack(side="left", padx=(8, 0))
        self.list = ctk.CTkFrame(vd, fg_color="transparent")
        self.list.pack(fill="x", padx=16, pady=(8, 14))

    # ---------- data ----------
    def game(self):
        return self.view_game.get()

    def games(self):
        return hs.known_games(self.store, self.meta, [self.app.vars["game"].get()])

    def save(self):
        try:
            hs.save(STATS, self.store, self.meta)
        except OSError:
            pass

    def remember_game(self):
        """The game typed in the Analysis tab joins the list of known games (saved with the statistics)."""
        g = self.app.vars["game"].get().strip()
        if g and hs.norm(g) not in {hs.norm(x) for x in self.meta["games"]}:
            self.meta["games"].append(g)
            self.save()

    def guess(self):
        """Give a game to the videos that have none, by title and hashtags. Returns how many got one."""
        games, n = self.games(), 0
        for v in self.store.values():
            if not v.get("game"):
                g = hs.guess_game(v, games)
                if g:
                    v["game"], n = g, n + 1
        if n:
            self.save()
        return n

    # ---------- actions ----------
    def pick_game(self, shown):
        self.view_game.set("" if shown == self.T(ALL) else shown)
        self.render_results()

    def guess_click(self):
        n = self.guess()
        messagebox.showinfo(self.T("Guess the games"), self.T("A game was found for {n} videos.").format(n=n) if n else
                            self.T("No game found. Type the game name in the Analysis tab first, or in the list below."), parent=self)
        self.reload()

    def bulk_click(self):
        g = self.bulk.get().strip()
        empty = [v for v in self.store.values() if not v.get("game")]
        if not g or not empty:
            messagebox.showinfo(self.T("Videos and games"), self.T("Type a game name first. Only videos without a game are changed.")
                                if not g else self.T("Every video already has a game."), parent=self)
            return
        if not messagebox.askyesno(self.T("Videos and games"), self.T("Set \"{g}\" for {n} videos without a game?").format(g=g, n=len(empty)),
                                   parent=self):
            return
        for v in empty:
            v["game"] = g
        if hs.norm(g) not in {hs.norm(x) for x in self.meta["games"]}:
            self.meta["games"].append(g)
        self.save()
        self.reload()

    def use_best(self):
        T, best = self.T, hs.best(self.store, self.game(), BEST)
        if not best:
            messagebox.showinfo(T("Strongest hashtags"), T("No hashtag is above the others yet."), parent=self)
            return
        var = self.app.vars["proven_tags"]
        if var.get().strip() and not messagebox.askyesno(T("Proven hashtags"), T("Replace your proven hashtags with the {n} best ones?")
                                                         .format(n=len(best)), parent=self):
            return
        var.set(" ".join(best))

    def commit(self, vid, entry):
        """A game typed into the list of videos: saved at once, the numbers are redone."""
        v, g = self.store.get(vid), entry.get().strip()
        if v is None or (v.get("game") or "") == g:
            return
        v["game"] = g
        if g and hs.norm(g) not in {hs.norm(x) for x in self.meta["games"]}:
            self.meta["games"].append(g)
        self.save()
        self.render_results()

    # ---------- showing ----------
    def on_show(self):
        if self.dirty:
            self.reload()

    def reload(self):
        """Rebuild everything from the data in memory (after an import, a language change, a bulk change)."""
        self.dirty = False
        self.render_results()
        self.build_videos()

    def relabel(self):
        if self.winfo_ismapped():
            self.reload()
        else:
            self.dirty = True
            self.render_results()

    def date_text(self):
        try:
            d = datetime.date.fromisoformat(self.meta.get("last_import", ""))
        except ValueError:
            return ""
        return f"{d.day}. {d.month}. {d.year}"

    def render_results(self):
        T, g = self.T, self.game()
        games = self.games()
        if g and hs.norm(g) not in {hs.norm(x) for x in games}:
            g = ""
            self.view_game.set("")
        n = len(self.store)
        if not n:
            self.data_lbl.configure(text=T("No YouTube data imported yet."))
        else:
            cnt = {}
            for v in self.store.values():
                k = v.get("game") or T("no game")
                cnt[k] = cnt.get(k, 0) + 1
            txt = T("{n} videos imported from YouTube.").format(n=n)
            if self.date_text():
                txt += " " + T("Last import: {d}.").format(d=self.date_text())
            self.data_lbl.configure(text=txt + "\n" + ", ".join(f"{k} ({c})" for k, c in sorted(cnt.items(), key=lambda x: -x[1])))
        self.menu.configure(values=[T(ALL)] + games)
        self.menu.set(g or T(ALL))
        self.bulk_box.configure(values=games or [""])
        rows, info = hs.rank(self.store, g or None)
        best = hs.best(self.store, g, BEST)
        self.prog.set(min(1, info["used"] / hs.MIN_VIDEOS))
        self.use_btn.configure(state="normal" if best else "disabled")
        if not n:
            self.count_lbl.configure(text=T("No YouTube data yet. Press \"Import YouTube export\" first."))
        else:
            txt = T("{used} of {total} videos used (older than {d} days).").format(used=info["used"], total=info["total"], d=hs.MIN_AGE_DAYS)
            txt += "  " + T("A reliable ranking needs about {m} videos.").format(m=hs.MIN_VIDEOS)
            self.count_lbl.configure(text=txt)
        self.best_lbl.configure(text=" ".join(best) if best else (T("Nothing to recommend yet.") if n else ""))
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        if rows:
            head = [T("Hashtag"), T("Game"), T("Videos"), T("Median views"), T("vs. without")]
            body = [[r["tag"][:20], r["game"][:14], str(r["n"]), fmt(r["median"]), f"{r['lift']:.1f}x"] for r in rows]
            w = [max(len(x[i]) for x in [head, *body]) + 2 for i in range(5)]  # every column as wide as its widest text
            line = lambda c: "".join(c[i].ljust(w[i]) if i < 2 else c[i].rjust(w[i]) for i in range(5)) + "\n"
            self.box.insert("end", line(head) + "".join(line(c) for c in body))
        self.box.configure(state="disabled")
        if not n:
            note = ""
        elif not rows:
            note = T("No hashtag is used in at least {k} videos and missing in at least {k} others yet, so nothing can be compared. "
                     "Post videos with different hashtag sets.").format(k=hs.MIN_SIDE)
        else:
            note = T("Videos with a hashtag are compared with videos without it. A higher number does not prove that the hashtag "
                     "caused it. Hashtags that were always used together get the same number.")
        if n and info["used"] < hs.MIN_VIDEOS:
            note = T("Preliminary: with fewer than {m} videos these numbers are mostly luck. Use them as a hint, not as proof.").format(
                m=hs.MIN_VIDEOS) + ("\n" + note if note else "")
        self.note_lbl.configure(text=note)
        self.render_overview(g)
        self.app.update_game_hint()

    def render_overview(self, g):
        T = self.T
        mine = {k: v for k, v in self.store.items() if not g or hs.norm(v.get("game")) == hs.norm(g)}
        o = hs.overview(mine)
        lines = []
        if o.get("sources"):
            s = o["sources"]
            lines.append(T("Views come from") + ": " + ", ".join(f"{T(SOURCE_NAMES[k])} {s[k]:.0f} %" for k in hs.SOURCES)
                         + f"  ({T('{n} videos').format(n=o['sources_n'])})")
            if s["hashtag"] < 5:
                lines.append(T("Only a small part of your views comes from hashtag pages."))
        if o.get("weekdays"):
            lines.append(T("Best weekdays (median views)") + ": " + ", ".join(f"{T(WEEKDAYS[d])} {fmt(m)} ({c})" for d, m, c in o["weekdays"][:3]))
        if o.get("lengths"):
            lines.append(T("By length (median views)") + ": " + ", ".join(f"{T(n)} {fmt(m)} ({c})" for n, m, c in o["lengths"]))
        if not lines:
            lines = [T("Not enough videos yet for an overview. Import the export again after the next videos.")]
        self.ov_lbl.configure(text="\n".join(lines))

    def build_videos(self):
        for w in self.list.winfo_children():
            w.destroy()
        T = self.T
        vids = sorted(self.store.values(), key=lambda v: v.get("published", ""), reverse=True)
        if not vids:
            ctk.CTkLabel(self.list, text=T("No YouTube data imported yet."), text_color=MUTED).pack(anchor="w")
            return
        for v in vids:
            r = ctk.CTkFrame(self.list, fg_color="transparent")
            r.pack(fill="x", pady=1)
            e = ctk.CTkEntry(r, width=190, height=28, fg_color=INPUT, border_color=BORDER, text_color=TEXT, placeholder_text=T("game"))
            e.pack(side="right")
            if v.get("game"):
                e.insert(0, v["game"])
            e.bind("<Return>", lambda ev, i=v["id"], x=e: (self.commit(i, x), self.focus_set()))
            e.bind("<FocusOut>", lambda ev, i=v["id"], x=e: self.commit(i, x))
            title = (v.get("title") or v["id"]).replace("\n", " ")
            ctk.CTkLabel(r, text=f"{title[:48]}{'…' if len(title) > 48 else ''}   ·   {fmt(v['views'])}", text_color=TEXT,
                         anchor="w", font=ctk.CTkFont(size=12)).pack(side="left", fill="x", expand=True)
