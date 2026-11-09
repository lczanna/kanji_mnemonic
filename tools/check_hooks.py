#!/usr/bin/env python3
"""Every kun sound-alike (^hook^ in a kanji story) must be made of real English words.

    pip install wordfreq; python3 tools/check_hooks.py

Catches hooks that glue a Japanese fragment onto an English word (Tsuge-tugboat, Utsu-seal). A word passes when it is
common enough in English or listed in OK below (names, exclamations and the few Japanese words a learner knows).
Exits 1 and lists the kanji when a hook fails; the regression tests run it when wordfreq is installed.
"""
import json, re, sys
from pathlib import Path
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parent.parent
OK = set('''itsy bitsy mutts cackle gashed knocker shimmers koto mochi yos hayabusa columbo okie achoo eesh sarong kaeru
tanuki acapella kazoo coots meerkat gerbils macaw squeegee ouchie nozomi neigh marimba fugu wassup hedgehog nag
qatari yeoman onsen minotaur gnocchi hookah cumin sashimi tattered'''.split())

bad = []
for c in json.loads((ROOT / 'kanji.json').read_text(encoding='utf8'))['cards']:
    for hook in re.findall(r'\^([^^]+)\^', c.get('story', '')):
        words = [w.lower() for w in re.findall(r"[A-Za-z]+", hook.replace("'s", ''))]
        odd = [w for w in words if len(w) > 1 and w not in OK and zipf_frequency(w, 'en') < 2.5]
        if odd:
            bad.append(f"{c['kanji']} ^{hook}^: {', '.join(odd)}")
print('\n'.join(bad) if bad else 'all kun sound-alikes are real English')
sys.exit(1 if bad else 0)
