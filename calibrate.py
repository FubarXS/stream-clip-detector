"""Loudness check: how loud is your normal voice compared with your loudest moments (your yelps)?"""
import json
import numpy as np

SR = 16000


def fmt(t):
    t = int(t)
    return f"{t // 3600}:{(t % 3600) // 60:02d}:{t % 60:02d}"


def report(audio, delta):
    n = len(delta)
    if n == 0:
        print("   Recording is too short to measure.", flush=True)
        return
    sec = audio[: n * SR].reshape(n, SR)
    typical = float(np.median(20 * np.log10(np.sqrt((sec ** 2).mean(axis=1)) + 1e-6)))
    p90, p99, mx = (float(np.percentile(delta, 90)), float(np.percentile(delta, 99)), float(delta.max()))
    top, taken = [], []
    for i in np.argsort(delta)[::-1]:
        if all(abs(int(i) - j) >= 30 for j in taken):
            taken.append(int(i))
            top.append([int(i), round(float(delta[i]))])
        if len(top) == 5:
            break
    suggest = int(min(20, max(6, round(p99))))
    print(f"   Typical level {typical:.0f} dB. 90% of the time within +{p90:.0f} dB of normal; loudest 1% above "
          f"+{p99:.0f} dB; loudest moment +{mx:.0f} dB.", flush=True)
    print("   Loudest moments (listen to them - was it you or the game?): "
          + ", ".join(f"{fmt(t)} (+{d} dB)" for t, d in top), flush=True)
    print(f"   Suggested minimum jump: {suggest} dB", flush=True)
    print("@@MEASURE " + json.dumps({"typical": round(typical), "p90": round(p90), "p99": round(p99),
                                     "max": round(mx), "suggest": suggest, "top": top}), flush=True)
