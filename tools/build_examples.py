#!/usr/bin/env python3
"""
Pick 2–3 short example sentences for every word in vocab.json, so a new word is seen in context.

Sentences come from the Tanaka corpus (examples.utf, CC-BY, http://ftp.edrdg.org/pub/Nihongo/examples.utf.gz),
whose index lines tag each word with its dictionary form and reading. A sentence qualifies when it uses the
word in that reading, is short, and has no kanji outside the deck (apart from the word's own kanji).
Checked sentences (marked ~ in the index) come first. Each sentence gets tap-to-read glosses, with each
word's meaning taken from the sense the corpus tags for that sentence.

Words the corpus can't cover (often kana words like いけない) take checked, written sentences from
data/written_examples.json ({word: [[ja, en, meaning here], ...]}) until they have 2–3.

  python3 tools/build_examples.py examples.utf.gz JMdict_e.gz     # writes examples.json
"""
import gzip, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gloss_grammar import gloss_indexed, gloss_sentence, load_jmdict, load_jmdict_entries  # noqa: E402
from gloss_fixes import fix_example, load  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOKEN = re.compile(r'^([^(\[{~]+)(?:\(([^)]+)\))?(?:\[\d+\])?(?:\{([^}]+)\})?(~)?$')
PER_WORD, MAX_JA, MAX_EN = 3, 28, 90
MAX_JA_LOOSE, MAX_EN_LOOSE = 40, 120   # only for words with fewer than 2 sentences at the learner's level


def main():
    deck_kanji = {c['kanji'] for c in json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards']}
    vocab = json.loads((ROOT / 'vocab.json').read_text(encoding='utf8'))
    wanted = {}
    for v in vocab:
        wanted.setdefault(v['w'], set()).add(v['r'])
        if v.get('f') == 'kana':
            wanted.setdefault(v['r'], set()).add(v['r'])

    # Kana words are often filed under a kanji spelling (まるで as 丸で), so they also match by reading.
    kana_word = {v['r']: v['r'] for v in vocab if v.get('f') == 'kana'}
    found, loose = {}, {}   # word -> list of (unchecked, length, ja, en, index line)
    lines = gzip.open(sys.argv[1]).read().decode('utf8').splitlines()
    for a, b in zip(lines, lines[1:]):
        if not (a.startswith('A: ') and b.startswith('B: ')):
            continue
        ja, en = a[3:].split('\t', 1)
        en = en.split('#ID=')[0].strip()
        if len(ja) > MAX_JA_LOOSE or len(en) > MAX_EN_LOOSE or len(ja) < 6:
            continue
        for tok in b[3:].split():
            m = TOKEN.match(tok)
            if not m:
                continue
            head, reading, checked = m.group(1), m.group(2), bool(m.group(4))
            if head not in wanted and reading in kana_word and reading in ja:
                head = kana_word[reading]
            if head not in wanted:
                continue
            readings = wanted[head]
            if reading and reading not in readings and head not in kana_word:
                continue
            # The index files 留める under 止める; keep only sentences that write the word as taught.
            if re.sub(r'[ぁ-ゖ]+$', '', head) not in ja:
                continue
            row = (not checked, abs(len(ja) - 16), ja, en, b[3:])
            # Stay at the learner's level: short, and no kanji beyond the deck except the word's own.
            strict = len(ja) <= MAX_JA and len(en) <= MAX_EN and not any(
                ch not in deck_kanji and ch not in head for ch in re.findall(r'[一-鿿々]', ja) if ch != '々')
            (found if strict else loose).setdefault(head, []).append(row)

    entries = load_jmdict_entries(sys.argv[2])
    fixes, senses = load('gloss_fixes.json'), load('example_senses.json')   # hand-checked meanings
    written, jm = load('written_examples.json'), load_jmdict(sys.argv[2])
    out = {}
    for v in vocab:
        pool = sorted(set(found.get(v['w'], []) + (found.get(v['r'], []) if v.get('f') == 'kana' else [])))
        if len({p[2] for p in pool}) < 2:   # too few at the learner's level: allow longer ones and unstudied kanji
            pool += sorted(set(loose.get(v['w'], []) + (loose.get(v['r'], []) if v.get('f') == 'kana' else [])))
        picks, seen = [], set()
        for _, _, ja, en, bline in pool:
            if ja in seen:
                continue
            seen.add(ja)
            # Meanings come from the corpus's own sense tags for this sentence (gloss_indexed).
            picks.append(fix_example(v['w'], v['r'], [ja, en, gloss_indexed(ja, en, bline, entries)], fixes, senses))
            if len(picks) == PER_WORD:
                break
        for ja, en, sense in written.get(v['w'], []):
            if len(picks) >= PER_WORD or ja in seen:
                continue
            gl = gloss_sentence(ja, jm)
            for g in gl:   # the word itself: the meaning this sentence uses
                if g[3] in (v['w'], v['r']) or g[4] == v['r']:
                    g[5] = sense
                    break
            picks.append(fix_example(v['w'], v['r'], [ja, en, gl], fixes, senses)); seen.add(ja)
        if picks:
            out[v['w']] = picks
    (ROOT / 'examples.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{len(out)} of {len(vocab)} words have examples, {sum(map(len, out.values()))} sentences')


if __name__ == '__main__':
    main()
