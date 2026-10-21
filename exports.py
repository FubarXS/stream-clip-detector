"""Extra outputs: clip thumbnails, subtitles and posts files (title, description and hashtags ready to copy)."""
import os
import subprocess


def hms(t):
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"


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
