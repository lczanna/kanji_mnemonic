#!/usr/bin/env python3
"""
Tap meanings for な-adjectives by what follows them (data/na_glosses.json): before な the adjective, before に the
adverb (自由に: freely), not the dictionary's first sense, which is often the noun (自由: freedom). Only words written
in their dictionary form match, so an inflected or longer word is left alone.

  python3 tools/na_glosses.py      # apply to grammar.json, examples.json and exam.json in place; run after the other gloss tools
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ['grammar.json', 'examples.json', 'exam.json']


def fix(gl, fixes):
    n = 0
    for text, words in gl.items():
        for g in words:
            st, ln, lemma = g[0], g[1], g[3]
            m = fixes.get(f'{lemma}|{text[st + ln:st + ln + 1]}')
            if m and text[st:st + ln] == lemma and g[5] != m:
                g[5] = m; n += 1
    return n


def walk(o, fixes):
    n = 0
    if isinstance(o, dict):
        for k, v in o.items():
            n += fix(v, fixes) if k == 'gl' and isinstance(v, dict) else walk(v, fixes)
    elif isinstance(o, list):
        for v in o:
            n += walk(v, fixes)
    return n


def examples(data, fixes):
    """examples.json: word -> [[sentence, english, tap meanings], ...]."""
    return sum(fix({ex[0]: ex[2]}, fixes) for exs in data.values() for ex in exs if len(ex) > 2 and isinstance(ex[2], list))


def main():
    fixes = {k: v for k, v in json.loads((ROOT / 'data' / 'na_glosses.json').read_text(encoding='utf8')).items() if not k.startswith('_')}
    for name in FILES:
        path = ROOT / name
        raw = path.read_text(encoding='utf8')
        data = json.loads(raw)
        n = examples(data, fixes) if name == 'examples.json' else walk(data, fixes)
        if n:   # keep the file's own layout
            sep = (', ', ': ') if '", "' in raw[:2000] else (',', ':')
            path.write_text(json.dumps(data, ensure_ascii=False, separators=sep), encoding='utf8')
        print(f'{name}: {n} meanings')


if __name__ == '__main__':
    main()
