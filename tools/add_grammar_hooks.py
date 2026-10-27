#!/usr/bin/env python3
"""
Copy the grammar memory hooks in data/grammar_mnemonics.json into grammar.json (field "mn": hook, picture, and
"contrast" for patterns easily mixed up), shown on grammar cards. "_families" lists patterns sharing one image
(the よう yo-yo) so each card can show them side by side ("family"); "_rev" marks hooks rewritten after you saw them
("rev"), so the app shows them to you again. A picture drawn from the hook
(tools/gen_images.py --grammar) is kept as "img" while the hook's picture text is unchanged.

  python3 tools/add_grammar_hooks.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    data = json.loads((ROOT / 'data' / 'grammar_mnemonics.json').read_text(encoding='utf8'))
    hooks = {k: v for k, v in data.items() if not k.startswith('_')}
    family = {gid: rows for rows in data.get('_families', {}).values() for gid, _, _ in rows}
    rev = data.get('_rev', {})
    path = ROOT / 'grammar.json'
    grammar = json.loads(path.read_text(encoding='utf8'))
    ids = {g['id'] for g in grammar}
    missing = [k for k in hooks if k not in ids]
    assert not missing, f'hooks for grammar points not in the deck: {missing}'
    n = 0
    for g in grammar:
        h = hooks.get(g['id'])
        if not h:
            g.pop('mn', None); g.pop('img', None)
            continue
        if (g.get('mn') or {}).get('picture') != h.get('picture'):
            g.pop('img', None)   # the scene changed: draw it again
        g['mn'] = {k: h[k] for k in ('hook', 'picture', 'contrast') if h.get(k)}
        if g['id'] in family:
            g['mn']['family'] = family[g['id']]
        if g['id'] in rev:
            g['mn']['rev'] = rev[g['id']]
        n += 1
    path.write_text(json.dumps(grammar, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{n} grammar points have a memory hook')


if __name__ == '__main__':
    main()
