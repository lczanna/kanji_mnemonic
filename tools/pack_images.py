#!/usr/bin/env python3
"""
Bundle the card pictures into a few JSON packs for the Claude link, which holds at most 512 files.

The app loads images/n3/<file>.jpg first; when that is missing it reads images/packs/index.json
to find the pack holding the picture (kanji by character, words by id), then shows it from that pack.
Kanji are packed in deck order and words most useful first, so a study session needs only a few packs.

  python3 tools/pack_images.py OUT_DIR    # writes OUT_DIR/images/packs/index.json and p00.json, p01.json, ...

Pictures go into the packs as WebP (about 37% smaller than the JPEG files at the same look), so all of them
fit the link's 256 MB per version next to the audio packs. The JPEG files in the repo stay as they are.

Rebuild the packs whenever pictures or the deck order change, then publish them with the app.
"""
import base64, io, json, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PER_PACK = 32


def main():
    out = Path(sys.argv[1]) / 'images' / 'packs'
    out.mkdir(parents=True, exist_ok=True)
    cards = [(c['kanji'], c['image']) for c in json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards'] if c.get('image')]
    words = sorted((v for v in json.loads((ROOT / 'vocab.json').read_text(encoding='utf8')) if v.get('img')), key=lambda v: v.get('p', 9999))
    cards += [(v['id'], v['img']) for v in words]
    deck = json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))
    cards += [('c:' + p['kanji'], p['image']) for p in deck.get('partCards', []) if p.get('image')]   # part cards, keyed c:<glyph>
    looks = ROOT / 'lookalikes.json'
    if looks.exists():   # look-alike group pictures, keyed l:<group id>
        for g in json.loads(looks.read_text(encoding='utf8')):
            cards += [('l:' + g['id'], g['img'])] if g.get('img') else []
            cards += [(f"l:{g['id']}:{k}", m['img']) for k, m in (g.get('mn') or {}).items() if m.get('img')]
    index = {}
    for n in range(0, len(cards), PER_PACK):
        pack = {}
        for key, rel in cards[n:n + PER_PACK]:
            buf = io.BytesIO()
            Image.open(ROOT / rel).convert('RGB').save(buf, 'WEBP', quality=75, method=6)
            pack[key] = 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()
            index[key] = n // PER_PACK
        (out / f'p{n // PER_PACK:02d}.json').write_text(json.dumps(pack), encoding='utf8')
    (out / 'index.json').write_text(json.dumps(index, ensure_ascii=False), encoding='utf8')
    print(f'{len(index)} pictures in {len(cards) // PER_PACK + bool(len(cards) % PER_PACK)} packs → {out}')


if __name__ == '__main__':
    main()
