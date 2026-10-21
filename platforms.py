"""Per-platform posting rules and text building (TikTok, YouTube Shorts, Instagram Reels).
The numbers come from third-party 2026 hashtag guides (no official documents) and those sources disagree a bit,
so tune them here. rec = how many hashtags go into the post, cap = hard maximum before it becomes a problem
(YouTube ignores ALL hashtags above 15; Instagram allows at most 30). must = tags that always come first."""
from llm_judge import clean_tags

PLATFORMS = {
    "tiktok": {"label": "TikTok", "rec": 5, "cap": 10, "title": 0, "must": []},
    "shorts": {"label": "YouTube Shorts", "rec": 5, "cap": 15, "title": 100, "must": ["#shorts"]},
    "reels": {"label": "Instagram Reels", "rec": 8, "cap": 30, "title": 0, "must": []},
}
RULES = (
    "You adapt a clip's post texts to each platform. Use ONLY facts from the given title and description; never "
    "invent events. Answer ONLY with JSON: {\"tiktok\": {\"description\": punchy caption, max 150 characters, no "
    "hashtags, \"hashtags\": exactly 5}, \"shorts\": {\"title\": catchy, max 90 characters, \"description\": 1-2 "
    "sentences, \"hashtags\": 5 including #shorts}, \"reels\": {\"description\": 1-2 sentence caption, \"hashtags\": 8}}. "
    "Pick hashtags from the given pool when they fit (best first); you may add a few platform-native ones. Prefer a "
    "mix of one broad tag, game tags and niche tags. Avoid spammy tags like #viral. Write texts in the language of "
    "the given title."
)


def build_all(ai, game, extra, raw=None):
    """Final per-platform title/description/hashtags: AI wording where usable, the rules enforced here."""
    pool, g, own = ai.get("hashtags", []), clean_tags([game]), clean_tags(extra.split())
    out = {}
    for key, p in PLATFORMS.items():
        r = raw.get(key) if isinstance(raw, dict) else None
        r = r if isinstance(r, dict) else {}
        h = r.get("hashtags")
        tags = clean_tags(h if isinstance(h, list) and h else pool, 60)
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
