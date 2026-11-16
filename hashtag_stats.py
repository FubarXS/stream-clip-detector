"""Hashtag insights: reads the CSV export of your YouTube Shorts and ranks the hashtags by the views of the videos
that used them. Plain Python, no window code.
Honest limit: it compares videos that had a hashtag with videos that did not. That shows what goes together with
more views; it does not prove that the hashtag caused them."""
import csv
import datetime
import json
import os
import re
import statistics
from collections import Counter

MIN_AGE_DAYS = 3  # younger videos are still collecting views
MIN_SIDE = 3      # a hashtag needs this many videos WITH it and this many WITHOUT it before it is compared
MIN_VIDEOS = 15   # below this the ranking is only a preliminary hint
TAG_GAME_SHARE = 0.8  # a hashtag counts as a game hashtag when this share of its videos belong to one game
HASHTAG = re.compile(r"#[^\W_]\w*")
SOURCES = ("feed", "search", "browse", "hashtag")  # where the views come from (percent columns of the export)
LENGTHS = ((15, "Up to 15 s"), (30, "16-30 s"), (60, "31-60 s"), (None, "Over 60 s"))


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
            src = ({k: _num(r.get(f"zdroj_{n}_pct")) for k, n in zip(SOURCES, ("shorts_feed", "vyhledavani", "prochazeni", "hashtagy"))}
                   if (r.get("zdroje_nactene") or "").strip().lower() == "ano" else None)
            videos.append({"id": vid, "title": (r.get("nazev") or "").strip(), "views": views,
                           "age_days": _num(r.get("stari_dni")), "published": (r.get("datum_publikace") or "").strip(),
                           "length": _num(r.get("delka_s")), "src": src,
                           "tags": tags_of(r.get("hashtagy_nazev"), r.get("hashtagy_popis") or r.get("popis"), r.get("nazev"))})
    return videos


def load_all(path):
    """(videos, meta). meta: 'games' (game names the user used) and 'last_import' (date). Empty when there is no file."""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        meta = {"games": [g for g in d.get("games", []) if isinstance(g, str)], "last_import": str(d.get("last_import", ""))}
        return d["videos"], meta
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}, {"games": [], "last_import": ""}


def load(path):
    return load_all(path)[0]


def save(path, store, meta=None):
    """Written only after the new content is complete (temp file, then replace). meta=None keeps the saved meta."""
    meta = meta if meta is not None else load_all(path)[1]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"videos": store, "games": meta.get("games", []), "last_import": meta.get("last_import", "")}, f,
                  ensure_ascii=False)
    os.replace(tmp, path)


def merge(store, videos):
    """Adds the videos to the store; a video that is already there is replaced (the newest import wins),
    but the game the user gave it is kept."""
    added = sum(v["id"] not in store for v in videos)
    for v in videos:
        old = store.get(v["id"])
        if old and old.get("game"):
            v["game"] = old["game"]
        store[v["id"]] = v
    return added, len(videos) - added


# ---------- games ----------
def norm(s):
    """Game names and hashtags compared without case, spaces and punctuation."""
    return re.sub(r"[\W_]+", "", (s or "").casefold())


def known_games(store, meta, extra=()):
    """The games the user has given so far (saved list, games of the videos, extra names), without duplicates."""
    out, seen = [], set()
    for g in [*meta.get("games", []), *(v.get("game") for v in store.values()), *extra]:
        g = (g or "").strip()
        if g and norm(g) not in seen:
            seen.add(norm(g))
            out.append(g)
    return out


def guess_game(video, games):
    """The game whose name (or its first part, 'World of Warcraft' of 'World of Warcraft: Forever') appears in the title
    or hashtags of the video; '' when none does. The longest match wins."""
    text = norm(video.get("title")) + "|" + "|".join(norm(t) for t in video.get("tags", []))
    best, best_len = "", 0
    for g in games:
        full = norm(g)
        names = {full, norm(re.split(r"[:|(\u2013\u2014-]", g)[0])}
        hit = max([len(n) for n in names if len(n) >= 4 and n in text]
                  + [len(norm(t)) for t in video.get("tags", []) if len(norm(t)) >= 6 and norm(t) in full], default=0)
        if hit > best_len:
            best, best_len = g, hit
    return best


def tag_games(store):
    """hashtag -> game, for the hashtags that belong to one game: at least TAG_GAME_SHARE of the videos that use them
    belong to it (MIN_SIDE videos at least), while MIN_SIDE or more other videos exist that could have used it too
    (videos without a game count as other videos). With only one game and no other videos nothing is marked."""
    vids = list(store.values())
    in_game = Counter(norm(v.get("game")) for v in vids if v.get("game"))
    used = {}
    for v in vids:
        for t in v.get("tags", []):
            used.setdefault(t, []).append(v.get("game") or "")
    out = {}
    for t, gs in used.items():
        c = Counter(norm(g) for g in gs if g)
        if not c:
            continue
        top, n = c.most_common(1)[0]
        if len(gs) >= MIN_SIDE and n / len(gs) >= TAG_GAME_SHARE and len(vids) - in_game[top] >= MIN_SIDE:
            out[t] = next(g for g in gs if norm(g) == top)
    return out


def _videos(store, game=None):
    """Videos old enough to count; only the ones of one game when 'game' is given."""
    key = norm(game) if game else None
    return [v for v in store.values() if (v.get("age_days") or 0) >= MIN_AGE_DAYS and (key is None or norm(v.get("game")) == key)]


def rank(store, game=None, top=60):
    """(rows, info). Rows: hashtag, number of videos, median views with it, how many times higher that is than the median of
    the videos without it, and the game it belongs to ('' = general). Only hashtags that can be compared (MIN_SIDE on both
    sides). game=None uses all videos, otherwise only the videos of that game."""
    vids = [(v["views"], set(v["tags"])) for v in _videos(store, game)]
    info = {"total": len(store) if not game else sum(norm(v.get("game")) == norm(game) for v in store.values()),
            "used": len(vids)}
    tg, rows = tag_games(store), []
    for t in {t for _, tags in vids for t in tags}:
        w = [views for views, tags in vids if t in tags]
        wo = [views for views, tags in vids if t not in tags]
        if len(w) >= MIN_SIDE and len(wo) >= MIN_SIDE:
            m = statistics.median(w)
            rows.append({"tag": t, "n": len(w), "median": m, "lift": m / max(statistics.median(wo), 1), "game": tg.get(t, "")})
    rows.sort(key=lambda r: (-r["lift"], -r["n"], r["tag"]))
    return rows[:top], info


def best(store, game="", limit=20):
    """The hashtags to use: the strong ones of this game first, then the strong general ones. Game hashtags of OTHER
    games are left out. Without a game only the general ones."""
    own = [r["tag"] for r in rank(store, game)[0] if r["lift"] > 1] if game else []
    general = [r["tag"] for r in rank(store)[0] if r["lift"] > 1 and not r["game"]]
    out = []
    for t in own + general:
        if t not in out:
            out.append(t)
    return out[:limit]


def overview(store):
    """What else the export tells: where the views come from, which weekday and which length did better.
    Every part is left out when there are not enough videos for it."""
    vids, res = _videos(store), {}
    src = [v for v in vids if v.get("src") and v.get("views")]
    total = sum(v["views"] for v in src)
    if src and total > 0:
        res["sources"] = {k: sum(v["views"] * (v["src"].get(k) or 0) for v in src) / total for k in SOURCES}
        res["sources_n"] = len(src)
    days, lens = {}, {}
    for v in vids:
        try:
            days.setdefault(datetime.date.fromisoformat(v.get("published", "")).weekday(), []).append(v["views"])
        except ValueError:
            pass
        if v.get("length"):
            lab = next(name for top, name in LENGTHS if top is None or v["length"] <= top)
            lens.setdefault(lab, []).append(v["views"])
    res["weekdays"] = sorted(((d, statistics.median(x), len(x)) for d, x in days.items() if len(x) >= MIN_SIDE), key=lambda r: -r[1])
    res["lengths"] = [(n, statistics.median(lens[n]), len(lens[n])) for _, n in LENGTHS if len(lens.get(n, [])) >= MIN_SIDE]
    return res
