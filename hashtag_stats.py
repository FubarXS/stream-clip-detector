"""Hashtag insights: reads the CSV export of your YouTube Shorts and ranks the hashtags by the views of the videos
that used them. Plain Python, no window code.
Honest limit: it compares videos that had a hashtag with videos that did not. That shows what goes together with
more views; it does not prove that the hashtag caused them."""
import csv
import json
import os
import re
import statistics

MIN_AGE_DAYS = 3  # younger videos are still collecting views
MIN_SIDE = 3      # a hashtag needs this many videos WITH it and this many WITHOUT it before it is compared
MIN_VIDEOS = 15   # below this the ranking is only a preliminary hint
HASHTAG = re.compile(r"#[^\W_]\w*")


def _num(s):
    s = str(s or "").replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def tags_of(*texts):
    """Hashtags of the given texts: lowercase, no duplicates, in order of appearance."""
    out = []
    for t in HASHTAG.findall(" ".join(x or "" for x in texts)):
        if t.lower() not in out:
            out.append(t.lower())
    return out


def parse_csv(path):
    """Videos of one export file. Raises ValueError when the file is not the YouTube export."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        head = f.readline()
        f.seek(0)
        rows = list(csv.DictReader(f, delimiter=";" if head.count(";") >= head.count(",") else ","))
    if not rows or "video_id" not in rows[0] or "zhlednuti" not in rows[0]:
        raise ValueError("not the YouTube export")
    videos = []
    for r in rows:
        vid, views = (r.get("video_id") or "").strip(), _num(r.get("zhlednuti"))
        if vid and views is not None:
            videos.append({"id": vid, "title": (r.get("nazev") or "").strip(), "views": views,
                           "age_days": _num(r.get("stari_dni")),
                           "tags": tags_of(r.get("hashtagy_nazev"), r.get("hashtagy_popis") or r.get("popis"), r.get("nazev"))})
    return videos


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)["videos"]
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def save(path, store):
    """Written only after the new content is complete (temp file, then replace)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"videos": store}, f, ensure_ascii=False)
    os.replace(tmp, path)


def merge(store, videos):
    """Adds the videos to the store; a video that is already there is replaced (the newest import wins)."""
    added = sum(v["id"] not in store for v in videos)
    for v in videos:
        store[v["id"]] = v
    return added, len(videos) - added


def rank(store, top=60):
    """(rows, info). Rows: hashtag, number of videos, median views with it, and how many times higher that is
    than the median of the videos without it. Only hashtags that can be compared (MIN_SIDE on both sides)."""
    vids = [(v["views"], set(v["tags"])) for v in store.values() if (v.get("age_days") or 0) >= MIN_AGE_DAYS]
    info = {"total": len(store), "used": len(vids)}
    rows = []
    for t in {t for _, tags in vids for t in tags}:
        w = [views for views, tags in vids if t in tags]
        wo = [views for views, tags in vids if t not in tags]
        if len(w) >= MIN_SIDE and len(wo) >= MIN_SIDE:
            m = statistics.median(w)
            rows.append({"tag": t, "n": len(w), "median": m, "lift": m / max(statistics.median(wo), 1)})
    rows.sort(key=lambda r: (-r["lift"], -r["n"], r["tag"]))
    return rows[:top], info
