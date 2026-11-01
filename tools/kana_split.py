#!/usr/bin/env python3
"""
Words the texts write in kana that the tokenizer cut into pieces or left untapped: かいさつ became かい ("floor") +
さつ, かたな became かた ("shoulder"). In every tap-to-read gloss, a run of kana that spells a common word written
with kanji (改札, 刀) becomes one tappable word with that word's meaning, when:
  - particles, punctuation or the ends of the text surround it, and it is a noun or a deck word, and
  - the glossed pieces inside it (if any) are shorter fragments: none crosses its edges, names this word or is a
    hand-checked phrase meaning.
A reading shared by several common words (きかん: 期間, 機関) lists them all. Deck words come first.

  python3 tools/kana_split.py JMdict_e.gz [--dry]   # run after gloss_audit.py
"""
import gzip, json, re, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KANA = re.compile(r'[ぁ-ゖー]{3,}')
EDGE = set('のをがはにでともへやかね。、！？「」『』（）・ ') | {''}
# Readings that are mostly grammar or other words inside sentences, never joined.
SKIP = {'ましょう', 'でしょう', 'たから', 'からだ', 'ていき', 'いなか', 'ないよう', 'しまい', 'たより', 'ていこう', 'かない',
        'いない', 'いたい', 'すぎる', 'はじめる', 'はじめ', 'はじめて', 'くれる', 'あげる', 'かかる', 'なくなる', 'やすい',
        'ところ', 'ください', 'かって', 'となり', 'したく', 'たいほ', 'ようか', 'さんか', 'いいん', 'ろうか', 'いくら',
        'しよう', 'じょう', 'しょう', 'じゅう', 'しゅう', 'おわり', 'ほしい', 'わたし', 'つける', 'かける', 'いつか', 'なんで',
        'どうし', 'どうか', 'きもの', 'りそう', 'しそう', 'さそう', 'あいて', 'さいてい', 'はいる', 'はやる', 'いためる',
        'ように', 'ために', 'について', 'という', 'ことに', 'ほうが', 'のうち', 'たほう', 'にとって', 'によって', 'において',
        'ことがある', 'ことがない', 'ことになる', 'ことができる', 'ないほう', 'とって', 'そうか', 'いよう', 'ないそう', 'どうや',
        'たよう', 'すいてい', 'いもの', 'いって', 'いってい', 'てきれい', 'かれは', 'はいた', 'なんだ', 'なると', 'ないか',
        'そうし', 'にそう', 'とこう', 'がいや', 'せたい', 'たいわ', 'たいか', 'こうや', 'かこう', 'かどう', 'くよう', 'いまや',
        'もうい', 'さいた', 'もって', 'とっても', 'のなか', 'のやま', 'いいん', 'はなし', 'そうなん', 'こうし', 'いそう', 'なんか',
        'いえいえ', 'おりから', 'そって', 'たいそう', 'くらい', 'ぐらい', 'かしら', 'ここの', 'したで',
        'あんだ', 'いいね', 'いたん', 'いるか', 'いれば', 'おいて', 'きない', 'したい', 'したね', 'しない', 'しょうか', 'すいし',
        'すまい', 'ていない', 'でいたん', 'ないし', 'あそこ', 'どこか', 'けして', 'によると', 'による', 'における', 'にしたがって', 'ほうがいい', 'ほうがよい'}


# Clearer than the dictionary's first sense for how the word is used in the texts.
PLAIN = {'改札': 'ticket gate (at a station)'}


def load(path, deck):
    by = collections.defaultdict(dict)   # reading -> {word: (meaning, is noun, common)}
    x = gzip.open(path).read().decode()
    for e in re.finditer(r'<entry>(.*?)</entry>', x, re.S):
        e = e.group(1)
        kebs = re.findall(r'<keb>([^<]+)<', e)
        if not kebs or not re.search(r'<(ke|re)_pri>(ichi1|news1|spec1|spec2)<', e):
            continue
        sense = re.search(r'<sense>(.*?)</sense>', e, re.S).group(1)
        gl = '; '.join(re.findall(r'<gloss>([^<]+)<', sense)[:2])
        noun = bool(re.search(r'<pos>(&n;|noun \(common\))', e))
        for r in re.findall(r'<reb>([^<]+)<', e):
            if len(r) >= 3 and r not in SKIP:
                by[r].setdefault(kebs[0], (gl, noun))
    for r in by:
        for w in by[r]:
            if w in PLAIN: by[r][w] = (PLAIN[w], by[r][w][1])
    for v in deck:   # the deck's own meaning wins for deck words
        if v['r'] in by and v['w'] in by[v['r']]:
            by[v['r']][v['w']] = (v['m'].split(';')[0].split(', ')[0] if len(v['m']) > 40 else v['m'], by[v['r']][v['w']][1])
    return by


def meaning(r, words, deck_words):
    ws = sorted(words, key=lambda w: (w not in deck_words, w))
    if ws[0] in deck_words:   # a deck word with this reading: only the deck's words (嫌い, not 機雷 "sea mine")
        ws = [w for w in ws if w in deck_words]
    if len(ws) == 1:
        return ws[0], f'{words[ws[0]][0]} ({ws[0]})'
    return ws[0], '; '.join(f'{words[w][0].split(";")[0]} ({w})' for w in ws[:3])


def fix(text, ws, by, deck_words, log):
    n, out = 0, list(ws)
    for run in KANA.finditer(text):
        i = run.start()
        while i < run.end():
            L = next((L for L in range(min(8, run.end() - i), 2, -1) if text[i:i + L] in by), 0)
            if not L:
                i += 1; continue
            a, b, r = i, i + L, text[i:i + L]
            straddle = any(t[0] < a < t[0] + t[1] or t[0] < b < t[0] + t[1] for t in out)
            inside = [t for t in out if a <= t[0] and t[0] + t[1] <= b]
            words = by[r]
            # Only a whole word between particles or punctuation; a noun, or a deck word; never over a hand-checked
            # phrase meaning ("(〜ように) so that") or a piece that already names this word.
            bounded = text[a - 1:a] in EDGE and text[b:b + 1] in EDGE
            nouns = {w: v for w, v in words.items() if v[1] or w in deck_words}
            ok = not straddle and bounded and nouns and all(t[1] < L and not t[5].startswith('(')
                                                             and t[3] not in words and not any(w in t[5] for w in words) for t in inside)
            if ok:
                words = nouns
            if ok:
                w, m = meaning(r, words, deck_words)
                out = [t for t in out if t not in inside] + [[a, L, r, w, r, m]]
                log.append((r, m, text[max(0, a - 6):b + 4], [t[5][:15] for t in inside]))
                n += 1
                i = b
            else:
                i += 1
    out.sort(key=lambda t: t[0])
    ws[:] = out
    return n


def main():
    dry = '--dry' in sys.argv
    deck = json.loads((ROOT / 'vocab.json').read_text(encoding='utf8'))
    deck_words = {v['w'] for v in deck}
    by = load(sys.argv[1], deck)
    log = []
    for name in ['grammar.json', 'examples.json', 'exam.json']:
        path = ROOT / name
        raw = path.read_text(encoding='utf8')
        d = json.loads(raw)
        n = 0
        if name == 'examples.json':
            for exs in d.values():
                for ex in exs:
                    if len(ex) > 2 and isinstance(ex[2], list):
                        n += fix(ex[0], ex[2], by, deck_words, log)
        else:
            st = [d]
            while st:
                o = st.pop()
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k == 'gl' and isinstance(v, dict):
                            n += sum(fix(t, w, by, deck_words, log) for t, w in v.items())
                        else:
                            st.append(v)
                elif isinstance(o, list):
                    st.extend(o)
        if not dry:
            sep = (', ', ': ') if '", "' in raw[:2000] else (',', ':')
            path.write_text(json.dumps(d, ensure_ascii=False, separators=sep), encoding='utf8')
        print(f'{name}: {n} words joined')
    if dry:
        seen = set()
        for r, m, ctx, ins in log:
            if (r, ctx) in seen: continue
            seen.add((r, ctx)); print(r, '|', m[:50], '|', ctx, '|', ins)


if __name__ == '__main__':
    main()
