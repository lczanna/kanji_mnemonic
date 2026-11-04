#!/usr/bin/env python3
"""
Rank the words deck by exam value, so study time goes to the words you'll meet most.

Value = how many of the Tanaka corpus's ~147,000 everyday sentences use the word (examples.utf index lines,
log scale), with small bonuses for the curated words shown on kanji cards and JMdict's "common word" tags.
Writes "p" (1 = most valuable) into vocab.json. The app studies words in that order.

  python3 tools/rank_vocab.py examples.utf.gz JMdict_e.gz
"""
import collections, gzip, json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEAD = re.compile(r'^([^(\[{~]+)')


def main():
    count = collections.Counter()
    for line in gzip.open(sys.argv[1]).read().decode('utf8').splitlines():
        if line.startswith('B: '):
            for tok in set(line[3:].split()):
                m = HEAD.match(tok)
                if m:
                    count[m.group(1)] += 1
    common, kanji_of = set(), collections.defaultdict(set)
    for e in re.finditer(r'<entry>(.*?)</entry>', gzip.open(sys.argv[2]).read().decode(), re.S):
        e = e.group(1)
        kebs, rebs = re.findall(r'<keb>([^<]+)<', e), re.findall(r'<reb>([^<]+)<', e)
        if re.search(r'<(ke|re)_pri>(ichi1|news1|spec1|spec2)<', e):
            common.update(kebs + rebs)
        for r in rebs:
            kanji_of[r].update(kebs)

    path = ROOT / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf8'))

    def value(v):
        n = count[v['w']]
        if v.get('f') == 'kana':
            # The corpus files kana words under their kanji spelling (ちょうど under 丁度).
            n = max([n, count[v['r']]] + [count[k] for k in kanji_of.get(v['r'], ())])
        # Card words were picked for the exam, so they get a nudge; frequency still decides.
        return math.log1p(n) + (1.0 if v.get('src') == 'card' else 0) + (0.5 if v['w'] in common or v['r'] in common else 0)

    for rank, v in enumerate(sorted(vocab, key=value, reverse=True), 1):
        v['p'] = rank
    path.write_text(json.dumps(vocab, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print('top 30:', ' '.join(v['w'] for v in sorted(vocab, key=lambda v: v['p'])[:30]))


if __name__ == '__main__':
    main()
