#!/usr/bin/env python3
"""
Join words the tokenizer split apart (不意 + 打ち → 不意打ち "surprise attack") in every tap-to-read gloss.

Two or three neighbouring glossed words are joined when, written together, they are a common JMdict word with
kanji (in its dictionary form, so nothing conjugated is touched), at least three characters long. The joined word
gets that entry's reading and meaning. Run after the gloss builders and before tools/kana_fill.py; running it
twice changes nothing.

  python3 tools/gloss_merge.py JMdict_e.gz
"""
import gzip, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KANJI = re.compile(r'[㐀-鿿々]')
# Joined forms that are usually two words in a sentence: そう言った is "said so" far more often than "like that".
SKIP = {'そう言った', 'そう言う'}
# Joined even though JMdict doesn't mark them common: idioms whose parts mislead (通り is "street", もう "already")
# and words whose reading changes when joined (一日中 いちにちじゅう, 三十分 さんじゅっぷん). Checked by hand.
ALWAYS = {'一日中', '今日中', '日本中', '三十分', '何曜日', '一番目', 'どちら様', 'もう少し', 'もう一回', 'もう一方', 'もう直',
          '予定どおり', '予定通り', '期待通り', 'いつも通り', '子供向け', '外国人向け', '人それぞれ', '知る限り', '十中八九',
          '良い子', '住み良い', 'ひと財産', '四つ折り', '早寝早起き', '人間嫌い', '一身上の都合', '一段上', '半時間',
          'お腹いっぱい', '飛ばし読み', 'あたり一帯', 'あたり一面', '大目に見る', '習い性となる', '真っ赤なうそ',
          '滅多に無い', '欠くべからざる', '男盛り', '貸し借り無し', '年越しそば', '天然パーマ', '偶然の一致', '入場お断り',
          '気の毒に思う', '一晩中'}


def load(path):
    x = gzip.open(path).read().decode()
    out = {}
    for ent in re.finditer(r'<entry>(.*?)</entry>', x, re.S):
        e = ent.group(1)
        common = '_pri>' in e
        if not common and not any(k in ALWAYS for k in re.findall(r'<keb>([^<]+)</keb>', e)):
            continue
        senses = [re.findall(r'<gloss>([^<]+)</gloss>', s) for s in re.findall(r'<sense>(.*?)</sense>', e, re.S)]
        if not senses or not senses[0]:
            continue
        g = '; '.join(senses[0][:2] + (senses[1][:1] if len(senses) > 1 and senses[1] else []))
        for k in re.findall(r'<keb>([^<]+)</keb>', e):
            out.setdefault(k, (re.findall(r'<reb>([^<]+)</reb>', e), g))
    return out


def merge(text, gl, jm):
    gl = sorted(gl, key=lambda g: g[0])
    out, i, n = [], 0, 0
    while i < len(gl):
        done = False
        for size in (3, 2):
            part = gl[i:i + size]
            if len(part) < size or any(part[j][0] + part[j][1] != part[j + 1][0] for j in range(size - 1)):
                continue
            word = text[part[0][0]:part[-1][0] + part[-1][1]]
            if len(word) < 3 or not KANJI.search(word) or word not in jm or word in SKIP:
                continue
            rebs, meaning = jm[word]
            joined = ''.join(p[2] for p in part)
            r = joined if joined in rebs else rebs[0] if len(rebs) == 1 or word in ALWAYS else None
            if not r:
                continue
            out.append([part[0][0], len(word), r, word, r, meaning])
            i += size; n += 1; done = True
            break
        if not done:
            out.append(gl[i]); i += 1
    return out, n


def walk(o, jm, key=None):
    n = 0
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'gl' and isinstance(v, dict):
                for text, gl in v.items():
                    if gl:
                        v[text], m = merge(text, gl, jm); n += m
            else:
                n += walk(v, jm)
    elif isinstance(o, list):
        for x in o:
            n += walk(x, jm)
    return n


def main():
    jm = load(sys.argv[1])
    load_j = lambda n: json.loads((ROOT / n).read_text(encoding='utf8'))
    save = lambda n, x: (ROOT / n).write_text(json.dumps(x, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    ex = load_j('examples.json'); n = 0
    for lst in ex.values():
        for e in lst:
            if e[2]:
                e[2], m = merge(e[0], e[2], jm); n += m
    save('examples.json', ex); print(f'examples.json: {n} words joined')
    for name in ('grammar.json', 'exam.json'):
        d = load_j(name); n = walk(d, jm); save(name, d); print(f'{name}: {n} words joined')


if __name__ == '__main__':
    main()
