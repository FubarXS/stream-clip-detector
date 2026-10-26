"""Remembers the speech transcript of a recording so a second analysis can skip the slow Whisper step.
Stored in <out>/cache/. The cache is only used when video (path, size, date), audio track, model,
language and secret word are the same; changed keywords don't matter (they are applied afterwards)."""
import os
import json
import hashlib


def _path(out, video, extra):
    st = os.stat(video)
    raw = "|".join([os.path.abspath(video), str(st.st_size), str(int(st.st_mtime))] + [str(e) for e in extra])
    return os.path.join(out, "cache", "transcript_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16] + ".json")


def load(out, video, extra):
    """Saved segments (start, end, text, words) or None when there is nothing usable."""
    try:
        with open(_path(out, video, extra), encoding="utf-8") as f:
            data = json.load(f)
        segs = [(s[0], s[1], s[2], [tuple(w) for w in s[3]]) for s in data["segments"]]
        return segs or None  # an empty transcript is a failed run, not a result: transcribe again
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None


def save(out, video, extra, segments):
    if not segments:
        return
    try:
        path = _path(out, video, extra)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"segments": segments}, f, ensure_ascii=False)
        os.replace(tmp, path)  # a half-written file can never be mistaken for a transcript
    except OSError as e:
        print(f"  (could not save the transcript cache: {e})", flush=True)


def get_or_run(out, video, extra, run, reuse=True):
    """The transcript from the cache, or run() and remember its result."""
    if reuse:
        segs = load(out, video, extra)
        if segs is not None:
            print("  Using the saved transcript from the earlier analysis (speech step skipped).", flush=True)
            return segs
    segs = run()
    save(out, video, extra, segs)
    return segs
