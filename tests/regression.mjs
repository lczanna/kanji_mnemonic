// Regression tests: the learner's progress must survive every app update and every way the app can start.
// Runs the real index.html in headless Chromium with a fake Claude account (window.claude: db + user).
//
//   node tests/regression.mjs          # from the repo root; exits 1 if any test fails
//
// Run before every publish (CLAUDE.md).
import { createRequire } from 'module';
import { spawn } from 'child_process';
import fs from 'fs';
const { chromium } = createRequire(import.meta.url)('playwright');   // global install works too

const ROOT = new URL('..', import.meta.url).pathname;
const PORT = 8790 + Math.floor(Math.random() * 100);
const URL_ = `http://localhost:${PORT}/index.html`;
const T = new Date(); const ymd = d => d.toISOString().slice(0, 10);
const daysAgo = n => ymd(new Date(Date.now() - n * 86400000));

// A learner several weeks in: kanji, words, grammar, parts, a look-alike pair; some reviewed many times.
const kanji = JSON.parse(fs.readFileSync(ROOT + 'kanji.json', 'utf8'));
const vocab = JSON.parse(fs.readFileSync(ROOT + 'vocab.json', 'utf8'));
const grammar = JSON.parse(fs.readFileSync(ROOT + 'grammar.json', 'utf8'));
const cards = {};
const pack = (s, reps, last, due) => [s, 5, reps, 0, last, due, 0];
kanji.cards.slice(0, 250).forEach((k, i) => { cards[k.kanji] = pack(10 + i % 30, 2 + i % 6, daysAgo(1 + i % 9), daysAgo(-3 - i % 20)); });
vocab.filter(v => v.p && v.p < 400).slice(0, 200).forEach((v, i) => { cards['v:' + v.w] = pack(8, 1 + i % 5, daysAgo(1 + i % 7), daysAgo(-2 - i % 15)); });
grammar.slice(0, 30).forEach((g, i) => { cards['g:' + g.id] = pack(6, 3, daysAgo(2), daysAgo(-4)); });
kanji.partCards.slice(0, 20).forEach(p => { cards['c:' + p.kanji] = pack(9, 2, daysAgo(3), daysAgo(-6)); });
cards['v:健康'] = pack(13.978, 5, daysAgo(2), daysAgo(-10));
cards['一'] = pack(34.7, 4, daysAgo(8), daysAgo(-20));
const REMOTE_N = Object.keys(cards).length;
const meta = { stats: { totalReviews: 3000, correctReviews: 2500 }, settings: {}, settingsAt: 1, history: { [daysAgo(1)]: 150 }, newByDay: {}, hookSeen: {} };

// The fake account: docs in memory, optional delay or failure, every write recorded.
function fakeClaude(opts) {
  window.__writes = [];
  const docs = opts.docs;
  const wait = () => new Promise(r => setTimeout(r, opts.delay || 0));
  const db = { doc: path => ({
    get: async () => { await wait(); if (opts.fail) throw new Error('offline'); const name = path.split('/').pop(); return { exists: !!docs[name], data: () => docs[name] }; },
    set: async body => { window.__writes.push([path.split('/').pop(), JSON.parse(JSON.stringify(body))]); },
  }) };
  window.claude = { use: async cap => cap === 'db' ? db : cap === 'user' ? { id: async () => 'u_test' } : null };
}

const server = spawn('python3', ['-m', 'http.server', String(PORT)], { cwd: ROOT, stdio: 'ignore' });
await new Promise(r => setTimeout(r, 800));
const browser = await chromium.launch(fs.existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {});
let failed = 0;
async function page(opts = {}, local) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const p = await ctx.newPage();
  p.errors = []; p.on('pageerror', e => p.errors.push(e.message));
  if (opts.cloud !== false) await p.addInitScript(fakeClaude, { docs: { meta, cards0: { cards } }, delay: opts.delay, fail: opts.fail });
  if (local) await p.addInitScript(([k, v]) => { if (!sessionStorage.__seeded) { localStorage.setItem(k, v); sessionStorage.__seeded = 1; } }, ['kanji_srs_data', JSON.stringify(local)]);
  await p.goto(URL_);
  await p.waitForFunction(() => typeof DECK !== 'undefined' && DECK.length > 0);
  return p;
}
async function test(name, fn) {
  try { await fn(); console.log('ok  ', name); }
  catch (e) { failed++; console.log('FAIL', name, '\n     ', e.message.split('\n')[0]); }
}
const eq = (a, b, what) => { if (a !== b) throw new Error(`${what}: expected ${b}, got ${a}`); };
const yes = (v, what) => { if (!v) throw new Error(what); };
const pulled = p => p.waitForFunction(() => SYNC.pulled && !SYNC.waiting, null, { timeout: 15000 });

await test('empty device loads every card from the account', async () => {
  const p = await page();
  await pulled(p);
  eq(await p.evaluate(() => Object.keys(appData.cards).length), REMOTE_N, 'cards after loading');
  eq(await p.evaluate(() => appData.cards['v:健康'].reps), 5, '健康 reviews');
  yes(!(await p.evaluate(() => newQueueOf('vocab').some(v => v.w === '健康'))), '健康 offered as new');
  yes(!(await p.evaluate(() => newQueueOf('kanji').some(k => k.kanji === '一'))), '一 offered as new');
  eq(p.errors.length, 0, 'page errors: ' + p.errors.join('; '));
});

await test('nothing is pushed until the account copy has been merged, and the push loses no card', async () => {
  const p = await page({ delay: 3000 });
  eq(await p.evaluate(() => window.__writes.length), 0, 'writes before loading');
  await pulled(p);
  await p.waitForTimeout(300);
  const pushed = await p.evaluate(() => window.__writes.filter(([n]) => n.startsWith('cards')).reduce((a, [, b]) => a + Object.keys(b.cards).length, 0));
  yes(pushed === 0 || pushed >= REMOTE_N, `push would drop cards: ${pushed} of ${REMOTE_N}`);
});

await test('studying waits while progress loads; lessons for cards you have are dropped', async () => {
  const p = await page({ delay: 2500 });
  await p.evaluate(() => runQueue([], [{ type: 'vocab', x: BY_WORD['健康'], mode: 'learn' }, { type: 'kanji', x: BY_KANJI['一'], mode: 'learn' },
    { type: 'vocab', x: VOCAB.find(v => v.p > 1500), mode: 'learn' }], 'all'));
  yes(await p.evaluate(() => !session && !$('modal').hidden && /Loading your progress/.test($('modal-body').textContent)), 'session started before progress loaded');
  await pulled(p);
  eq(await p.evaluate(() => $('modal').hidden), true, 'loading notice closes');
  eq(await p.evaluate(() => parked ? parked.queue.length : 0), 1, 'lessons left after loading (only the unknown word)');
});

await test('a session restored at start-up waits for progress and loses its known lessons', async () => {
  const p = await page({ delay: 2000 });
  await p.evaluate(() => { localStorage.setItem('kanji_srs_session', JSON.stringify({ day: today(), parked: false, s: { queue: [{ t: 'vocab', k: 'v:健康', mode: 'learn' }, { t: 'kanji', k: '一', mode: 'learn' }], i: 0, revealed: false, done: 0, kind: 'study', type: 'all' } })); });
  await p.reload();
  await p.waitForFunction(() => typeof DECK !== 'undefined' && DECK.length > 0);
  eq(await p.evaluate(() => !!session), false, 'restored session opened before progress loaded');
  await pulled(p);
  eq(await p.evaluate(() => !!session || !!(parked && parked.queue.length)), false, 'known lessons survived loading');
});

await test('if the account cannot be reached, nothing is written and studying asks first', async () => {
  const p = await page({ fail: true });
  await p.waitForFunction(() => SYNC.failed);
  await p.evaluate(() => runQueue([], [{ type: 'vocab', x: BY_WORD['健康'], mode: 'learn' }], 'all'));
  yes(await p.evaluate(() => !session && /Couldn't load your progress/.test($('modal-body').textContent)), 'no warning before studying');
  eq(await p.evaluate(() => window.__writes.length), 0, 'writes to the account');
});

await test('merge: the copy with more reviews wins, whatever the dates', async () => {
  const p = await page({ cloud: false });
  const r = await p.evaluate(() => {
    const old = { stability: 14, difficulty: 7, reps: 5, lapses: 1, lastReview: '2026-01-02', due: '2026-02-01' };
    const relearned = { stability: 3, difficulty: 5, reps: 1, lapses: 0, lastReview: '2099-01-01', due: '2099-01-03' };
    appData.cards['v:健康'] = relearned; mergeRemote({ cards: { 'v:健康': old }, meta: null });
    const a = appData.cards['v:健康'].reps;
    appData.cards['v:健康'] = Object.assign({}, old, { reps: 6, lastReview: '2026-01-05' }); mergeRemote({ cards: { 'v:健康': old }, meta: null });
    return [a, appData.cards['v:健康'].reps];
  });
  eq(r[0], 5, 're-taught copy vs real history');
  eq(r[1], 6, 'newer review on this device');
});

await test('"Already know it" and "Got it" never overwrite a reviewed card', async () => {
  const p = await page();
  await pulled(p);
  const r = await p.evaluate(() => {
    markKnown('v:健康'); const a = appData.cards['v:健康'].reps;
    SYNC.anyway = true; runQueue([], [{ type: 'vocab', x: BY_WORD['健康'], mode: 'learn' }], 'all');
    document.getElementById('a-learned')?.click();
    return [a, appData.cards['v:健康'].reps, (session ? session.queue : []).filter(q => q.x === BY_WORD['健康'] && q.mode === 'quiz').length];
  });
  eq(r[0], 5, 'reviews after "Already know it"'); eq(r[1], 5, 'reviews after "Got it"'); eq(r[2], 0, 'extra first-quiz for a reviewed card');
});

await test('old saved data (no newer fields) loads with every card and keeps the storage keys', async () => {
  const local = { version: 2, cards: { '一': { stability: 30, difficulty: 3, reps: 4, lapses: 0, lastReview: daysAgo(5), due: daysAgo(-20) },
    'v:健康': { stability: 13, difficulty: 7, reps: 5, lapses: 1, lastReview: daysAgo(2), due: daysAgo(-9) } },
    stats: { totalReviews: 10 }, settings: {}, history: {}, newByDay: {}, triaged: {} };
  const p = await page({ cloud: false }, local);
  const r = await p.evaluate(() => [Object.keys(appData.cards).length, typeof appData.hookSeen, !!localStorage.getItem('kanji_srs_data'), appData.cards['v:健康'].reps]);
  eq(r[0], 2, 'cards'); eq(r[1], 'object', 'missing fields filled'); eq(r[2], true, 'storage key kanji_srs_data'); eq(r[3], 5, 'reviews kept');
  eq(p.errors.length, 0, 'page errors: ' + p.errors.join('; '));
});

await test('every card key the app uses still exists in the decks (no orphaned progress)', async () => {
  const p = await page({ cloud: false });
  const missing = await p.evaluate(keys => keys.filter(k => k.startsWith('v:') ? !BY_WORD[k.slice(2)] : k.startsWith('g:') ? !BY_GID[k.slice(2)]
    : k.startsWith('c:') ? !BY_PART[k.slice(2)] : k.startsWith('p:') ? false : !BY_KANJI[k]), Object.keys(cards));
  eq(missing.length, 0, 'keys without a card: ' + missing.slice(0, 5).join(' '));
});

await test('look-alike groups with a part card (矢): shown on cards, never quizzed or turned into a lesson card', async () => {
  const p = await page({ cloud: false });
  await p.waitForFunction(() => LOOK.length > 0);
  const r = await p.evaluate(() => {
    const C = { stability: 5, difficulty: 5, reps: 3, lapses: 0, lastReview: today(), due: '2099-01-01' };
    for (const c of ['午', '牛', '天', '夫', '失', 'c:矢']) appData.cards[c] = Object.assign({}, C);
    const quizzed = new Set([...peersOf('牛'), ...peersOf('失'), ...whichItem(BY_KANJI['午']).opts, ...whichItem(BY_KANJI['失']).opts]);
    return { inGroups: groupsOf('矢').length, quizzedPart: quizzed.has('矢'), lessons: pendingLookLessons(20).every(i => i.x && BY_KANJI[i.x.kanji]),
      panel: /Don't confuse/.test(partBackHtml(BY_PART['矢'])) };
  });
  yes(r.inGroups >= 1, 'dart not in any group'); eq(r.quizzedPart, false, 'part offered as a quiz answer');
  eq(r.lessons, true, 'lesson card for a part'); eq(r.panel, true, 'part card shows its look-alikes');
  eq(p.errors.length, 0, 'page errors: ' + p.errors.join('; '));
});

await test('sorting added N4 words: Know it makes a light card, Not yet leaves it to learn, Undo restores, reviewed cards untouched', async () => {
  const p = await page({ cloud: false });
  const r = await p.evaluate(() => {
    const ws = wordsToSort(); if (ws.length < 3) return { n: ws.length };
    appData.cards['v:' + ws[2].w] = { stability: 9, difficulty: 5, reps: 4, lapses: 0, lastReview: today(), due: '2099-01-01' };
    startWordTriage();
    const a = session.queue[0].x.w, b = session.queue[1].x.w;
    triageAnswer(true); triageAnswer(false); triageUndo(); triageAnswer(false);
    return { n: ws.length, a: appData.cards['v:' + a], triA: appData.triaged['v:' + a], b: appData.cards['v:' + b] || null, triB: appData.triaged['v:' + b],
      third: appData.cards['v:' + ws[2].w].reps, inQueue: session.queue.some(q => q.x.w === ws[2].w) };
  });
  yes(r.n >= 3, 'no words to sort');
  eq(r.triA, 'known', 'first word marked'); eq(r.a.reps, 1, 'known word gets a light card'); eq(!!r.a.triaged, true, 'known card is triaged');
  eq(r.b, null, '"Not yet" makes no card'); eq(r.triB, 'unknown', 'second word marked unknown');
  eq(r.inQueue, false, 'a word you already have offered for sorting'); eq(r.third, 4, 'reviewed card kept');
  eq(p.errors.length, 0, 'page errors: ' + p.errors.join('; '));
});

await test('furigana only over kanji you haven\'t studied, in sentences and ordering parts', async () => {
  const p = await page({ cloud: false });
  const r = await p.evaluate(() => {
    for (const c of ['話', '仕', '事']) appData.cards[c] = { stability: 5, difficulty: 5, reps: 3, lapses: 0, lastReview: today(), due: '2099-01-01' };
    const o = BY_GID['ni-tsuite'].order;
    return { split: furiHtml('話し合った', 'はなしあった'), known: furiHtml('仕事', 'しごと'), chunk: rubyRuns(o.chunks[2], o.rb.chunks[2]), hasRb: GRAMMAR.filter(g => g.order).every(g => g.order.rb) };
  });
  eq(r.split, '話し<ruby>合<rt>あ</rt></ruby>った', 'reading split over the kanji'); eq(r.known, '仕事', 'studied kanji stay bare');
  yes(/<ruby>両親<rt>りょうしん<\/rt><\/ruby>/.test(r.chunk), 'ordering part without its reading: ' + r.chunk); eq(r.hasRb, true, 'ordering items without readings');
});

await test('a word a text spells in kana shows in kanji once you\'ve studied it, never a homophone', async () => {
  const p = await page({ cloud: false });
  const r = await p.evaluate(() => {
    const t = Object.keys(GL).find(s => s.includes('かいだんを使ってください'));
    const before = glossHtml(t, true), plain = glossHtml(t);
    appData.cards['v:階段'] = { stability: 5, difficulty: 5, reps: 2, lapses: 0, lastReview: today(), due: '2099-01-01' };
    const after = glossHtml(t, true), after2 = glossHtml(t);
    let swaps = 0, bad = [];
    for (const [s, ws] of Object.entries(GL)) for (const [st, len, , lemma, lr, m] of ws) {
      const w = s.slice(st, st + len), v = kanaWordOf(lemma, lr, m);
      if (!v) continue;
      appData.cards['v:' + v.w] = appData.cards['v:' + v.w] || { reps: 1 };
      const k = kanaToKanji(w, lemma, m, lr);
      if (k !== w) { swaps++; if (kata2hira(v.r).slice(0, 1) !== w.slice(0, 1) || k.length > w.length) bad.push(w + '→' + k); }
    }
    return { plain: after2 === plain, before: !/>かいだん<\/button>/.test(before), after: /<ruby>階段<rt>かいだん<\/rt><\/ruby>/.test(after), swaps, bad: bad.slice(0, 10) };
  });
  eq(r.before, false, 'kana until studied'); eq(r.plain, true, 'swapped outside reading passages'); eq(r.after, true, '階段 with furigana over the kanji not studied');
  yes(r.swaps > 20, 'few words swapped: ' + r.swaps); eq(r.bad.length, 0, 'odd swaps: ' + r.bad);
});

await test('a kana word whose meaning names the studied word shows in kanji (たのみ → 頼み); kana-spelled words and unclear ones stay', async () => {
  const p = await page({ cloud: false });
  const r = await p.evaluate(() => {
    for (const w of ['頼む', '為', '沢山', '厚い', '暑い', '熱い', '傘']) appData.cards['v:' + w] = { reps: 2 };
    return [kanaToKanji('たのみ', 'たのむ', 'to ask, request (頼む); (たのむよ) please', 'たのむ'),
      kanaToKanji('ため', 'ため', 'for (the sake of); in order to', 'ため'),
      kanaToKanji('たくさん', 'たくさん', 'a lot; many', 'たくさん'),
      kanaToKanji('あつい', 'あつい', 'hot (暑い weather; 熱い to the touch); thick (厚い)', 'あつい'),
      kanaToKanji('かさ', 'かさ', 'umbrella', 'かさ'),
      kanaToKanji('とれる', 'とれる', '(photo) to come out (撮れる)', 'とれる')];
  });
  eq(r.join(' '), '頼み ため たくさん あつい 傘 とれる', 'swaps');
});

await test('exam conditions: no tap meanings until answered, long texts come up early, the setting survives old data', async () => {
  const p = await page({ cloud: false });
  const r = await p.evaluate(() => {
    const x = EXAM.read.find(r => r.kind === 'long');
    const it = { type: 'exam', x, mode: 'exam', answers: [] };
    session = { kind: 'study', queue: [it], i: 0, revealed: false };
    const open = examScreen(it, []).inner.front;
    appData.settings.examMode = true;
    const strict = examScreen(it, []).inner.front;
    session.revealed = true;
    const after = examScreen(it, []).inner.front;
    appData.settings.examMode = false; session = null;
    return { longs: EXAM.read.filter(r => r.kind === 'long').length, open: /class="gl"/.test(open), strict: /class="gl"/.test(strict),
      after: /class="gl"/.test(after), firstKinds: mixKinds(EXAM.read).slice(0, 4).map(r => r.kind).join(' '), def: emptyData().settings.examMode };
  });
  yes(r.longs >= 8, 'long texts: ' + r.longs); eq(r.open, true, 'taps normally'); eq(r.strict, false, 'no taps under exam conditions');
  eq(r.after, true, 'taps after answering'); eq(r.firstKinds, 'short medium long info', 'kinds in turn'); eq(r.def, false, 'off by default');
});

await test('underlined phrases ①②③ in reading texts: underlined with and without tap meanings, the number itself not', async () => {
  const p = await page({ cloud: false });
  const r = await p.evaluate(() => {
    const x = EXAM.read.find(r => r.under && r.under.length === 3);
    const d = document.createElement('div');
    d.innerHTML = passageHtml(x.text, x.under);
    const tapped = [...d.querySelectorAll('.ul')].map(e => e.textContent).join('');
    d.innerHTML = x.text.split('\n').map(l => underHtml(l, underRanges(l, x.under))).join('');
    const plain = [...d.querySelectorAll('.ul')].map(e => e.textContent).join('');
    const want = x.under.join('');
    return { tapped: tapped.replace(/[\u3040-\u309f]*(?=)/g, '') && tapped.includes(x.under[0].slice(-2)), plainOk: plain === want, circled: /[①②③]/.test(tapped + plain), first: EXAM.read.filter(r => r.kind === 'medium').length && mixKinds(hardFirst(EXAM.read)).find(r => r.kind === 'medium').hard };
  });
  yes(r.tapped, 'underlined with tap meanings'); yes(r.plainOk, 'underlined without tap meanings');
  eq(r.circled, false, 'the circled number is not underlined'); eq(r.first, true, 'the exam-style texts come first');
});

await test('"I mix these up" on a look-alike makes a pair card and leaves both kanji cards untouched', async () => {
  const p = await page({ cloud: false });
  await p.waitForFunction(() => LOOK.length && groupsOf('以').length);
  const r = await p.evaluate(() => {
    for (const c of ['以', '代']) appData.cards[c] = { stability: 9, difficulty: 5, reps: 4, lapses: 0, lastReview: today(), due: '2099-01-01' };
    const before = JSON.stringify([appData.cards['以'], appData.cards['代']]);
    document.body.insertAdjacentHTML('beforeend', `<div id="t-lk">${lookPanelHtml(BY_KANJI['以'])}</div>`);
    const b = document.querySelector('#t-lk [data-mix="代|以"]');
    if (b) b.click();
    return { btn: !!b, card: !!appData.cards['p:代|以'], same: JSON.stringify([appData.cards['以'], appData.cards['代']]) === before, again: !document.querySelector('#t-lk [data-mix="代|以"]') };
  });
  eq(r.btn, true, 'button shown'); eq(r.card, true, 'pair card made'); eq(r.same, true, 'kanji cards changed'); eq(r.again, true, 'button still there');
});

await test('reading traps keep the kana you can see (代わり: only the 代 part changes)', async () => {
  const p = await page({ cloud: false });
  const r = await p.evaluate(() => {
    const mixed = VOCAB.filter(v => vform(v) === 'kanji' && /[ぁ-ん]/.test(v.w) && /[一-鿿]/.test(v.w));
    let withQ = 0; const bad = [];
    for (const v of mixed) {
      const t = readingTraps(v.r, v.w); if (!t) continue; withQ++;
      const tail = v.w.match(/[ぁ-ん]+$/), head = v.w.match(/^[ぁ-ん]+/);
      for (const x of t) if ((tail && !x.endsWith(tail[0])) || (head && !x.startsWith(head[0]))) bad.push(v.w + ':' + x);
    }
    return { n: mixed.length, withQ, bad: bad.slice(0, 8), kawari: readingTraps('かわり', '代わり') };
  });
  eq(r.bad.length, 0, 'traps change visible kana: ' + r.bad); yes(r.withQ > r.n * 0.7, `only ${r.withQ}/${r.n} words get the question`);
  yes(r.kawari && r.kawari.every(x => x.endsWith('わり')), '代わり traps: ' + r.kawari);
});

await test('a backlog fits the day\'s minutes: most-forgotten reviews first, the rest wait untouched, no new cards', async () => {
  const p = await page({ cloud: false });
  const r = await p.evaluate(() => {
    const t = today(), ago = n => addDays(t, -n);
    DECK.slice(0, 300).forEach((k, i) => { appData.cards[k.kanji] = { stability: 2 + i % 40, difficulty: 5, reps: 3, lapses: 0, lastReview: ago(5 + i % 10), due: ago(1 + i % 3) }; });
    Object.assign(appData.settings, { budgetWeekday: '30', budgetWeekend: '30' }); appData.planDay = null; appData.studySec = {}; planCache = null;
    const before = JSON.stringify(appData.cards);
    const p = planToday(), rev = appData.planDay.rev, cap = Math.max(20, Math.floor((30 - p.practiceMin) * 60 / p.t.review));
    const shown = dueToday('kanji').length, allDue = dueOf('kanji').length;
    const untouched = JSON.stringify(appData.cards) === before;
    const worstIn = Math.max(...rev.map(k => recall(appData.cards[k]))), bestOut = Math.min(...dueOf('kanji').map(x => x.kanji).filter(k => !rev.includes(k)).map(k => recall(appData.cards[k])));
    // An old day plan (no review list) from earlier today is refitted, minus the minutes already studied.
    appData.planDay = { date: t, due: 300, t: timing() }; appData.studySec = { [t]: 600 }; planCache = null; planToday();
    const refit = appData.planDay.rev.length;
    // A light day: everything due fits, nothing waits, and new cards come back.
    for (const k of DECK.slice(20, 300)) delete appData.cards[k.kanji];
    appData.planDay = null; appData.studySec = {}; planCache = null; const light = planToday();
    return { cap, revN: rev.length, shown, allDue, untouched, firstOk: worstIn <= bestOut,
      newToday: TYPES.reduce((a, ty) => a + p.limit[ty], 0), refit, lightRev: appData.planDay.rev, lightNew: TYPES.reduce((a, ty) => a + light.limit[ty], 0) };
  });
  eq(r.revN, r.cap, 'reviews fitted to the budget'); eq(r.shown, r.cap, 'today shows only the fitted reviews'); yes(r.allDue > r.cap, 'backlog stays due');
  eq(r.firstOk, true, 'most-forgotten first'); eq(r.untouched, true, 'waiting cards changed'); eq(r.newToday, 0, 'new cards while the backlog fills the day');
  yes(r.refit < r.cap, `old plan refitted minus minutes studied: ${r.refit} vs ${r.cap}`); eq(r.lightRev, null, 'light day: nothing waits'); yes(r.lightNew > 0, 'light day: new cards');
});

await test('a full study session runs: every screen opens and 80 cards of all kinds answer without an error', async () => {
  const p = await page();
  await p.waitForFunction(() => SYNC.pulled && LOOK.length && Object.keys(EXAMPLES).length);
  const r = await p.evaluate(() => {
    for (const v of ['today', 'deck', 'stats', 'more', 'today']) { view = v; render(); }
    document.getElementById('go-all').click();
    const kinds = new Set();
    for (let i = 0; i < 80; i++) {
      const it = session && session.queue[session.i];
      if (!it) break;
      kinds.add(it.type + ':' + (it.task || it.mode));
      let el = null;
      for (const q of ['#a-reveal', '#a-hook', '#a-continue', '.ans.good', '.ans.next', '#r-more', '.ans', 'button']) { el = document.querySelector('#answer-bar ' + q); if (el) break; }
      if (!el || el.disabled) el = document.querySelector('#sheet .opts button:not([disabled])') || el;
      if (!el) return { stuck: [...kinds] };
      el.click();
    }
    return { kinds: [...kinds] };
  });
  eq(p.errors.length, 0, 'errors: ' + p.errors); eq(r.stuck, undefined, 'session stuck after ' + r.stuck); yes(r.kinds.length >= 5, 'kinds: ' + r.kinds);
});

await test('a reading quiz never offers another real reading of the word as wrong (空: そら and から)', async () => {
  const p = await page({ cloud: false });
  const r = await p.evaluate(() => {
    const bad = [];
    for (let k = 0; k < 3; k++) for (const v of VOCAB) {   // traps are random: three rounds
      const t = readingTraps(v.r, v.w);
      for (const x of t || []) if ((v.ar || []).includes(x)) bad.push(v.w + ':' + x);
    }
    return { bad: [...new Set(bad)].slice(0, 10), sora: BY_WORD['空'].ar };
  });
  eq(r.bad.length, 0, 'real readings offered as wrong: ' + r.bad); yes((r.sora || []).includes('そら'), '空 lists そら');
});

await test('a removed duplicate word (いくら next to 幾ら) moves its progress to the word that stays, from load and from the account', async () => {
  const local = { version: 3, cards: { 'v:お皿': { stability: 10, difficulty: 3, reps: 1, lapses: 0, lastReview: daysAgo(1), due: daysAgo(-3), triaged: true },
      'v:いくら': { stability: 10, difficulty: 3, reps: 1, lapses: 0, lastReview: daysAgo(1), due: daysAgo(-5), triaged: true },
      'v:幾ら': { stability: 6, difficulty: 5, reps: 2, lapses: 0, lastReview: daysAgo(2), due: daysAgo(-4) } },
    stats: {}, settings: {}, history: {}, newByDay: {}, triaged: { 'v:お皿': 'known' } };
  const p = await page({ cloud: false }, local);
  const r = await p.evaluate(() => {
    const a = { plate: !!appData.cards['v:皿'], plateOld: !!appData.cards['v:お皿'], ikura: appData.cards['v:幾ら'].reps, kana: !!appData.cards['v:いくら'], tri: appData.triaged['v:皿'] };
    mergeRemote({ cards: { 'v:お弁当': { stability: 10, difficulty: 3, reps: 1, lastReview: today(), due: today(), triaged: true } }, meta: null }); moveKeys(appData);
    return Object.assign(a, { bento: !!appData.cards['v:弁当'], bentoOld: !!appData.cards['v:お弁当'], gone: ['いただく', 'いくら', 'お皿', 'お菓子', 'お弁当'].filter(w => BY_WORD[w]) });
  });
  eq(r.plate, true, 'お皿 progress on 皿'); eq(r.plateOld, false, 'old key left'); eq(r.ikura, 2, '幾ら keeps its own card'); eq(r.kana, false, 'いくら key left');
  eq(r.tri, 'known', 'sort answer moved'); eq(r.bento, true, 'pulled お弁当 moved to 弁当'); eq(r.bentoOld, false, 'pulled old key left'); eq(r.gone.length, 0, 'duplicates still in the deck: ' + r.gone);
});

await test('every kun reading in a story (green word) is in that kanji\'s word list', async () => {
  const miss = kanji.cards.filter(c => /\^/.test(c.story || '')).filter(c => {
    const r = ((c.story.match(/\(([\u3041-\u3096]+)\)/g) || []).pop() || '').slice(1, -1);
    return !(c.vocab || []).some(v => v.r.startsWith(r));   // the story may give the stem (なな for 七つ)
  }).map(c => c.kanji);
  eq(miss.join(''), '', 'kanji whose kun word is not listed');
});

await test('a kanji\'s kun word card shares that kanji\'s sound-alike sentence and picture', async () => {
  const byK = Object.fromEntries(kanji.cards.map(c => [c.kanji, c]));
  const bad = vocab.filter(v => v.ki).filter(v => !byK[v.ki] || !(v.mn || '').includes('^') || !byK[v.ki].story.includes(v.mn.match(/\^[^^]+\^/)[0])).map(v => v.w);
  eq(bad.join(' '), '', 'words whose shared hook is broken');
  eq(vocab.filter(v => v.ki).length > 400, true, 'kun words sharing their kanji\'s hook');
  const p = await page({ cloud: false }, null);
  const r = await p.evaluate(() => { const h = vocabBackHtml(BY_WORD['連れる'], 'learn'); return { img: /data-kanji="連"/.test(h), green: /class="kun">Two Rails</.test(h) }; });
  eq(r.img, true, '連れる shows 連\'s picture'); eq(r.green, true, 'Two Rails in green on the word card');
});

await test('reading passages with indented paragraphs keep tap meanings and underlines', async () => {
  const p = await page({ cloud: false }, null);
  const r = await p.evaluate(() => {
    const x = EXAM.read.find(x => x.id === 'rd086'), h = passageHtml(x.text, x.under);
    const lines = x.text.split('\n').filter(l => l.trim()), tappable = lines.filter(l => /class="gl/.test(passageHtml(l, x.under))).length;
    return { tappable, lines: lines.length, ul: (h.match(/\bul\b/g) || []).length };
  });
  eq(r.tappable, r.lines, 'every paragraph has tappable words');
  eq(r.ul > 0, true, 'underlined phrases still underlined');
});

await browser.close(); server.kill();
console.log(failed ? `\n${failed} failed` : '\nall passed');
process.exit(failed ? 1 : 0);
