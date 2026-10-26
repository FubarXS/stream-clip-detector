"""Source & output rules of the main window:
- only ONE source at a time (a video file or a Twitch link): once one is filled in, the other field is locked,
- 'Save clips next to the recording': the clips go into a folder named after the video, beside it."""
import os

from brand import TEXT, DIM


def beside_dir(video):
    """<video folder>/<video name>_clips - one folder per recording, so results.json of different streams never mix."""
    stem = os.path.splitext(os.path.basename(video))[0]
    return os.path.join(os.path.dirname(video), stem + "_clips")


class SourceMixin:
    """Mixin for the App: call init_source(cfg) before building the window and setup_source() after it."""

    def init_source(self, cfg):
        self.out_custom, self.beside_on = cfg["out"], False  # the folder typed by the user / is 'next to video' active

    def setup_source(self):
        for k in ("video", "url", "out_beside"):
            self.vars[k].trace_add("write", self.sync_source)
        self.sync_source()

    def lock_field(self, key, locked):
        entry, buttons = self.fields[key]
        entry.configure(state="disabled" if locked else "normal", text_color=DIM if locked else TEXT)
        for b in buttons:
            b.configure(state="disabled" if locked else "normal")

    def sync_source(self, *_):
        """Called when the video, the link or the 'next to the recording' switch changes (and when the language changes)."""
        V = self.vars
        video, url = V["video"].get().strip(), V["url"].get().strip()
        # exactly one filled in -> lock the other. (Both filled, e.g. from old settings: leave both open so one can be cleared.)
        self.lock_field("video", bool(url) and not video)
        self.lock_field("url", bool(video) and not url)
        hint = ("Only one source is used. Clear the Twitch link to pick a file." if url and not video else
                "Only one source is used. Clear the recording file to use a Twitch link." if video and not url else
                "Both a file and a link are filled in. Clear one of them." if video and url else "")
        self.source_hint.configure(text=self.tr(hint))
        # output folder
        active = bool(V["out_beside"].get() and video and not url)
        if active and not self.beside_on:
            self.out_custom = V["out"].get()  # remember the user's own folder
        if active:
            V["out"].set(beside_dir(video))
        elif self.beside_on:
            V["out"].set(self.out_custom)
        self.beside_on = active
        self.lock_field("out", active)
        self.beside_sw.configure(state="disabled" if url and not video else "normal")
