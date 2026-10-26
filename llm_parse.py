"""Tolerant reading of what a local LLM (Ollama) sends back.

Small models wrap the JSON in words or a ``` fence, write "8/10" instead of 8, give the hashtags as one string,
leave a field out or get cut off in the middle. One bad field must not cost a clip all of its texts."""
import json
import re


def load_reply(text):
    """The JSON object inside a reply (plain, in a ``` fence or after some words). {} when there is none."""
    s = str(text or "").strip()
    a, b = s.find("{"), s.rfind("}")
    candidates = [s, *re.findall(r"```(?:json)?\s*(.*?)```", s, re.S)] + ([s[a:b + 1]] if 0 <= a < b else [])
    for c in candidates:
        try:
            d = json.loads(c)
        except ValueError:
            continue
        if isinstance(d, list) and d and isinstance(d[0], dict):  # a list with one object
            d = d[0]
        if isinstance(d, dict):
            return d
    return {}


def salvage(text):
    """The fields that can still be read in a reply that was cut off or is not valid JSON."""
    s, out = str(text or ""), {}
    quoted = r'"((?:[^"\\]|\\.)*)"'
    for key in ("why", "moment", "evidence", "title", "description"):
        m = re.search(rf'"{key}"\s*:\s*{quoted}', s)
        if m:
            try:
                out[key] = json.loads('"' + m[1] + '"')
            except ValueError:
                out[key] = m[1]
    m = re.search(r'"funny"\s*:\s*"?([^",}\n]+)', s)
    if m:
        out["funny"] = m[1]
    for key in ("hashtags", "meme_terms"):
        m = re.search(rf'"{key}"\s*:\s*\[([^\]]*)', s)  # a last, unfinished item has no closing quote and is skipped
        if m:
            out[key] = re.findall(quoted, m[1])
    return out


def to_float(v, default=0.0):
    """0-10 rating from 8, 8.5, "8", "8/10", "8,5"; default when it is missing or not a number."""
    if isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return min(10.0, max(0.0, float(v)))
    m = re.search(r"\d+(?:[.,]\d+)?", str(v or ""))
    return min(10.0, max(0.0, float(m[0].replace(",", ".")))) if m else default


def to_list(v, words=True):
    """A list of strings from a list, or from one string (words=True: split on spaces and commas, else on commas)."""
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if x is not None]
    if isinstance(v, str):
        return re.findall(r"[^\s,;]+", v) if words else [x.strip() for x in re.split(r"[,;\n]+", v) if x.strip()]
    return []


def to_text(v, limit):
    """Text cut to limit characters; a missing value (null) becomes '' instead of the word 'None'."""
    return "" if v is None else str(v)[:limit]
