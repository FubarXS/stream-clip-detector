#!/usr/bin/env python3
"""
analyze_hashtags.py - analýza vztahu mezi hashtagy a dosahem YouTube Shorts.

Vstup : jedno nebo více CSV z Tampermonkey exportu (středník, UTF-8 BOM, desetinná čárka).
        Videa se sloučí podle video_id, platí nejnovější export (datum_exportu).
Výstup: report v konzoli + report.md + tagy.csv + videa.csv ve složce --out.

Použití:
    python analyze_hashtags.py youtube-shorts-export-*.csv
    python analyze_hashtags.py *.csv --min-age-days 3 --labels stitky.csv

Volitelné štítky (--labels), CSV se středníkem:
    video_id;typ_obsahu;sada
    DdoAXfXIJkY;komedie;A
Díky nim jde oddělit vliv obsahu od vlivu hashtagů (viz sekce "Typ obsahu").

Jen standardní knihovna Pythonu 3.9+.
"""
import argparse, csv, glob, math, random, re, statistics as st, sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

HASHTAG_RE = re.compile(r"#[^\W_][\w]*", re.UNICODE)


# ---------- načítání ----------
def num(s):
    if s is None:
        return None
    s = str(s).replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def extract_tags(text):
    seen, out = set(), []
    for m in HASHTAG_RE.findall(text or ""):
        t = m.lower()
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def load_videos(paths, labels_path=None):
    best = {}
    for p in paths:
        for r in read_csv(p):
            vid = (r.get("video_id") or "").strip()
            if not vid:
                continue
            if vid not in best or (r.get("datum_exportu") or "") >= (best[vid].get("datum_exportu") or ""):
                best[vid] = r
    labels = {}
    if labels_path:
        for r in read_csv(labels_path):
            labels[r["video_id"].strip()] = r
    vids = []
    for vid, r in best.items():
        # pozor: sloupec "popis_kompletni" je jen příznak ano/NE, text je v "popis"
        desc_tags = extract_tags(r.get("hashtagy_popis") or r.get("popis") or "")
        tags = extract_tags(" ".join([r.get("hashtagy_nazev") or "", " ".join(desc_tags),
                                      r.get("nazev") or ""]))
        hour = None
        m = re.match(r"(\d{1,2}):", r.get("cas_publikace") or "")
        if m:
            hour = int(m.group(1))
        lab = labels.get(vid, {})
        vids.append(dict(
            id=vid, nazev=r.get("nazev", ""), tags=tags, first3=desc_tags[:3],
            n_tags=len(tags), views=num(r.get("zhlednuti")), age_d=num(r.get("stari_dni")),
            age_h=num(r.get("stari_hodin")), dur=num(r.get("delka_s")), hour=hour,
            stayed=num(r.get("zustali_sledovali_pct")), avg_view=num(r.get("prum_mira_sledovani_pct")),
            feed=num(r.get("zdroj_shorts_feed_pct")), search=num(r.get("zdroj_vyhledavani_pct")),
            hashsrc=num(r.get("zdroj_hashtagy_pct")), sources=r.get("zdroje_vse", ""),
            typ=(lab.get("typ_obsahu") or r.get("typ_obsahu") or "").strip(),
            sada=(lab.get("sada") or r.get("sada") or "").strip(),
        ))
    return vids


# ---------- statistika ----------
def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    rk = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            rk[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return rk


def spearman(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    if n < 5:
        return None, n
    rx, ry = ranks([p[0] for p in pairs]), ranks([p[1] for p in pairs])
    mx, my = st.mean(rx), st.mean(ry)
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if sx == 0 or sy == 0:
        return None, n
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy), n


def perm_pvalue(with_, without, iters=5000, seed=1):
    """Permutační test rozdílu průměrů log(zhlédnutí). Dvoustranný."""
    a = [math.log10(max(v, 1)) for v in with_]
    b = [math.log10(max(v, 1)) for v in without]
    obs = abs(st.mean(a) - st.mean(b))
    pool, na = a + b, len(a)
    rng = random.Random(seed)
    hits = 0
    for _ in range(iters):
        rng.shuffle(pool)
        if abs(st.mean(pool[:na]) - st.mean(pool[na:])) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (iters + 1)


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 0.0


def fmt(x, nd=0, suffix=""):
    if x is None:
        return "—"
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",") + suffix


# ---------- analýza ----------
def analyze(vids, min_age, min_support):
    L = []
    P = L.append
    usable = [v for v in vids if v["views"] is not None]
    old = [v for v in usable if (v["age_d"] or 0) >= min_age]
    young = [v for v in usable if v not in old]
    P(f"# Analýza hashtagů – {len(usable)} videí\n")
    P(f"- Použito v analýze (stáří ≥ {min_age} dny): **{len(old)}**")
    P(f"- Vyřazeno jako příliš mladé: {len(young)}"
      + (" (" + ", ".join(v['nazev'] for v in young) + ")" if young else ""))
    if len(old) < 8:
        P(f"\n> ⚠️ **Málo dat ({len(old)} videí).** Cokoli níže je jen popis vzorku, ne důkaz. "
          "Sada tagů se u většiny videí opakuje, takže nejde oddělit vliv jednotlivých tagů. "
          "Rozumný práh pro první hrubé závěry je ~15–20 videí s různými sadami.")

    # --- přehled videí
    P("\n## Videa podle zhlédnutí\n")
    P("| Video | Zhl. | Stáří | Tagů | Feed % | Hashtag % | Zůstali % | Prům. sledování % | Typ |")
    P("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for v in sorted(usable, key=lambda v: -v["views"]):
        flag = "" if v in old else " *(mladé)*"
        P(f"| {v['nazev']}{flag} | {fmt(v['views'])} | {fmt(v['age_d'])} d | {v['n_tags']} | "
          f"{fmt(v['feed'],1)} | {fmt(v['hashsrc'],1)} | {fmt(v['stayed'],1)} | "
          f"{fmt(v['avg_view'],1)} | {v['typ'] or '—'} |")

    # --- zdroj hashtagy
    hs = [v["hashsrc"] for v in usable if v["hashsrc"] is not None]
    P("\n## Přivádějí hashtagy vůbec někoho?\n")
    if hs:
        P(f"Podíl návštěvnosti ze zdroje „hashtagy“: průměr {fmt(st.mean(hs),2,' %')}, "
          f"max {fmt(max(hs),2,' %')} (n={len(hs)}).")
        if max(hs) < 1:
            P("\n**Tagy přímo nepřivádějí téměř nikoho.** To neznamená, že nepomáhají nepřímo "
              "(YouTube je může použít ke zařazení do Shorts feedu), ale přímý kanál to není.")
    else:
        P("Data o zdroji hashtagů chybí.")
    P("\nPoznámka: počty tagů nad limit YouTube (15 podle starších zdrojů, 60 podle novějších; "
      "jisté to nemám) mohou způsobit, že se **všechny** hashtagy ignorují. "
      f"Videa nad 15 tagů: {sum(v['n_tags']>15 for v in usable)}, nad 60: {sum(v['n_tags']>60 for v in usable)}.")

    # --- korelace
    P("\n## Co koreluje se zhlédnutími (Spearman, vyžaduje ≥5 videí)\n")
    views = [v["views"] for v in old]
    rows = [("počet hashtagů", [v["n_tags"] for v in old]),
            ("délka videa (s)", [v["dur"] for v in old]),
            ("hodina publikace", [v["hour"] for v in old]),
            ("zůstali sledovat %", [v["stayed"] for v in old]),
            ("průměrná míra sledování %", [v["avg_view"] for v in old]),
            ("podíl Shorts feed %", [v["feed"] for v in old]),
            ("stáří (dny)", [v["age_d"] for v in old])]
    P("| Proměnná | ρ | n |\n|---|---:|---:|")
    for name, xs in rows:
        r, n = spearman(xs, views)
        P(f"| {name} | {fmt(r,2) if r is not None else '—'} | {n} |")
    P("\nČtení: |ρ| < 0,3 slabé, 0,3–0,6 střední, > 0,6 silné. Korelace není příčina; "
      "pokud nejvíc vysvětluje retence (zůstali / míra sledování), je za úspěchem pravděpodobně obsah, ne tagy.")

    # --- typ obsahu
    types = defaultdict(list)
    for v in old:
        if v["typ"]:
            types[v["typ"]].append(v["views"])
    if types:
        P("\n## Typ obsahu (kontrola matoucího faktoru)\n")
        P("| Typ | n | medián zhl. | min–max |\n|---|---:|---:|---|")
        for t, xs in sorted(types.items(), key=lambda kv: -st.median(kv[1])):
            P(f"| {t} | {len(xs)} | {fmt(st.median(xs))} | {fmt(min(xs))}–{fmt(max(xs))} |")
        P("\nPorovnávej tagy **uvnitř jednoho typu obsahu**, jinak měříš obsah, ne tagy.")
    else:
        P("\n> Tip: doplň štítky `typ_obsahu` (komedie/horor/…) přes `--labels`, "
          "jinak nejde oddělit obsah od hashtagů.")

    # --- podobnost sad
    if len(old) >= 2:
        P("\n## Podobnost sad tagů mezi videi (Jaccard)\n")
        pairs = sorted(((jaccard(a["tags"], b["tags"]), a, b) for a, b in combinations(old, 2)),
                       key=lambda t: -t[0])
        for j, a, b in pairs[:8]:
            P(f"- {fmt(j*100)} % shoda: {a['nazev']} ↔ {b['nazev']}")
        P("\nVysoká shoda = prakticky jeden pokus, ne dva nezávislé. "
          "Pro testování musí sady být opravdu různé.")

    # --- jednotlivé tagy, seskupené podle identického vzoru výskytu
    P(f"\n## Jednotlivé hashtagy (min. {min_support} videí s tagem i bez něj)\n")
    n = len(old)
    presence = defaultdict(set)
    for v in old:
        for t in v["tags"]:
            presence[t].add(v["id"])
    groups = defaultdict(list)
    for t, ids in presence.items():
        if min_support <= len(ids) <= n - min_support:
            groups[frozenset(ids)].append(t)
    out = []
    byid = {v["id"]: v for v in old}
    for ids, tags in groups.items():
        w = [byid[i]["views"] for i in ids]
        wo = [v["views"] for v in old if v["id"] not in ids]
        mw, mwo = st.median(w), st.median(wo)
        p = perm_pvalue(w, wo) if n <= 14 or len(w) * len(wo) > 0 else 1.0
        out.append(dict(tags=sorted(tags), n_with=len(w), n_without=len(wo), med_with=mw,
                        med_without=mwo, ratio=(mw / mwo if mwo else None), p=p))
    out.sort(key=lambda d: (d["p"], -(d["ratio"] or 0)))
    if not out:
        P("Žádný tag nemá dost variability (je u všech nebo skoro u žádného videa). "
          "Nasbírej víc videí s **různými** sadami.")
    else:
        P("Tagy se **shodným vzorem výskytu** jsou sloučeny – data je nedokážou rozlišit.\n")
        P("| Skupina tagů (ukázka) | Počet | S tagem (n, medián) | Bez (n, medián) | Poměr | p |")
        P("|---|---:|---|---|---:|---:|")
        for d in out[:25]:
            sample = " ".join(d["tags"][:5]) + (f" … (+{len(d['tags'])-5})" if len(d["tags"]) > 5 else "")
            P(f"| {sample} | {len(d['tags'])} | {d['n_with']}, {fmt(d['med_with'])} | "
              f"{d['n_without']}, {fmt(d['med_without'])} | "
              f"{fmt(d['ratio'],2,'×') if d['ratio'] else '—'} | {fmt(d['p'],3)} |")
        P(f"\nTestováno {len(out)} skupin najednou, takže ~{fmt(0.05*len(out),1)} „významných“ "
          "(p<0,05) vyjde jen náhodou. Bere to jako nápovědu k dalšímu testu, ne jako důkaz.")
    return "\n".join(L), old, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="CSV soubory (lze použít zástupné znaky)")
    ap.add_argument("--min-age-days", type=float, default=3)
    ap.add_argument("--min-support", type=int, default=2)
    ap.add_argument("--labels")
    ap.add_argument("--out", default="analyza_vystup")
    a = ap.parse_args()

    paths = sorted({p for pat in a.files for p in glob.glob(pat)})
    if not paths:
        sys.exit("Žádné CSV nenalezeno.")
    vids = load_videos(paths, a.labels)
    if not vids:
        sys.exit("V CSV nejsou žádná videa.")
    report, old, tagstats = analyze(vids, a.min_age_days, a.min_support)
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    (out / "report.md").write_text(report, encoding="utf-8")
    with open(out / "tagy.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["tagy", "pocet_tagu", "n_s", "n_bez", "median_s", "median_bez", "pomer", "p"])
        for d in tagstats:
            w.writerow([" ".join(d["tags"]), len(d["tags"]), d["n_with"], d["n_without"],
                        d["med_with"], d["med_without"], d["ratio"], d["p"]])
    with open(out / "videa.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["video_id", "nazev", "zhlednuti", "stari_dni", "pocet_tagu", "typ", "sada", "prvni3"])
        for v in vids:
            w.writerow([v["id"], v["nazev"], v["views"], v["age_d"], v["n_tags"], v["typ"], v["sada"], " ".join(v["first3"])])
    print(report)
    print(f"\n[Uloženo do: {out.resolve()}]")


if __name__ == "__main__":
    main()
