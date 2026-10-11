#!/usr/bin/env python3
"""
Generate mnemonic illustrations for kanji cards with the OpenAI image API.

Each picture is drawn from the card's current story, including its sound-cast character,
then saved as a 480x320 JPEG (the size the app shows) under images/n3/, and kanji.json is updated.

Needs OPENAI_API_KEY (or OPENAI_KEY), either in the environment or in the repo's .env file (git-ignored). Uses only the standard library plus Pillow.

  python3 tools/gen_images.py --test                 # 10 hard-to-draw kanji, medium and high, for comparison
  python3 tools/gen_images.py --all --quality medium # every card without a new image
  python3 tools/gen_images.py --kanji 況只閉          # specific cards
  python3 tools/gen_images.py --leeches progress.json # cards you've missed 3+ times (from More → Download progress)
"""
import argparse, base64, io, json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DECK = ROOT / 'kanji.json'
OUT = ROOT / 'images' / 'n3'
API = 'https://api.openai.com/v1'
# Newest first; the first one this key can use is picked.
MODELS = ['gpt-image-2.5-sunburst', 'gpt-image-2.5-flare', 'gpt-image-2', 'gpt-image-1.5', 'gpt-image-1']
TEST_SET = '況只閉的無可身畑以'

STYLE = ('Vivid, slightly surreal storybook illustration with warm cinematic lighting and bold, readable shapes. '
         'One clear scene, landscape framing, main action in the centre, plain uncluttered background. '
         'Absolutely no text, letters, numbers, signs with writing, kanji or any written characters anywhere in the image.')


def load_dotenv():
    """Read KEY=value lines from the repo's .env (git-ignored) without overriding the real environment."""
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def key():
    load_dotenv()
    k = os.environ.get('OPENAI_API_KEY') or os.environ.get('OPENAI_KEY')
    if not k:
        sys.exit('No key found. Set OPENAI_API_KEY or OPENAI_KEY in the environment or in .env, then run again.')
    return k


def call(path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None,
                                 headers={'Authorization': 'Bearer ' + key(), 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def pick_model():
    have = {m['id'] for m in call('/models')['data']}
    for m in MODELS:
        if m in have:
            return m
    sys.exit('None of these image models are available to this key: ' + ', '.join(MODELS))


# Trademarked characters, brands and real people get refused or drawn with logos, so the
# picture prompt describes a look-alike instead. The story text the app shows is unchanged.
DEPICT = {
    'Mickey Mouse': 'a cheerful cartoon mouse with big round ears and red shorts',
    'Han Solo': 'a roguish space-smuggler pilot in a black vest',
    'Chewbacca': 'a tall shaggy brown furry space co-pilot with a bandolier',
    'Yoda': 'a tiny wrinkled green old sage with long pointed ears and a brown robe',
    'Minion': 'a small yellow capsule-shaped henchman in goggles and blue overalls',
    'Ken doll': 'a plastic fashion-doll man with perfect blond hair and a fixed smile',
    'Riddler': 'a lanky trickster villain in a bright green suit and bowler hat',
    'hobbit': 'barefoot halfling', 'Hobbit': 'barefoot halfling',
    'Tweety bird': 'a tiny round yellow cartoon canary with a big head',
    'Sonic the Hedgehog': 'a blue cartoon hedgehog with spiky quills and red sneakers',
    'Goofy': 'a tall clumsy cartoon dog',
    'Luigi': 'a tall plumber with a green cap, a moustache and blue overalls',
    'Luke Skywalker': 'a young space farm-boy hero with a glowing blue energy sword',
    'Kung Fu Panda': 'a chubby kung-fu panda warrior',
    'Goku': 'spiky-haired martial artist',
    'Mordor': 'a dark volcanic wasteland',
    'Madonna': 'a flamboyant pop diva with a headset microphone',
    'Charlie Chaplin': 'a silent-film tramp with a bowler hat, small moustache and cane',
    'Zorro': 'a masked swordsman in black with a cape',
    'Zatoichi': 'a blind swordsman with a cane sword',
    'Rocky': 'champion boxer',
    'Kawasaki': 'green sport',
    'Yamaha': 'grand',
    'Zamboni': 'ice-resurfacing machine',
    'Tater Tots': 'crispy potato nuggets',
    'Kool-Aid Man': 'giant grinning pitcher of red fruit punch',
    'Kool': 'giant grinning pitcher of red fruit punch',
}
# Hooks that are a brand or place, not a character: the story already shows them.
NOT_CAST = {'Kawasaki', 'Yamaha', 'Zamboni', 'Tater Tots', 'Mordor'}


def depict(text):
    for name in sorted(DEPICT, key=len, reverse=True):
        text = text.replace(name, DEPICT[name])
    return text


def plain(story):
    """Story without the app's markup ({keyword}, [part], ~hook~)."""
    for a in '{}[]~':
        story = story.replace(a, '')
    return story


def prompt(card):
    cast = '; '.join(f"the recurring character '{depict(s['hook'])}'" for s in card.get('sound', []) if s.get('hook') and s['hook'] not in NOT_CAST)
    return (f"{STYLE}\n\nScene: {depict(plain(card['story']))}\n"
            f"The idea to convey is '{card['keyword']}'." + (f" Make sure {cast} is clearly visible doing what the scene says." if cast else ''))


def generate(card, model, quality, suffix=''):
    name = f"u{ord(card['kanji']):04x}{suffix}.jpg"
    path = OUT / name
    for attempt in range(3):
        try:
            res = call('/images/generations', {'model': model, 'prompt': prompt(card), 'size': '1536x1024', 'quality': quality, 'n': 1})
            img = Image.open(io.BytesIO(base64.b64decode(res['data'][0]['b64_json']))).convert('RGB')
            img = img.resize((480, 320), Image.LANCZOS)
            img.save(path, 'JPEG', quality=80, optimize=True)
            return card['kanji'], f'images/n3/{name}', None
        except urllib.error.HTTPError as e:
            err = e.read().decode()[:300]
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(10 * (attempt + 1)); continue
            return card['kanji'], None, f'HTTP {e.code}: {err}'
        except Exception as e:  # network hiccup
            if attempt < 2:
                time.sleep(5); continue
            return card['kanji'], None, str(e)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--test', action='store_true', help='10 cards at medium and high quality, saved side by side')
    g.add_argument('--all', action='store_true', help='every card that has no images/n3 picture yet')
    g.add_argument('--kanji', help='specific kanji, e.g. 況只閉')
    g.add_argument('--leeches', metavar='PROGRESS_JSON', help='cards missed 3+ times, from a progress download')
    ap.add_argument('--quality', default='medium', choices=['low', 'medium', 'high'])
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()

    data = json.loads(DECK.read_text(encoding='utf8'))
    cards = data['cards']
    by = {c['kanji']: c for c in cards}
    OUT.mkdir(parents=True, exist_ok=True)
    model = pick_model()
    print('model:', model)

    if a.test:
        chosen = [by[k] for k in TEST_SET if k in by]
        jobs = [(c, q, '-' + q) for c in chosen for q in ('medium', 'high')]
    else:
        if a.all:
            chosen = [c for c in cards if not (c.get('image') or '').startswith('images/n3/')]
        elif a.kanji:
            chosen = [by[k] for k in a.kanji if k in by]
        else:
            prog = json.loads(Path(a.leeches).read_text(encoding='utf8'))
            chosen = [by[k] for k, c in prog.get('cards', {}).items() if k in by and (c.get('lapses') or 0) >= 3]
        jobs = [(c, a.quality, '') for c in chosen]
    print(f'{len(jobs)} images to generate')

    done, failed = 0, []
    with ThreadPoolExecutor(a.workers) as ex:
        for k, rel, err in ex.map(lambda j: generate(j[0], model, j[1], j[2]), jobs):
            if err:
                failed.append((k, err)); print('FAIL', k, err)
            else:
                done += 1
                if not a.test:
                    by[k]['image'] = rel
                print(f'{done}/{len(jobs)}', k, rel)

    if not a.test:
        DECK.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'done: {done}, failed: {len(failed)}')
    if a.test:
        print('Compare the -medium and -high files in images/n3/ on your phone at full size.')


if __name__ == '__main__':
    main()
