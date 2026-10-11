# N3 Kanji Sprint

A spaced-repetition app for learning the ~612 kanji needed for JLPT N3, using Heisig-style stories plus reading hooks.

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
- **Backup:** progress is stored in the browser. Use More → Back up progress to move it between devices.

## Files

| File | Contents |
|---|---|
| `index.html` | The app (no build step) |
| `kanji.json` | The deck: cards, sound cast |
| `images/` | Illustrations (93 cards have one so far) |
| `data/sound_cast.json`, `data/primitives.json` | Shared hook and part names used to write stories |
| `optimize_images.py` | Resizes generated images to 480×320 JPEG |
| `index_original.html`, `kanji_srs_app.html` | Earlier versions, kept for reference |

Run locally: `python3 -m http.server`, then open http://localhost:8000. Opening `index.html` straight from disk won't load the deck.

## Sources

Kanji levels, frequency and WaniKani parts come from [kanji-data](https://github.com/davidluzgouveia/kanji-data). Heisig keywords come from [kanjiapi.dev](https://kanjiapi.dev). RTK frame numbers come from [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project). JLPT vocabulary comes from [open-anki-jlpt-decks](https://github.com/jamsinclair/open-anki-jlpt-decks). Readings were checked against [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html). Stories were written for this deck.
