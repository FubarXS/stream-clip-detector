"""Analyze finished clips (e.g. exported from DaVinci Resolve): transcript + subtitles, and the AI writes
title, description, hashtags per platform and meme ideas.
Usage: python analyze_finished.py clip1.mp4 clip2.mp4 --game "Project Zomboid" --llm gemma3:12b --out clips"""
import argparse
import json
import os

import clip_detector as c
import exports
import llm_judge
import transcript_cache


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--out", default="clips")
    ap.add_argument("--model", default="medium")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument("--llm", default="")
    ap.add_argument("--game", default="")
    ap.add_argument("--extra-tags", default="")
    ap.add_argument("--proven-tags", default="")
    ap.add_argument("--tag-pool", type=int, default=50)
    ap.add_argument("--no-transcript-files", action="store_true", help="do not save the .srt subtitles / transcript text")
    ap.add_argument("--no-transcript-cache", action="store_true", help="always transcribe again")
    ap.add_argument("--no-info-files", action="store_true", help="no *_info.txt file per clip")
    args = ap.parse_args()
    folder = os.path.join(args.out, "finished")
    os.makedirs(folder, exist_ok=True)
    new = []
    for n, clip in enumerate(args.clips, 1):
        name = os.path.basename(clip)
        print(f"@@Clip {n}/{len(args.clips)}: {name}", flush=True)
        print(f"Analyzing {name} ...", flush=True)
        audio = c.load_audio(clip)
        dur = len(audio) / c.SR
        _, delta = c.loudness_score(audio, 6.0)
        segs = transcript_cache.get_or_run(
            args.out, clip, (args.model, args.lang), lambda: c.transcribe(audio, args.model, args.lang, args.game, args.device),
            not args.no_transcript_cache)
        stem = os.path.splitext(name)[0]
        print(f"   speech found: {len(segs)} segment(s), {len(c.window_text(segs, 0, dur).strip())} characters", flush=True)
        if not args.no_transcript_files:
            exports.write_srt(segs, os.path.join(folder, stem + ".srt"))
        peak = int(delta.argmax()) if len(delta) else 0
        thumb = os.path.join(folder, "thumbs", stem + ".png")
        new.append({"kind": "finished", "peak": peak, "start": 0, "end": int(dur), "score": 0, "ai": None,
                    "file": clip, "links": [], "topic": stem, "why": f"finished clip: {name}", "text": c.window_text(segs, 0, dur),
                    "lines": c.window_lines(segs, 0, dur), "hint": c.spike_hint(delta, 0, dur),
                    "thumb": exports.make_thumb(clip, min(peak, max(0, int(dur) - 1)), thumb)})
    if args.llm:
        talk = list(new)  # clips without speech are judged too, from the game, the file name and the audio signals
        if any(not it["text"].strip() for it in new):
            print("   Some clips contain no recognized speech - the AI writes their texts from the game and the file name only.", flush=True)
        if talk and llm_judge.judge_all(args.llm, talk, game=args.game, extra_tags=args.extra_tags, pool=args.tag_pool):
            llm_judge.adapt_all(args.llm, talk, args.game, args.extra_tags, proven=args.proven_tags)
            for it in talk:
                if it["ai"]:
                    it["links"] = llm_judge.links(it["ai"]["meme_terms"])
    if not args.no_info_files:
        for it in new:
            exports.write_info(it, exports.info_path(it, args.out), not args.no_transcript_files)
    path = os.path.join(args.out, "finished.json")
    try:
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        old = []
    mine = {it["file"] for it in new}
    items = [o for o in old if o.get("file") not in mine] + new
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    exports.write_posts(items, args.out, "finished_posts.txt")
    print(f"\nDone. {len(new)} clip(s) analyzed. Texts: finished_posts.txt, subtitles: finished/*.srt", flush=True)


if __name__ == "__main__":
    main()
