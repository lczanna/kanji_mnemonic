# Notes for working on this repo

## Never lose the learner's progress

Progress must survive every app update. Before changing `index.html` or the decks:

- **Publish to the same Claude link:** the one after "Use it here" in `README.md`. Cloud progress lives in that
  artifact's database (`data/users/<uid>/meta`, `cards0`–`cards3`). Update it in place; publishing a new artifact
  starts from zero. In a copy of this repo, that link is still the original owner's (you can't publish to it):
  publish once as a new artifact, with the files listed under Images, put its link in `README.md`, and use it from then on.
- **Keep the storage keys:** `localStorage` `kanji_srs_data` and `kanji_srs_snapshots`, and the database paths above.
  `kanji_srs_session` holds the session in progress (resumed after a reload or from Today); cards in it are
  stored by key, so keep `unpackItem` able to read old entries.
- **Keep the card keys:** kanji character, `v:<word>` for words, `g:<id>` for grammar, `p:<a>|<b>` for look-alike
  pairs, `c:<glyph>` for part cards (data/part_cards.json). Fixing a word's spelling
  or a grammar id orphans its progress, so carry the old key's entry over to the new key in `loadData`.
- **Only add fields.** `loadData` fills missing fields from `emptyData()`; never drop or rename existing ones.
  If a format change is unavoidable, migrate in `loadData` and bump `version`.
- **Test on old data** before publishing: load an existing backup (More → Download progress) and check the
  card count is unchanged.
- **Run `node tests/regression.mjs`** before every publish: loading progress from the account on an empty device,
  waiting for it before studying, the merge rule (more reviews wins), never overwriting a reviewed card, old data.
  Add a test for every progress bug found.

The app keeps the last 3 daily snapshots on each device (More → Back up progress) as a fallback.

## Deck order and parts

After changing stories or adding cards, run `tools/build_parts.py ids.txt`: it refreshes the `parts` map
and moves parts ahead of the kanji that use them. Progress is keyed by kanji, so reordering is safe.

## Word data

A kanji's own kun word (連れる for 連) has no hook of its own: `tools/add_word_hooks.py` gives it the kanji story's
`^sound-alike^` sentence and picture (field `ki`), so the learner memorises one mnemonic. After changing a kanji story's
kun sentence, rerun `python3 tools/add_word_hooks.py`. Sound-alikes are real English words or phrases you can picture
(Two Rails, Minotaur), never the Japanese word with an animal glued on.

After adding words or changing a reading in `vocab.json`, run `python3 tools/kanji_readings.py` (how each kanji is
read inside each word) and `python3 tools/gloss_fixes.py` (checked meanings and readings in the sentences). Also `python3 tools/alt_readings.py JMdict_e.gz`:
the other readings each spelling has (空: から and そら), which the reading quiz never offers as wrong answers.
`tools/build_exam.py JMdict_e.gz` keeps what exam.json already has (hand-fixed tap meanings, word questions, both
practice exams) and builds only new or edited items; new words' questions need `--add-words` once checked, and `--fresh`
starts over (losing hand fixes). After a rebuild, the chain below should leave exam.json unchanged except for what you added.
After rebuilding examples, grammar glosses or exam.json, run `python3 tools/gloss_merge.py JMdict_e.gz` (joins words the
tokenizer split, like 不意 + 打ち; run it after gloss_fixes.py, whose fixes count tokens) and then `python3 tools/kana_fill.py`: it adds tap meanings for
kana words from `data/kana_meanings.json` (checked word by word; null marks tokenizer slips). Last, `python3 tools/na_glosses.py`: な-adjectives before に/な get their adverb or adjective meaning
(自由に: freely, not 'freedom'; `data/na_glosses.json`). Then `python3 tools/gloss_audit.py`: the hand-checked fixes from the
sentence audit (`data/gloss_audit.json`: wrong senses and readings, keyed by word, reading and old meaning, plus a few
one-sentence fixes). Finally `python3 tools/kana_split.py JMdict_e.gz`: words the texts spell in kana that the
tokenizer cut up (かいさつ → かい "floor" + さつ) become one tappable word (改札); its SKIP list holds grammar endings that look like nouns.

## Images

`tools/gen_images.py` draws pictures from the stories. Never print or commit the OpenAI key.
After drawing kanji pictures, run `python3 tools/check_images.py --kanji "<those>"`: it lists pictures where the
Japanese-reading sound-alike (`^hook^`) is missing or too small; redraw those. Hooks must be drawable things (pictures never contain text).

The Claude link holds at most 512 files, so it gets the pictures as packs, not one file per card:
run `python3 tools/pack_images.py <scratch dir> --keep <published images/packs/index.json>` (read it from the link first)
and publish the packs that changed (built, not committed): pictures stay in their published packs and new ones go in new packs
together with `index.html`, `kanji.json`, `vocab.json`, `grammar.json` and `examples.json`. Don't publish `images/n3/`.
The app tries `images/n3/` first and falls back to the packs, so GitHub Pages needs nothing extra.

## Listening audio

`tools/gen_speech.py` records words and sentences; after recording sentences run `--readings JMdict_e.gz`: it checks each
sentence against the tap readings (the voice guesses readings: 古家 came out こいえ, not ふるや) and records misread ones
again with ambiguous words in kana. `--accent` does the same for single words that sound foreign.

`tools/gen_audio.py` records the listening items with clearly male and clearly female voices and checks each line's
pitch. For the Claude link, read the published `audio/packs/clips.json` and run
`python3 tools/pack_audio.py <scratch dir> --keep <that index>`: clips stay in their published packs, so only the packs
holding re-recorded clips need publishing. Packs are plain MP3 bytes (`c00.mp3`…), not base64: the link holds at most
256 MB a version (pictures ~134 MB, audio ~95 MB), so check the total before adding much more.
