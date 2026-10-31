"""YouTube export import and the 'Hashtag insights' window (the ranking itself is in hashtag_stats.py)."""
import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

import hashtag_stats as hs
from brand import BG, BORDER, BTN2, INPUT, MUTED, TEXT
from gui_config import DATA
from gui_widgets import FitButton

STATS = os.path.join(DATA, "youtube_stats.json")  # the imported videos, kept between starts
BEST = 20  # how many hashtags "Use the best as proven hashtags" copies


def _fmt(n):
    return f"{int(n):,}".replace(",", " ")


class InsightsMixin:
    def render_stats(self):
        n = len(hs.load(STATS))
        self.stats_lbl.configure(text=self.tr("{n} videos imported from YouTube.").format(n=n) if n
                                 else self.tr("No YouTube data imported yet."))

    def import_stats(self):
        files = filedialog.askopenfilenames(parent=self, title=self.tr("Choose the YouTube export (CSV)"),
                                            initialdir=self.start_dir("stats"),
                                            filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not files:
            return
        self.dirs["stats"] = os.path.dirname(files[0])
        store, added, updated = hs.load(STATS), 0, 0
        try:
            for f in files:
                a, u = hs.merge(store, hs.parse_csv(f))
                added, updated = added + a, updated + u
            hs.save(STATS, store)
        except ValueError:
            messagebox.showerror(self.tr("Import"), self.tr("This file does not look like the YouTube export "
                                 "(the columns video_id and zhlednuti are missing)."))
            return
        except OSError as e:
            messagebox.showerror(self.tr("Import"), str(e))
            return
        self.render_stats()
        messagebox.showinfo(self.tr("Import"), self.tr("Imported {n} videos ({new} new, {upd} updated). Total: {tot} videos.")
                            .format(n=added + updated, new=added, upd=updated, tot=len(store)))

    def show_insights(self):
        T, store = self.tr, hs.load(STATS)
        rows, info = hs.rank(store)
        win = ctk.CTkToplevel(self)
        win.title(T("Hashtag insights"))
        win.configure(fg_color=BG)
        win.geometry(f"660x560+{self.winfo_rootx() + 100}+{self.winfo_rooty() + 60}")
        win.after(150, win.lift)

        def label(text, color=TEXT, size=12):
            ctk.CTkLabel(win, text=text, text_color=color, font=ctk.CTkFont(size=size), justify="left", wraplength=610,
                         anchor="w").pack(anchor="w", padx=20, pady=(10, 0))

        if not store:
            label(T("No YouTube data yet. Press \"Import YouTube export\" in the AI section first."))
        else:
            label(T("{used} of {total} videos used (older than {d} days).").format(used=info["used"], total=info["total"],
                                                                                  d=hs.MIN_AGE_DAYS))
            if info["used"] < hs.MIN_VIDEOS:
                label(T("Preliminary: with fewer than {m} videos these numbers are mostly luck. Use them as a hint, "
                        "not as proof.").format(m=hs.MIN_VIDEOS), MUTED)
            if not rows:
                label(T("No hashtag is used in at least {k} videos and missing in at least {k} others yet, so nothing "
                        "can be compared. Post videos with different hashtag sets.").format(k=hs.MIN_SIDE))
            else:
                box = ctk.CTkTextbox(win, fg_color=INPUT, text_color=TEXT, border_color=BORDER, border_width=1,
                                     font=("Consolas", 12))
                box.pack(fill="both", expand=True, padx=20, pady=(12, 0))
                box.insert("end", f"{T('Hashtag'):<28}{T('Videos'):>8}{T('Median views'):>16}{T('vs. without'):>14}\n")
                for r in rows:
                    box.insert("end", f"{r['tag']:<28}{r['n']:>8}{_fmt(r['median']):>16}{r['lift']:>13.1f}x\n")
                box.configure(state="disabled")
                label(T("Videos with a hashtag are compared with videos without it. A higher number does not prove that "
                        "the hashtag caused it. Hashtags that were always used together get the same number."), MUTED, 11)

        def use_best():
            best = [r["tag"] for r in rows if r["lift"] > 1][:BEST]
            if not best:
                messagebox.showinfo(T("Hashtag insights"), T("No hashtag is above the others yet."), parent=win)
                return
            if self.vars["proven_tags"].get().strip() and not messagebox.askyesno(
                    T("Proven hashtags"), T("Replace your proven hashtags with the {n} best ones?").format(n=len(best)),
                    parent=win):
                return
            self.vars["proven_tags"].set(" ".join(best))
            win.destroy()

        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=14)
        FitButton(row, text=T("Close"), width=90, height=32, command=win.destroy, **BTN2).pack(side="right")
        if rows:
            FitButton(row, text=T("Use the best as proven hashtags"), width=230, height=32, command=use_best,
                      **BTN2).pack(side="right", padx=(0, 10))
