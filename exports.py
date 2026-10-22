"""Extra outputs: clip thumbnails, subtitles and posts files (title, description and hashtags ready to copy)."""
import os
import re
import subprocess

VIDEO_EXT = (".mp4", ".mov", ".mkv")


def hms(t):
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"


def cut(video, start, end, out_path):
    """Cut [start, end] without re-encoding. -map keeps the video plus ALL audio tracks (OBS multitrack 1-6).
    If the chosen container refuses the codecs (for example Opus audio in .mov), the audio is converted to AAC."""
    base = ["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-i", video, "-t", str(end - start), "-map", "0:v:0", "-map", "0:a?"]
    r = subprocess.run(base + ["-c", "copy", out_path], capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        r = subprocess.run(base + ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out_path], capture_output=True,
                           text=True, errors="replace")
    if r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, "ffmpeg", stderr=(r.stderr or "")[-300:])


def make_thumb(video, t, path):
    """One still frame from the video at time t (seconds), as PNG. Returns the path, or '' on failure."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    err = ""
    for seek in (["-ss", str(int(t))], []):  # second try without seeking (very short files)
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", *seek, "-i", video, "-frames:v", "1", "-vf", "scale=320:-2", path],
                           capture_output=True, text=True, errors="replace")
        if r.returncode == 0 and os.path.exists(path):
            return path
        err = (r.stderr or "").strip()[-200:]
    print(f"   Thumbnail failed for {os.path.basename(video)}: {err}", flush=True)
    return ""


def write_srt(segments, path):
    def t(x):
        ms = int(x * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(path, "w", encoding="utf-8") as f:
        for i, s in enumerate(segments, 1):
            f.write(f"{i}\n{t(s[0])} --> {t(s[1])}\n{s[2]}\n\n")


def info_path(it, out):
    """Where the info file of a clip lives: next to the clip (clip_04_0-46-03.mp4 -> clip_04_0-46-03_info.txt);
    finished clips (your own files) get theirs in <out>/finished/."""
    stem = os.path.splitext(os.path.basename(it.get("file") or "clip"))[0]
    folder = os.path.join(out, "finished") if it.get("kind") == "finished" else os.path.dirname(it.get("file") or out)
    return os.path.join(folder, stem + "_info.txt")


def own_files(it, out):
    """Files we created for a clip besides the video and thumbnail: its info file (and the .srt of a finished clip)."""
    files = [info_path(it, out)]
    if it.get("kind") == "finished":
        files.append(os.path.join(out, "finished", os.path.splitext(os.path.basename(it.get("file") or ""))[0] + ".srt"))
    return files


def write_info(it, path, include_transcript=True):
    """Text file with everything used for a clip: time, why, AI notes, title, description, hashtags, transcript.
    Texts edited in the Clips window (it['edits']['General']) win over the AI originals."""
    a = it.get("ai") or {}
    g = (it.get("edits") or {}).get("General") or {}
    title = g.get("title", a.get("title", ""))
    desc = g.get("description", a.get("description") or a.get("why", ""))
    tags = g.get("hashtags", " ".join(a.get("hashtags", [])))
    rows = [f"Clip: {os.path.basename(it.get('file') or '(not cut)')}",
            f"Time: {hms(it['start'])} - {hms(it['end'])} (peak {hms(it['peak'])})", f"Score: {it['score']}",
            f"Why picked: {it['why']}"]
    if it.get("favorite"):
        rows.append("Favorite: yes")
    if a:
        rows.append(f"AI funny rating: {a.get('funny', 0):g}/10 - {a.get('why', '')}")
    rows += ["", f"Title: {title}", f"Description: {desc}", f"Hashtags: {tags}"]
    if include_transcript:
        rows += ["", "Transcript:", it.get("lines") or it.get("text") or ""]
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:  # content is ready before the file is opened
            f.write("\n".join(rows) + "\n")
    except OSError as e:
        print(f"   Could not write {os.path.basename(path)}: {e}", flush=True)


def _secs(text):
    return sum(int(v) * 60 ** i for i, v in enumerate(reversed(text.split(":"))))


def read_info(path, clip_path):
    """Rebuilds a clip item from its *_info.txt (the format of write_info). None if the file cannot be read."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    head, _, tr = text.partition("\nTranscript:\n")
    one = lambda name: (re.search(rf"^{name}: (.*)$", head, re.M) or [None, ""])[1].strip()
    block = lambda name, nxt: ((re.search(rf"^{name}: (.*?)(?=^{nxt}:|\Z)", head, re.S | re.M) or [None, ""])[1]).strip()
    t = re.search(r"(\d+:\d\d:\d\d) - (\d+:\d\d:\d\d)(?: \(peak (\d+:\d\d:\d\d)\))?", one("Time"))
    start, end = (_secs(t[1]), _secs(t[2])) if t else (0, 0)
    peak = _secs(t[3]) if t and t[3] else start
    title, desc, tags = block("Title", "Description"), block("Description", "Hashtags"), block("Hashtags", "Transcript")
    name = os.path.basename(clip_path)
    stem = os.path.splitext(name)[0]
    thumb = os.path.join(os.path.dirname(clip_path), "thumbs", stem + ".png")
    lines = tr.strip()
    it = {"kind": "marker" if name.startswith("marker_") else "clip", "file": clip_path, "start": start, "end": end,
          "peak": peak, "score": float(one("Score") or 0) if re.match(r"^[\d.]+$", one("Score")) else 0,
          "why": one("Why picked"), "lines": lines, "links": [], "hint": "", "ai": None,
          "text": " ".join(re.sub(r"^\[[\d:]+\] ", "", ln) for ln in lines.splitlines()),
          "thumb": thumb if os.path.exists(thumb) else "", "favorite": one("Favorite") == "yes",
          "edits": {"General": {"title": title, "description": desc, "hashtags": tags}}}
    m = re.match(r"([\d.]+)/10 - (.*)", one("AI funny rating"))
    if m:
        it["ai"] = {"funny": float(m[1]), "why": m[2], "title": title, "description": desc, "hashtags": tags.split(),
                    "moment": None, "evidence": "", "evidence_ok": True, "meme_terms": []}
    return it


def scan_folder(out, known):
    """Clips in the output folder (clip_01_... / marker_01_... videos) that no results file mentions,
    with the texts from their *_info.txt. 'known' = file paths already loaded from results.json / finished.json."""
    try:
        names = sorted(os.listdir(out))
    except OSError:
        return []
    # compare file NAMES: results.json may store the path differently (relative / other working folder) than the window sees it
    seen = {os.path.normcase(os.path.basename(k)) for k in known if k}
    found = []
    for n in names:
        stem, ext = os.path.splitext(n)
        m = re.match(r"(?:clip|marker)_\d+_(\d+)-(\d\d)-(\d\d)$", stem)
        path = os.path.join(out, n)
        if ext.lower() not in VIDEO_EXT or not m or os.path.normcase(n) in seen:
            continue
        it = read_info(os.path.join(out, stem + "_info.txt"), path)
        if not it:  # no info file: the clip name still tells the time of the peak
            peak = _secs(":".join(m.groups()))
            thumb = os.path.join(out, "thumbs", stem + ".png")
            it = {"kind": "marker" if n.startswith("marker_") else "clip", "file": path, "start": peak, "end": peak,
                  "peak": peak, "score": 0, "why": "found in the folder (no info file)", "text": "", "lines": "",
                  "links": [], "hint": "", "ai": None, "thumb": thumb if os.path.exists(thumb) else ""}
        it["_src"] = "folder"
        found.append(it)
    return found


def sync_info(it, out):
    """After editing in the Clips window: refresh an info file that already exists (keeps its transcript choice)."""
    path = info_path(it, out)
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            had = "\nTranscript:\n" in f.read()
    except OSError:
        return
    write_info(it, path, had)


def write_posts(items, out, name="posts.txt"):
    """For every clip: title, description, hashtags (top 5 / top 10 / all) and a section per platform."""
    from platforms import PLATFORMS, post_text
    blocks = []
    for i, it in enumerate(items, 1):
        a = it.get("ai") or {}
        tags, title = a.get("hashtags", []), a.get("title", "")
        desc = a.get("description") or a.get("why", "")
        post = "\n\n".join(x for x in (title, desc, " ".join(tags)) if x)
        b = [f"=== CLIP {i}  |  {hms(it['start'])} - {hms(it['end'])}  |  {os.path.basename(it.get('file') or '(not cut)')} ===",
             f"TITLE: {title}", f"DESCRIPTION: {desc}",
             f"HASHTAGS (top 5):  {' '.join(tags[:5])}", f"HASHTAGS (top 10): {' '.join(tags[:10])}",
             f"HASHTAGS (all):    {' '.join(tags)}", "", "FULL POST (copy this):", post]
        for key, p in (a.get("platforms") or {}).items():
            b += ["", f"--- {PLATFORMS[key]['label']} ({len(p['hashtags'])} hashtags) - copy this ---", post_text(p)]
        blocks.append("\n".join(b))
    with open(os.path.join(out, name), "w", encoding="utf-8") as f:
        f.write("\n\n\n".join(blocks) + "\n")
