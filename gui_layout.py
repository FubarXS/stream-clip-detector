"""The main window layout. Colors and widget styles come from brand.py."""
import threading
import webbrowser
import customtkinter as ctk

from brand import (BG, PANEL_BORDER, BORDER, BORDER_H, TEXT, MUTED, DIM, ACCENT, RADIUS_LG, KOFI_URL, VERSION,
                   BTN2, OPTION, COMBO, ENTRY, BOX, SEG, TABS, SWITCH, SLIDER, BrandButton, image, window_icon)
from gui_clips import ClipsPanel
from gui_config import MODELS, LANGS, DEVICES
import ollama_models


class LayoutMixin:
    """Mixin: builds the whole window."""

    def build(self, cfg):
        self.configure(fg_color=BG)
        window_icon(self)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.build_header()
        self.left = left = ctk.CTkScrollableFrame(self, width=430, fg_color="transparent", scrollbar_button_color=BORDER,
                                      scrollbar_button_hover_color=BORDER_H)
        left.grid(row=1, column=0, sticky="ns", padx=(14, 6))
        self.build_left(left)
        self.right = right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 14))
        self.build_right(right, cfg)
        self.clips_panel = ClipsPanel(self, self)
        self.build_bar()
        self.build_footer()

    def set_view(self, name):
        """Switch between the Analysis tab and the Clips tab (inside this one window)."""
        self.view_name = name
        if name == "Clips":
            if self.clips_dirty:  # the cards are built only when the tab is opened (faster start)
                self.load_clips()
            self.left.grid_remove()
            self.right.grid_remove()
            self.clips_panel.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=14)
        else:
            self.clips_panel.grid_remove()
            self.left.grid()
            self.right.grid()
        self.view_seg.set(self.tr(name))

    def show_view(self, choice):
        self.set_view(("Analysis", "Clips")[self.view_seg.cget("values").index(choice)])

    def refresh_models(self):
        """Ask Ollama and the GPU in a background thread (nvidia-smi can take seconds); poll() shows the answer."""
        def work():
            if not hasattr(self, "_vram"):
                self._vram = ollama_models.gpu_gb()
            self.q.put(("models", (ollama_models.installed(), self._vram)))
        threading.Thread(target=work, daemon=True).start()

    def render_models(self):
        T, data = self.tr, getattr(self, "models_data", None)
        if data is None:
            return
        models, vram = data
        if models is None:
            self.models_lbl.configure(text=T("Ollama is not running or not installed. Start it, then press Refresh."))
            return
        if not models:
            self.models_lbl.configure(text=T("No models installed yet. In a terminal run: ollama pull <model name>"))
            return
        self.model_combo.configure(values=[n for n, _ in models])
        txt = T("Installed:") + " " + ", ".join(f"{n} ({s:.1f} GB){'*' if vram and s > vram * 0.85 else ''}" for n, s in models)
        if vram:
            txt += f"\n{T('GPU memory')}: {vram:.0f} GB. " + T("* = probably too large for your GPU memory (much slower).")
        self.models_lbl.configure(text=txt)

    def build_header(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 8))
        top = ctk.CTkFrame(head, fg_color="transparent")
        top.pack(anchor="w")
        icon = image("icon128.png", (38, 38))
        if icon:
            ctk.CTkLabel(top, text="", image=icon).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(top, text="Stream Clip Detector", text_color=TEXT,
                     font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkLabel(head, text="Finds the best moments in your stream recordings. Free and runs on your PC.",
                     text_color=MUTED).pack(anchor="w", pady=(2, 0))
        self.view_name = "Analysis"
        self.view_seg = ctk.CTkSegmentedButton(head, values=[self.tr("Analysis"), self.tr("Clips")], command=self.show_view,
                                               height=34, **SEG)
        self.view_seg.set(self.tr("Analysis"))
        self.view_seg.pack(anchor="w", pady=(10, 0))
        ctk.CTkOptionMenu(head, values=["English", "Čeština"], variable=self.ui_lang_var, width=110,
                          command=self.set_lang, **OPTION).place(relx=1.0, rely=0.0, anchor="ne")
        ctk.CTkButton(head, text="↺ Reset all", width=100, height=28, command=self.reset_all,
                      **BTN2).place(relx=1.0, x=-122, rely=0.0, anchor="ne")

    def build_left(self, left):
        src = self.card(left, "Source & output")
        self.entry(src, "Recording (video file)", "video", self.pick_video, "A recording of your stream (.mp4, .mkv, ...).")
        self.entry(src, "...or Twitch VOD link", "url", None,
                   "Paste a VOD link and it will be downloaded first. Only use content you have the rights to.")
        self.entry(src, "Save clips to", "out", self.pick_out, "Folder where the clips and clips.txt are saved.")

        sel = self.card(left, "Clip selection")
        self.slider(sel, "Max clips", "top", 3, 50, 1, "The N best moments are kept.")
        self.slider(sel, "Strictness", "threshold", 1.5, 6.0, 0.1,
                    "Lower = more clips (also weaker ones). Higher = only the most striking moments.", dec=1)
        self.slider(sel, "Seconds before peak", "before", 5, 60, 1, "How much lead-up is included in each clip.", " s")
        self.slider(sel, "Seconds after peak", "after", 5, 60, 1, "How much is included after the moment.", " s")
        self.slider(sel, "Min. gap between clips", "gap", 20, 300, 5, "Prevents several clips of the same moment.", " s")
        ctk.CTkSwitch(sel, text="Cut video clips (off = timestamps only)", variable=self.vars["cut"],
                      **SWITCH).pack(anchor="w", padx=16, pady=(10, 0))
        ctk.CTkSwitch(sel, text="Save an info file next to each clip", variable=self.vars["save_info"],
                      **SWITCH).pack(anchor="w", padx=16, pady=(8, 0))
        ctk.CTkSwitch(sel, text="Save transcript files (.txt, .srt)", variable=self.vars["save_transcript"],
                      **SWITCH).pack(anchor="w", padx=16, pady=(8, 14))

        sig = self.card(left, "Detection signals")
        self.option(sig, "Audio track for analysis",
                    "Recordings from OBS can contain several audio tracks. Track 1 is usually everything mixed (game, music "
                    "and voice). If your microphone is on its own track (for example track 2), choose it: loudness and "
                    "speech are then measured from your voice only, which usually gives much better clips. A Twitch VOD "
                    "normally has only one track.", self.vars["audio_track"], ["1", "2", "3", "4", "5", "6"])
        ctk.CTkSwitch(sig, text="Loudness detection (shouting, laughing)", variable=self.vars["loud_on"],
                      **SWITCH).pack(anchor="w", padx=16, pady=(8, 0))
        self.slider(sig, "Minimum loudness jump", "loud_db", 3, 20, 1,
                    "A moment counts as a loud spike only if it is at least this many dB louder than your normal "
                    "level over the last 3 minutes. Roughly: +6 dB = clearly louder, +10 dB = sounds about twice as "
                    "loud, +15 dB or more = shouting. Lower = more sensitive. After a run the log shows the loudest "
                    "spike found, which helps you tune this.", " dB")
        self.lab(sig, "Measure my loudness",
                 "Analyzes the loudness of the selected recording and shows how loud your normal voice is compared "
                 "with your loudest moments, so you can match the setting to your microphone. Tip: pick a recording "
                 "that contains some of your yelps. Takes a minute or two for a long video.")
        btns = ctk.CTkFrame(sig, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(2, 2))
        self.measure_btn = ctk.CTkButton(btns, text="Measure", width=110, height=30, command=self.measure, **BTN2)
        self.measure_btn.pack(side="left")
        self.apply_btn = ctk.CTkButton(btns, text="Use suggestion", width=130, height=30, state="disabled",
                                       command=self.use_suggestion, **BTN2)
        self.apply_btn.pack(side="left", padx=(8, 0))
        self.measure_lbl = ctk.CTkLabel(sig, text="", text_color=MUTED, font=ctk.CTkFont(size=11), justify="left",
                                        wraplength=380, anchor="w")
        self.measure_lbl.pack(anchor="w", padx=16, pady=(4, 6))
        ctk.CTkSwitch(sig, text="Speech detection (trigger words)", variable=self.vars["whisper"],
                      **SWITCH).pack(anchor="w", padx=16, pady=(10, 4))
        self.lab(sig, "Transcription quality",
                 "The model is the 'brain' that turns speech into text. Bigger = more accurate but slower and "
                 "needs more memory (Accurate needs about 5 GB of GPU memory).")
        ctk.CTkSegmentedButton(sig, values=list(MODELS), variable=self.model_name, **SEG).pack(fill="x", padx=16, pady=(2, 4))
        self.option(sig, "Speech language", "The language you mostly speak. 'Mixed' tries to detect the language "
                    "of every sentence - experimental, switch back if the text looks odd.", self.lang_name, LANGS)
        self.option(sig, "Processor", "GPU (NVIDIA) is much faster. If the GPU fails or you have none, choose CPU "
                    "- slower but works everywhere.", self.dev_name, DEVICES)
        ctk.CTkSwitch(sig, text="Reuse the saved transcript of this video", variable=self.vars["reuse_transcript"],
                      **SWITCH).pack(anchor="w", padx=16, pady=(8, 0))
        ctk.CTkFrame(sig, height=10, fg_color="transparent").pack()

        ai = self.card(left, "AI suggestions (optional)",
                       "Uses a free AI that runs on your PC (Ollama, ollama.com) to rate how funny each candidate is, "
                       "explain why, and suggest a title, hashtags and meme/GIF ideas. Install Ollama, then run once in "
                       "a terminal:  ollama pull <model name>.  Nothing is sent online.")
        ctk.CTkSwitch(ai, text="Rate clips, suggest hashtags and memes", variable=self.vars["llm_on"],
                      **SWITCH).pack(anchor="w", padx=16, pady=(8, 4))
        self.lab(ai, "Ollama model name",
                 "Any model you installed with 'ollama pull' (see 'ollama list'). All Ollama models are free to download; "
                 "the limit is your GPU memory - bigger models understand humor better but are slower, and models larger "
                 "than your GPU memory are much slower.")
        mrow = ctk.CTkFrame(ai, fg_color="transparent")
        mrow.pack(fill="x", padx=16, pady=(2, 2))
        self.model_combo = ctk.CTkComboBox(mrow, variable=self.vars["llm_model"], height=32,
                                           values=[self.vars["llm_model"].get() or "gemma3:12b"], **COMBO)
        self.model_combo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(mrow, text="Refresh", width=80, height=32, command=self.refresh_models, **BTN2).pack(side="left", padx=(8, 0))
        self.models_lbl = ctk.CTkLabel(ai, text="", text_color=MUTED, font=ctk.CTkFont(size=11), justify="left",
                                       wraplength=380, anchor="w")
        self.models_lbl.pack(anchor="w", padx=16, pady=(2, 4))
        self.after(700, self.refresh_models)
        self.entry(ai, "Game being played", "game", None,
                   "The game in this recording, e.g. Project Zomboid. The AI adds hashtags for the game, its genre "
                   "and its community.")
        self.entry(ai, "Always add these hashtags", "extra_tags", None,
                   "Your own hashtags for every clip, e.g. #yourchannel. Separate with spaces. They are added at the "
                   "end of the list.")
        self.slider(ai, "Minimum funny rating", "min_funny", 1, 9, 1,
                    "Only clips the AI rates at least this high (out of 10) are kept. With AI on, a wider pool of "
                    "candidates is checked than normal.")
        self.slider(ai, "Hashtag pool size", "tag_pool", 15, 50, 5,
                    "How many hashtags the AI collects in the General tab - a big list to pick from. TikTok, YouTube Shorts "
                    "and Reels use far fewer (more hashtags do not add reach there).")
        ctk.CTkFrame(ai, height=8, fg_color="transparent").pack()

    def build_right(self, right, cfg):
        sec = self.card(right, "Secret word", "Say this phrase right after something great happens. A clip is "
                        "ALWAYS created, covering the seconds before you said it. Leave empty to disable.")
        sec.pack_configure(pady=(0, 10))
        ctk.CTkEntry(sec, textvariable=self.vars["secret"], **ENTRY).pack(fill="x", padx=16, pady=(4, 0))
        self.slider(sec, "Seconds to look back", "secret_back", 10, 120, 5, "How much footage before the phrase is saved.", " s")
        ctk.CTkFrame(sec, height=6, fg_color="transparent").pack()

        kw = self.card(right, "Trigger words", "When you say one of these, that moment gets a bonus. One word or "
                       "phrase per line. 'Strong' words give a much bigger bonus. Click Save to keep changes.")
        tabs = ctk.CTkTabview(kw, height=150, **TABS)
        tabs.pack(fill="x", padx=16, pady=(4, 0))
        self.kwbox = {}
        for key, name in (("kw_en", "English"), ("kw_cs", "Other language"), ("kw_strong", "Strong")):
            box = ctk.CTkTextbox(tabs.add(name), height=90, **BOX)
            box.pack(fill="both", expand=True)
            box.insert("1.0", cfg[key])
            box.bind("<KeyRelease>", lambda e: self.count_kw())
            self.kwbox[key] = box
        self.kw_info = ctk.CTkLabel(kw, text="", text_color=MUTED, font=ctk.CTkFont(size=11), anchor="w")
        self.kw_info.pack(anchor="w", padx=16, pady=(4, 12))
        self.count_kw()

        self.tabs = ctk.CTkTabview(right, border_width=1, border_color=PANEL_BORDER, corner_radius=RADIUS_LG, **TABS)
        self.tabs.pack(fill="both", expand=True)
        mono = ctk.CTkFont(family="Consolas", size=12)
        self.log = ctk.CTkTextbox(self.tabs.add("Log"), font=mono, **BOX)
        self.log.pack(fill="both", expand=True)
        self.results = ctk.CTkTextbox(self.tabs.add("Results"), font=mono, wrap="word", **BOX)
        self.results.pack(fill="both", expand=True)
        self.log.insert("end", "Ready. Pick a recording and press Start.\n")
        self.results.insert("end", "Clip suggestions (why picked, AI rating, hashtags, meme ideas) appear here.\n")

    def build_bar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(8, 8))
        bar.grid_columnconfigure(0, weight=1)
        mid = ctk.CTkFrame(bar, fg_color="transparent")
        mid.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        self.status = ctk.CTkLabel(mid, text="Ready", anchor="w", text_color=TEXT)
        self.status.pack(fill="x")
        self.prog = ctk.CTkProgressBar(mid, mode="determinate", progress_color=ACCENT, fg_color=BORDER)
        self.prog.pack(fill="x", pady=(6, 0))
        self.prog.set(0)
        self.save_btn = ctk.CTkButton(bar, text="Save", width=110, height=42, command=self.save, **BTN2)
        self.save_btn.grid(row=0, column=1, padx=(0, 10))
        ctk.CTkButton(bar, text="Open folder", width=120, height=42, command=self.open_out, **BTN2).grid(
            row=0, column=2, padx=(0, 10))
        self.btn = BrandButton(bar, "▶  Start analysis", self.start)
        self.btn.grid(row=0, column=4)

    def build_footer(self):
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))
        ctk.CTkFrame(foot, height=1, fg_color=PANEL_BORDER).pack(fill="x", pady=(0, 8))
        row = ctk.CTkFrame(foot, fg_color="transparent")
        row.pack(fill="x")
        img, img_h = image("kofi.png", (14, 14)), image("kofi_hover.png", (14, 14))
        kofi = ctk.CTkLabel(row, text="Enjoying the app? Support it on Ko-fi", image=img, compound="left",
                            text_color=MUTED, font=ctk.CTkFont(size=11), cursor="hand2")
        kofi.pack(side="left")

        def look(color, im):
            kofi.configure(text_color=color)
            if im:
                kofi.configure(image=im)

        kofi.bind("<Enter>", lambda e: look(TEXT, img_h))
        kofi.bind("<Leave>", lambda e: look(MUTED, img))
        kofi.bind("<Button-1>", lambda e: webbrowser.open(KOFI_URL))
        ctk.CTkLabel(row, text=f"v{VERSION}", text_color=DIM, font=ctk.CTkFont(family="Consolas", size=10)).pack(side="right")
