#!/usr/bin/env python3
"""
Recorded audio for the ▶ buttons: the most useful words and sentences, spoken by OpenAI's neural voices in place
of the phone's (better pitch accent and readings, and several different voices to get used to).

What's recorded: every word, the example sentences of the top 1,200 words, and the grammar examples, fill-in answers and
ordering sentences. Each clip is speech/<id>.mp3 (id = hash of the text the app speaks); speech/index.json maps that
text to the id. Clips are checked like the listening items (transcribed back and compared with the reading).

  python3 tools/gen_speech.py --plan         # how many clips, characters and estimated minutes
  python3 tools/gen_speech.py --run          # record everything not yet recorded
"""
import argparse, hashlib, json, random, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_audio as A  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'speech'
FOCUS = 1200
# Same rule as the app's sayText: compounds read from their kanji, single kanji and ambiguous words from kana.
SAY_KANA = set('今日 明日 明後日 一昨日 日本 昨夜 大人 上手 下手 人気 今年 生物 最中 大家 市場 風車 色紙 一行 心中 工夫 見物 仮名 目下 十分 分別 上下 大事 一寸 大分 後生 寒気 上着'.split())
KANJI = re.compile(r'[一-鿿々]')


def say_text(w, r):
    n = len(KANJI.findall(w))
    if n >= 2 and w not in SAY_KANA and not re.search('[一二三四五六七八九十百千万何]', w):
        return w
    if n and KANJI.match(w[-1]):
        return re.sub(r'([おこごそぞとどのほぼぽもよろょ])う', r'\1ー', r)
    return r


def plan():
    vocab = json.loads((ROOT / 'vocab.json').read_text(encoding='utf8'))
    examples = json.loads((ROOT / 'examples.json').read_text(encoding='utf8'))
    grammar = json.loads((ROOT / 'grammar.json').read_text(encoding='utf8'))
    texts = []
    for v in sorted(vocab, key=lambda v: v.get('p', 9999))[:FOCUS]:
        texts.append(say_text(v['w'], v['r']))
        texts += [ex[0] for ex in examples.get(v['w'], [])]
    # The other words too (word only): the phone's voice can misread a compound (上京 as かみぎょう).
    texts += [say_text(v['w'], v['r']) for v in sorted(vocab, key=lambda v: v.get('p', 9999))[FOCUS:]]
    for g in grammar:
        texts += [x['ja'] for x in g['examples']]
        texts += [f['q'].replace('（　）', f['choices'][f['answer']]) for f in g['fill']]
        o = g.get('order')
        if o:
            texts.append(o['before'] + ''.join(o['chunks']) + o['after'])
    return list(dict.fromkeys(t for t in texts if t))


def clip_id(text):
    return hashlib.sha1(text.encode()).hexdigest()[:12]


def record(text):
    cid = clip_id(text)
    r = random.Random(cid)
    voice = r.choice(A.MALE + A.FEMALE)
    style = A.BASE + r.choice(A.MOODS)
    try:
        spoken = text.replace('明日', 'あした')
        wav = A.to_pace(A.tts(spoken, voice, style), spoken) if len(text) > 6 else A.tts_wav(spoken, voice, style)
        mp3 = A.encode(wav, 32)
        score, txt = check(spoken, mp3)
        (OUT / f'{cid}.mp3').write_bytes(mp3)
        return text, cid, score, txt, None
    except Exception as e:
        return text, cid, 0, '', str(e)


def check(text, mp3):
    import difflib
    txt = A.post('/audio/transcriptions', {'model': A.STT_MODEL, 'language': 'ja', 'response_format': 'text'}, files=mp3).decode()
    strip = lambda t: re.sub(r'[^一-鿿々ぁ-ゖァ-ヺー]', '', t)
    return difflib.SequenceMatcher(None, A.reading(strip(text)), A.reading(strip(txt)), autojunk=False).ratio(), txt.strip()


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--plan', action='store_true'); g.add_argument('--run', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--drop-weak', action='store_true', help="keep clips that didn't pass the check out of the index")
    a = ap.parse_args()
    texts = plan()
    if a.plan:
        chars = sum(map(len, texts))
        print(f'{len(texts)} clips, {chars} characters, about {chars / 6.5 / 60 * 1.3:.0f} minutes of audio')
        return
    OUT.mkdir(exist_ok=True)
    idx_path = OUT / 'index.json'
    index = json.loads(idx_path.read_text(encoding='utf8')) if idx_path.exists() else {}
    todo = [t for t in texts if t not in index or not (OUT / f'{index[t]}.mp3').exists()]
    if a.limit:
        todo = todo[:a.limit]
    print(f'{len(todo)} to record')
    weak = {}
    with ThreadPoolExecutor(a.workers) as pool:
        for n, (text, cid, score, txt, err) in enumerate(pool.map(record, todo), 1):
            if err or score < 0.8:
                weak[text] = {'score': round(score, 3), 'heard': txt, 'error': err}
            if not err and (score >= 0.8 or not a.drop_weak):
                index[text] = cid
            elif not err:
                (OUT / f'{cid}.mp3').unlink(missing_ok=True)   # misread: the app's phone voice reads the kana instead
            if n % 100 == 0:
                idx_path.write_text(json.dumps(index, ensure_ascii=False), encoding='utf8')
                print(f'{n}/{len(todo)}', flush=True)
    idx_path.write_text(json.dumps(index, ensure_ascii=False), encoding='utf8')
    (OUT / 'check.json').write_text(json.dumps(weak, ensure_ascii=False, indent=1), encoding='utf8')
    print(f'done: {len(todo) - len(weak)} ok, {len(weak)} to look at (speech/check.json)')


if __name__ == '__main__':
    main()
