#!/usr/bin/env python3
"""
Bundle the recordings (audio/<id>.mp3 listening items, speech/<id>.mp3 words and sentences) into a few packs for the
Claude link, which caps its file count (512) and its size (256 MB a version).
The app plays audio/<id>.mp3 when it exists (GitHub Pages) and otherwise finds the clip in audio/packs/clips.json.

Each pack is the clips' MP3 files one after another (audio/packs/c00.mp3, c01.mp3, ...), and clips.json says where
each clip is: {id: [pack, offset, length]}. Plain bytes, not base64 text, so the packs are a quarter smaller.

  python3 tools/pack_audio.py OUT_DIR    # writes OUT_DIR/audio/packs/clips.json and c00.mp3, c01.mp3, ...
  python3 tools/pack_audio.py OUT_DIR --keep PUBLISHED_CLIPS_JSON
      # every clip stays in the pack the published index puts it in (new clips go into new packs), so re-recorded
      # clips only change their own packs and the rest need not be published again
  python3 tools/pack_audio.py OUT_DIR --keep ... --speech-kbps 20
      # word and sentence clips re-encoded at 20 kbps for the link (listening items stay as recorded): the link holds
      # 256 MB a version. Re-encoded clips are cached in OUT_DIR/../speech_kbps<N>/.
"""
import argparse, json, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_BYTES = 1_100_000   # small packs: playing a word downloads only its pack


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--keep'); ap.add_argument('--speech-kbps', type=int)
    a = ap.parse_args()
    out = Path(a.out) / 'audio' / 'packs'
    keep = {k: v[0] for k, v in json.loads(Path(a.keep).read_text(encoding='utf8')).items()} if a.keep else {}
    out.mkdir(parents=True, exist_ok=True)
    # Listening items (audio/) and recorded words and sentences (speech/) share the packs, keyed by clip id.
    # Speech clips go in study order (speech/index.json lists the most useful words first), so the words of a
    # session mostly share a pack.
    idx = ROOT / 'speech' / 'index.json'
    order = {cid: n for n, cid in enumerate(json.loads(idx.read_text(encoding='utf8')).values())} if idx.exists() else {}
    files = sorted((ROOT / 'audio').glob('*.mp3')) + sorted((ROOT / 'speech').glob('*.mp3'), key=lambda f: order.get(f.stem, 10**9))
    if a.speech_kbps:   # smaller word and sentence clips (speech/), same ids
        cache = Path(a.out).parent / f'speech_kbps{a.speech_kbps}'
        cache.mkdir(parents=True, exist_ok=True)
        def enc(f):
            g = cache / f.name
            if not g.exists() or g.stat().st_mtime < f.stat().st_mtime:
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(f), '-ac', '1', '-ar', '24000', '-b:a', f'{a.speech_kbps}k', str(g)], check=True)
            return g
        speech = [f for f in files if f.parent.name == 'speech']
        with ThreadPoolExecutor(8) as ex:
            small = dict(zip(speech, ex.map(enc, speech)))
        files = [small.get(f, f) for f in files]
    packs, cur, size = [[] for _ in range(max(keep.values(), default=-1) + 1)], [], 0
    for f in files:
        if f.stem in keep:
            packs[keep[f.stem]].append(f)
            continue
        n = f.stat().st_size
        if cur and size + n > PACK_BYTES:
            packs.append(cur); cur, size = [], 0
        cur.append(f); size += n
    if cur:
        packs.append(cur)
    index = {}
    for n, pack in enumerate(packs):
        blob = bytearray()
        for f in pack:
            data = f.read_bytes()
            index[f.stem] = [n, len(blob), len(data)]
            blob += data
        (out / f'c{n:02d}.mp3').write_bytes(bytes(blob))
    (out / 'clips.json').write_text(json.dumps(index, separators=(',', ':')), encoding='utf8')
    print(f'{len(index)} recordings in {len(packs)} packs → {out}')


if __name__ == '__main__':
    main()
