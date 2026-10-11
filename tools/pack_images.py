#!/usr/bin/env python3
"""
Bundle the card pictures into a few JSON packs for the Claude link, which holds at most 512 files.

The app loads images/n3/<file>.jpg first; when that is missing it reads images/packs/index.json
to find the pack holding the kanji, then shows the picture from that pack. Cards are packed in
deck order, so a study session mostly needs one or two packs.

  python3 tools/pack_images.py OUT_DIR    # writes OUT_DIR/images/packs/index.json and p00.json, p01.json, ...

Rebuild the packs whenever pictures or the deck order change, then publish them with the app.
"""
import base64, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PER_PACK = 32


def main():
    out = Path(sys.argv[1]) / 'images' / 'packs'
    out.mkdir(parents=True, exist_ok=True)
    cards = [c for c in json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards'] if c.get('image')]
    index = {}
    for n in range(0, len(cards), PER_PACK):
        pack = {}
        for c in cards[n:n + PER_PACK]:
            pack[c['kanji']] = 'data:image/jpeg;base64,' + base64.b64encode((ROOT / c['image']).read_bytes()).decode()
            index[c['kanji']] = n // PER_PACK
        (out / f'p{n // PER_PACK:02d}.json').write_text(json.dumps(pack), encoding='utf8')
    (out / 'index.json').write_text(json.dumps(index, ensure_ascii=False), encoding='utf8')
    print(f'{len(index)} pictures in {len(cards) // PER_PACK + bool(len(cards) % PER_PACK)} packs → {out}')


if __name__ == '__main__':
    main()
