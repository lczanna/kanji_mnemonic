# N3 Kanji Sprint

A spaced-repetition app for JLPT N3 with three decks:

- **漢字 Kanji:** the 619 N5–N3 kanji, with Heisig-style stories and reading hooks.
- **語彙 Words:** 2,989 words: the words shown on each kanji card (they unlock right after their kanji) plus 2,096 of the 2,140 N3 words. 947 use kanji from the deck and unlock once you've learned those kanji. 911 use kanji above N3 and 238 are written only in kana; these are studied by sound and meaning, the way the exam prints them.
- **文法 Grammar:** 114 N3 grammar points, quizzed in the exam's own formats.

**Use it here (syncs progress to your Claude account):** https://claude.ai/artifact/4zcASpfem692NjoQduRPuD

**Public copy (saves in the browser only):** https://lczanna.github.io/kanji_mnemonic/

## How it works

- **Deck order:** N5 → N4 → N3. Within each level, the most frequent kanji come first, in groups of about 60. Any deck kanji used as a part (directly, or inside another part such as 土 inside 寺 "Buddhist temple") is moved forward so it is always learned before the kanji built from it.
- **Parts:** tap any part in a story, or a part chip on a card, to see it. A part that is a deck kanji shows its readings and links to its card; any other part shows what it is made of (寺 = soil + glue), and each piece can be tapped in turn.
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
- **Daily plan in minutes:** set your study time for weekdays and weekends (More → Settings; default 30 and 60). Each day, reviews come first and the remaining time is filled with new cards: grammar, then kanji, then words (always at least 30% of the room once words are unlocked). Weekends get proportionally more. The plan recalculates daily from what's left, learns your real speed per card, and Today shows whether each deck is ahead of or behind schedule.
- **Most useful words first:** words are ranked by how often they appear in everyday Japanese; the top 1,200 are scheduled automatically, the rest only once those are all started. "Learn 5 more" adds a mix of kanji, words and grammar on top of the plan.
- **Rounds:** long sessions pause every 50 answers so you can stop at a natural point.
- **Exam plan:**
  - New cards finish 14 days before the exam (adjustable); the rest is review, practice tests and slack.
  - The daily pace recalculates after a missed day, and "Busy day: reviews only" keeps your memory intact on short days.
  - Target recall rises to 95% in the last 14 days, and "Weak spots" drills the 40 cards you're most likely to forget.
- **Exam formats:** 漢字読み multiple choice uses trap answers (long vowels, small っ, ゛), alongside 表記, fill-in-the-blank and ★ ordering. The listening drill plays words and sentences you've studied.
- **Reading help:** words in grammar and example sentences can be tapped for their reading, dictionary form and the meaning used in that sentence, kana words included. Grammar sentences use a hand-checked list of kana words (`tools/kana_glosses.py`) with per-sentence meanings; example sentences pick the dictionary sense that matches their English translation. When the sense can't be pinned down, a kana word shows nothing rather than a wrong meaning.
- **Translations:** every grammar question has its English behind a "Show translation" button, shown automatically once you answer.
- **Words in context:** word cards show 2–3 short example sentences that only use kanji from the deck.
- **Look back:** during a session, ‹ or swipe right shows the cards you just did.
- **Saving:**
  - On the Claude link, progress syncs to your private storage on claude.ai and works across devices.
  - Elsewhere it stays in the browser.
  - More → Your data downloads a full .json backup, per-card stats (.csv) and daily history (.csv).

## Files

| File | Contents |
|---|---|
| `index.html` | The app (no build step) |
| `kanji.json` | Kanji deck and sound cast |
| `vocab.json` | Words deck (`f` = kanji / mixed / kana, `k` = deck kanji in the word, `d` = 表記 distractors) |
| `grammar.json` | Grammar deck |
| `images/n3/` | One illustration per kanji card, drawn from its current story (`u<codepoint>.jpg`, 480×320) |
| `data/sound_cast.json`, `data/primitives.json` | Shared hook and part names used to write stories |
| `tools/build_parts.py` | Records what each story part is made of and reorders the deck so parts come first (needs CHISE `ids.txt`) |
| `tools/pack_images.py` | Bundles the pictures into ~20 packs for the Claude link, which caps its file count |
| `tools/gen_images.py` | Generates card illustrations from the current stories (needs `OPENAI_API_KEY`) |
| `examples.json` | 2–3 example sentences per word (Tanaka corpus, CC-BY), with tap-to-read glosses |
| `tools/rank_vocab.py` | Ranks words by everyday frequency (`p` in `vocab.json`), so the most useful are studied first |
| `tools/build_examples.py` | Builds `examples.json` from `examples.utf` and JMdict |
| `tools/gloss_grammar.py` | Builds the tap-to-read glosses in `grammar.json` |
| `optimize_images.py` | Resizes generated images to 480×320 JPEG |
| `index_original.html`, `kanji_srs_app.html` | Earlier versions, kept for reference |

Run locally: `python3 -m http.server`, then open http://localhost:8000. Opening `index.html` straight from disk won't load the deck.

## Sources

Kanji levels, frequency and WaniKani parts come from [kanji-data](https://github.com/davidluzgouveia/kanji-data). Heisig keywords come from [kanjiapi.dev](https://kanjiapi.dev). RTK frame numbers come from [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project). JLPT vocabulary comes from [open-anki-jlpt-decks](https://github.com/jamsinclair/open-anki-jlpt-decks). Readings were checked against [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html). Stories were written for this deck.
