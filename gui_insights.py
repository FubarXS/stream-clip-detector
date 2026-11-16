"""YouTube export import and the hint under the game field (the Stats tab itself is in gui_stats.py, the numbers in
hashtag_stats.py)."""
import datetime
import os
from tkinter import filedialog, messagebox

import hashtag_stats as hs
from gui_config import STATS


class InsightsMixin:
    def render_stats(self):
        """The language changed: the Stats tab and the game hint are written again."""
        self.stats_panel.relabel()

    def import_stats(self):
        panel = self.stats_panel
        files = filedialog.askopenfilenames(parent=self, title=self.tr("Choose the YouTube export (CSV)"),
                                            initialdir=self.start_dir("stats"),
                                            filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not files:
            return
        self.dirs["stats"] = os.path.dirname(files[0])
        store, added, updated = panel.store, 0, 0
        try:
            for f in files:
                a, u = hs.merge(store, hs.parse_csv(f))
                added, updated = added + a, updated + u
            panel.meta["last_import"] = datetime.date.today().isoformat()
            hs.save(STATS, store, panel.meta)
        except ValueError:
            messagebox.showerror(self.tr("Import"), self.tr("This file does not look like the YouTube export "
                                 "(the columns video_id and zhlednuti are missing)."))
            return
        except OSError as e:
            messagebox.showerror(self.tr("Import"), str(e))
            return
        panel.remember_game()
        guessed = panel.guess()  # the games of the new videos, by title and hashtags
        panel.reload()
        msg = self.tr("Imported {n} videos ({new} new, {upd} updated). Total: {tot} videos.").format(
            n=added + updated, new=added, upd=updated, tot=len(store))
        if guessed:
            msg += "\n" + self.tr("A game was found for {n} videos.").format(n=guessed)
        messagebox.showinfo(self.tr("Import"), msg)

    def update_game_hint(self):
        """The line under 'Game being played' in the Analysis tab: what the statistics say for this game."""
        lbl, panel = getattr(self, "game_hint", None), getattr(self, "stats_panel", None)
        if lbl is None or panel is None:
            return
        T, game = self.tr, self.vars["game"].get().strip()
        if not panel.store:
            lbl.configure(text=T("Tip: import your YouTube data in the Stats tab to get hashtags that worked for you."))
            return
        best = hs.best(panel.store, game)
        if not best:
            lbl.configure(text=T("Statistics: not enough data yet for hashtag tips."))
            return
        shown = " ".join(best[:6]) + (f" (+{len(best) - 6})" if len(best) > 6 else "")
        auto = T("used automatically") if self.vars["auto_tags"].get() else T("not used automatically - see the Stats tab")
        lbl.configure(text=T("Strong hashtags from your statistics:") + f" {shown}\n({auto})")
