"""Optional AI step: a local LLM (Ollama, free, runs on your PC) rates how funny/shareable each
candidate clip is, finds the funniest moment, and suggests a title, hashtags and meme/GIF ideas.
Nothing is sent online. Needs Ollama (ollama.com) and a model: ollama pull <model>."""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

import llm_parse as parse

URL = "http://localhost:11434/api/chat"
# Without num_ctx an old Ollama uses a 2048-token window and silently cuts off the START of the prompt (the
# instructions), without num_predict a model that loops on hashtags writes until the window is full and the JSON is cut.
OPTIONS = {"temperature": 0.3, "num_ctx": 4096, "num_predict": 1500}
MEMES = ("to be continued (JoJo), vine boom, bruh sound effect, this is fine dog, surprised pikachu, sad violin, "
         "GTA wasted, mission failed we'll get 'em next time, nope (leaving the room), oh no no no, "
         "Michael Scott no god please no, Homer disappearing into bushes, awkward look, skeleton waiting, "
         "Roblox oof, Windows error sound")
PROMPT = (
    "You help a streamer pick funny or shareable clips. You get an automatic transcript with timestamps [H:MM:SS] "
    "(may contain recognition errors; Czech or English) plus audio signals. Judge ONLY from the transcript and "
    "signals - you cannot see the video. Be strict: ordinary game talk, reading menus or planning scores 1-3. "
    "NEVER mention words or events that are not in the transcript. A setup followed by a sudden event (for example "
    "'I have to be careful' and then a loud spike a few seconds later = jump scare) makes a good clip: use the loud "
    "spike timestamp. For meme ideas prefer well-known named memes/sounds that fit the situation, e.g.: " + MEMES +
    ". Setup + sudden surprise -> 'to be continued' or 'vine boom'; failure -> 'sad violin', 'GTA wasted', "
    "'mission failed'; denying a problem -> 'this is fine'. Answer ONLY with JSON: {\"funny\": number 0-10, "
    "\"why\": one short sentence in the transcript's language, \"moment\": \"H:MM:SS\" timestamp of the funniest "
    "moment, \"evidence\": short EXACT quote (max 12 words) copied from the transcript that supports your rating, "
    "or \"\" if none, \"title\": short catchy title in the transcript's language, \"description\": 1-2 engaging sentences for a post caption in the transcript's language (no hashtags), \"hashtags\": 15-20 hashtags, ordered from the broadest, most used tag first to the most niche tag last (broad gaming/funny tags, genre tags, game-specific tags), "
    " \"meme_terms\": 2-3 short English search phrases for a fitting meme/GIF/sound}."
)


def clean_tags(raw, limit=20):
    """Hashtags: lowercase, no spaces or punctuation, no duplicates; the reach order is kept."""
    out = []
    for h in raw:
        t = "#" + re.sub(r"\W", "", str(h).lstrip("#").lower())
        if len(t) > 1 and t not in out:
            out.append(t)
    return out[:limit]


def finalize_tags(ai, game, extra):
    """Make sure the game tag is near the top and add the streamer's own tags at the end."""
    tags, g = ai["hashtags"], clean_tags([game])
    if g and g[0] not in tags:
        tags.insert(min(1, len(tags)), g[0])
    for t in clean_tags(extra.split()):
        if t not in tags:
            tags.append(t)
    ai["hashtags"] = tags


def _norm(t):
    return " ".join(re.findall(r"\w+", str(t).lower()))


def _secs(v):
    m = re.fullmatch(r"\s*(?:(\d+):)?(\d{1,2}):(\d{2})\s*", str(v))
    return int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) if m else None


def _evidence_ok(ev, text):
    words, have = _norm(ev).split(), set(_norm(text).split())
    return bool(words) and sum(w in have for w in words) / len(words) >= 0.8


def ask(model, transcript, hint, plain, url=URL, timeout=300, game="", pool=20):
    """One clip -> rating + texts. An unusable answer gets one more try that asks for fewer hashtags
    (a long list is what makes small models loop); then ValueError says what the model sent."""
    err = ValueError("no answer")
    for n in dict.fromkeys((pool, min(pool, 20))):
        try:
            return _ask_once(model, transcript, hint, plain, url, timeout, game, n)
        except ValueError as e:  # includes json.JSONDecodeError
            err = e
    raise err


def _ask_once(model, transcript, hint, plain, url, timeout, game, pool):
    body = json.dumps({
        "model": model, "stream": False, "format": "json", "options": OPTIONS,
        "messages": [{"role": "system", "content": PROMPT.replace("15-20 hashtags", f"{pool} hashtags")},
                     {"role": "user", "content": f"Game being played: {game or 'unknown'}\nAudio signals: {hint}\nTranscript:\n{transcript[:3500]}"}],
    }).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = json.loads(r.read())["message"]["content"]
    data = parse.load_reply(raw) or parse.salvage(raw)  # a cut-off reply still gives the fields that were finished
    if not (data.get("title") or data.get("description") or data.get("hashtags")):
        raise ValueError("the AI reply has no title/description/hashtags: " + " ".join(str(raw).split())[:100])
    ev = parse.to_text(data.get("evidence"), 160)
    return {"funny": parse.to_float(data.get("funny")), "why": parse.to_text(data.get("why"), 300),
            "moment": _secs(data.get("moment")), "evidence": ev, "evidence_ok": _evidence_ok(ev, plain),
            "title": parse.to_text(data.get("title"), 100), "description": parse.to_text(data.get("description"), 400),
            "hashtags": clean_tags(parse.to_list(data.get("hashtags")), pool),
            "meme_terms": parse.to_list(data.get("meme_terms"), words=False)[:3]}


def _judge_loop(model, items, url=URL, game="", extra_tags="", pool=20):
    """Adds an 'ai' dict to every item. Returns False if Ollama/model is unusable (stops early)."""
    for i, it in enumerate(items, 1):
        print(f"@@AI is judging clip {i}/{len(items)}", flush=True)
        try:
            it["ai"] = ask(model, it.get("lines") or it["text"], it["why"] + "; " + it.get("hint", ""), it["text"], url, game=game, pool=pool)
            finalize_tags(it["ai"], game, extra_tags)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"   AI model '{model}' not found. Run in a terminal:  ollama pull {model}", flush=True)
                return False
            print(f"   AI error for clip {i}: HTTP {e.code}", flush=True)
        except urllib.error.URLError:
            print("   Ollama is not reachable. Install it from ollama.com and keep it running. "
                  "AI step skipped.", flush=True)
            return False
        except Exception as e:
            print(f"   AI answer for clip {i} could not be used ({type(e).__name__}: {str(e)[:160]}).", flush=True)
    return True


def unload(model, url=URL):
    """Free the GPU memory right away (otherwise Ollama keeps the model loaded for a few minutes)."""
    try:
        body = json.dumps({"model": model, "keep_alive": 0}).encode()
        req = urllib.request.Request(url.replace("/api/chat", "/api/generate"), body,
                                     {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        pass


def judge_all(model, items, url=URL, game="", extra_tags="", pool=20):
    try:
        return _judge_loop(model, items, url, game, extra_tags, pool)
    finally:
        unload(model, url)


def links(terms):
    """Search links (no API key needed) where you can pick the actual GIF/meme yourself."""
    return [{"term": t,
             "giphy": "https://giphy.com/search/" + urllib.parse.quote(t.strip().replace(" ", "-")),
             "youtube": "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(t + " meme")}
            for t in terms]


def _chat(model, system, user, url=URL, timeout=300):
    body = json.dumps({"model": model, "stream": False, "format": "json", "options": OPTIONS,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return parse.load_reply(json.loads(r.read())["message"]["content"])


def adapt_all(model, items, game="", extra_tags="", url=URL):
    """A second, short AI call per clip: texts and hashtags written for TikTok, YouTube Shorts and Reels."""
    import platforms
    todo, down = [it for it in items if it.get("ai")], False
    try:
        for i, it in enumerate(todo, 1):
            a, raw = it["ai"], None
            if not down:
                print(f"@@AI is adapting texts for each platform {i}/{len(todo)}", flush=True)
                msg = (f"Game: {game or 'unknown'}\nGeneral title: {a['title']}\nGeneral description: "
                       f"{a.get('description') or a['why']}\nHashtag pool (best first): {' '.join(a['hashtags'])}")
                try:
                    raw = _chat(model, platforms.RULES, msg, url)
                except urllib.error.URLError:
                    down = True
                except Exception:
                    raw = None
            a["platforms"] = platforms.build_all(a, game, extra_tags, raw)
    finally:
        unload(model, url)
