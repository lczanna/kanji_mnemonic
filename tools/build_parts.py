#!/usr/bin/env python3
"""
Teach parts before the kanji built from them, and record what each non-deck part is made of.

1. kanji.json gets a top-level "parts" map for every [part] used in a story that is not itself a deck
   kanji: {"Buddhist temple": {"g": "寺", "of": ["soil", "glue"]}}. The app shows it when a part is tapped.
   Breakdowns come from the CHISE IDS data (https://github.com/cjkvi/cjkvi-ids, ids.txt), mapped onto
   the deck's part names (data/primitives.json and the deck keywords).
2. Cards are reordered so that every deck kanji used as a part, directly or inside another part,
   comes before the cards that use it. Otherwise the order is unchanged.

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
        todo += of

    def deck_deps(name, seen):
        """Deck kanji a part relies on: the part itself, or the deck kanji inside it."""
        if name in seen:
            return []
        seen.add(name)
        g = parts.get(name, {}).get('g')
        if g in by_kanji:
            return [g]
        return [k for p in parts.get(name, {}).get('of', []) for k in deck_deps(p, seen)]

    deps = {c['kanji']: [k for n in re.findall(r'\[([^\]]+)\]', c['story']) for k in deck_deps(n, set()) if k != c['kanji']]
            for c in cards}
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
    moved = sum(1 for a, b in zip(cards, order) if a is not b)
    deck['cards'] = order
    deck['parts'] = parts
    (ROOT / 'kanji.json').write_text(json.dumps(deck, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    pos = {c['kanji']: i for i, c in enumerate(order)}
    late = [(k, d) for k in deps for d in deps[k] if pos[d] > pos[k]]
    print(f'{len(parts)} parts recorded, {moved} positions changed, parts still taught late: {late}')


if __name__ == '__main__':
    main()
