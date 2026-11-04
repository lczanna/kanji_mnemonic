#!/usr/bin/env python3
"""
Hand-checked tap meanings from the sentence audit (data/gloss_audit.json): wrong senses (時 とき "o'clock" -> time,
本 ぽん "origin" -> counter), wrong readings (二度 ふたたび -> にど, 上手 かみて -> じょうず) and one-sentence fixes.

  python3 tools/gloss_audit.py      # apply to grammar.json, examples.json and exam.json; run last, after na_glosses.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def reread(g, new_lr):
    """Change the reading of a gloss entry g (surface reading g[2], dictionary reading g[4]) to new_lr, keeping
    the inflection: 帰して きして -> かえして."""
    old = g[4]
    k = 0
    while k < min(len(old), len(new_lr)) and old[-1 - k] == new_lr[-1 - k]:
        k += 1
    stem_old, stem_new = old[:len(old) - k], new_lr[:len(new_lr) - k]
    if g[2].startswith(stem_old):
        g[2] = stem_new + g[2][len(stem_old):]
    g[4] = new_lr


def fix(text, words, pair, sent):
    n = 0
    for i, g in enumerate(words):
        new = sent.get(text, {}).get(str(i)) or pair.get(f'{g[3]}|{g[4]}|{g[5]}')
        if not new:
            continue
        if isinstance(new, dict):
            if new.get('lr') and g[4] != new['lr']:
                reread(g, new['lr'])
            new = new['m']
        if g[5] != new:
            g[5] = new
        n += 1
    return n


def walk(o, pair, sent):
    n = 0
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'gl' and isinstance(v, dict):
                n += sum(fix(t, w, pair, sent) for t, w in v.items())
            else:
                n += walk(v, pair, sent)
    elif isinstance(o, list):
        for v in o:
            n += walk(v, pair, sent)
    return n


def main():
    data = json.loads((ROOT / 'data' / 'gloss_audit.json').read_text(encoding='utf8'))
    pair, sent = data['pair'], data['sent']
    for name in ['grammar.json', 'examples.json', 'exam.json']:
        path = ROOT / name
        raw = path.read_text(encoding='utf8')
        d = json.loads(raw)
        if name == 'examples.json':   # word -> [[sentence, english, tap meanings], ...]
            n = sum(fix(ex[0], ex[2], pair, sent) for exs in d.values() for ex in exs if len(ex) > 2 and isinstance(ex[2], list))
        else:
            n = walk(d, pair, sent)
        sep = (', ', ': ') if '", "' in raw[:2000] else (',', ':')
        path.write_text(json.dumps(d, ensure_ascii=False, separators=sep), encoding='utf8')
        print(f'{name}: {n} meanings')


if __name__ == '__main__':
    main()
