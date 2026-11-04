#!/usr/bin/env python3
"""
Bundle the listening recordings (audio/<id>.mp3) into a few JSON packs for the Claude link, which caps its file count.
The app plays audio/<id>.mp3 when it exists (GitHub Pages) and otherwise finds the item in audio/packs/index.json.

  python3 tools/pack_audio.py OUT_DIR    # writes OUT_DIR/audio/packs/index.json and a00.json, a01.json, ...
  python3 tools/pack_audio.py OUT_DIR --keep PUBLISHED_INDEX_JSON
      # every clip stays in the pack the published index puts it in (new clips go into new packs), so re-recorded
      # clips only change their own packs and the rest need not be published again
"""
import argparse, base64, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_BYTES = 1_500_000   # small packs: playing a word downloads only its pack


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--keep')
    a = ap.parse_args()
    out = Path(a.out) / 'audio' / 'packs'
    keep = json.loads(Path(a.keep).read_text(encoding='utf8')) if a.keep else {}
    out.mkdir(parents=True, exist_ok=True)
    # Listening items (audio/) and recorded words and sentences (speech/) share the packs, keyed by clip id.
    # Speech clips go in study order (speech/index.json lists the most useful words first), so the words of a
    # session mostly share a pack.
    idx = ROOT / 'speech' / 'index.json'
    order = {cid: n for n, cid in enumerate(json.loads(idx.read_text(encoding='utf8')).values())} if idx.exists() else {}
    files = sorted((ROOT / 'audio').glob('*.mp3')) + sorted((ROOT / 'speech').glob('*.mp3'), key=lambda f: order.get(f.stem, 10**9))
    index = {}
    packs, cur, size = [{} for _ in range(max(keep.values(), default=-1) + 1)], {}, 0
    for f in files:
        data = 'data:audio/mpeg;base64,' + base64.b64encode(f.read_bytes()).decode()
        if f.stem in keep:
            packs[keep[f.stem]][f.stem] = data
            continue
        if cur and size + len(data) > PACK_BYTES:
            packs.append(cur); cur, size = {}, 0
        cur[f.stem] = data; size += len(data)
    if cur:
        packs.append(cur)
    for n, pack in enumerate(packs):
        index.update({k: n for k in pack})
        (out / f'a{n:02d}.json').write_text(json.dumps(pack), encoding='utf8')
    (out / 'index.json').write_text(json.dumps(index), encoding='utf8')
    print(f'{len(index)} recordings in {len(packs)} packs → {out}')


if __name__ == '__main__':
    main()
