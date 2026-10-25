#!/usr/bin/env python3
"""
Bundle the card pictures into a few JSON packs for the Claude link, which holds at most 512 files.

The app loads images/n3/<file>.jpg first; when that is missing it reads images/packs/index.json
to find the pack holding the picture (kanji by character, words by id), then shows it from that pack.
Kanji are packed in deck order and words most useful first, so a study session needs only a few packs.

  python3 tools/pack_images.py OUT_DIR    # writes OUT_DIR/images/packs/index.json and p00.json, p01.json, ...
  python3 tools/pack_images.py OUT_DIR --keep PUBLISHED_INDEX_JSON
      # every picture stays in the pack the published index puts it in, new pictures go into new packs: adding
      # pictures then changes only the new packs (and packs whose pictures were redrawn or removed)

Pictures go into the packs as WebP (about 37% smaller than the JPEG files at the same look), so all of them
fit the link's 256 MB per version next to the audio packs. The JPEG files in the repo stay as they are.

Rebuild the packs whenever pictures or the deck order change, then publish them with the app.
"""
import argparse, base64, io, json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PER_PACK = 32


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--keep')
    a = ap.parse_args()
    out = Path(a.out) / 'images' / 'packs'
    keep = json.loads(Path(a.keep).read_text(encoding='utf8')) if a.keep else {}
    out.mkdir(parents=True, exist_ok=True)
    cards = [(c['kanji'], c['image']) for c in json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards'] if c.get('image')]
    words = sorted((v for v in json.loads((ROOT / 'vocab.json').read_text(encoding='utf8')) if v.get('img')), key=lambda v: v.get('p', 9999))
    cards += [(v['id'], v['img']) for v in words]
    gram = ROOT / 'grammar.json'   # grammar memory-hook pictures, keyed g:<id>
    cards += [('g:' + g['id'], g['img']) for g in json.loads(gram.read_text(encoding='utf8')) if g.get('img')] if gram.exists() else []
    deck = json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))
    cards += [('c:' + p['kanji'], p['image']) for p in deck.get('partCards', []) if p.get('image')]   # part cards, keyed c:<glyph>
    looks = ROOT / 'lookalikes.json'
    if looks.exists():   # look-alike group pictures, keyed l:<group id>
        for g in json.loads(looks.read_text(encoding='utf8')):
            cards += [('l:' + g['id'], g['img'])] if g.get('img') else []
            cards += [(f"l:{g['id']}:{k}", m['img']) for k, m in (g.get('mn') or {}).items() if m.get('img')]
    # Pack number of each picture: the published one when kept, else the next free packs, PER_PACK at a time.
    first_new = max(keep.values(), default=-1) + 1
    fresh = [key for key, _ in cards if key not in keep]
    where = {key: keep[key] for key, _ in cards if key in keep}
    where.update({key: first_new + i // PER_PACK for i, key in enumerate(fresh)})
    packs = {}
    for key, rel in cards:
        buf = io.BytesIO()
        Image.open(ROOT / rel).convert('RGB').save(buf, 'WEBP', quality=75, method=6)
        packs.setdefault(where[key], {})[key] = 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()
    for n, pack in packs.items():
        (out / f'p{n:02d}.json').write_text(json.dumps(pack), encoding='utf8')
    (out / 'index.json').write_text(json.dumps(where, ensure_ascii=False), encoding='utf8')
    print(f'{len(where)} pictures in {len(packs)} packs → {out}')


if __name__ == '__main__':
    main()
