#!/usr/bin/env python3
"""
Copy the memory hooks in data/word_mnemonics.json into vocab.json (field "mn"), shown on word cards, and the
"don't confuse" notes in data/word_twins.json (field "nc": {other, note}) for words that sound almost the same.
Edit the hooks there and rerun; a word without a hook simply shows none.
A kanji's own kun word (連れる for 連, whose story ends "… ^Two Rails^ … (つれる).") instead gets that sentence as
its hook and "ki": the kanji, whose picture it shows, so the word and the kanji share one mnemonic.

  python3 tools/add_word_hooks.py
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def kun_hooks(vocab):
    """word -> (the kanji story's kun sentence, kanji) for each kanji whose story teaches that word's reading."""
    by_w = {v['w']: v for v in vocab}
    cards = json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards']
    out = {}
    for c in cards:
        story = c.get('story', '')
        reads = re.findall(r'\(([\u3041-\u3096]+)\)', story)
        at = story.find('^')
        if at < 0 or not reads:
            continue
        # the sentence holding the sound-alike: from the sentence break before it to the one after its (かな)
        starts = [m.end() for m in re.finditer(r"[.!?]'?\s+(?=[A-Z'^~])", story[:at + 1])]
        start = starts[-1] if starts else 0
        close = story.find(')', story.find('(' + reads[-1] + ')', at))
        end = re.search(r"[.!?]'?(?=\s|$)|$", story[close:])
        sent = story[start:close + end.end()].strip()
        sent = re.sub(r'\[([^\]]+)\]', r'\1', sent)   # [part] links belong to the kanji card
        for e in c.get('vocab', []):
            v = by_w.get(e['w'])
            # the kanji plus kana only (連れる, 七つ, 表), read as the story says
            if v and e['r'] == v['r'] and v['r'].startswith(reads[-1]) and re.fullmatch(re.escape(c['kanji']) + r'[\u3041-\u3096々]*', v['w']):
                out[v['w']] = (sent, c['kanji'])
                break
    return out


def main():
    hooks = json.loads((ROOT / 'data' / 'word_mnemonics.json').read_text(encoding='utf8'))
    path = ROOT / 'vocab.json'
    vocab = json.loads(path.read_text(encoding='utf8'))
    words = {v['w'] for v in vocab}
    missing = [w for w in hooks if not w.startswith('_') and w not in words]
    assert not missing, f'hooks for words not in the deck: {missing}'
    n = 0
    for v in vocab:
        if v['w'] in hooks:
            v['mn'] = hooks[v['w']]; n += 1
        else:
            v.pop('mn', None)
    kun = kun_hooks(vocab)
    for v in vocab:
        if v['w'] in kun:
            v['mn'], v['ki'] = kun[v['w']]
        else:
            v.pop('ki', None)
    print(f'{len(kun)} words share their kanji\'s sound-alike')
    # "fa": a word stored as mixed (shown in kana) whose kanji are now all in the deck; the app shows it in kanji
    # once the learner has those kanji.
    deck = {c['kanji'] for c in json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards']}
    for v in vocab:
        if v.get('f') == 'mixed' and '々' not in v['w'] and all(ch in deck for ch in v['w'] if re.match(r'[\u3400-\u9fff]', ch)):
            v['fa'] = 1
        else:
            v.pop('fa', None)
    twins = json.loads((ROOT / 'data' / 'word_twins.json').read_text(encoding='utf8')) if (ROOT / 'data' / 'word_twins.json').exists() else {}
    assert all(w in words and all(o in words for o in t['other'].split('・')) for w, t in twins.items()), 'twins for words not in the deck'
    for v in vocab:
        if v['w'] in twins:
            v['nc'] = twins[v['w']]
        else:
            v.pop('nc', None)
    path.write_text(json.dumps(vocab, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    print(f'{n} words have a memory hook')


if __name__ == '__main__':
    main()
