"""Stream Clip Detector - main window (settings, language, results). The layout itself is in gui_layout.py.
Files: gui_config.py = constants and defaults | gui_layout.py = window layout | gui_widgets.py = form helpers |
gui_runner.py = start/stop of the analysis | brand.py = colors and styles | clip_detector.py = the engine.
Run: python clip_gui.py   (needs: pip install customtkinter pillow)"""
import os
import sys
import json
import queue
import traceback
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except ImportError:
    _r = tk.Tk()
    _r.withdraw()
    messagebox.showerror("Missing library", "Run in a terminal:\n\npip install customtkinter")
    sys.exit(1)

import exports
from brand import ACCENT
from gui_config import CFG, DATA, DEFAULTS, DEVICES, FORMATS, LANGS, MODELS, NUM
from gui_layout import LayoutMixin
from gui_widgets import Blocks, Tip
from gui_strings import CS, tr as tr_text
from gui_runner import RunnerMixin
from gui_source import SourceMixin


class App(LayoutMixin, Blocks, RunnerMixin, SourceMixin, ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("Stream Clip Detector")
        self.geometry("1100x860")
        self.minsize(1000, 700)
        self.q, self.proc = queue.Queue(), None
        self.running = self.cancel = False
        self.status_text, self.t0, self.last_out, self.bar_det = "Ready", 0, 0, False
        self.updaters, self.en_text = [], {}
        self.measure_result, self.measuring = None, False
        self.clips_dirty, self.clips_loaded, self.clips_dir = True, False, ""
        self.finished_run = False
        cfg = dict(DEFAULTS)
        try:
            with open(CFG, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
        V = self.vars = {}
        for k in ("video", "url", "out", "secret", "llm_model", "game", "extra_tags", "audio_track", "clips_view"):
            V[k] = tk.StringVar(value=str(cfg[k]))
        for k in NUM:
            try:
                V[k] = tk.DoubleVar(value=float(cfg[k]))
            except Exception:
                V[k] = tk.DoubleVar(value=float(DEFAULTS[k]))
        for k in ("whisper", "cut", "loud_on", "llm_on", "ai_scan", "save_transcript", "save_info", "reuse_transcript", "out_beside"):
            V[k] = tk.BooleanVar(value=bool(cfg[k]))
        pick = lambda d, v, default: next((n for n, c in d.items() if c == v), default)
        self.model_name = tk.StringVar(value=pick(MODELS, cfg["model"], "Balanced"))
        self.lang_name = tk.StringVar(value=pick(LANGS, cfg["lang"], "English"))
        self.fmt_name = tk.StringVar(value=pick(FORMATS, cfg["clip_format"], "MP4"))
        self.dev_name = tk.StringVar(value=pick(DEVICES, cfg["device"], "Auto (GPU if available)"))
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.lang = cfg["ui_lang"]
        self.ui_lang_var = tk.StringVar(value="Čeština" if self.lang == "cs" else "English")
        self.init_source(cfg)
        self.build(cfg)
        self.setup_source()
        self.apply_language(self.lang)
        self.after(250, self.poll)

    # ---------- helpers ----------
    def words(self, key):
        return [w.strip() for w in self.kwbox[key].get("1.0", "end").splitlines() if w.strip()]

    def count_kw(self):
        c = [len(self.words(k)) for k in ("kw_en", "kw_cs", "kw_strong")]
        self.kw_info.configure(text=f"English: {c[0]} · Other: {c[1]} · Strong: {c[2]}   (one per line)")

    def pick_video(self):
        p = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mkv *.flv *.mov *.ts"), ("All", "*.*")])
        if p:
            self.vars["video"].set(p)

    def pick_clips_folder(self):
        """Clips tab: load the clips (with their info files) of any folder."""
        p = filedialog.askdirectory(initialdir=self.vars["out"].get() or None)
        if p:
            self.save_items()  # the folder we are leaving
            self.vars["out"].set(p)
            self.load_clips()

    def pick_out(self):
        p = filedialog.askdirectory()
        if p:
            self.vars["out"].set(p)

    def open_out(self):
        d = self.vars["out"].get()
        os.makedirs(d, exist_ok=True)
        try:
            os.startfile(d)
        except Exception:
            pass

    def collect(self):
        v = self.vars
        i = lambda k: str(int(round(v[k].get())))
        return {
            "video": v["video"].get().strip(), "url": v["url"].get().strip(), "out": v["out"].get().strip(), "out_beside": v["out_beside"].get(),
            "top": i("top"), "before": i("before"), "after": i("after"), "gap": i("gap"),
            "threshold": f"{v['threshold'].get():.1f}", "loud_db": i("loud_db"), "loud_on": v["loud_on"].get(),
            "model": MODELS[self.model_name.get()], "lang": LANGS[self.lang_name.get()],
            "device": DEVICES[self.dev_name.get()], "whisper": v["whisper"].get(), "cut": v["cut"].get(),
            "save_transcript": v["save_transcript"].get(), "save_info": v["save_info"].get(),
            "reuse_transcript": v["reuse_transcript"].get(), "clip_format": FORMATS[self.fmt_name.get()],
            "clips_view": v["clips_view"].get(),
            "secret": v["secret"].get().strip(), "secret_back": i("secret_back"),
            "audio_track": v["audio_track"].get(), "tag_pool": i("tag_pool"),
            "ui_lang": self.lang, "game": v["game"].get().strip(), "extra_tags": v["extra_tags"].get().strip(),
            "llm_on": v["llm_on"].get(), "ai_scan": v["ai_scan"].get(), "llm_model": v["llm_model"].get().strip(), "min_funny": i("min_funny"),
            **{k: "\n".join(self.words(k)) for k in ("kw_en", "kw_cs", "kw_strong")},
        }

    def save_cfg(self, cfg=None):
        cfg = dict(cfg or self.collect())
        if self.beside_on:  # keep the user's own folder, not the one derived from the video
            cfg["out"] = self.out_custom
        try:
            with open(CFG, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def save(self):
        self.save_cfg()
        self.save_btn.configure(text="✓  Saved")
        self.after(1500, lambda: self.save_btn.configure(text=self.tr("Save")))

    def tr(self, s):
        return tr_text(s, self.lang)

    def apply_language(self, lang):
        """Swap visible texts by lookup (English text is the key); tooltips follow through Tip.lang."""
        Tip.lang = self.lang = lang

        def walk(w):
            yield w
            for ch in w.winfo_children():
                yield from walk(ch)

        for w in walk(self):
            if w is self.btn or w is self.status or not isinstance(w, ctk.CTkBaseClass):
                continue
            try:
                cur = w.cget("text")
            except Exception:
                continue
            en = self.en_text.setdefault(str(w), cur)
            if en in CS:
                w.configure(text=tr_text(en, lang))
        for show in getattr(self, "choices", []):  # dropdown lists in the new language
            show()
        self.sync_source()  # the hint under the source fields
        self.set_run_button(self.running)
        if not self.running:
            self.status.configure(text=self.tr("Ready"))
        names = [self.tr("Analysis"), self.tr("Clips")]
        self.view_seg.configure(values=names)
        self.view_seg.set(names[1 if self.view_name == "Clips" else 0])
        self.clips_panel.relabel()
        if self.view_name == "Clips":
            self.clips_panel.refresh(self.clips_panel.items)
        else:
            self.clips_dirty = True  # rebuilt in the new language when the tab is opened
        self.render_models()

    def set_lang(self, choice):
        self.apply_language("cs" if choice == "Čeština" else "en")
        self.save_cfg()

    def reset_all(self):
        if not messagebox.askyesno(self.tr("Reset"), self.tr("Reset all settings to their defaults? Your keyword lists, "
                                   "file paths, secret word and AI model name stay as they are.")):
            return
        for k in NUM:
            self.vars[k].set(float(DEFAULTS[k]))
        for k in ("whisper", "cut", "loud_on", "llm_on", "ai_scan", "save_transcript", "save_info", "reuse_transcript"):
            self.vars[k].set(DEFAULTS[k])
        first = lambda d, v: next(n for n, c in d.items() if c == v)
        self.model_name.set(first(MODELS, DEFAULTS["model"]))
        self.lang_name.set(first(LANGS, DEFAULTS["lang"]))
        self.dev_name.set(first(DEVICES, DEFAULTS["device"]))
        self.fmt_name.set(first(FORMATS, DEFAULTS["clip_format"]))
        for u in self.updaters:
            u()

    def show_results(self):
        T = self.tr
        tb, hms = self.results, lambda t: f"{int(t) // 3600}:{int(t) % 3600 // 60:02d}:{int(t) % 60:02d}"
        tb.delete("1.0", "end")
        try:
            with open(os.path.join(self.vars["out"].get(), "results.json"), encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            tb.insert("end", T("No results found.") + "\n")
            return
        tb.tag_config("link", foreground=ACCENT, underline=True)

        def link(text, action):
            tag = f"lk{len(tb.get('1.0', 'end'))}"
            tb.insert("end", text, ("link", tag))
            tb.tag_bind(tag, "<Button-1>", lambda e: action())
            tb.insert("end", "   ")

        if not items:
            tb.insert("end", T("No clips found. Try a lower Strictness or Minimum loudness jump.") + "\n")
        for i, it in enumerate(items, 1):
            tb.insert("end", f"#{i}   {hms(it['start'])} - {hms(it['end'])}   score {it['score']}\n")
            tb.insert("end", f"{T('Why picked:')} {it['why']}\n")
            a = it.get("ai")
            if a:
                tb.insert("end", f"{T('AI rating:')} {a['funny']:g}/10 - {a['why']}\n")
                if a.get("moment") is not None:
                    tb.insert("end", f"{T('Funniest moment:')} {hms(a['moment'])}\n")
                if a.get("evidence"):
                    mark = "✔" if a.get("evidence_ok") else T("⚠ not found in the transcript - the AI may be wrong")
                    tb.insert("end", f"{T('Evidence:')} \"{a['evidence']}\" {mark}\n")
                tb.insert("end", f"{T('Title:')} {a['title']}\n{T('Hashtags:')} {' '.join(a['hashtags'])}\n"
                                 f"{T('Meme/GIF ideas:')} ")
                for m in it.get("links", []):
                    tb.insert("end", f"\"{m['term']}\" ")
                    link("[GIPHY]", lambda u=m["giphy"]: webbrowser.open(u))
                    link("[YouTube]", lambda u=m["youtube"]: webbrowser.open(u))
                tb.insert("end", "\n")
            tb.insert("end", f"{T('Transcript:')} {it['text']}\n")
            if it.get("file"):
                link(T("▶ open clip"), lambda p=it["file"]: os.startfile(p))
            tb.insert("end", "\n\n")
        self.tabs.set("Results")

    def load_clips(self, switch=False, quiet=False):
        """Read results.json and finished.json from the output folder into the Clips tab.
        Favorites and typed edits of clips that are still in the list are kept."""
        old = {}
        if self.clips_loaded:
            self.clips_panel.collect()
            old = {(it.get("_src"), it.get("file"), it.get("start")): it for it in self.clips_panel.items}
        out, items = self.vars["out"].get(), []
        for name in ("results.json", "finished.json"):
            try:
                with open(os.path.join(out, name), encoding="utf-8") as f:
                    for d in json.load(f):
                        d["_src"] = name
                        items.append(d)
            except Exception:
                pass
        items += exports.scan_folder(out, [d.get("file") for d in items])  # clips (and their info files) in the folder
        for d in items:
            prev = old.get((d["_src"], d.get("file"), d.get("start")))
            if prev:
                d["favorite"] = prev.get("favorite", d.get("favorite"))
                # Edits belong to the AI texts they were made on. A new analysis of the same clip (same name and
                # start) brings new AI texts - old edits, often just the empty texts of a run without AI, would hide them.
                if prev.get("edits") and prev.get("ai") == d.get("ai"):
                    d["edits"] = prev["edits"]
        self.clips_dirty = False
        if switch and quiet and not items:  # a run that found nothing: stay where we are
            return
        self.clips_dir = out
        self.clips_panel.refresh(items)
        self.clips_loaded = True
        if switch:
            self.set_view("Clips")

    def save_items(self):
        """Write favorites and edited texts back to results.json / finished.json (in the folder they were loaded from)."""
        if not self.clips_loaded:
            return
        self.clips_panel.collect()
        for name in ("results.json", "finished.json"):
            path = os.path.join(self.clips_dir, name)
            mine = [{k: v for k, v in it.items() if k != "_src"} for it in self.clips_panel.items if it.get("_src") == name]
            if mine or os.path.exists(path):
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(mine, f, ensure_ascii=False, indent=2)
                except OSError:
                    pass
        for it in self.clips_panel.items:  # keep the *_info.txt files in step with the edited texts
            if (it.get("edits") or it.get("favorite")) and it.get("file"):
                exports.sync_info(it, self.clips_dir)

    def show_clips(self, quiet=False):
        self.load_clips(switch=True, quiet=quiet)

    def on_close(self):
        self.save_cfg()
        self.save_items()
        self.kill()
        self.destroy()


def main():
    if os.name == "nt":  # own taskbar entry and icon instead of the "Python" one
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FubarXS.StreamClipDetector")
        except Exception:
            pass
    try:
        App().mainloop()
    except Exception:
        err = traceback.format_exc()
        with open(os.path.join(DATA, "crash_log.txt"), "w", encoding="utf-8") as f:
            f.write(err)
        messagebox.showerror("Stream Clip Detector crashed", err[-1500:] + "\n\n(Also saved to crash_log.txt)")


if __name__ == "__main__":
    main()
