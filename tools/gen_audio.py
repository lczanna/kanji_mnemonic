#!/usr/bin/env python3
"""
Recorded audio for the listening practice (exam.json items), with OpenAI's neural voices instead of the phone's.

Each item becomes one MP3 in the exam's order: quick response = the line, then the three replies ("1、…") in the other
speaker's voice; dialogue = the narrator's intro and question, the turns (man / woman voices), the question again.
Every clip is checked by transcribing it back to hiragana and comparing with the script's reading (Sudachi), so
misread kanji and garbled lines are caught without anyone listening; failures are listed and can be regenerated.

Needs OPENAI_API_KEY (or OPENAI_KEY) like tools/gen_images.py, ffmpeg, and sudachipy.

  python3 tools/gen_audio.py --ids qr001,dl001     # specific items
  python3 tools/gen_audio.py --all                 # every item without audio (writes audio/<id>.mp3)
"""
import argparse, difflib, io, json, re, subprocess, sys, tempfile, time, urllib.request, urllib.error, uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_images import key  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'audio'
TTS_MODEL, STT_MODEL = 'gpt-4o-mini-tts', 'gpt-4o-mini-transcribe'
VOICES = {'M': 'ash', 'F': 'coral', 'N': 'sage'}   # man, woman, narrator
STYLE = {
    'M': '自然な標準語の日本語で、落ち着いた男性の話し方で話してください。日本語能力試験の聴解問題のように、はっきり、普通の速さで。',
    'F': '自然な標準語の日本語で、明るい女性の話し方で話してください。日本語能力試験の聴解問題のように、はっきり、普通の速さで。',
    'N': '日本語能力試験の聴解問題のナレーターとして、標準語で、はっきり落ち着いて読んでください。',
}


def post(path, body=None, files=None):
    for attempt in range(4):
        try:
            if files:
                b = uuid.uuid4().hex
                data = b''.join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in body.items())
                data += f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode() + files + f'\r\n--{b}--\r\n'.encode()
                req = urllib.request.Request('https://api.openai.com/v1' + path, data=data, headers={'Authorization': 'Bearer ' + key(), 'Content-Type': f'multipart/form-data; boundary={b}'})
            else:
                req = urllib.request.Request('https://api.openai.com/v1' + path, data=json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + key(), 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(5 * (attempt + 1)); continue
            raise RuntimeError(f'HTTP {e.code}: {e.read().decode()[:200]}')
        except Exception:
            if attempt < 3:
                time.sleep(5); continue
            raise


def tts(text, who):
    return post('/audio/speech', {'model': TTS_MODEL, 'voice': VOICES[who], 'input': text, 'instructions': STYLE[who], 'response_format': 'mp3'})


def segments(x):
    if x['id'].startswith('mg'):   # 概要理解: who is talking, the talk, then the question and the options, all spoken
        return [('N', x['intro'])] + [(x['s'], t) for t in x['talk']] + [('N', x['question'])] + [('N', f'{i + 1}、{o}') for i, o in enumerate(x['options'])]
    if x['id'].startswith('ms'):   # 発話表現: the narrator sets the scene, then three spoken lines
        return [('N', x['intro'])] + [('M', f'{i + 1}、{o}') for i, o in enumerate(x['options'])]
    if x['id'].startswith('qr'):
        other = 'F' if x['s'] == 'M' else 'M'
        return [(x['s'], x['line'])] + [(other, f'{i + 1}、{o}') for i, o in enumerate(x['options'])]
    return [('N', x['intro'])] + [(t['s'], t['t']) for t in x['turns']] + [('N', x['question'])]


def join(clips, pause=0.7):
    """Concatenate MP3 clips with short silences into one mono 48 kbps MP3."""
    with tempfile.TemporaryDirectory() as d:
        parts = []
        for i, c in enumerate(clips):
            p = Path(d) / f'{i}.mp3'; p.write_bytes(c); parts.append(p)
        sil = Path(d) / 'sil.mp3'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', f'anullsrc=r=24000:cl=mono', '-t', str(pause), '-q:a', '9', str(sil), '-y'], check=True)
        lst = Path(d) / 'list.txt'
        lst.write_text(''.join(f"file '{p}'\nfile '{sil}'\n" for p in parts))
        out = Path(d) / 'out.mp3'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-ac', '1', '-ar', '24000', '-b:a', '48k', str(out), '-y'], check=True)
        return out.read_bytes()


_tok = None
def reading(text):
    """Hiragana reading of a script line (Sudachi), punctuation removed, for comparing with the transcript."""
    global _tok
    from sudachipy import dictionary
    _tok = _tok or dictionary.Dictionary().tokenizer()
    kata = ''.join(m.reading_form() for m in _tok.tokenize(text))
    return norm(kata)


def norm(t):
    t = ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in t)
    return re.sub(r'[^ぁ-ゖー]', '', t.replace('ー', ''))


def check(x, audio):
    """Transcribe in hiragana and compare with the script's reading; returns (similarity 0–1, transcript)."""
    txt = post('/audio/transcriptions', {'model': STT_MODEL, 'language': 'ja', 'response_format': 'text',
                                          'prompt': 'すべてひらがなで書き起こしてください。'}, files=audio).decode()
    # Option numbers ("1、") and digits are written differently by the transcriber: compare without them.
    strip = lambda t: re.sub(r'[^一-鿿々ぁ-ゖァ-ヺー]', '', t)   # also punctuation, which Sudachi reads as きごう
    want = reading(strip(''.join(t for _, t in segments(x))))
    got = reading(strip(txt))   # the transcript may contain kanji: read it the same way
    return difflib.SequenceMatcher(None, want, got).ratio(), txt.strip()


def make(x):
    try:
        audio = join([tts(t, who) for who, t in segments(x)])
        score, txt = check(x, audio)
        (OUT / f"{x['id']}.mp3").write_bytes(audio)
        return x['id'], score, txt, None
    except Exception as e:
        return x['id'], 0, '', str(e)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--all', action='store_true'); g.add_argument('--ids')
    ap.add_argument('--src', default=str(ROOT / 'exam.json'))
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    ex = json.loads(Path(a.src).read_text(encoding='utf8'))
    items = ex['qr'] + ex['dlg'] + ex.get('mock_listen', []) + [x for x in ex.get('mock_items', []) if x['id'][:2] in ('qr', 'dl')]
    chosen = [x for x in items if x['id'] in a.ids.split(',')] if a.ids else [x for x in items if not (OUT / f"{x['id']}.mp3").exists()]
    OUT.mkdir(exist_ok=True)
    print(f'{len(chosen)} items')
    report = {}
    with ThreadPoolExecutor(a.workers) as pool:
        for id_, score, txt, err in pool.map(make, chosen):
            report[id_] = {'score': round(score, 3), 'transcript': txt, 'error': err}
            print(f"{id_} {'ERROR ' + err if err else f'{score:.2f}'}")
    weak = {k: v for k, v in report.items() if v['error'] or v['score'] < 0.85}
    (OUT / 'check.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf8')
    print(f'done: {len(report) - len(weak)} ok, {len(weak)} to look at: {sorted(weak)}')


if __name__ == '__main__':
    main()
