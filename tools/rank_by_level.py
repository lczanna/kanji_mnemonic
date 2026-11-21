#!/usr/bin/env python3
"""
Put the words of the JLPT N3 list first in the study order, since those are the words the exam tests.

    python3 tools/rank_by_level.py LISTS_DIR      # n5.csv n4.csv n3.csv n2.csv (open-anki-jlpt-decks src/)

Run after tools/rank_vocab.py (which ranks by how common a word is): each word gets "jl", the lowest list it is on
(n5, n4, n3, n2), and "p" is renumbered N3 words first, then N5/N4 words, then the rest, keeping the usefulness order
within each group. N5/N4 words you haven't met go to the quick "Know it / Not yet" sort instead of a full lesson, so
the daily new words are N3 words. A real N3 practice test (Nov 2026) asked mostly N3-list words ranked past 1,200 by
usefulness alone (共通, 農業, 余る), which the plan never reached. Progress is keyed by word, so reordering is safe.
"""
import csv, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    level = {}
    for lv in ('n5', 'n4', 'n3', 'n2'):   # easiest list a word is on wins
        for row in csv.DictReader(open(Path(sys.argv[1]) / f'{lv}.csv', encoding='utf8')):
            for col in ('expression', 'reading'):
                w = re.split(r'[;、,（(]', row[col])[0].strip()
                if w and not KANA_ONLY_READING(col, row):
                    level.setdefault(w, lv)
    path = ROOT / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf8'))
    for v in vocab:
        jl = level.get(v['w']) or (level.get(v['r']) if v.get('f') == 'kana' or not re.search(r'[一-鿿]', v['w']) else None)
        if jl:
            v['jl'] = jl
        else:
            v.pop('jl', None)
    # Very common words the lists miss (不可能, 可能性: src "common") rank with the N3 words, by how common they are.
    group = lambda v: 0 if v.get('jl') == 'n3' or v.get('src') == 'common' else 1 if v.get('jl') in ('n5', 'n4') else 2
    for i, v in enumerate(sorted(vocab, key=lambda v: (group(v), v.get('p', 9999)))):
        v['p'] = i + 1
    path.write_text(json.dumps(vocab, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    n = [sum(group(v) == g for v in vocab) for g in range(3)]
    print(f'N3 words first: {n[0]}; N5/N4 (quick sort): {n[1]}; others: {n[2]}')


# A reading column only names a kana word when the expression has no kanji (読み of 学校 is not the word がっこう).
KANA_ONLY_READING = lambda col, row: col == 'reading' and re.search(r'[一-鿿]', row['expression'])

if __name__ == '__main__':
    main()
