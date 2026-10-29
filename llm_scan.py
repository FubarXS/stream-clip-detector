"""The AI reads the whole transcript and points out moments worth clipping.

The loudness / trigger-word step only sees spikes and certain words, so a joke told in a calm voice never becomes a
candidate. Here the model reads the transcript piece by piece and names the moments itself. They are added to the normal
candidates and then go through exactly the same detailed rating (llm_judge) as everything else - this step only finds,
it does not decide what is kept.
"""
import json
import urllib.error

import llm_judge
import llm_parse as parse

PROMPT = """You find clip-worthy moments in the transcript of a live stream. The streamer plays a game and talks.
You only get text, with a [h:mm:ss] time before each line. The speech-to-text makes mistakes.

Pick at most 3 moments in THIS excerpt that would work as a short clip a stranger enjoys without any context:
an unexpected event, a big reaction, a good joke, a fail, a scare, a surprising story or a quotable line.
It is usually a setup followed by a sudden turn.
NOT moments: plain chatting, reading chat, greetings, thanking for follows, menus and settings, planning what to do next,
the same word repeated, and lines that look like speech-to-text nonsense.

Reply with JSON only: {"moments": [{"time": "h:mm:ss", "why": "<short reason>", "funny": <0-10>}]}
- "time" MUST be one of the times shown in the excerpt: the line with the punchline or the reaction, not the setup.
- "funny" is strict: ordinary talk 1-3, a decent joke 5-6, really great 8-10.
- Returning {"moments": []} is normal and correct when nothing is worth clipping. Never invent a moment to fill the list."""

MAX_SECONDS, MAX_CHARS, OVERLAP = 300, 6000, 30  # a piece: at most 5 minutes / 6000 characters, neighbours overlap 30 s
GIVE_UP_AFTER = 3  # failed pieces in a row (model missing, broken, too slow)


def _fmt(t):
    t = int(t)
    return f"{t // 3600}:{(t % 3600) // 60:02d}:{t % 60:02d}"


def chunks(segments, max_s=MAX_SECONDS, max_chars=MAX_CHARS, overlap=OVERLAP):
    """The transcript cut into pieces of at most max_s seconds and max_chars characters. Neighbouring pieces overlap
    by `overlap` seconds, so a joke on the border is seen whole at least once. Empty lines are dropped."""
    segs = [s for s in segments if str(s[2]).strip()]
    out, i = [], 0
    while i < len(segs):
        j, size = i, 0
        while j < len(segs) and (j == i or (segs[j][1] - segs[i][0] <= max_s and size + len(segs[j][2]) <= max_chars)):
            size += len(segs[j][2]) + 12
            j += 1
        out.append(segs[i:j])
        if j >= len(segs):
            break
        end, k, back = segs[j - 1][1], j, 0
        while k - 1 > i and segs[k - 1][0] >= end - overlap and back + len(segs[k - 1][2]) <= max_chars // 5:
            back += len(segs[k - 1][2])  # step back so the next piece starts `overlap` s earlier (at most 1/5 of a piece)
            k -= 1
        i = k
    return out


def excerpt(part):
    return "\n".join(f"[{_fmt(s[0])}] {str(s[2]).strip()}" for s in part)


def moments_from(raw, lo, hi):
    """(second, rating, reason) for every usable moment in a reply. Times outside the piece (lo..hi) are an invention
    of the model and are dropped; a bare list, a single moment or a ``` fence are all accepted."""
    s = str(raw or "").strip()
    try:
        top = json.loads(s)
    except ValueError:
        top = parse.load_reply(s)
    if isinstance(top, dict):
        top = top.get("moments", [top] if "time" in top else [])
    out = []
    for m in top if isinstance(top, list) else []:
        if not isinstance(m, dict):
            continue
        t = m.get("time")
        t = int(t) if isinstance(t, (int, float)) and not isinstance(t, bool) else llm_judge._secs(t)
        if t is not None and lo - 5 <= t <= hi + 5:
            out.append((t, parse.to_float(m.get("funny")), parse.to_text(m.get("why"), 160)))
    return out[:3]


def scan(model, segments, game="", url=llm_judge.URL, min_score=4.0):
    """All moments the AI finds in the transcript, rated at least min_score: [(second, rating, reason)]."""
    found, parts, failed = [], chunks(segments), 0
    for i, part in enumerate(parts, 1):
        print(f"@@AI is reading the transcript {i}/{len(parts)}", flush=True)
        try:
            raw = llm_judge._chat_raw(model, PROMPT, f"Game being played: {game or 'unknown'}\nExcerpt:\n{excerpt(part)}", url)
            failed = 0
        except urllib.error.HTTPError as e:
            print(f"   AI model '{model}' not found. Run in a terminal:  ollama pull {model}" if e.code == 404
                  else f"   AI error while reading the transcript: HTTP {e.code}", flush=True)
            return found
        except urllib.error.URLError:
            print("   Ollama is not reachable - the transcript was not scanned.", flush=True)
            return found
        except Exception as e:
            failed += 1
            print(f"   The AI could not read part {i} of the transcript ({type(e).__name__}: {str(e)[:120]}).", flush=True)
            if failed >= GIVE_UP_AFTER:
                print("   Giving up on reading the transcript.", flush=True)
                return found
            continue
        found += [m for m in moments_from(raw, part[0][0], part[-1][1]) if m[1] >= min_score]
    print(f"   Reading the transcript, the AI named {len(found)} moment(s).", flush=True)
    return found


def add_candidates(model, segments, pool, args, n):
    """The normal candidates plus the moments the AI found: best first, at most args.top of them, none closer than one
    clip length to another candidate. Returns (all candidate seconds, {second: why the AI picked it})."""
    gap, taken, why = args.before + args.after, list(pool), {}
    found = scan(model, segments, game=args.game, min_score=max(1.0, args.min_funny - 1))
    for t, score, reason in sorted(found, key=lambda m: -m[1]):
        if len(why) < args.top and 0 <= t < n and all(abs(t - p) >= gap for p in taken):
            taken.append(t)
            why[t] = f"found by the AI in the transcript ({score:g}/10: {reason}); "
    if found:
        print(f"   New candidates from that: {len(why)} (the others overlap clips that were already found).", flush=True)
    return taken, why
