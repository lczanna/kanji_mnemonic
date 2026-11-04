#!/usr/bin/env python3
"""
Check the wrong options of the "pick the right spelling" quiz (vocab.json "d") against JMdict.

An option that is a real spelling of the same word (彼等 for 彼ら, 観る for 見る, お目にかかる) would mark a
correct answer wrong, so it is replaced by a sound-alike: one kanji swapped for a deck kanji with the same
on'yomi (the exam's own trap, 天才 → 天歳). Options that are real words with another meaning stay, and get
"dx": {option: "reading · meaning"} so the app can say what they mean after you answer.

  python3 tools/check_spell_options.py JMdict_e.gz      # rewrites vocab.json
"""
import json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gloss_grammar import load_jmdict_entries  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KANJI = lambda ch: '一' <= ch <= '鿿'


def main():
    jm = load_jmdict_entries(sys.argv[1])
    deck = json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards']
    by_on = {}
    for k in deck:
        for on in k.get('on', []):
            by_on.setdefault(on, []).append(k['kanji'])
    on_of = {k['kanji']: k.get('on', []) for k in deck}
    path = ROOT / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf8'))

    def same_word(o, v):
        """o is another way to write the same word: listed in v's own JMdict entry, written partly or wholly in
        kana (立ちあがる, 御目にかかる), or with digits (１人１人). Homophones that are other words (冷める for 覚める)
        are the exam's trap and stay."""
        w = v['w']
        if o == v['r'] or any(o in e['kebs'] for e in jm.get(w, []) if w in e['kebs'] and v['r'] in e['rebs']):
            return True
        if any(c in o for c in '０１２３４５６７８９0123456789'):
            return True
        ko, kw = [c for c in o if KANJI(c)], [c for c in w if KANJI(c)]
        it = iter(kw)
        return len(ko) < len(kw) and all(c in it for c in ko) and o != w   # some kanji written in kana instead


    def real(o):
        es = [e for e in jm.get(o, []) if o in e['kebs']]
        if not es:
            return None
        e = es[0]
        return f"{e['rebs'][0]} · {'; '.join(e['senses'][0][:2])}"

    def candidates(v, taken):
        rnd = random.Random(v['w'])
        out = []
        for i, ch in enumerate(v['w']):
            if not KANJI(ch):
                continue
            for on in on_of.get(ch, []):
                for c in by_on.get(on, []):
                    o = v['w'][:i] + c + v['w'][i + 1:]
                    if c != ch and o not in taken and not same_word(o, v):
                        out.append((real(o) is not None, rnd.random(), o))
        return [o for _, _, o in sorted(out)]   # made-up spellings first: they can't be mistaken for another word

    replaced, explained = [], 0
    for v in vocab:
        d = v.get('d') or []
        if not d:
            continue
        keep = [o for o in d if not same_word(o, v)]
        if len(keep) < len(d):
            fresh = candidates(v, set(keep) | {v['w']})
            new = keep + fresh[:len(d) - len(keep)]
            replaced.append((v['w'], [o for o in d if o not in keep], new[len(keep):]))
            v['d'] = new if len(new) == len(d) else keep if len(keep) >= 2 else []
        dx = {o: real(o) for o in v.get('d', []) if real(o)}
        if dx:
            v['dx'] = dx; explained += len(dx)
        else:
            v.pop('dx', None)
    path.write_text(json.dumps(vocab, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    for w, old, new in replaced:
        print(w, old, '→', new)
    print(f'{len(replaced)} words had a valid spelling among the wrong options; {explained} options are real words (explained)')


if __name__ == '__main__':
    main()
