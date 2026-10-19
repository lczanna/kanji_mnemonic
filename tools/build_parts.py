#!/usr/bin/env python3
"""
Teach parts before the kanji built from them, and record what each non-deck part is made of.

1. kanji.json gets a top-level "parts" map for every [part] used in a story that is not itself a deck
   kanji: {"Buddhist temple": {"g": "寺", "of": ["soil", "glue"]}}. The app shows it when a part is tapped.
   Breakdowns come from the CHISE IDS data (https://github.com/cjkvi/cjkvi-ids, ids.txt), mapped onto
   the deck's part names (data/primitives.json and the deck keywords).
2. Cards are reordered so that every deck kanji used as a part, directly or inside another part,
   comes before the cards that use it. Otherwise the order is unchanged.
3. A part name can stand for different glyphs: [head] is the kanji 頭 in some stories but the part 頁 in 題,
   [house] is 家 or the roof 宀. When the map's glyph isn't inside a card's kanji (by the IDS breakdown) and
   another glyph with that name is, the card gets "pg": {part name: glyph}, which the app shows instead.
4. Part cards (data/part_cards.json) go into kanji.json "partCards", each with "usedIn": the deck kanji whose
   story uses it (in deck order) and "image" when images/parts/<code>.jpg exists.

  curl -sSO https://raw.githubusercontent.com/cjkvi/cjkvi-ids/master/ids.txt
  python3 tools/build_parts.py ids.txt
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDC = set('⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻')
# Single strokes: a breakdown made only of these says nothing, so basic parts stay unbroken.
STROKES = {'one', 'slash', 'drop', 'walking stick', 'fishhook', 'barb'}
# Where the IDS split doesn't match how the deck names things, or drops a piece it can't name.
OVERRIDES = {'computer': ['rice field', 'soil'], 'fortune-telling': ['magic wand', 'mouth'],
             'excuse': [], 'brush': [], 'adjusted': [], 'acorn': [], 'long robe': [], 'melancholy': [],
             'bushel basket': [], 'bamboo': [], 'axe': []}
# Parts with no character of their own: the app describes where they are instead.
SHAPES = {'stairs': 'the left half of 段'}


def load_ids(path):
    ids = {}
    for line in Path(path).read_text(encoding='utf8').splitlines():
        f = line.split('\t')
        if len(f) < 3 or line.startswith('#'):
            continue
        # Prefer the Japanese form when the sources disagree.
        seqs = f[2:]
        pick = next((s for s in seqs if '[' in s and 'J' in s[s.index('['):]), seqs[0])
        seq = re.sub(r'\[.*?\]', '', pick)
        parts = [ch for ch in seq if ch not in IDC]
        if parts and parts != [f[1]]:
            ids[f[1]] = parts
    return ids


def main():
    ids = load_ids(sys.argv[1])
    deck = json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))
    cards = deck['cards']
    prim = json.loads((ROOT / 'data' / 'primitives.json').read_text(encoding='utf8'))
    by_kanji = {c['kanji']: c for c in cards}
    kw2k = {c['keyword']: c['kanji'] for c in cards}
    # Stories name some deck kanji by their part name (日 is the [sun]), so part names win for display.
    glyph2name = {c['kanji']: c['keyword'] for c in cards}
    glyph2name.update(prim)
    name2glyph = dict(kw2k)
    for g, n in prim.items():
        name2glyph.setdefault(n, g)

    def named_parts(g, depth=0):
        """Break a glyph into parts that have a deck name, going one level deeper for unnamed pieces."""
        out = []
        for p in ids.get(g, []):
            if p in glyph2name:
                out.append(glyph2name[p])
            elif depth < 2:
                out += named_parts(p, depth + 1)
        return out

    # Every part name in a story or a breakdown gets an entry, so each one can be tapped.
    # A part that is a deck kanji has no "of": the app opens that kanji's card instead.
    used = sorted({m for c in cards for m in re.findall(r'\[([^\]]+)\]', c['story'])})
    parts, todo = {}, list(used)
    while todo:
        n = todo.pop()
        if n in parts:
            continue
        g = name2glyph.get(n, '')
        of = [] if g in by_kanji else [p for p in named_parts(g) if p != n]
        if len(of) < 2 or set(of) <= STROKES:
            of = []
        of = OVERRIDES.get(n, of)
        parts[n] = {'g': g, 'of': of}
        if n in SHAPES:
            parts[n]['d'] = SHAPES[n]
        todo += of

    # Which glyph each story part really is in each card's kanji.
    names = {}
    for c in cards:
        names.setdefault(c['keyword'], []).append(c['kanji'])
    for g, n in prim.items():
        names.setdefault(n, []).append(g)

    def inside(g, depth=0):
        out = set()
        for p in ids.get(g, []):
            if p != g:
                out |= {p} | (inside(p, depth + 1) if depth < 5 else set())
        return out

    fixed = 0
    for c in cards:
        within, pg = inside(c['kanji']), {}
        for n in dict.fromkeys(re.findall(r'\[([^\]]+)\]', c['story']) + (c.get('components') or [])):
            g = parts.get(n, {}).get('g')
            alt = [x for x in names.get(n, []) if x in within]
            if g not in within and alt:
                pg[n] = alt[0]
        if pg:
            c['pg'] = pg; fixed += len(pg)
        else:
            c.pop('pg', None)

    def deck_deps(name, seen):
        """Deck kanji a part relies on: the part itself, or the deck kanji inside it."""
        if name in seen:
            return []
        seen.add(name)
        g = parts.get(name, {}).get('g')
        if g in by_kanji:
            return [g]
        return [k for p in parts.get(name, {}).get('of', []) for k in deck_deps(p, seen)]

    def card_deps(c):
        out = []
        for n in re.findall(r'\[([^\]]+)\]', c['story']):
            g = (c.get('pg') or {}).get(n)
            out += ([g] if g in by_kanji else []) if g else deck_deps(n, set())
        return [k for k in out if k != c['kanji']]

    deps = {c['kanji']: card_deps(c) for c in cards}
    order, placed, active = [], set(), set()

    def place(k):
        if k in placed or k in active:
            return
        active.add(k)
        for d in deps[k]:
            place(d)
        active.discard(k)
        placed.add(k)
        order.append(by_kanji[k])

    for c in cards:
        place(c['kanji'])
    pc = json.loads((ROOT / 'data' / 'part_cards.json').read_text(encoding='utf8'))
    part_cards = []
    for g, x in pc.items():
        if g.startswith('_'):
            continue
        used = [c['kanji'] for c in order if any(((c.get('pg') or {}).get(n) or parts.get(n, {}).get('g')) == g
                                                 for n in re.findall(r'\[([^\]]+)\]', c['story']))]
        img = f'images/parts/{ord(g):x}.jpg'
        part_cards.append(dict({'kanji': g, 'keyword': x['keyword'], 'components': x.get('components') or [], 'story': x['story'],
                                'usedIn': used}, **({'image': img} if (ROOT / img).exists() else {})))
    deck['partCards'] = sorted(part_cards, key=lambda p: min((i for i, c in enumerate(order) if c['kanji'] in p['usedIn']), default=9999))
    moved = sum(1 for a, b in zip(cards, order) if a is not b)
    deck['cards'] = order
    deck['parts'] = parts
    (ROOT / 'kanji.json').write_text(json.dumps(deck, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    pos = {c['kanji']: i for i, c in enumerate(order)}
    late = [(k, d) for k in deps for d in deps[k] if pos[d] > pos[k]]
    print(f'{len(parts)} parts recorded, {fixed} story parts point to the glyph really in the kanji, '
          f'{moved} positions changed, parts still taught late: {late}')


if __name__ == '__main__':
    main()
