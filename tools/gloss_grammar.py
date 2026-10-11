#!/usr/bin/env python3
"""
Add tap-to-read glosses to grammar.json: for every Japanese sentence, each word that contains kanji
gets its in-context reading, dictionary form and a short English meaning. Words written in kana get a
meaning from the checked list in kana_glosses.py, chosen for the sentence they are in.

  pip install sudachipy sudachidict_core
  python3 tools/gloss_grammar.py path/to/JMdict_e.gz

Stored per grammar point as gl = {sentence: [[start, length, reading, lemma, lemma_reading, meaning], ...]}.
"""
import gzip, json, re, sys
from pathlib import Path
from sudachipy import dictionary, tokenizer
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kana_glosses import kana_meaning  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ('名詞', '動詞', '形容詞', '副詞', '連体詞', '接続詞', '感動詞', '形状詞', '代名詞')
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


def load_jmdict_entries(path):
    """Every entry with all its senses, indexed by spelling and by reading, for sense-tagged sentences."""
    x = gzip.open(path).read().decode()
    index = {}
    for ent in re.finditer(r'<entry>(.*?)</entry>', x, re.S):
        e = ent.group(1)
        senses = [re.findall(r'<gloss>([^<]+)</gloss>', z) for z in re.findall(r'<sense>(.*?)</sense>', e, re.S)]
        entry = {'kebs': re.findall(r'<keb>([^<]+)</keb>', e), 'rebs': re.findall(r'<reb>([^<]+)</reb>', e),
                 'senses': senses, 'pos': set(re.findall(r'<pos>&([^;]+);</pos>', e)), 'common': '_pri>' in e}
        for k in entry['kebs'] + entry['rebs']:
            index.setdefault(k, []).append(entry)
    return index


GRAMMATICAL = {'prt', 'aux', 'aux-v', 'aux-adj', 'cop', 'cop-da'}
# Helper words every learner already knows; glossing them would clutter every sentence.
BASIC = {'為る', 'する', '下さる', 'ください', 'である', 'です', 'だ', '居る', '有る', 'ある', '成る', 'から', 'まで', 'より',
         'ので', 'のに', 'けど', 'が', 'は', 'を', 'に', 'で', 'と', 'も', 'の', 'へ', 'か', 'ね', 'よ', 'お', 'ご', '御',
         'この', 'その', 'あの', 'これ', 'それ', 'あれ', 'ここ', 'そこ', 'あそこ', 'どこ', 'こと', '事', 'にも', 'ではない'}
STOPWORDS = {'the', 'one', 'someone', 'something', 'with', 'for', 'and', 'into', 'from', 'that', 'this', 'etc', 'one\'s'}


def words(text):
    return [w for w in re.findall(r"[a-z']+", text.lower()) if len(w) >= 3 and w not in STOPWORDS]


def pick_sense(senses, english):
    """The sense whose glosses appear in the sentence's English translation ("received" matches "to receive"),
    as (index, the matching glosses), or (None, []) when none does."""
    eng = words(english)
    best, hits = None, []
    for i, gl in enumerate(senses):
        found = [g for g in gl if any(e.startswith(w[:5]) for w in words(re.sub(r'\(.*?\)', '', g).replace('to ', '', 1)) for e in eng)]
        if len(found) > len(hits):
            best, hits = i, found
    return best, hits


def sentence_readings(text):
    """Reading of every character span Sudachi sees as a word, so a word is read as it is in this sentence."""
    spans, pos = {}, 0
    for m in TOK.tokenize(text, MODE):
        s = m.surface()
        start = text.index(s, pos)
        pos = start + len(s)
        spans[start] = (len(s), hira(m.reading_form()))
    return spans


def reading_in(text, spans, start, length):
    out, i = '', start
    while i < start + length:
        if i not in spans:
            return None
        n, r = spans[i]
        out += r
        i += n
    return out if i == start + length else None


def gloss_indexed(text, english, bline, entries):
    """Gloss a Tanaka-corpus sentence from its index line, which tags each word with its dictionary form,
    reading and the form written in the sentence ({...}). The meaning is the sense matching the sentence's
    English translation, else the only sense; otherwise a kanji word lists its main senses and a kana word
    gets no gloss, so no word shows a meaning this sentence doesn't use."""
    spans = sentence_readings(text)
    out, pos = [], 0
    for tok in bline.split():
        m = re.match(r'^([^(\[{~#]+)(?:\(([^)]+)\))?(?:\[(\d+)\])?(?:\{([^}]+)\})?(~)?$', tok)
        if not m:
            continue
        head, reading, form = m.group(1), m.group(2), m.group(4) or m.group(1)
        start = text.find(form, pos)
        if start < 0:
            continue
        pos = start + len(form)
        if head in BASIC or form in BASIC:
            continue
        if form == 'したがって' and text[start - 1:start] == 'に':   # 〜にしたがって, not the conjunction "therefore"
            out.append([start, len(form), form, '従う', 'したがう', 'following; in accordance with (〜にしたがって)'])
            continue
        cands = [e for e in entries.get(head, []) if not reading or reading in e['rebs']]
        if not cands:
            continue
        e = max(cands, key=lambda e: e['common'])
        if e['pos'] & GRAMMATICAL and not e['pos'] - GRAMMATICAL:
            continue
        # The corpus's own sense numbers follow an older dictionary and are often off (受ける[04] "to sustain
        # damage" for "received a notice"), so the sentence's English decides which sense is meant.
        senses = [z for z in e['senses'] if z]
        i, hits = pick_sense(senses, english)
        if i is not None:
            meaning = '; '.join(dict.fromkeys(hits + senses[i])) if len(hits) < 2 else '; '.join(hits[:2])
            meaning = '; '.join(meaning.split('; ')[:2])
        elif len(senses) == 1:
            meaning = '; '.join(senses[0][:2])
        elif HAS_KANJI.search(form):
            meaning = ' / '.join(z[0] for z in senses[:3])
        else:
            continue
        form_reading = form if not HAS_KANJI.search(form) else (reading_in(text, spans, start, len(form)) or reading_of(form))
        lemma_reading = reading or (e['rebs'][0] if e['rebs'] else head)
        out.append([start, len(form), form_reading, head, lemma_reading, meaning[:70]])
    return out


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
            # Kana words get a meaning only from the checked list in kana_glosses.py, chosen for this sentence.
            p = m.part_of_speech()
            meaning = p[0] in CONTENT and p[1] != '非自立可能' and kana_meaning(m.dictionary_form(), text)
            if meaning:
                out.append([start, len(s), s, m.dictionary_form(), m.dictionary_form(), meaning])
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
            # Keep offsets stable: tokenize the blank as a same-length placeholder.
            words = gloss_sentence(t.replace('（　）', '＿＿＿'), jm) if t else []
            if words:
                gl[t] = words
                n += len(words)
        g['gl'] = gl
    path.write_text(json.dumps(deck, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{n} glossed words across {len(deck)} grammar points')


if __name__ == '__main__':
    main()
