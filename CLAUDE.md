# Notes for working on this repo

## Never lose the learner's progress

Progress must survive every app update. Before changing `index.html` or the decks:

- **Publish to the same Claude link.** Cloud progress lives in that artifact's database
  (`data/users/<uid>/meta`, `cards0`–`cards3`). Update https://claude.ai/artifact/4zcASpfem692NjoQduRPuD
  in place; publishing a new artifact starts from zero.
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

The app keeps the last 3 daily snapshots on each device (More → Back up progress) as a fallback.

## Deck order and parts

After changing stories or adding cards, run `tools/build_parts.py ids.txt`: it refreshes the `parts` map
and moves parts ahead of the kanji that use them. Progress is keyed by kanji, so reordering is safe.

## Word data

After adding words or changing a reading in `vocab.json`, run `python3 tools/kanji_readings.py` (how each kanji is
read inside each word) and `python3 tools/gloss_fixes.py` (checked meanings and readings in the sentences).
After rebuilding examples, grammar glosses or exam.json, run `python3 tools/gloss_merge.py JMdict_e.gz` (joins words the
tokenizer split, like 不意 + 打ち) and then `python3 tools/kana_fill.py`: it adds tap meanings for
kana words from `data/kana_meanings.json` (checked word by word; null marks tokenizer slips).

## Images

`tools/gen_images.py` draws pictures from the stories. Never print or commit the OpenAI key.

The Claude link holds at most 512 files, so it gets the pictures as packs, not one file per card:
run `python3 tools/pack_images.py <scratch dir>` and publish `images/packs/*` (built, not committed)
together with `index.html`, `kanji.json`, `vocab.json`, `grammar.json` and `examples.json`. Don't publish `images/n3/`.
The app tries `images/n3/` first and falls back to the packs, so GitHub Pages needs nothing extra.
