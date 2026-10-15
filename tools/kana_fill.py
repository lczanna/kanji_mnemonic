#!/usr/bin/env python3
"""
Tap-to-read meanings for kana words in every sentence the app shows (word examples, grammar, exam practice).

Example sentences are glossed from the corpus's sense tags, which skip most kana words, and the other sentences
only glossed kana words on the short checked list. This adds the kana words the sentence's glosses still miss,
with meanings from tools/kana_glosses.py (data/kana_meanings.json). Glosses already there are kept as they are.
Run it after build_examples.py, gloss_grammar.py or build_exam.py; running it twice changes nothing.

  python3 tools/kana_fill.py
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gloss_grammar import HAS_KANJI, MODE, TOK, kana_gloss  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KANA = re.compile(r'[ぁ-ヿ]')


def fill(text, gl):
    """gl with the missing kana words added, in sentence order."""
    taken = set()
    for g in gl:
        taken.update(range(g[0], g[0] + g[1]))
    # The blank is tokenized as a same-length placeholder so the words next to it keep their offsets.
    t = text.replace('（　）', '＿＿＿')
    toks, pos, add = list(TOK.tokenize(t, MODE)), 0, []
    for i, m in enumerate(toks):
        s = m.surface()
        start = t.index(s, pos)
        pos = start + len(s)
        if HAS_KANJI.search(s) or not KANA.search(s) or taken & set(range(start, start + len(s))):
            continue
        g = kana_gloss(toks, i, text, start)
        if g:
            add.append(g)
    return sorted(gl + add, key=lambda g: g[0]), len(add)


def fill_dict(d):
    n = 0
    for text in list(d):
        d[text], k = fill(text, d[text] or [])
        n += k
        if not d[text]:
            del d[text]   # nothing to tap
    return n


def walk(o):
    """Every gl dict in exam.json, plus word-question sentences and options that had no gloss yet."""
    n = 0
    if isinstance(o, dict):
        if 'options' in o and isinstance(o.get('gl'), dict):
            for t in [o.get('s'), *o['options']]:
                if isinstance(t, str) and t and t not in o['gl']:
                    o['gl'][t] = []
        for k, v in o.items():
            n += fill_dict(v) if k == 'gl' and isinstance(v, dict) else walk(v)
    elif isinstance(o, list):
        for x in o:
            n += walk(x)
    return n


def main():
    load = lambda n: json.loads((ROOT / n).read_text(encoding='utf8'))
    save = lambda n, x: (ROOT / n).write_text(json.dumps(x, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    ex = load('examples.json')
    n = 0
    for lst in ex.values():
        for e in lst:
            e[2], k = fill(e[0], e[2] or [])
            n += k
    save('examples.json', ex)
    print(f'examples.json: {n} kana words added')
    gr = load('grammar.json')
    n = sum(fill_dict(g.setdefault('gl', {})) for g in gr)
    save('grammar.json', gr)
    print(f'grammar.json: {n} kana words added')
    exam = load('exam.json')
    n = walk(exam)
    save('exam.json', exam)
    print(f'exam.json: {n} kana words added')


if __name__ == '__main__':
    main()
