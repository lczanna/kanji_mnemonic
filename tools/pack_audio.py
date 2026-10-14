#!/usr/bin/env python3
"""
Bundle the listening recordings (audio/<id>.mp3) into a few JSON packs for the Claude link, which caps its file count.
The app plays audio/<id>.mp3 when it exists (GitHub Pages) and otherwise finds the item in audio/packs/index.json.

  python3 tools/pack_audio.py OUT_DIR    # writes OUT_DIR/audio/packs/index.json and a00.json, a01.json, ...
"""
import base64, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PER_PACK = 25


def main():
    out = Path(sys.argv[1]) / 'audio' / 'packs'
    out.mkdir(parents=True, exist_ok=True)
    files = sorted((ROOT / 'audio').glob('*.mp3'))
    index = {}
    for n in range(0, len(files), PER_PACK):
        pack = {f.stem: 'data:audio/mpeg;base64,' + base64.b64encode(f.read_bytes()).decode() for f in files[n:n + PER_PACK]}
        index.update({k: n // PER_PACK for k in pack})
        (out / f'a{n // PER_PACK:02d}.json').write_text(json.dumps(pack), encoding='utf8')
    (out / 'index.json').write_text(json.dumps(index), encoding='utf8')
    print(f'{len(index)} recordings in {(len(files) + PER_PACK - 1) // PER_PACK} packs → {out}')


if __name__ == '__main__':
    main()
