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


def fix_gloss(ja, gl, fixes):
    """Overwrite meanings in a sentence's gloss list where a checked correction exists."""
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
