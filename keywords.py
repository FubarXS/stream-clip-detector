"""Default trigger words. A tiny module on purpose: the window needs them but must not import numpy."""
KEYWORDS_CS = [
    "co to bylo", "ne ne ne", "jé", "páni", "wow", "wtf", "no way",
    "do prdele", "do píči", "sakra", "to není možný", "to jako", "konečně",
    "gg", "clutch", "vyhráli jsme", "vyhrál", "prohrál", "umřel", "jo!",
    "pomoc", "fakt", "neee", "ježíš", "hahaha", "to snad ne",
]

KEYWORDS_EN = [
    "yeah baby", "let's go", "lets go", "oh my god", "holy shit", "no way",
    "what the fuck", "bruh", "oh no", "six seven", "let him cook",
]
KEYWORDS = KEYWORDS_CS + KEYWORDS_EN
EXTRA_SIGNALS = []  # plug-in point: functions (video, n_seconds, args) -> per-second score array. Chat activity can go here later.
STRONG_KEYWORDS = []  # strong words: much bigger bonus
