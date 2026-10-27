#!/usr/bin/env python3
"""
Readings for the kanji in sentence-ordering questions, so the app can print furigana over kanji you haven't
studied (as the exam does over kanji above the level) instead of leaving you to guess.

For each ordering item (grammar.json "order", exam.json mock grammar "order") the finished sentence is read with
Sudachi and every run of kanji gets its reading, aligned past the kana around it (話し合った → 話 はな, 合 あ).
Stored as "rb": {"before": [[start, length, reading], ...], "chunks": [[...], ...], "after": [...]}, offsets within
each part. Kanji runs never cross a part boundary, so a word split across two parts still gets both readings.

  python3 tools/order_ruby.py
"""
import json, re
from pathlib import Path
from sudachipy import dictionary, tokenizer

ROOT = Path(__file__).resolve().parent.parent
TOK, MODE = dictionary.Dictionary().tokenizer(), tokenizer.Tokenizer.SplitMode.C
KAN = re.compile(r'[一-鿿々〆ヶ]+')
hira = lambda s: ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in s)


def kanji_runs(text):
    """[[start, length, reading]] for each run of kanji in text."""
    out = []
    for m in TOK.tokenize(text, MODE):
        surf, read, at = m.surface(), hira(m.reading_form()), m.begin()
        if not KAN.search(surf):
            continue
        parts = re.split(r'([一-鿿々〆ヶ]+)', surf)
        pat = ''.join('(.+?)' if KAN.fullmatch(p) else re.escape(hira(p)) for p in parts if p)
        mm = re.fullmatch(pat, read)
        pos, g = at, 0
        for p in parts:
            if not p:
                continue
            if KAN.fullmatch(p):
                g += 1
                if mm:
                    out.append([pos, len(p), mm.group(g)])
                elif len([q for q in parts if q and KAN.fullmatch(q)]) == 1:   # one kanji run: kana around it read as written
                    lead = len(hira(parts[0])) if parts[0] and not KAN.fullmatch(parts[0]) else 0
                    tail = len(hira(parts[-1])) if parts[-1] and not KAN.fullmatch(parts[-1]) else 0
                    out.append([pos, len(p), read[lead:len(read) - tail or None]])
            pos += len(p)
    return out


def ruby(o):
    segs = [o['before']] + o['chunks'] + [o['after']]
    full, bounds, at = ''.join(segs), [], 0
    for s in segs:
        bounds.append((at, at + len(s))); at += len(s)
    runs = kanji_runs(full)
    per = [[[s - a, l, r] for s, l, r in runs if a <= s and s + l <= b] for a, b in bounds]
    return {'before': per[0], 'chunks': per[1:-1], 'after': per[-1]}


def main():
    n = 0
    path = ROOT / 'grammar.json'
    grammar = json.loads(path.read_text(encoding='utf8'))
    for g in grammar:
        if g.get('order'):
            g['order']['rb'] = ruby(g['order']); n += 1
    path.write_text(json.dumps(grammar, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    path = ROOT / 'exam.json'
    exam = json.loads(path.read_text(encoding='utf8'))
    for m in exam.get('mocks', []):
        for o in (m.get('gram') or {}).get('order', []):
            o['rb'] = ruby(o); n += 1
    path.write_text(json.dumps(exam, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{n} ordering items have readings')


if __name__ == '__main__':
    main()
