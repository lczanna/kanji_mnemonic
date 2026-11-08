#!/usr/bin/env python3
"""Check that each kanji picture shows its Japanese-reading sound-alike (the story's ^hook^) clearly.

    python3 tools/check_images.py [--kanji 数頼] [--out report.json]

An image-reading model looks at each picture and says whether a learner would spot the hook at a glance.
Prints the kanji whose hook is missing or too small; redraw them with gen_images.py --kanji "<those>".
Hooks that are only spoken words ('Oi!') are reported as speech, not as missing.
"""
import argparse, base64, io, json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gen_images as g
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MODEL = 'gpt-5.4-mini'
ASK = ("This picture illustrates a memory story. The story's sound-alike for the Japanese reading is '{hook}' "
       "(in the story: \"{line}\"). Be strict: answer clear only if the {hook} is big, in the foreground and the first or second thing a learner glancing for two seconds would notice and name; small if it is there but small, partly hidden, held, in a mouth, in the background or easy to mistake for something else; missing if it is not there. "
       "Answer with JSON only: {{\"kind\": \"thing\" or \"speech\" (speech if the hook is only a spoken word or exclamation, "
       "not something that can be drawn), \"seen\": \"clear\", \"small\" (there but easy to miss) or \"missing\", \"note\": short reason}}")


def check(card):
    hooks = re.findall(r'\^([^^]+)\^', card['story'])
    img = ROOT / card.get('image', '')
    if not hooks or not img.is_file():
        return card['kanji'], None
    line = next((s for s in re.split(r'(?<=[.!?])\s+', card['story']) if '^' in s), card['story'])
    im = Image.open(img).convert('RGB'); im.thumbnail((768, 768))
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=85)
    url = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
    hook = ' '.join(hooks)
    for _ in range(3):
        try:
            r = g.call('/chat/completions', {'model': MODEL, 'response_format': {'type': 'json_object'}, 'messages': [{'role': 'user', 'content': [
                {'type': 'text', 'text': ASK.format(hook=g.depict(hook), line=g.plain(line))},
                {'type': 'image_url', 'image_url': {'url': url}}]}]})
            return card['kanji'], dict(json.loads(r['choices'][0]['message']['content']), hook=hook)
        except Exception as e:
            err = str(e)
    return card['kanji'], {'error': err, 'hook': hook}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--kanji')
    ap.add_argument('--out', default='image_check.json')
    ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    cards = json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards']
    cards = [c for c in cards if '^' in c.get('story', '') and (not a.kanji or c['kanji'] in a.kanji)]
    with ThreadPoolExecutor(a.workers) as ex:
        res = {k: v for k, v in ex.map(check, cards) if v}
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf8')
    bad = [k for k, v in res.items() if v.get('kind') != 'speech' and v.get('seen') != 'clear']
    print(f"{len(res)} checked; {sum(v.get('kind') == 'speech' for v in res.values())} speech hooks; {len(bad)} not clear:")
    print(''.join(bad))
