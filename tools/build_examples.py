#!/usr/bin/env python3
"""
Pick 2–3 short example sentences for every word in vocab.json, so a new word is seen in context.

Sentences come from the Tanaka corpus (examples.utf, CC-BY, http://ftp.edrdg.org/pub/Nihongo/examples.utf.gz),
whose index lines tag each word with its dictionary form and reading. A sentence qualifies when it uses the
word in that reading, is short, and has no kanji outside the deck (apart from the word's own kanji).
Checked sentences (marked ~ in the index) come first. Each sentence gets tap-to-read glosses, with each
word's meaning taken from the sense the corpus tags for that sentence.

  python3 tools/build_examples.py examples.utf.gz JMdict_e.gz     # writes examples.json
"""
import gzip, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gloss_grammar import gloss_indexed, load_jmdict_entries  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOKEN = re.compile(r'^([^(\[{~]+)(?:\(([^)]+)\))?(?:\[\d+\])?(?:\{([^}]+)\})?(~)?$')
PER_WORD, MAX_JA, MAX_EN = 3, 28, 90


def main():
    deck_kanji = {c['kanji'] for c in json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards']}
    vocab = json.loads((ROOT / 'vocab.json').read_text(encoding='utf8'))
    wanted = {}
    for v in vocab:
        wanted.setdefault(v['w'], set()).add(v['r'])
        if v.get('f') == 'kana':
            wanted.setdefault(v['r'], set()).add(v['r'])

    found = {}   # word -> list of (checked, length, ja, en)
    lines = gzip.open(sys.argv[1]).read().decode('utf8').splitlines()
    for a, b in zip(lines, lines[1:]):
        if not (a.startswith('A: ') and b.startswith('B: ')):
            continue
        ja, en = a[3:].split('\t', 1)
        en = en.split('#ID=')[0].strip()
        if len(ja) > MAX_JA or len(en) > MAX_EN or len(ja) < 6:
            continue
        for tok in b[3:].split():
            m = TOKEN.match(tok)
            if not m or m.group(1) not in wanted:
                continue
            head, reading, checked = m.group(1), m.group(2), bool(m.group(4))
            readings = wanted[head]
            if reading and reading not in readings:
                continue
            # The index files 留める under 止める; keep only sentences that write the word as taught.
            if re.sub(r'[ぁ-ゖ]+$', '', head) not in ja:
                continue
            # Stay at the learner's level: no kanji beyond the deck, except the word's own.
            if any(ch not in deck_kanji and ch not in head for ch in re.findall(r'[一-鿿々]', ja) if ch != '々'):
                continue
            found.setdefault(head, []).append((not checked, abs(len(ja) - 16), ja, en, b[3:]))

    entries = load_jmdict_entries(sys.argv[2])
    out = {}
    for v in vocab:
        pool = sorted(set(found.get(v['w'], []) + (found.get(v['r'], []) if v.get('f') == 'kana' else [])))
        picks, seen = [], set()
        for _, _, ja, en, bline in pool:
            if ja in seen:
                continue
            seen.add(ja)
            # Meanings come from the corpus's own sense tags for this sentence (gloss_indexed).
            picks.append([ja, en, gloss_indexed(ja, en, bline, entries)])
            if len(picks) == PER_WORD:
                break
        if picks:
            out[v['w']] = picks
    (ROOT / 'examples.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{len(out)} of {len(vocab)} words have examples, {sum(map(len, out.values()))} sentences')


if __name__ == '__main__':
    main()
