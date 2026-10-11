# N3 Kanji Sprint

A spaced-repetition app for JLPT N3 with three decks:

- **漢字 Kanji:** the ~612 N3 kanji, with Heisig-style stories and reading hooks.
- **語彙 Words:** 2,096 N3 words, almost the full list. 947 use kanji from the deck and unlock once you've learned those kanji. 911 use kanji above N3 and 238 are written only in kana; these are studied by sound and meaning, the way the exam prints them.
- **文法 Grammar:** 114 N3 grammar points, quizzed in the exam's own formats.

**Live:** https://lczanna.github.io/kanji_mnemonic/

## How it works

- **Deck order:** N5 → N4 → N3. Within each level, the most frequent kanji come first, in groups of about 60. Inside a group the order follows Heisig (RTK), so parts are learned before the kanji built from them.
- **Each card has:**
  - the Heisig keyword
  - a bizarre story built from named parts
  - a *sound cast* hook for the reading the exam uses
  - 2–3 real JLPT words, with readings checked against JMdict
- **Sound cast:** every on'yomi is played by one recurring character (ショウ = Showman, カン = Kangaroo). Voiced readings are that character's "muddy cousin": mud stands for ゛. The full list is in the app under More → Sound cast.
- **Studying:**
  - New cards are learned, quizzed again a few cards later, then checked the next day.
  - Reviews come in order of the lowest recall chance first (FSRS-4.5).
  - Mature cards alternate between the bare kanji and exam-style word reading (e.g. read 学習).
  - No interval runs past exam week.
- **Triage:** one quick pass marks kanji you already know, so the daily plan only counts what's left.
- **Words:** reviews alternate between 漢字読み (read the word aloud) and 表記 (pick the correct kanji spelling from same-sound look-alikes). Kana-only and above-N3 words are quizzed as 意味 (hear or see the kana, recall the meaning), with the kanji spelling shown on the back. Readings were checked against JMdict.
- **Grammar:** each point has a meaning, formation, nuance note and examples. Quizzes alternate between fill-in-the-blank （　） and ★ sentence ordering. The sentences were written for this deck and have not had a native-speaker review; report anything that sounds off.
- **Audio:** ▶ buttons use the phone's built-in Japanese voice.
- **Backup:** progress is stored in the browser. Use More → Back up progress to move it between devices.

## Files

| File | Contents |
|---|---|
| `index.html` | The app (no build step) |
| `kanji.json` | Kanji deck and sound cast |
| `vocab.json` | Words deck (`f` = kanji / mixed / kana, `k` = deck kanji in the word, `d` = 表記 distractors) |
| `grammar.json` | Grammar deck |
| `images/` | Illustrations (93 cards have one so far) |
| `data/sound_cast.json`, `data/primitives.json` | Shared hook and part names used to write stories |
| `optimize_images.py` | Resizes generated images to 480×320 JPEG |
| `index_original.html`, `kanji_srs_app.html` | Earlier versions, kept for reference |

Run locally: `python3 -m http.server`, then open http://localhost:8000. Opening `index.html` straight from disk won't load the deck.

## Sources

Kanji levels, frequency and WaniKani parts come from [kanji-data](https://github.com/davidluzgouveia/kanji-data). Heisig keywords come from [kanjiapi.dev](https://kanjiapi.dev). RTK frame numbers come from [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project). JLPT vocabulary comes from [open-anki-jlpt-decks](https://github.com/jamsinclair/open-anki-jlpt-decks). Readings were checked against [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html). Stories were written for this deck.
