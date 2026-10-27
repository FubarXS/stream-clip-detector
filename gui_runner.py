"""Starting/stopping the analysis in a separate process, streaming its output, status line."""
import os
import re
import json
import time
import queue
import threading
import subprocess
import traceback
from tkinter import filedialog, messagebox

from gui_dialogs import ask_text

from gui_config import NOWIN, LOWPRI, DATA, HERE, worker_cmd


VIDEO_EXT = (".mp4", ".mkv", ".ts", ".flv", ".mov")
MEASURE_TEXT = ("Typical level {typical} dB. About 90% of the time you stay within +{p90} dB of that; your loudest 1% "
                "goes above +{p99} dB (loudest +{max} dB). Suggested minimum jump: {suggest} dB. The log lists your "
                "loudest moments - listen to them to check it was you and not the game.")


class RunnerMixin:
    """Mixin with start / stop / exec / worker / poll."""
    # ---------- running ----------
    def start(self, measure=False, finished=None):
        cfg = self.collect()
        if not finished and not cfg["video"] and not cfg["url"]:
            messagebox.showwarning("No source", "Pick a video file or paste a Twitch VOD link.")
            return
        if not finished and cfg["video"] and cfg["url"]:
            messagebox.showwarning(self.tr("Two sources"), self.tr("Both a file and a link are filled in. Clear one of them."))
            return
        self.save_cfg(cfg)
        self.cancel, self.running, self.t0, self.status_text = False, True, time.time(), "Starting..."
        self.last_out = time.time()
        self.measuring, self.finished_run = measure, bool(finished)
        self.set_run_button(True)
        self.log.delete("1.0", "end")
        self.tabs.set("Log")
        self.prog.configure(mode="indeterminate")
        self.prog.start()
        self.bar_det = False
        threading.Thread(target=self.worker, args=(cfg, measure, finished), daemon=True).start()

    def kill(self):
        p = self.proc
        if p and p.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], creationflags=NOWIN, capture_output=True)
                else:
                    p.kill()
            except Exception:
                pass

    def stop(self):
        self.cancel = True
        self.status_text = "Stopping..."
        self.kill()

    def exec(self, cmd):
        """Run a command, stream its output; progress lines go to the status bar, not the log."""
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", HF_HUB_DISABLE_SYMLINKS_WARNING="1")
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     encoding="utf-8", errors="replace", env=env, cwd=HERE, creationflags=NOWIN | LOWPRI)
        for line in self.proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            if line.startswith("@@MEASURE "):
                self.q.put(("measure", line[10:]))
            elif line.startswith("@@"):
                self.q.put(("status", line[2:]))
            elif "%|" in line or line.startswith("[download]"):
                self.q.put(("status", "Downloading model/video... " + line[:60]))
            else:
                if re.match(r"\[\d/4\]", line):
                    self.q.put(("status", line))
                self.q.put(("log", line + "\n"))
        return self.proc.wait()

    @staticmethod
    def save_flags(cfg):
        """Switches for the info file, transcript files and the transcript cache."""
        return (["--no-info-files"] if not cfg["save_info"] else []) + \
               (["--no-transcript-files"] if not cfg["save_transcript"] else []) + \
               (["--no-transcript-cache"] if not cfg["reuse_transcript"] else [])

    def worker(self, cfg, measure=False, finished=None):
        try:
            if finished:
                self.exec([*worker_cmd("analyze_finished"), *finished, "--model", cfg["model"],
                           "--lang", cfg["lang"], "--device", cfg["device"], "--llm", cfg["llm_model"],
                           "--game", cfg["game"], "--extra-tags", cfg["extra_tags"], "--tag-pool", cfg["tag_pool"],
                           "--out", cfg["out"], *self.save_flags(cfg)])
                return
            video = cfg["video"]
            if cfg["url"]:
                dl = os.path.join(cfg["out"], "downloads")
                os.makedirs(dl, exist_ok=True)
                vid = re.search(r"videos/(\d+)", cfg["url"])
                have = [os.path.join(dl, f) for f in os.listdir(dl) if vid and vid.group(1) in f and f.lower().endswith(VIDEO_EXT)]
                if have:  # downloaded before (for example by the loudness measurement): do not download again
                    video = max(have, key=os.path.getmtime)
                    self.q.put(("log", f"VOD already downloaded - using {os.path.basename(video)}\n"))
                else:
                    self.q.put(("log", "Downloading VOD...\n"))
                    rc = self.exec([*worker_cmd("yt_dlp"), "--newline", "--no-warnings", "-N", "4", "-o",
                                    os.path.join(dl, "%(id)s.%(ext)s"), "--progress-template",
                                    "download:@@Downloading VOD %(progress._percent_str)s  %(progress._speed_str)s  "
                                    "ETA %(progress._eta_str)s", cfg["url"]])
                    files = [os.path.join(dl, f) for f in os.listdir(dl) if f.lower().endswith(VIDEO_EXT)]
                    if self.cancel or rc != 0 or not files:
                        self.q.put(("log", "Download failed or cancelled.\n"))
                        return
                    video = max(files, key=os.path.getmtime)
            if measure:
                self.exec([*worker_cmd("clip_detector"), video, "--measure", "--loud-db", cfg["loud_db"],
                           "--audio-track", cfg["audio_track"]])
                return
            conf = os.path.join(DATA, "run_config.json")
            kd = lambda t: [k.strip().lower() for k in t.splitlines() if k.strip()]
            with open(conf, "w", encoding="utf-8") as f:
                json.dump({"keywords": kd(cfg["kw_en"]) + kd(cfg["kw_cs"]), "strong": kd(cfg["kw_strong"])}, f)
            cmd = [*worker_cmd("clip_detector"), video, "--top", cfg["top"],
                   "--before", cfg["before"], "--after", cfg["after"], "--min-gap", cfg["gap"],
                   "--threshold", cfg["threshold"], "--model", cfg["model"], "--lang", cfg["lang"],
                   "--device", cfg["device"], "--loud-db", cfg["loud_db"], "--audio-track", cfg["audio_track"], "--config", conf, "--out", cfg["out"]]
            if cfg["secret"]:
                cmd += ["--secret", cfg["secret"], "--secret-back", cfg["secret_back"]]
            if not (cfg["llm_on"] and cfg["llm_model"]):  # the most common reason for clips without titles and hashtags
                self.q.put(("log", self.tr("AI suggestions are OFF - clips get no titles or hashtags. "
                                           "Turn on 'Rate clips, suggest hashtags and memes' in the Analysis tab.") + "\n"))
            if cfg["llm_on"] and cfg["llm_model"]:
                cmd += ["--llm", cfg["llm_model"], "--min-funny", cfg["min_funny"], "--tag-pool", cfg["tag_pool"]]
                if cfg["game"]:
                    cmd += ["--game", cfg["game"]]
                if cfg["extra_tags"]:
                    cmd += ["--extra-tags", cfg["extra_tags"]]
            if not cfg["loud_on"]:
                cmd.append("--no-loudness")
            if not cfg["whisper"]:
                cmd.append("--no-whisper")
            if not cfg["cut"]:
                cmd.append("--no-cut")
            cmd += ["--format", cfg["clip_format"]]
            cmd += self.save_flags(cfg)
            if self.exec(cmd) != 0 and not self.cancel:
                self.q.put(("log", "\nThe analysis stopped with an error (see above).\n"))
        except Exception:
            self.q.put(("log", traceback.format_exc()))
        finally:
            self.q.put(("done", ""))

    def set_run_button(self, running):
        if running:
            self.btn.set_mode("stop", self.tr("■  Stop"), self.stop)
        else:
            self.btn.set_mode("start", self.tr("▶  Start analysis"), self.start)

    def add_finished(self):
        if self.running:
            messagebox.showinfo(self.tr("Busy"), self.tr("An analysis is already running. Wait for it to finish or press Stop."))
            return
        files = filedialog.askopenfilenames(parent=self,
                                            filetypes=[("Video", "*.mp4 *.mkv *.mov *.webm"), ("All", "*.*")])
        if not files:
            return
        game = ask_text(self, self.tr("Which game?"), self.tr("Which game are these clips from? It is used for the game "
                        "hashtags. Leave it empty if you do not want game hashtags."), self.vars["game"].get(),
                        ok=self.tr("OK"), cancel=self.tr("Cancel"))
        if game is None:
            return
        self.vars["game"].set(game)
        self.start(finished=list(files))

    def measure(self):
        self.start(measure=True)

    def show_measure(self):
        self.measure_lbl.configure(text=self.tr(MEASURE_TEXT).format(**self.measure_result))
        self.apply_btn.configure(state="normal")

    def use_suggestion(self):
        if self.measure_result:
            self.vars["loud_db"].set(self.measure_result["suggest"])
            for u in self.updaters:
                u()

    def poll(self):
        logs, done = [], False
        try:
            while True:
                kind, text = self.q.get_nowait()
                self.last_out = time.time()
                if kind == "log":
                    logs.append(text)
                elif kind == "status":
                    self.status_text = text
                elif kind == "models":
                    self.models_data = text
                    self.render_models()
                elif kind == "measure":
                    self.measure_result = json.loads(text)
                    self.show_measure()
                else:
                    done = True
        except queue.Empty:
            pass
        if logs:
            self.log.insert("end", "".join(logs))
            if int(self.log.index("end-1c").split(".")[0]) > 1500:
                self.log.delete("1.0", "500.0")
            self.log.see("end")
        m = re.search(r"(\d+(?:\.\d+)?)%", self.status_text) if self.running and not done else None
        if m:  # real progress bar when the status line has a percentage
            if not self.bar_det:
                self.prog.stop()
                self.prog.configure(mode="determinate")
                self.bar_det = True
            self.prog.set(min(1.0, float(m.group(1)) / 100))
        elif self.running and self.bar_det:
            self.prog.configure(mode="indeterminate")
            self.prog.start()
            self.bar_det = False
        if done:
            self.running = False
            self.prog.stop()
            self.prog.configure(mode="determinate")
            self.prog.set(0)
            self.bar_det = False
            self.set_run_button(False)
            self.status.configure(text=self.tr("Cancelled.") if self.cancel else self.tr("Measurement finished. See the Log.") if self.measuring else self.tr("Finished clips analyzed. See the Clips window.") if self.finished_run else self.tr("Finished. See the Results tab."))
            if not self.cancel and not self.measuring:
                if not self.finished_run:
                    self.show_results()
                self.show_clips(quiet=True)
        elif self.running:
            el = int(time.time() - self.t0)
            idle = int(time.time() - self.last_out)
            warn = f"   ·   no new output for {idle // 60} min (long files can be quiet; press Stop if it stays that way)" if idle > 120 else ""
            self.status.configure(text=f"{self.status_text}   ·   elapsed {el // 60}:{el % 60:02d}{warn}")
        self.after(250, self.poll)
