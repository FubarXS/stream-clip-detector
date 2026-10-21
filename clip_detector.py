"""
Automatic clip detection for stream recordings (free, runs locally).

Signals: 1) loudness spikes (shouting, laughing)  2) speech transcript (faster-whisper)
   with trigger words and an optional "secret word" you say to mark a moment manually.

Usage:
  python clip_detector.py vod.mp4
  python clip_detector.py vod.mp4 --top 20 --before 25 --after 10 --device cpu
"""
import argparse
import os
import re
import json
import time
import difflib
import threading
import unicodedata
import subprocess
import numpy as np

SR = 16000  # analysis sample rate


def _add_cuda_dlls():
    """Finds CUDA libraries installed via pip (nvidia-cublas-cu12, nvidia-cudnn-cu12)."""
    import sys
    import glob
    if os.name != "nt":
        return
    for base in sys.path:
        for d in glob.glob(os.path.join(base, "nvidia", "*", "bin")):
            try:
                os.add_dll_directory(d)
            except Exception:
                pass
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


_add_cuda_dlls()

# Edit to taste. Czech list = example for another language
from keywords import KEYWORDS_CS, KEYWORDS_EN, KEYWORDS, STRONG_KEYWORDS, EXTRA_SIGNALS  # noqa: F401  (lists live in keywords.py)


def norm(text):
    """Lowercase, no accents or punctuation: 'Yeah, baby!' -> 'yeah baby'."""
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", t))


def fmt(t):
    t = int(t)
    return f"{t // 3600}:{(t % 3600) // 60:02d}:{t % 60:02d}"


def load_audio(path, track=0):
    print("[1/4] Extracting audio (ffmpeg)...")
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-map", f"0:a:{track}", "-vn", "-ac", "1",
           "-ar", str(SR), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def loudness_score(audio, min_db=6.0, baseline_window=180):
    """Per second: how many dB louder than the typical level of the last 3 minutes.
    Jumps smaller than min_db are ignored; above that, every 5 dB counts as 1 point."""
    print("[2/4] Measuring loudness...", flush=True)
    n = len(audio) // SR
    if n == 0:
        z = np.zeros(0, dtype=np.float32)
        return z, z
    sec = audio[: n * SR].reshape(n, SR)
    db = 20 * np.log10(np.sqrt((sec ** 2).mean(axis=1)) + 1e-6)
    delta = np.zeros(n, dtype=np.float32)
    for i in range(n):
        lo = max(0, i - baseline_window)
        window = db[lo:i + 1] if i - lo > 30 else db[: min(n, 60)]
        delta[i] = db[i] - np.median(window)
    print(f"   typical level {np.median(db):.0f} dB, loudest spike +{delta.max():.0f} dB above normal", flush=True)
    score = np.where(delta >= min_db, delta / 5.0, 0.0).astype(np.float32)
    return np.convolve(np.clip(score, 0, 8), np.ones(3) / 3, mode="same"), delta


def transcribe(audio, model_size, language, prompt="", device="auto"):
    from faster_whisper import WhisperModel
    total = max(1.0, len(audio) / SR)
    st = {"stage": "Loading model", "pct": 0.0, "t0": time.time()}
    done = threading.Event()
    hist = []

    def beat():  # status line every 5 s, even while the model loads or a hard part is decoded
        while not done.wait(5):
            el = time.time() - st["t0"]
            if st["stage"] == "Loading model":
                print(f"@@Loading model ({int(el)} s)", flush=True)
                continue
            hist.append((time.time(), st["pct"]))
            while len(hist) > 2 and hist[-1][0] - hist[0][0] > 90:  # speed over roughly the last 90 s
                hist.pop(0)
            dt, dp = hist[-1][0] - hist[0][0], hist[-1][1] - hist[0][1]
            rate = dp / dt if dt >= 20 and dp > 0 else (st["pct"] / el if st["pct"] >= 2 else 0)
            eta = f" - ETA ~{fmt((100 - st['pct']) / rate)}" if rate > 0 else ""
            print(f"@@Transcribing {int(st['pct'])}%{eta}", flush=True)

    def run(dev, compute):
        st.update(stage="Loading model", pct=0.0, t0=time.time())
        model = WhisperModel(model_size, device=dev, compute_type=compute)
        print(f"   model ready ({model_size} on {dev}), transcribing...", flush=True)
        st.update(stage="Transcribing", t0=time.time())
        hist.clear()
        kw = dict(vad_filter=True, beam_size=1, word_timestamps=True, initial_prompt=prompt or None,
                  condition_on_previous_text=False)  # avoids slow repetition loops on music/noise
        if language in ("mix", "auto", "", None):
            kw["language"] = None
            if language == "mix":
                kw["multilingual"] = True  # detect language per sentence
        else:
            kw["language"] = language
        segs, _ = model.transcribe(audio, **kw)
        out = []
        for s in segs:
            out.append((s.start, s.end, s.text.strip(),
                        [(w.start, w.end, w.word) for w in (s.words or [])]))
            st["pct"] = min(100.0, 100 * s.end / total)
        return out

    print("[3/4] Transcribing speech (Whisper)... this can take a while", flush=True)
    threading.Thread(target=beat, daemon=True).start()
    try:
        if device == "cpu":
            return run("cpu", "int8")
        try:
            return run("cuda", "float16")
        except Exception as e:
            if device == "cuda":
                raise
            print(f"   GPU failed ({type(e).__name__}: {e}), falling back to CPU (slower).", flush=True)
            return run("cpu", "int8")
    finally:
        done.set()


def keyword_score(segments, n_seconds):
    kws = [norm(k) for k in KEYWORDS if norm(k)]
    strong = [norm(k) for k in STRONG_KEYWORDS if norm(k)]
    score = np.zeros(n_seconds, dtype=np.float32)
    for seg in segments:
        start, end, text = seg[0], seg[1], seg[2]
        low = " " + norm(text) + " "
        hits = sum(1 for k in kws if f" {k} " in low)
        add = min(hits, 2) * 2.0 + (5.0 if any(f" {k} " in low for k in strong) else 0.0)
        if add:
            a, b = int(start), min(n_seconds, int(end) + 1)
            score[a:b] += add
    return score


def find_secret(segments, phrase):
    """Finds the secret phrase even if Whisper spells it a bit differently (Klipec Skřipec ~ klipec skripec)."""
    target = norm(phrase).replace(" ", "")
    n = len(norm(phrase).split())
    words = [(ws, norm(w)) for seg in segments for ws, we, w in seg[3] if norm(w)]
    hits = []
    for i in range(len(words)):
        for size in (n - 1, n, n + 1):
            if size < 1 or i + size > len(words):
                continue
            cand = "".join(w for _, w in words[i:i + size])
            if difflib.SequenceMatcher(None, target, cand).ratio() >= 0.78:
                if not hits or words[i][0] - hits[-1] > 15:
                    hits.append(words[i][0])
                break
    return hits


def window_text(segments, start, end):
    return " ".join(s[2] for s in segments if s[1] >= start and s[0] <= end)


def window_lines(segments, start, end):
    return "\n".join(f"[{fmt(s[0])}] {s[2]}" for s in segments if s[1] >= start and s[0] <= end)


def spike_hint(delta, start, end):
    seg = delta[int(start):int(end) + 1]
    if len(seg) == 0 or seg.max() <= 0:
        return "no loudness spike in this clip"
    return f"loudest moment in this clip: +{seg.max():.0f} dB at {fmt(int(start) + int(seg.argmax()))}"


def save_transcript(segments, out):
    """Full transcript with timestamps: transcript.txt and subtitles transcript.srt."""
    def srt(t):
        ms = int(t * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "transcript.txt"), "w", encoding="utf-8") as f:
        f.writelines(f"[{fmt(s[0])}] {s[2]}\n" for s in segments)
    with open(os.path.join(out, "transcript.srt"), "w", encoding="utf-8") as f:
        for i, s in enumerate(segments, 1):
            f.write(f"{i}\n{srt(s[0])} --> {srt(s[1])}\n{s[2]}\n\n")
    print(f"   transcript saved to {out} (transcript.txt, transcript.srt)", flush=True)


def explain(p, loud, segments, start, end):
    """Plain-language reason why a moment was picked."""
    db = float(loud[min(int(p), len(loud) - 1)]) * 5
    low = " " + norm(window_text(segments, start, end)) + " "
    words = [k for k in KEYWORDS + STRONG_KEYWORDS if norm(k) and f" {norm(k)} " in low]
    a = f"loudness +{db:.0f} dB" if db > 0 else "no loudness spike"
    b = "trigger words: " + ", ".join(words) if words else "no trigger words"
    note = " (loudness only - may be game sound, not you)" if db > 0 and not words else ""
    return f"{a}; {b}{note}"


def pick_peaks(score, top, min_gap, threshold):
    order = np.argsort(score)[::-1]
    picked = []
    for idx in order:
        if score[idx] < threshold or len(picked) >= top:
            break
        if all(abs(idx - p) >= min_gap for p in picked):
            picked.append(int(idx))
    return sorted(picked)


def snippet(segments, t):
    texts = [s[2] for s in segments if s[0] - 5 <= t <= s[1] + 5]
    return " ".join(texts)[:150]


def cut(video, start, end, out_path):
    # -map 0:v:0 -map 0:a? = the video + ALL audio tracks (OBS multitrack 1-6 stay separate in the clip).
    # Without -map ffmpeg would keep just one audio track.
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-i", video,
                    "-t", str(end - start), "-map", "0:v:0", "-map", "0:a?", "-c", "copy", out_path], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--top", type=int, default=15, help="max number of clips")
    ap.add_argument("--before", type=int, default=20, help="seconds before the peak")
    ap.add_argument("--after", type=int, default=10, help="seconds after the peak")
    ap.add_argument("--min-gap", type=int, default=60, help="min. gap between clips (s)")
    ap.add_argument("--threshold", type=float, default=3.0, help="min. score")
    ap.add_argument("--model", default="medium", help="small / medium / large-v3")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument("--loud-db", type=float, default=6.0, help="min. jump above normal loudness (dB)")
    ap.add_argument("--no-loudness", action="store_true", help="ignore loudness")
    ap.add_argument("--audio-track", type=int, default=1, help="audio track to analyze (1 = first)")
    ap.add_argument("--measure", action="store_true", help="only measure loudness and print a suggestion")
    ap.add_argument("--llm", default="", help="Ollama model for the optional AI step")
    ap.add_argument("--min-funny", type=float, default=5.0, help="min. AI funny rating (0-10)")
    ap.add_argument("--game", default="", help="game being played (for hashtags)")
    ap.add_argument("--extra-tags", default="", help="your own hashtags added to every clip")
    ap.add_argument("--tag-pool", type=int, default=50, help="how many hashtags the AI collects (General list)")
    ap.add_argument("--config", default="", help="JSON with keyword lists")
    ap.add_argument("--secret", default="", help="secret word = manual marker")
    ap.add_argument("--secret-back", type=int, default=45, help="seconds to look back for the secret word")
    ap.add_argument("--no-whisper", action="store_true")
    ap.add_argument("--no-transcript-files", action="store_true",
                    help="speech is still transcribed (needed for the analysis) but transcript files are not saved")
    ap.add_argument("--no-info-files", action="store_true", help="no *_info.txt file next to each clip")
    ap.add_argument("--no-cut", action="store_true", help="timestamps only, no cutting")
    ap.add_argument("--out", default="clips")
    args = ap.parse_args()

    if args.config:
        with open(args.config, encoding="utf-8") as f:
            c = json.load(f)
        KEYWORDS[:] = c.get("keywords", KEYWORDS)
        STRONG_KEYWORDS[:] = c.get("strong", [])
    audio = load_audio(args.video, args.audio_track - 1)
    n = len(audio) // SR
    if args.measure:
        import calibrate
        calibrate.report(audio, loudness_score(audio, args.loud_db)[1])
        return
    if args.no_loudness:
        total, delta = np.zeros(n, dtype=np.float32), np.zeros(n, dtype=np.float32)
    else:
        total, delta = loudness_score(audio, args.loud_db)

    loud = total.copy()
    kwarr = np.zeros(n, dtype=np.float32)
    segments = []
    if not args.no_whisper:
        prompt = ", ".join(([args.secret] if args.secret else []) + STRONG_KEYWORDS + KEYWORDS)[:200]
        segments = transcribe(audio, args.model, args.lang, prompt, args.device)
        kwarr = keyword_score(segments, n)
        total = total + kwarr
        if not args.no_transcript_files:
            save_transcript(segments, args.out)

    for fn in EXTRA_SIGNALS:
        total = total + fn(args.video, n, args)
    print("[4/4] Picking the best moments...")
    peaks = pick_peaks(total, args.top, args.min_gap, args.threshold)
    use_ai = bool(args.llm)
    if use_ai and not segments:
        print("AI step needs speech detection (Whisper) - skipped.")
        use_ai = False
    pool = pick_peaks(total, max(args.top * 2, args.top + 6), args.min_gap, args.threshold * 0.6) if use_ai else peaks
    os.makedirs(args.out, exist_ok=True)

    marks = find_secret(segments, args.secret) if (args.secret and segments) else []
    if args.secret:
        print(f"Secret word '{args.secret}' found {len(marks)}x.")
    jobs = [("marker", t, max(0, int(t) - args.secret_back), min(n, int(t) + 1)) for t in marks]
    for p in pool:
        if not any(st <= p <= en for _, _, st, en in jobs):
            jobs.append(("clip", p, max(0, p - args.before), min(n, p + args.after)))

    items = [{"kind": k, "peak": int(p), "start": int(st), "end": int(en),
              "score": round(float(total[min(int(p), n - 1)]), 1), "why": explain(p, loud, segments, st, en),
              "text": window_text(segments, st, en), "lines": window_lines(segments, st, en),
              "hint": spike_hint(delta, st, en), "ai": None, "file": "", "links": []}
             for k, p, st, en in jobs]
    if use_ai and items:
        import llm_judge
        if llm_judge.judge_all(args.llm, items, game=args.game, extra_tags=args.extra_tags, pool=args.tag_pool):
            ranked = sorted([it for it in items if it["kind"] != "marker" and it["ai"]], key=lambda it: -it["ai"]["funny"])
            good = [it for it in ranked if it["ai"]["funny"] >= args.min_funny]
            if not good:
                print(f"   AI rated no clip {args.min_funny:g}/10 or higher; showing the best 3 anyway.")
                good = ranked[:3]
            items = [it for it in items if it["kind"] == "marker"] + good[: args.top]
        else:
            keep = {int(p) for p in peaks}
            items = [it for it in items if it["kind"] == "marker" or it["peak"] in keep]

    for it in items:  # center the clip on the moment the AI found funniest
        a, m = it["ai"], (it["ai"] or {}).get("moment")
        if m is not None and it["kind"] != "marker" and it["start"] <= m <= it["end"]:
            it.update(peak=m, start=max(0, m - args.before), end=min(n, m + args.after))

    if use_ai and items:
        llm_judge.adapt_all(args.llm, items, args.game, args.extra_tags)
    import exports
    lines = []
    for i, it in enumerate(items, 1):
        name = f"{'marker' if it['kind'] == 'marker' else 'clip'}_{i:02d}_{fmt(it['peak']).replace(':', '-')}.mp4"
        if not args.no_cut:
            it["file"] = os.path.join(args.out, name)
            cut(args.video, it["start"], it["end"], it["file"])
            if not args.no_info_files:
                exports.write_info(it, exports.info_path(it, args.out), not args.no_transcript_files)
        it["thumb"] = exports.make_thumb(args.video, it["peak"], os.path.join(args.out, "thumbs", name[:-4] + ".png"))
        tag = "MARKER" if it["kind"] == "marker" else "clip"
        block = [f"#{i:02d} [{tag}]  {fmt(it['start'])} - {fmt(it['end'])}  score {it['score']}", f"    why: {it['why']}"]
        a = it["ai"]
        if a:
            it["links"] = llm_judge.links(a["meme_terms"])
            block += [f"    AI: funny {a['funny']:g}/10 - {a['why']}", f"    title: {a['title']}",
                      f"    tags: {' '.join(a['hashtags'])}"]
            if a["moment"] is not None:
                block.append(f"    funniest moment: {fmt(a['moment'])}")
            if a["evidence"]:
                ok = "(found in transcript)" if a["evidence_ok"] else "(NOT found in transcript - AI may be wrong)"
                block.append(f"    evidence: '{a['evidence']}' {ok}")
        block.append(f"    said: {it['text'][:150]}")
        print("\n".join(block))
        lines.append("\n".join(block))

    with open(os.path.join(args.out, "clips.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(lines))
    with open(os.path.join(args.out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    exports.write_posts(items, args.out)
    print(f"\nDone. Results are in folder '{args.out}'.")

if __name__ == "__main__":
    main()
