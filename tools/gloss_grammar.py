#!/usr/bin/env python3
"""
Add tap-to-read glosses to grammar.json: for every Japanese sentence, each word that contains kanji
gets its in-context reading, dictionary form and a short English meaning.

  pip install sudachipy sudachidict_core
  python3 tools/gloss_grammar.py path/to/JMdict_e.gz

Stored per grammar point as gl = {sentence: [[start, length, reading, lemma, lemma_reading, meaning], ...]}.
"""
import gzip, json, re, sys
from pathlib import Path
from sudachipy import dictionary, tokenizer

ROOT = Path(__file__).resolve().parent.parent
TOK = dictionary.Dictionary().tokenizer()
MODE = tokenizer.Tokenizer.SplitMode.C
OVERRIDE = {'日本': 'にほん', '込む': 'こむ'}   # Sudachi prefers にっぽん, and reads 込む alone as ごむ
# Single kanji used as suffixes, where the dictionary's first sense misleads in a sentence.
MEANING = {('日', 'にち'): 'day (counter)', ('中', 'ちゅう'): 'during; in the middle of', ('背', 'せ'): 'height; stature; back',
           ('寺', 'じ'): '... Temple (in names)', ('大丈夫', 'だいじょうぶ'): "all right; OK; safe"}
HAS_KANJI = re.compile(r'[一-鿿々]')


def hira(s):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def load_jmdict(path):
    """Meanings keyed by (spelling, reading) and by spelling alone. Many spellings have several
    entries (字 is じ "character" and あざ "village section"), so the reading picks the right one;
    by spelling alone, the common entry wins."""
    x = gzip.open(path).read().decode()
    by_pair, by_keb = {}, {}
    for ent in re.finditer(r'<entry>(.*?)</entry>', x, re.S):
        e = ent.group(1)
        senses = [re.findall(r'<gloss>([^<]+)</gloss>', x) for x in re.findall(r'<sense>(.*?)</sense>', e, re.S)]
        if not senses or not senses[0]:
            continue
        # The first sense is often not the everyday one (運転 "operation" before "driving"), so add the
        # start of the second sense too.
        g = '; '.join(senses[0][:2] + (senses[1][:1] if len(senses) > 1 and senses[1] else []))
        common = '_pri>' in e
        for k in re.findall(r'<keb>([^<]+)</keb>', e):
            for r in re.findall(r'<reb>([^<]+)</reb>', e):
                if (k, r) not in by_pair or common and not by_pair[(k, r)][1]:
                    by_pair[(k, r)] = (g, common)
            if k not in by_keb or common and not by_keb[k][1]:
                by_keb[k] = (g, common)
    return {'pair': {k: v[0] for k, v in by_pair.items()}, 'keb': {k: v[0] for k, v in by_keb.items()}}


def meaning_of(jm, word, reading):
    return MEANING.get((word, reading)) or jm['pair'].get((word, reading)) or jm['keb'].get(word)


def reading_of(word):
    if word in OVERRIDE:
        return OVERRIDE[word]
    return hira(''.join(m.reading_form() for m in TOK.tokenize(word, MODE)))


E_TO_U = dict(zip('けげせてねべめれえ', 'くぐすつぬぶむるう'))


def potential(lemma, jm):
    # Sudachi keeps potential verbs as their own lemma (書ける); fall back to the base verb (書く).
    if len(lemma) >= 2 and lemma.endswith('る') and lemma[-2] in E_TO_U:
        base = lemma[:-2] + E_TO_U[lemma[-2]]
        if base in jm['keb']:
            return 'can ' + jm['keb'][base].split(';')[0].replace('to ', '', 1)
    return ''


def gloss_sentence(text, jm):
    out, pos = [], 0
    for m in TOK.tokenize(text, MODE):
        s = m.surface()
        start = text.index(s, pos)
        pos = start + len(s)
        if not HAS_KANJI.search(s):
            continue
        lemma = m.dictionary_form()
        r = OVERRIDE.get(s) or hira(m.reading_form())
        lr = reading_of(lemma) if lemma != s else r
        meaning = meaning_of(jm, lemma, lr) or meaning_of(jm, s, r) or potential(lemma, jm)
        out.append([start, len(s), r, lemma, lr, meaning[:60]])
    return out


def main():
    jm = load_jmdict(sys.argv[1])
    path = ROOT / 'grammar.json'
    deck = json.loads(path.read_text(encoding='utf8'))
    n = 0
    for g in deck:
        texts = [x['ja'] for x in g['examples']] + [f['q'] for f in g['fill']] + [g['order']['before'], g['order']['after']]
        gl = {}
        for t in texts:
            if t and HAS_KANJI.search(t):
                # Keep offsets stable: tokenize the blank as a same-length placeholder.
                gl[t] = gloss_sentence(t.replace('（　）', '＿＿＿'), jm)
                n += len(gl[t])
        g['gl'] = gl
    path.write_text(json.dumps(deck, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{n} glossed words across {len(deck)} grammar points')


if __name__ == '__main__':
    main()
