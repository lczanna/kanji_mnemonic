#!/usr/bin/env python3
"""
Exam practice for the app → exam.json.

- Listening and reading items written for the exam's formats: data/exam_listening_qr.json (即時応答),
  data/exam_listening_dlg.json (dialogues), data/exam_reading.json (passages); each gets tap-to-read glosses.
- Two practice exams (data/exam_mock.json for the parts daily practice lacks: grammar, 文章の文法, a long passage,
  概要理解, 発話表現), filled up from the pools above. Items used in a mock are kept out of daily practice.
- Word questions: data/exam_vocab.json (言い換え "para" and 用法 "usage", written per word) plus 文脈規定 "ctx",
  built here from the word's example sentences: the word is blanked out where it appears in dictionary form, and
  three decoys of the same shape (same okurigana, or the same number of kanji) and similar usefulness fill the options.

  python3 tools/build_exam.py JMdict_e.gz
"""
import json, random, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gloss_grammar import gloss_sentence, load_jmdict  # noqa: E402
from gloss_fixes import fix_gloss, load  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KANJI = re.compile(r'[一-鿿々]')


def shape(w):
    """Words that could stand in each other's place: trailing kana (okurigana) and number of kanji."""
    tail = re.search(r'[ぁ-ゖ]*$', w).group()
    return (tail, len(KANJI.findall(w)) if not tail else 0)


def ctx_questions(vocab, examples, rnd):
    by_shape = {}
    for v in vocab:
        if v.get('f') != 'kana' and KANJI.search(v['w']):
            by_shape.setdefault(shape(v['w']), []).append(v)
    out = {}
    for v in vocab:
        if v.get('f') == 'kana' or not KANJI.search(v['w']):
            continue
        qs = []
        for ex in examples.get(v['w'], []):
            ja, en, gl = ex[:3]
            tok = next((g for g in gl if g[3] == v['w'] and ja[g[0]:g[0] + g[1]] == v['w']), None)
            if not tok:
                continue
            pool = [u for u in by_shape.get(shape(v['w']), []) if u['w'] != v['w'] and u['w'] not in ja
                    and abs(u.get('p', 9999) - v.get('p', 9999)) < 600]
            if len(pool) < 3:
                continue
            opts = [v['w']] + [u['w'] for u in rnd.sample(pool, 3)]
            rnd.shuffle(opts)
            s = ja[:tok[0]] + '（　）' + ja[tok[0] + tok[1]:]
            qs.append({'s': s, 'options': opts, 'answer': opts.index(v['w']), 'en': en})
            if len(qs) == 2:
                break
        if qs:
            out[v['w']] = qs
    return out


def build_mocks(spec, qr, dlg, read, words, vocab, jm, fixes):
    """Each mock follows the N3 paper: vocabulary 8 reading + 6 spelling + 11 fill-in + 5 paraphrase + 5 usage;
    grammar 13 + 5 ordering + 5 in a text; reading 4 short + 2 medium + 1 long + 1 information; listening 6+6 dialogues,
    3 gist, 4 what-to-say, 9 quick responses. Word items come from N3-level words (rank 300–2500) with the needed data."""
    rnd = random.Random(11)
    mocks, mock_listen, taken = [], [], set()
    by_rank = sorted(vocab, key=lambda v: v.get('p', 9999))
    mid = [v for v in by_rank if 300 <= v.get('p', 9999) <= 2500 and v.get('f', 'kanji') == 'kanji']
    def pick(pool, n, ok=lambda v: True):
        got = [v for v in pool if v['w'] not in taken and ok(v)]
        rnd.shuffle(got); got = got[:n]; taken.update(v['w'] for v in got); return got
    def take(items, n, ok=lambda x: True):
        got = [x for x in items if ok(x) and x['id'] not in taken][-n:]   # from the end: daily practice starts at the front
        taken.update(x['id'] for x in got); return got
    for sid in ('A', 'B'):
        sp = spec.get(sid)
        if not sp:
            continue
        ctx_words = pick(mid, 11, lambda v: v['w'] in words and 'ctx' in words[v['w']])
        para_words = pick(by_rank[:600], 5, lambda v: v['w'] in words and 'para' in words[v['w']])
        use_words = pick(by_rank[:600], 5, lambda v: v['w'] in words and 'usage' in words[v['w']])
        m = {'id': sid,
             'vocab': {'read': [v['w'] for v in pick(mid, 8)],
                       'spell': [v['w'] for v in pick(mid, 6, lambda v: len(v.get('d') or []) == 3)],
                       'ctx': [words[v['w']]['ctx'][-1] for v in ctx_words],
                       'para': [words[v['w']].pop('para') for v in para_words],
                       'usage': [dict(words[v['w']].pop('usage'), w=v['w'] if v.get('f') == 'kanji' else v['r']) for v in use_words]},
             'gram': {'fill': sp['fill'], 'order': sp['order'], 'textgram': sp['textgram']},
             'read': [*take(read, 4, lambda x: x['kind'] == 'short'), *take(read, 2, lambda x: x['kind'] == 'medium'),
                      dict(sp['long'], kind='long', gl=gloss_all([sp['long']['text']], jm, fixes)), *take(read, 1, lambda x: x['kind'] == 'info')],
             'listen': []}
        for g in sp['gist'] + sp['say']:
            mock_listen.append(g)
        m['listen'] = [x['id'] for x in take(dlg, 12)] + [g['id'] for g in sp['gist']] + [g['id'] for g in sp['say']] + [x['id'] for x in take(qr, 9)]
        mocks.append(m)
    return mocks, mock_listen


def gloss_all(texts, jm, fixes):
    gl = {}
    for t in texts:
        for line in t.split('\n'):
            line = line.strip()
            if line and line not in gl:
                words = gloss_sentence(line, jm)
                if words:
                    gl[line] = fix_gloss(line, words, fixes)
    return gl


def main():
    jm, fixes = load_jmdict(sys.argv[1]), load('gloss_fixes.json')
    data = lambda n: json.loads((ROOT / 'data' / n).read_text(encoding='utf8')) if (ROOT / 'data' / n).exists() else []
    qr, dlg, read, vx = data('exam_listening_qr.json'), data('exam_listening_dlg.json'), data('exam_reading.json'), data('exam_vocab.json') or {}
    for x in qr:
        x['gl'] = gloss_all([x['line'], *x['options']], jm, fixes)
    for x in dlg:
        x['gl'] = gloss_all([t['t'] for t in x['turns']], jm, fixes)
    for x in read:
        x['gl'] = gloss_all([x['text']], jm, fixes)
    vocab = json.loads((ROOT / 'vocab.json').read_text(encoding='utf8'))
    examples = json.loads((ROOT / 'examples.json').read_text(encoding='utf8'))
    ctx = ctx_questions(vocab, examples, random.Random(7))
    words = {}
    for w in set(ctx) | {w for w, q in vx.items() if q}:
        q = dict(vx.get(w) or {})
        if w in ctx:
            q['ctx'] = ctx[w]
        words[w] = {k: q[k] for k in ('ctx', 'para', 'usage') if q.get(k)}
    mocks, mock_listen = build_mocks(data('exam_mock.json') or {}, qr, dlg, read, words, vocab, jm, fixes)
    used = {i for m in mocks for i in m['listen']} | {p['id'] for m in mocks for p in m['read'] if p.get('id')}
    qr, dlg, read = [x for x in qr if x['id'] not in used], [x for x in dlg if x['id'] not in used], [x for x in read if x['id'] not in used]
    out = {'qr': qr, 'dlg': dlg, 'read': read, 'vocab': words, 'mocks': mocks, 'mock_listen': mock_listen,
           'mock_items': [x for x in data('exam_listening_qr.json') + data('exam_listening_dlg.json') + data('exam_reading.json') if x['id'] in used]}
    (ROOT / 'exam.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f"{len(qr)} quick-response, {len(dlg)} dialogues, {len(read)} reading items; word questions for {len(words)} words "
          f"(fill-in {sum('ctx' in q for q in words.values())}, closest meaning {sum('para' in q for q in words.values())}, usage {sum('usage' in q for q in words.values())})")


if __name__ == '__main__':
    main()
