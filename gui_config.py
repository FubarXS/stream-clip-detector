"""Constants and default settings used by the GUI (edit colors, defaults, option lists here)."""
import os
import sys
import subprocess

import keywords  # default keyword lists (light module: the window does not need numpy)

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "gui_settings.json")
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LOWPRI = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)  # keeps the PC responsive
PY = sys.executable
if PY.lower().endswith("pythonw.exe"):
    PY = PY[:-5] + ".exe"

MODELS = {"Fast": "small", "Balanced": "medium", "Accurate": "large-v3"}
LANGS = {"English": "en", "Czech": "cs", "Slovak": "sk", "German": "de", "Spanish": "es", "Polish": "pl",
         "Auto-detect": "auto", "Mixed (experimental)": "mix"}
DEVICES = {"Auto (GPU if available)": "auto", "GPU (NVIDIA)": "cuda", "CPU": "cpu"}
NUM = ("top", "before", "after", "gap", "threshold", "secret_back", "loud_db", "min_funny", "tag_pool")
DEFAULTS = {
    "video": "", "url": "", "out": os.path.join(HERE, "clips"),
    "top": "15", "before": "20", "after": "10", "gap": "60", "threshold": "3.0", "loud_db": "6",
    "model": "medium", "lang": "en", "device": "auto", "whisper": True, "cut": True, "loud_on": True,
    "secret": "clip that", "secret_back": "45", "audio_track": "1",
    "ui_lang": "en", "game": "", "extra_tags": "", "llm_on": False, "llm_model": "gemma3:12b", "min_funny": "5", "tag_pool": "50",
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
    "tag_pool": "50 gives you a big list to choose from in the General tab. The platform tabs use only the recommended number anyway.",
}
