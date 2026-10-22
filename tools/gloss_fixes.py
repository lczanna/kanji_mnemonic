"""
Hand-checked corrections to the tap-to-read meanings, kept apart from the generated files so a rebuild keeps them.

data/gloss_fixes.json:     {sentence: {"<token index>|<dictionary form>": meaning}}, the sense used in that sentence.
data/example_senses.json:  {word: {sentence: [meaning here, same as the card?]}}, for word example sentences.

  python3 tools/gloss_fixes.py      # apply both to grammar.json and examples.json in place
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    p = ROOT / 'data' / name
    return json.loads(p.read_text(encoding='utf8')) if p.exists() else {}


# Readings the tokenizer picks that aren't the everyday ones (or are plain wrong): dictionary form ->
# (reading it gives, reading to show). The conjugated reading is fixed too (破られて: われ… → やぶれ…).
READINGS = {
    '明日': ('あす', 'あした'), '私': ('わたくし', 'わたし'), '言う': ('ゆう', 'いう'), '公平': ('きんぴら', 'こうへい'),
    '破る': ('わる', 'やぶる'), '破れる': ('われる', 'やぶれる'), '故郷': ('くに', 'こきょう'), '悪口': ('わるぐち', 'わるくち'),
}


def fix_reading(g, text):
    """g is one gloss entry, text the word as written in the sentence (kana-written words keep their reading)."""
    if g[3] not in READINGS or not any('\u4e00' <= c <= '\u9fff' for c in text):
        return
    bad, good = READINGS[g[3]]
    okuri = len(g[3]) - len(g[3].rstrip(KANA))   # trailing kana: 破る -> 1
    stem_bad, stem_good = bad[:len(bad) - okuri], good[:len(good) - okuri]
    if g[2].startswith(stem_bad) and not g[2].startswith(stem_good):
        g[2] = stem_good + g[2][len(stem_bad):]
    if g[4] == bad:
        g[4] = good


KANA = ''.join(chr(c) for c in range(0x3041, 0x3097))


def fix_gloss(ja, gl, fixes):
    """Overwrite meanings in a sentence's gloss list where a checked correction exists, and fix readings."""
    for g in gl:
        fix_reading(g, ja[g[0]:g[0] + g[1]])
    for key, meaning in fixes.get(ja, {}).items():
        i, lemma = key.split('|', 1)
        i = int(i)
        if i < len(gl) and gl[i][3] == lemma:
            gl[i][5] = meaning
    return gl


def fix_example(word, reading, ex, fixes, senses):
    """One example [ja, en, gl] of a word: corrected meanings, plus the word's sense here when it differs from the card."""
    ja, en, gl = ex[:3]
    fix_gloss(ja, gl, fixes)
    here = senses.get(word, {}).get(ja)
    if not here:
        return [ja, en, gl]
    sense, same = here
    for g in gl:
        if g[3] in (word, reading) or g[4] == reading and g[3] in (word, reading):
            g[5] = sense
            break
    return [ja, en, gl] if same else [ja, en, gl, sense]


# In a grammar point's sentences, the words that make up its pattern mean what the pattern means:
# 通じて in 一年を通じて is "(〜を通じて) throughout", not 通ずる "to be open (to traffic)".
PATTERN_LEMMA = {'通ずる': ('通じる', 'つうじる')}


def pattern_senses(g):
    variants = [v.strip().lstrip('〜~').strip() for v in re.split('[／/]', g['pattern'])]
    kanji = {ch for v in variants for ch in v if '\u4e00' <= ch <= '\u9fff'}
    # Hand-checked pattern meanings already in this grammar point's sentences, each with the form it names:
    # に対して has two ("(〜に対して) toward", "(〜のに対して) whereas"), and the sentence decides which applies.
    fixed = {}
    for gl in (g.get('gl') or {}).values():
        for e in gl or []:
            form = re.match(r'\(〜([^)]+)\)', str(e[5]))
            if form and any(v and v in form.group(1) for v in variants):
                fixed.setdefault(e[3], {})[form.group(1)] = e[5]

    def sense(lemma, text):
        own = {ch for ch in lemma if '\u4e00' <= ch <= '\u9fff'}
        if not own or not own <= kanji:   # kana words and compounds (個人的, 外国人向け) keep their own meaning
            return None
        forms = sorted(((f, m) for f, m in (fixed.get(lemma) or {}).items() if f in text), key=lambda x: -len(x[0]))
        if forms:
            return forms[0][1]
        hit = [v for v in variants if own & set(v)]
        return f"(〜{hit[0]}) {g['meaning']}" if hit else None

    o = g.get('order') or {}
    full = o.get('before', '') + ''.join(o.get('chunks') or []) + o.get('after', '')
    entries = [(e, t, 3, 4, 5) for t, gl in (g.get('gl') or {}).items() for e in gl or []] + \
              [(w, full, 0, 1, 2) for chunk in o.get('cgl') or [] for w in chunk]
    n = 0
    for e, text, li, ri, mi in entries:
        if str(e[mi]).startswith('('):   # already a pattern-specific meaning
            continue
        m = sense(e[li], text)
        if m:
            e[mi] = m; n += 1
            if e[li] in PATTERN_LEMMA:
                e[li], e[ri] = PATTERN_LEMMA[e[li]]
    return n


def main():
    fixes, senses = load('gloss_fixes.json'), load('example_senses.json')
    vocab = {v['w']: v for v in json.loads((ROOT / 'vocab.json').read_text(encoding='utf8'))}
    gpath, epath = ROOT / 'grammar.json', ROOT / 'examples.json'
    grammar = json.loads(gpath.read_text(encoding='utf8'))
    pn = 0
    for g in grammar:
        for ja, gl in (g.get('gl') or {}).items():
            fix_gloss(ja, gl, fixes)
        pn += pattern_senses(g)
    examples = json.loads(epath.read_text(encoding='utf8'))
    for w, lst in examples.items():
        examples[w] = [fix_example(w, vocab[w]['r'], ex, fixes, senses) for ex in lst]
    gpath.write_text(json.dumps(grammar, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    epath.write_text(json.dumps(examples, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{sum(map(len, fixes.values()))} meaning fixes, {sum(map(len, senses.values()))} example senses applied, '
          f'{pn} grammar-pattern words given the pattern meaning')


if __name__ == '__main__':
    main()
