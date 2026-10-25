#!/usr/bin/env python3
"""
Add the words of a JLPT level list that the words deck is missing (the deck was built from the N3 list and the
kanji cards, so N4 words like 将来, 地震, 比べる weren't in it). New entries get "src": "n4" (the level), and the
app offers them first in a quick "know it / not yet" sort, so only the ones you don't know become cards.

  python3 tools/add_jlpt_words.py n4.csv examples.utf.gz JMdict_e.gz N4

The list is a CSV with expression,reading,meaning columns (e.g. open-anki-jlpt-decks src/n4.csv). Skipped:
affixes (～区), katakana loanwords, entries JMdict doesn't know (typos), and other spellings of a word the deck has
(子ども when 子供 is in). Each new word gets an exam-value rank between the existing ones, computed as in
tools/rank_vocab.py, without renumbering them. Then run tools/kanji_readings.py and tools/gloss_fixes.py.
"""
import collections, csv, gzip, json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEAD = re.compile(r'^([^(\[{~]+)')
KANJI = re.compile(r'[一-鿿々]')
KATA = re.compile(r'^[ァ-ヺー・]+$')


def main():
    src, examples, jmdict, level = sys.argv[1:5]
    count = collections.Counter()
    for line in gzip.open(examples).read().decode('utf8').splitlines():
        if line.startswith('B: '):
            for tok in set(line[3:].split()):
                m = HEAD.match(tok)
                if m:
                    count[m.group(1)] += 1
    common, kanji_of, entry_of = set(), collections.defaultdict(set), collections.defaultdict(set)
    for n, e in enumerate(re.finditer(r'<entry>(.*?)</entry>', gzip.open(jmdict).read().decode(), re.S)):
        e = e.group(1)
        kebs, rebs = re.findall(r'<keb>([^<]+)<', e), re.findall(r'<reb>([^<]+)<', e)
        if re.search(r'<(ke|re)_pri>(ichi1|news1|spec1|spec2)<', e):
            common.update(kebs + rebs)
        for r in rebs:
            kanji_of[r].update(kebs)
        for x in kebs + (rebs if not kebs else []):
            entry_of[x].add(n)

    def value(v):   # as in tools/rank_vocab.py
        n = count[v['w']]
        if v.get('f') == 'kana':
            n = max([n, count[v['r']]] + [count[k] for k in kanji_of.get(v['r'], ())])
        return math.log1p(n) + (1.0 if v.get('src') == 'card' else 0) + (0.5 if v['w'] in common or v['r'] in common else 0)

    path = ROOT / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf8'))
    deck = {c['kanji'] for c in json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards']}
    have = {v['w'] for v in vocab} | {v['r'] for v in vocab if v.get('f') == 'kana'}
    have_entries = set().union(*(entry_of.get(v['w'], set()) for v in vocab))
    next_id = max(int(v['id'][1:]) for v in vocab) + 1
    ranked = sorted(vocab, key=lambda v: v['p'])
    scores = [(value(v), v['p']) for v in ranked]
    added = []
    for row in csv.DictReader(open(src, encoding='utf8')):
        w, r = row['expression'].split(';')[0].strip(), row['reading'].split(';')[0].strip()
        if r.endswith('する') and not w.endswith('する'):   # 入学 is listed as にゅうがくする
            r = r[:-2]
        if '～' in w or '〜' in w or KATA.match(w) or w in have or not (entry_of.get(w) or entry_of.get(r)):
            continue
        if entry_of.get(w, set()) & have_entries:   # another spelling of a deck word
            continue
        meaning = ', '.join(s.strip() for s in row['meaning'].split(',')[:3])
        ks = [c for c in dict.fromkeys(w) if c in deck]
        f = 'kana' if not KANJI.search(w) else 'kanji' if all(c in deck for c in w if KANJI.match(c)) else 'mixed'
        v = {'w': w, 'r': r, 'm': meaning, 'k': ks, 'f': f, 'd': [], 'id': f'v{next_id}', 'src': level.lower()}
        val = value(v)
        # Just after the last existing word at least as valuable: a fractional rank keeps every existing rank.
        before = max([p for s, p in scores if s >= val], default=0)
        v['p'] = round(before + 0.5 + len(added) * 1e-4, 4)
        next_id += 1
        have.add(w)
        added.append(v)
    vocab += added
    path.write_text(json.dumps(vocab, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{len(added)} {level} words added; in the top 1500: {sum(v["p"] <= 1500 for v in added)}')
    print(' '.join(v['w'] for v in sorted(added, key=lambda v: v['p'])[:60]))


if __name__ == '__main__':
    main()
