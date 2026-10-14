#!/usr/bin/env python3
"""
Look-alike kanji groups for the app: data/lookalike_groups.json (groups, tips, picture scenes, checked by hand)
plus stroke drawings from KanjiVG → lookalikes.json, which the app loads.

For each kanji the strokes come from KanjiVG (CC BY-SA 3.0, Ulrich Apel, https://kanjivg.tagaini.net). Strokes are
matched between look-alikes by where they start and end; the strokes of a kanji that have no match in its closest
look-alike are the ones that tell them apart, and the app colours them.

  python3 tools/build_lookalikes.py kanjivg.xml.gz      # writes lookalikes.json
"""
import gzip, json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NUM = re.compile(r'[MmCcSsLlHhVvZz]|-?\d*\.?\d+(?:e-?\d+)?')


def polyline(d):
    """Points along an SVG path (KanjiVG uses M, C/c, S/s and occasionally L/l/H/V), curves sampled every 1/6."""
    toks, i, x, y, cmd, pts, last_ctrl = NUM.findall(d), 0, 0.0, 0.0, None, [], None
    def cubic(p0, p1, p2, p3):
        for t in (1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6, 1):
            u = 1 - t
            pts.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                        u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd, i = t, i + 1
            continue
        n = {'M': 2, 'm': 2, 'L': 2, 'l': 2, 'C': 6, 'c': 6, 'S': 4, 's': 4, 'H': 1, 'h': 1, 'V': 1, 'v': 1}[cmd]
        a = [float(v) for v in toks[i:i + n]]; i += n
        rel = cmd.islower()
        P = lambda k: (a[k] + (x if rel else 0), a[k + 1] + (y if rel else 0))
        if cmd in 'Mm':
            x, y = P(0); pts.append((x, y)); last_ctrl = None
            cmd = 'l' if rel else 'L'
        elif cmd in 'Ll':
            x, y = P(0); pts.append((x, y)); last_ctrl = None
        elif cmd in 'Hh':
            x = a[0] + (x if rel else 0); pts.append((x, y))
        elif cmd in 'Vv':
            y = a[0] + (y if rel else 0); pts.append((x, y))
        elif cmd in 'Cc':
            c1, c2, e = P(0), P(2), P(4); cubic((x, y), c1, c2, e); last_ctrl, (x, y) = c2, e
        elif cmd in 'Ss':
            c1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl else (x, y)
            c2, e = P(0), P(2); cubic((x, y), c1, c2, e); last_ctrl, (x, y) = c2, e
    return pts


def resample(pts, n=12):
    """n points evenly spaced along the stroke, so two strokes can be compared point by point."""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(seg) or 1
    out, k, acc = [], 0, 0.0
    for s in range(n):
        target = total * s / (n - 1)
        while k < len(seg) - 1 and acc + seg[k] < target:
            acc += seg[k]; k += 1
        if not seg:
            out.append(pts[0]); continue
        f = (target - acc) / seg[k] if seg[k] else 0
        a, b = pts[k], pts[k + 1]
        out.append((a[0] + (b[0] - a[0]) * min(1, f), a[1] + (b[1] - a[1]) * min(1, f)))
    return out


def shape(d):
    return resample(polyline(d))


def load_kvg(path, wanted):
    x = gzip.open(path).read().decode('utf8')
    out = {}
    for m in re.finditer(r'<kanji id="kvg:kanji_([0-9a-f]{5})">(.*?)</kanji>', x, re.S):
        ch = chr(int(m.group(1), 16))
        if ch in wanted:
            out[ch] = re.findall(r'<path id="kvg:[0-9a-f]{5}(?:-[^"]*)?-s\d+"[^>]*\sd="([^"]+)"', m.group(2))
    return out


def unmatched(a, b, tol=9):
    """Indexes of strokes in a with no stroke in b that follows the same path (mean distance along the stroke,
    in KanjiVG's 109-unit box), matching the closest pairs first."""
    sa, sb = [shape(d) for d in a], [shape(d) for d in b]
    cost = lambda p, q: sum(math.dist(u, v) for u, v in zip(p, q)) / len(p)
    pairs = sorted((cost(p, q), i, j) for i, p in enumerate(sa) for j, q in enumerate(sb))
    used_a, used_b = set(), set()
    length = lambda d: sum(math.dist(u, v) for u, v in zip(polyline(d), polyline(d)[1:]))
    la, lb = [length(d) for d in a], [length(d) for d in b]
    differ = set()
    for c, i, j in pairs:
        if c <= tol and i not in used_a and j not in used_b:
            used_a.add(i); used_b.add(j)
            if min(la[i], lb[j]) / max(la[i], lb[j]) < 0.8:   # same stroke, clearly longer or shorter (未 / 末)
                differ.add(i)
    return sorted(differ | {i for i in range(len(a)) if i not in used_a})


def main():
    groups = json.loads((ROOT / 'data' / 'lookalike_groups.json').read_text(encoding='utf8'))
    strokes = load_kvg(sys.argv[1], {k for g in groups for k in g['kanji']})
    out, missing = [], []
    for g in groups:
        ks = [k for k in g['kanji'] if k in strokes]
        missing += [k for k in g['kanji'] if k not in strokes]
        diff = {}
        for k in ks:
            others = [o for o in ks if o != k]
            # Against the closest look-alike: the one sharing the most strokes.
            # (one that differs in at least one stroke: 持 has nothing 特 lacks, so it is compared with 待).
            diffs = sorted((unmatched(strokes[k], strokes[o]) for o in others), key=len)
            best = next((d for d in diffs if d), [])
            diff[k] = best
        out.append({**g, 'kanji': ks, 'strokes': {k: strokes[k] for k in ks}, 'diff': diff})
    (ROOT / 'lookalikes.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{len(out)} groups, {sum(len(g["kanji"]) for g in out)} kanji' + (f'; no strokes for {missing}' if missing else ''))


if __name__ == '__main__':
    main()
