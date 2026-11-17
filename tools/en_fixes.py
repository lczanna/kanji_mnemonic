#!/usr/bin/env python3
"""Apply data/en_fixes.json (Japanese sentence -> closer English) to examples.json and the word questions in exam.json.

    python3 tools/en_fixes.py

The example sentences come from Tatoeba, where some English versions are loose or carry extra text
("You must make up your mind, and that at once." for あなたは決心しなければならない). Run after rebuilding
examples.json or exam.json.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
fx = {k: v for k, v in json.loads((ROOT / 'data' / 'en_fixes.json').read_text(encoding='utf8')).items() if not k.startswith('_')}
dump = lambda p, d: p.write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':')), encoding='utf8')

p = ROOT / 'examples.json'; ex = json.loads(p.read_text(encoding='utf8')); n = 0
for rows in ex.values():
    for r in rows:
        if r[0] in fx and r[1] != fx[r[0]]:
            r[1] = fx[r[0]]; n += 1
dump(p, ex)

p = ROOT / 'exam.json'; exam = json.loads(p.read_text(encoding='utf8')); m = 0
for q in exam['vocab'].values():
    for c in q.get('ctx', []):
        full = c['s'].replace('（　）', c['w'][c['answer']])
        if full in fx and c.get('en') != fx[full]:
            c['en'] = fx[full]; m += 1
dump(p, exam)
print(f'{n} example translations and {m} word-question translations updated')
