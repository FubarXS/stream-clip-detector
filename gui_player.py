"""Small player inside the app for the clip previews. No extra Python packages: ffmpeg (already needed by the
program) decodes the pictures, ffplay (comes with ffmpeg) plays the sound. Without ffplay the clip plays muted;
without Pillow or ffmpeg the clip opens in the system player instead."""
import os
import queue
import shutil
import subprocess
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from brand import BG, MUTED, BTN2, SLIDER, Image, ImageTk, window_icon
from gui_config import NOWIN

SIZES = [(480, 270), (720, 405), (1024, 576)]  # picture size: small / medium / large
FPS = 30
LAG = 0.35  # seconds the sound needs to start; the picture waits for it


def duration_of(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                           capture_output=True, text=True, timeout=8, creationflags=NOWIN)
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def open_external(path):
    try:
        os.startfile(path)
    except AttributeError:
        webbrowser.open("file://" + path)


def open_player(master, it, T):
    """Opens the clip in the in-app player (one at a time); falls back to the system player."""
    path = it.get("file")
    if not path or not os.path.exists(path):
        messagebox.showinfo(T("No clip file"), T("This clip was not cut (the option 'Cut video clips' was off)."))
        return
    if ImageTk is None or not shutil.which("ffmpeg"):
        open_external(path)
        return
    old = getattr(master, "_player", None)
    if old is not None and old.winfo_exists():
        old.close()
    master._player = Player(master, path, it["end"] - it["start"] if it.get("kind") != "finished" else 0, T)


class Player(ctk.CTkToplevel):
    def __init__(self, master, path, fallback_duration, T):
        super().__init__(master, fg_color=BG)
        self.path, self.T, self.size_i = path, T, 1
        self.title(os.path.basename(path))
        window_icon(self)
        self.resizable(False, False)
        self.dur = duration_of(path) or fallback_duration
        self.ffplay = shutil.which("ffplay")
        self.gen, self.q, self.procs = 0, queue.Queue(), []
        self.pos = self.start_pos = 0.0
        self.shown, self.t0, self.playing, self.dragging = 0, 0.0, False, False
        self.screen = tk.Label(self, bg="black", bd=0)
        self.screen.pack(padx=10, pady=(10, 6))
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=(0, 4))
        self.play_btn = ctk.CTkButton(bar, text="⏸", width=44, height=30, command=self.toggle, **BTN2)
        self.play_btn.pack(side="left")
        self.slider = ctk.CTkSlider(bar, from_=0, to=max(self.dur, 1), **SLIDER)
        self.slider.set(0)
        self.slider.pack(side="left", fill="x", expand=True, padx=10)
        self.slider.bind("<ButtonPress-1>", lambda e: setattr(self, "dragging", True))
        self.slider.bind("<ButtonRelease-1>", self.seek)
        self.time_lbl = ctk.CTkLabel(bar, text="0:00", text_color=MUTED, width=84)
        self.time_lbl.pack(side="left")
        ctk.CTkButton(bar, text="⤢", width=36, height=30, command=self.resize, **BTN2).pack(side="left", padx=(6, 0))
        ctk.CTkButton(bar, text=T("Open in system player"), width=170, height=30, command=lambda: open_external(path),
                      **BTN2).pack(side="left", padx=(6, 0))
        if not self.ffplay:
            ctk.CTkLabel(self, text=T("No sound: ffplay (part of the ffmpeg download) was not found."), text_color=MUTED,
                         font=ctk.CTkFont(size=11)).pack(anchor="w", padx=12, pady=(0, 8))
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.show_blank()
        self.after(100, self.lift)
        self.start_at(0.0)
        self.tick()

    # ---------- playback ----------
    def stop_procs(self):
        for p in self.procs:
            try:
                p.kill()
            except Exception:
                pass
        self.procs = []

    def start_at(self, t):
        """(Re)start picture and sound at second t."""
        self.stop_procs()
        self.gen += 1
        self.q = queue.Queue(maxsize=FPS)
        self.pos = self.start_pos = max(0.0, t)
        self.shown, self.playing = 0, True
        self.t0 = time.time() + LAG
        self.play_btn.configure(text="⏸")
        if self.ffplay:
            try:
                self.procs.append(subprocess.Popen([self.ffplay, "-v", "quiet", "-nodisp", "-vn", "-autoexit", "-ss", f"{self.pos:.2f}", self.path],
                                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                                   stderr=subprocess.DEVNULL, creationflags=NOWIN))
            except OSError:
                pass
        threading.Thread(target=self.reader, args=(self.gen, self.q, self.pos, SIZES[self.size_i]), daemon=True).start()

    def reader(self, gen, q, t, size):
        """Thread: decode raw pictures with ffmpeg and queue them (the queue is small, so ffmpeg waits for us)."""
        w, h = size
        vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"
        try:
            p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", self.path, "-an", "-vf", vf, "-r", str(FPS),
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, creationflags=NOWIN)
        except OSError:
            q.put((gen, None))
            return
        self.procs.append(p)
        n = w * h * 3
        while gen == self.gen:
            buf = p.stdout.read(n)
            if len(buf) < n:
                break
            while gen == self.gen:
                try:
                    q.put((gen, buf), timeout=0.2)
                    break
                except queue.Full:
                    pass
        if gen == self.gen:
            q.put((gen, None))
        try:
            p.kill()
        except Exception:
            pass

    def show_blank(self):
        w, h = SIZES[self.size_i]
        self.show(bytes(w * h * 3))

    def show(self, buf):
        img = ImageTk.PhotoImage(Image.frombytes("RGB", SIZES[self.size_i], buf))
        self.screen.configure(image=img)
        self.screen.image = img

    def tick(self):
        if self.playing and time.time() >= self.t0:
            due, frame = int((time.time() - self.t0) * FPS), None
            while self.shown <= due:  # take every picture that is due; late ones are skipped
                try:
                    g, buf = self.q.get_nowait()
                except queue.Empty:
                    break
                if g != self.gen:
                    continue
                if buf is None:
                    self.finish()
                    break
                self.shown += 1
                frame = buf
            if frame is not None and self.playing:
                self.show(frame)
                self.pos = self.start_pos + self.shown / FPS
                if not self.dragging:
                    self.slider.set(min(self.pos, max(self.dur, 1)))
                self.time_lbl.configure(text=f"{self.clock(self.pos)} / {self.clock(self.dur)}")
        self._job = self.after(10, self.tick)

    @staticmethod
    def clock(t):
        return f"{int(t) // 60}:{int(t) % 60:02d}"

    def finish(self):
        self.stop_procs()
        self.playing = False
        self.play_btn.configure(text="↻")
        self.pos = 0.0

    # ---------- controls ----------
    def toggle(self):
        if self.playing:
            self.stop_procs()
            self.gen += 1
            self.playing = False
            self.play_btn.configure(text="▶")
        else:
            self.start_at(self.pos)

    def seek(self, _event=None):
        self.dragging = False
        self.start_at(self.slider.get())

    def resize(self):
        self.size_i = (self.size_i + 1) % len(SIZES)
        self.show_blank()
        self.start_at(self.pos)

    def close(self):
        self.gen += 1
        self.stop_procs()
        try:
            self.after_cancel(self._job)
        except Exception:
            pass
        self.destroy()
