#!/usr/bin/env python3
"""
Copy the memory hooks in data/word_mnemonics.json into vocab.json (field "mn"), shown on word cards, and the
"don't confuse" notes in data/word_twins.json (field "nc": {other, note}) for words that sound almost the same.
Edit the hooks there and rerun; a word without a hook simply shows none.

  python3 tools/add_word_hooks.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    hooks = json.loads((ROOT / 'data' / 'word_mnemonics.json').read_text(encoding='utf8'))
    path = ROOT / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf8'))
    words = {v['w'] for v in vocab}
    missing = [w for w in hooks if not w.startswith('_') and w not in words]
    assert not missing, f'hooks for words not in the deck: {missing}'
    n = 0
    for v in vocab:
        if v['w'] in hooks:
            v['mn'] = hooks[v['w']]; n += 1
        else:
            v.pop('mn', None)
    twins = json.loads((ROOT / 'data' / 'word_twins.json').read_text(encoding='utf8')) if (ROOT / 'data' / 'word_twins.json').exists() else {}
    assert all(w in words and t['other'] in words for w, t in twins.items()), 'twins for words not in the deck'
    for v in vocab:
        if v['w'] in twins:
            v['nc'] = twins[v['w']]
        else:
            v.pop('nc', None)
    path.write_text(json.dumps(vocab, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{n} words have a memory hook')


if __name__ == '__main__':
    main()
