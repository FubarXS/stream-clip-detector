"""Constants and default settings used by the GUI (edit colors, defaults, option lists here)."""
import os
import shutil
import sys
import subprocess

import keywords  # default keyword lists (light module: the window does not need numpy)

FROZEN = getattr(sys, "frozen", False)  # True in the packaged .exe
HERE = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))  # the program, ffmpeg, default clips


def _data_dir():
    """Where settings, run files and the crash log live. The packaged app keeps them in %APPDATA%\\StreamClipDetector,
    because every release unpacks into a NEW folder and settings next to the .exe would start from the defaults again
    (for example the AI switch is off by default). Running from the source files keeps them next to the code."""
    if FROZEN and os.name == "nt" and os.environ.get("APPDATA"):
        d = os.path.join(os.environ["APPDATA"], "StreamClipDetector")
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except OSError:
            pass
    return HERE


DATA = _data_dir()
CFG = os.path.join(DATA, "gui_settings.json")
_OLD = os.path.join(HERE, "gui_settings.json")  # where versions up to 0.5.1 kept it
if DATA != HERE and not os.path.exists(CFG) and os.path.exists(_OLD):
    try:
        shutil.copy2(_OLD, CFG)  # first start after the move: take over the settings from next to the .exe
    except OSError:
        pass
_FF = os.path.join(HERE, "ffmpeg")  # a bundled ffmpeg folder (ffmpeg, ffprobe, ffplay) is used before the system one
if os.path.isdir(_FF):
    os.environ["PATH"] = _FF + os.pathsep + os.environ.get("PATH", "")
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LOWPRI = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)  # keeps the PC responsive
PY = sys.executable
if PY.lower().endswith("pythonw.exe"):
    PY = PY[:-5] + ".exe"


def worker_cmd(module, *args):
    """Command line that runs a helper module (clip_detector, analyze_finished, yt_dlp) in its own process."""
    if FROZEN:  # the .exe starts itself again in helper mode (see app_main.py)
        return [sys.executable, "--worker", module, *args]
    return [PY, "-m", module, *args] if module == "yt_dlp" else [PY, "-u", os.path.join(HERE, module + ".py"), *args]

MODELS = {"Fast": "small", "Balanced": "medium", "Accurate": "large-v3"}
LANGS = {"English": "en", "Czech": "cs", "Slovak": "sk", "German": "de", "Spanish": "es", "Polish": "pl",
         "Auto-detect": "auto", "Mixed (experimental)": "mix"}
FORMATS = {"MP4": "mp4", "MOV (DaVinci Resolve)": "mov", "MKV (like OBS)": "mkv"}
DEVICES = {"Auto (GPU if available)": "auto", "GPU (NVIDIA)": "cuda", "CPU": "cpu"}
NUM = ("top", "before", "after", "gap", "threshold", "secret_back", "loud_db", "min_funny", "tag_pool")
DEFAULTS = {
    "video": "", "url": "", "out": os.path.join(HERE, "clips"), "out_beside": False,
    "top": "15", "before": "20", "after": "10", "gap": "60", "threshold": "3.0", "loud_db": "6",
    "model": "medium", "lang": "en", "device": "auto", "whisper": True, "cut": True, "loud_on": True,
    "save_transcript": True, "save_info": True, "reuse_transcript": True,
    "clip_format": "mp4", "clips_view": "list",
    "secret": "clip that", "secret_back": "45", "audio_track": "1",
    "ui_lang": "en", "game": "", "extra_tags": "", "proven_tags": "", "llm_on": False, "ai_scan": False, "llm_model": "gemma3:12b", "min_funny": "5", "tag_pool": "50",
    "kw_en": "\n".join(keywords.KEYWORDS_EN), "kw_cs": "\n".join(keywords.KEYWORDS_CS), "kw_strong": "",
}

# Why each default is what it is (shown in the (i) tooltip next to the reset arrow)
WHY = {
    "top": "15 gives you enough clips to choose from without drowning in them.",
    "threshold": "3.0 means a moment needs a clear signal (about +15 dB louder than usual, or trigger words). Lower values mostly add noise.",
    "before": "20 s usually covers the build-up to a reaction.",
    "after": "10 s covers the reaction itself; longer clips tend to drag.",
    "gap": "60 s avoids picking the same moment twice.",
    "secret_back": "45 s is long enough to include whatever just happened before you said the phrase.",
    "loud_db": "6 dB is where a sound is clearly louder than normal speech level; lower picks up ordinary variation.",
    "min_funny": "5/10 keeps clips the AI finds at least moderately funny.",
    "tag_pool": "50 gives you a big list to choose from in the General tab. TikTok and Reels use 5 of them, YouTube Shorts up to 30.",
}
