"""Per-platform posting rules and text building (TikTok, YouTube Shorts, Instagram Reels).

All numbers live in PLATFORMS - the AI prompt (RULES) is built from them, so change a number only here.
  rec  = how many hashtags go into the post
  cap  = hard maximum
  must = tags that always come first

YouTube (YouTube Help, "Find playlists & videos using hashtags"): if a video has more than 60 hashtags,
ALL hashtags are ignored, and over-tagging may remove the video from search. YouTube also shows only up
to three hashtags above the title, so keep the first ones the most relevant. cap stays below 60 on purpose.
Instagram: since December 2025 posts and Reels allow at most 5 hashtags (announced by Instagram / Adam Mosseri).
TikTok: the 5 / 10 comes from third-party guides and is NOT verified against official documents - tune it."""
from llm_judge import clean_tags

PLATFORMS = {
    "tiktok": {"label": "TikTok", "rec": 5, "cap": 10, "title": 0, "must": []},
    "shorts": {"label": "YouTube Shorts", "rec": 30, "cap": 50, "title": 100, "must": ["#shorts"]},
    "reels": {"label": "Instagram Reels", "rec": 5, "cap": 5, "title": 0, "must": []},
}
ASK_MAX = 8  # the AI is asked for at most this many per platform (long lists make small models loop);
#              build_all() tops the post up to "rec" from the General list


def _rules():
    n = {k: min(p["rec"], ASK_MAX) for k, p in PLATFORMS.items()}
    return (
        "You adapt a clip's post texts to each platform. Use ONLY facts from the given title and description; "
        "never invent events. Answer ONLY with JSON: "
        '{"tiktok": {"description": punchy caption, max 150 characters, no hashtags, '
        f'"hashtags": exactly {n["tiktok"]}}}, '
        '"shorts": {"title": catchy, max 90 characters, "description": 1-2 sentences, '
        f'"hashtags": {n["shorts"]} including #shorts}}, '
        '"reels": {"description": 1-2 sentence caption, '
        f'"hashtags": {n["reels"]}}}}}. '
        "Pick hashtags from the given pool when they fit (best first); you may add a few platform-native ones. "
        "Prefer a mix of one broad tag, game tags and niche tags. Avoid spammy tags like #viral. "
        "Write texts in the language of the given title."
    )


RULES = _rules()


def build_all(ai, game, extra, raw=None):
    """Final per-platform title/description/hashtags: AI wording where usable, the rules enforced here."""
    pool, g, own = ai.get("hashtags", []), clean_tags([game]), clean_tags(extra.split())
    out = {}
    for key, p in PLATFORMS.items():
        r = raw.get(key) if isinstance(raw, dict) else None
        r = r if isinstance(r, dict) else {}
        h = r.get("hashtags")
        # the platform-specific AI tags first, then the general pool tops it up to the wanted count
        tags = clean_tags((h if isinstance(h, list) else []) + pool, 100)
        tags = p["must"] + [t for t in tags if t not in p["must"] and t not in own]
        if g and g[0] not in tags:
            tags.insert(len(p["must"]), g[0])
        tags = tags[: max(1, p["rec"] - len(own))] + own  # the streamer's own tags are always kept
        title = str(r.get("title") or ai.get("title", ""))[: p["title"]] if p["title"] else ""
        desc = str(r.get("description") or ai.get("description") or ai.get("why", ""))[:2000]
        out[key] = {"title": title, "description": desc, "hashtags": tags[: p["cap"]]}
    return out


def post_text(p):
    return "\n\n".join(x for x in (p["title"], p["description"], " ".join(p["hashtags"])) if x)
