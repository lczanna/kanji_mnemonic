#!/usr/bin/env python3
"""
How each kanji is read inside each word (寒さ: 寒 = さむ), written to vocab.json as "kr": {kanji: reading}.

The app shows that reading wherever a word lists or explains its kanji, so a word that uses the native reading
(さむ) doesn't point at the sound-story reading (カン). Readings come from the deck's on/kun lists, allowing the
usual sound changes in compounds: voicing (か→が, ひ→び/ぴ), a small っ (がく→がっ), and 々. Words read as a whole
(今日 きょう, 大人 おとな) get "kr": {} plus "jk": true, and the app says so.

  python3 tools/kanji_readings.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICE = dict(zip('かきくけこさしすせそたちつてとはひふへほ', 'がぎぐげござじずぜぞだぢづでどばびぶべぼ'))
HALF = dict(zip('はひふへほ', 'ぱぴぷぺぽ'))
hira = lambda s: ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def variants(r):
    out = {r}
    if r[0] in VOICE: out.add(VOICE[r[0]] + r[1:])
    if r[0] in HALF: out.add(HALF[r[0]] + r[1:])
    for v in list(out):
        if len(v) > 1 and v[-1] in 'つくちき': out.add(v[:-1] + 'っ')
    return out


I_ROW = dict(zip('うくぐすつぬぶむる', 'いきぎしちにびみり'))
# Words whose split the rules can't find (日 is に only in 日本).
MANUAL = {'日本': {'日': 'に', '本': 'ほん'}, '日本酒': {'日': 'に', '本': 'ほん', '酒': 'しゅ'}}


def readings(k):
    """On readings, and each kun reading's stem plus its forms inside compounds (建.てる: た, たて; 語.る: かたり)."""
    rs = [hira(o) for o in k.get('on', [])]
    for r in k.get('kun', []):
        r = r.replace('-', '')
        stem, _, okuri = r.partition('.')
        rs += [stem, stem + okuri]
        if okuri:
            rs.append(stem + okuri[:-1])
            if okuri[-1] in I_ROW: rs.append(stem + okuri[:-1] + I_ROW[okuri[-1]])
    return [r for r in dict.fromkeys(rs) if r]


def single(w, r, deck):
    """One kanji with kana around it (入る, お腹): the kanji takes whatever reading the kana leave."""
    ks = [i for i, c in enumerate(w) if '\u4e00' <= c <= '\u9fff']
    if len(ks) != 1 or w[ks[0]] not in deck:
        return None
    pre, post = hira(w[:ks[0]]), hira(w[ks[0] + 1:])
    if r.startswith(pre) and r.endswith(post) and len(r) > len(pre) + len(post):
        return [(w[ks[0]], r[len(pre):len(r) - len(post)])]
    return None


def align(w, r, deck):
    """[(char, reading)] for the whole word, or None when it can't be split (a reading of the whole word)."""
    def go(i, j, prev):
        if i == len(w):
            return [] if j == len(r) else None
        c = w[i]
        if not ('一' <= c <= '鿿' or c == '々'):
            h = hira(c)
            return [(c, h)] + rest if r.startswith(h, j) and (rest := go(i + 1, j + len(h), None)) is not None else None
        cands = prev if c == '々' else readings(deck[c]) if c in deck else None
        if cands is None:   # a kanji outside the deck: let it take 1–4 kana
            cands = [r[j:j + n] for n in range(1, 5)]
        for base in sorted(cands, key=len, reverse=True):
            for v in sorted(variants(base) if base else [], key=len, reverse=True):
                if r.startswith(v, j) and (rest := go(i + 1, j + len(v), [base])) is not None:
                    return [(c, v)] + rest
        return None
    return go(0, 0, None)


def main():
    deck = {k['kanji']: k for k in json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards']}
    path = ROOT / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf8'))
    whole = []
    for v in vocab:
        v.pop('kr', None); v.pop('jk', None)
        if not any(c in deck for c in v['w']):
            continue
        parts = list(MANUAL[v['w']].items()) if v['w'] in MANUAL else align(v['w'], v['r'], deck) or single(v['w'], v['r'], deck)
        if parts is None:
            v['kr'], v['jk'] = {}, True; whole.append(f"{v['w']} {v['r']}")
        else:
            v['kr'] = {c: x for c, x in parts if c in deck}
    path.write_text(json.dumps(vocab, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f"{sum('kr' in v for v in vocab) - len(whole)} words split by kanji; {len(whole)} read as a whole:", ' · '.join(whole))


if __name__ == '__main__':
    main()
