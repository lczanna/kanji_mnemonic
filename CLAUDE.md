# Notes for working on this repo

## Never lose the learner's progress

Progress must survive every app update. Before changing `index.html` or the decks:

- **Publish to the same Claude link.** Cloud progress lives in that artifact's database
  (`data/users/<uid>/meta`, `cards0`–`cards3`). Update https://claude.ai/artifact/4zcASpfem692NjoQduRPuD
  in place; publishing a new artifact starts from zero.
- **Keep the storage keys:** `localStorage` `kanji_srs_data` and `kanji_srs_snapshots`, and the database paths above.
- **Keep the card keys:** kanji character, `v:<word>` for words, `g:<id>` for grammar. Fixing a word's spelling
  or a grammar id orphans its progress, so carry the old key's entry over to the new key in `loadData`.
- **Only add fields.** `loadData` fills missing fields from `emptyData()`; never drop or rename existing ones.
  If a format change is unavoidable, migrate in `loadData` and bump `version`.
- **Test on old data** before publishing: load an existing backup (More → Download progress) and check the
  card count is unchanged.

The app keeps the last 3 daily snapshots on each device (More → Back up progress) as a fallback.

## Images

`tools/gen_images.py` draws pictures from the stories. Never print or commit the OpenAI key.
