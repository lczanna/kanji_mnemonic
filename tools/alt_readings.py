#!/usr/bin/env python3
"""
Other readings a word's spelling has in the dictionary (空: から, and also そら; 月: つき, がつ, げつ), saved as "ar" in
vocab.json. The reading quiz never offers one of them as a wrong answer, since it would be right too.

  python3 tools/alt_readings.py JMdict_e.gz      # after adding words or changing a reading
"""
import gzip, json, re, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
kata2hira = lambda s: ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def main():
    alt = collections.defaultdict(set)
    for e in re.finditer(r'<entry>(.*?)</entry>', gzip.open(sys.argv[1]).read().decode(), re.S):
        e = e.group(1)
        kebs = re.findall(r'<keb>([^<]+)<', e)
        for r in re.finditer(r'<r_ele>(.*?)</r_ele>', e, re.S):
            r = r.group(1)
            if '<re_nokanji/>' in r:
                continue
            reb = kata2hira(re.search(r'<reb>([^<]+)<', r).group(1))
            if re.fullmatch(r'[ぁ-ゖー]+', reb):
                for k in re.findall(r'<re_restr>([^<]+)<', r) or kebs:
                    alt[k].add(reb)
    path = ROOT / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf8'))
    n = 0
    for v in vocab:
        ar = sorted(alt.get(v['w'], set()) - {kata2hira(v['r'])})
        if ar:
            v['ar'] = ar; n += 1
        else:
            v.pop('ar', None)
    path.write_text(json.dumps(vocab, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{n} words have other readings')


if __name__ == '__main__':
    main()
