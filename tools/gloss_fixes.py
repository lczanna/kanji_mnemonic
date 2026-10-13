"""
Hand-checked corrections to the tap-to-read meanings, kept apart from the generated files so a rebuild keeps them.

data/gloss_fixes.json:     {sentence: {"<token index>|<dictionary form>": meaning}}, the sense used in that sentence.
data/example_senses.json:  {word: {sentence: [meaning here, same as the card?]}}, for word example sentences.

  python3 tools/gloss_fixes.py      # apply both to grammar.json and examples.json in place
"""
import json
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


def main():
    fixes, senses = load('gloss_fixes.json'), load('example_senses.json')
    vocab = {v['w']: v for v in json.loads((ROOT / 'vocab.json').read_text(encoding='utf8'))}
    gpath, epath = ROOT / 'grammar.json', ROOT / 'examples.json'
    grammar = json.loads(gpath.read_text(encoding='utf8'))
    for g in grammar:
        for ja, gl in (g.get('gl') or {}).items():
            fix_gloss(ja, gl, fixes)
    examples = json.loads(epath.read_text(encoding='utf8'))
    for w, lst in examples.items():
        examples[w] = [fix_example(w, vocab[w]['r'], ex, fixes, senses) for ex in lst]
    gpath.write_text(json.dumps(grammar, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    epath.write_text(json.dumps(examples, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{sum(map(len, fixes.values()))} meaning fixes, {sum(map(len, senses.values()))} example senses applied')


if __name__ == '__main__':
    main()
