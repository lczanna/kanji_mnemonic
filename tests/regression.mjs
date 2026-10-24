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

await browser.close(); server.kill();
console.log(failed ? `\n${failed} failed` : '\nall passed');
process.exit(failed ? 1 : 0);
