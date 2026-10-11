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
TOK = dictionary.Dictionary().create()
MODE = tokenizer.Tokenizer.SplitMode.C
OVERRIDE = {'日本': 'にほん'}   # Sudachi prefers にっぽん
HAS_KANJI = re.compile(r'[一-鿿々]')


def hira(s):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def load_jmdict(path):
    x = gzip.open(path).read().decode()
    gloss = {}
    for ent in re.finditer(r'<entry>(.*?)</entry>', x, re.S):
        e = ent.group(1)
        sense = re.search(r'<sense>(.*?)</sense>', e, re.S)
        if not sense:
            continue
        g = '; '.join(re.findall(r'<gloss>([^<]+)</gloss>', sense.group(1))[:3])
        for k in re.findall(r'<keb>([^<]+)</keb>', e):
            gloss.setdefault(k, g)
    return gloss


def reading_of(word):
    if word in OVERRIDE:
        return OVERRIDE[word]
    return hira(''.join(m.reading_form() for m in TOK.tokenize(word, MODE)))


E_TO_U = dict(zip('けげせてねべめれえ', 'くぐすつぬぶむるう'))


def potential(lemma, jm):
    # Sudachi keeps potential verbs as their own lemma (書ける); fall back to the base verb (書く).
    if len(lemma) >= 2 and lemma.endswith('る') and lemma[-2] in E_TO_U:
        base = lemma[:-2] + E_TO_U[lemma[-2]]
        if base in jm:
            return 'can ' + jm[base].split(';')[0].replace('to ', '', 1)
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
        meaning = jm.get(lemma) or jm.get(s) or potential(lemma, jm)
        out.append([start, len(s), r, lemma, reading_of(lemma) if lemma != s else r, meaning[:60]])
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
