import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdtemp, readFile, rm, access } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { scrapeQuotes } from '../src/scrape.mjs';

const batches = [
  [{ text: 'Первая цитата', author: 'Автор 1', tags: ['тест'] }],
  [{ text: 'Second quote', author: 'Author 2', tags: [] }],
  [{ text: 'Third quote', author: 'Author 3', tags: ['last'] }],
];
const html = `<!doctype html><meta charset="utf-8">
<style>.quote { height: 1000px; }</style>
<div class="quotes"></div><div id="loading">Loading...</div>
<script>
let page = 1, busy = false, hasNext = true;
async function load() {
  busy = true;
  document.querySelector('#loading').style.display = 'block';
  const data = await (await fetch('/api/quotes?page=' + page++)).json();
  for (const q of data.quotes) {
    const el = document.createElement('div');
    el.className = 'quote';
    el.innerHTML = '<span class="text"></span><small class="author"></small><div class="tags"></div>';
    el.querySelector('.text').textContent = q.text;
    el.querySelector('.author').textContent = q.author;
    for (const t of q.tags) {
      const tag = document.createElement('a'); tag.className = 'tag';
      tag.textContent = t; el.querySelector('.tags').append(tag);
    }
    document.querySelector('.quotes').append(el);
  }
  hasNext = data.has_next;
  document.querySelector('#loading').style.display = 'none';
  busy = false;
}
addEventListener('scroll', () => {
  if (!busy && hasNext && Math.abs(scrollY + innerHeight - document.documentElement.scrollHeight) <= 1) load();
});
load();
</script>`;

async function fixture(t, { failPage = false, failApi = false } = {}) {
  const directory = await mkdtemp(join(tmpdir(), 'quotes-test-'));
  const pages = [];
  const server = createServer((request, response) => {
    const url = new URL(request.url, 'http://localhost');
    if (url.pathname === '/api/quotes') {
      const number = Number(url.searchParams.get('page'));
      pages.push(number);
      if (failApi) { response.writeHead(500).end('Failure'); return; }
      // A delay forces the scraper to wait for JavaScript and AJAX.
      setTimeout(() => {
        response.setHeader('Content-Type', 'application/json');
        response.end(JSON.stringify({ quotes: batches[number - 1], has_next: number < batches.length }));
      }, 150);
    } else {
      response.writeHead(failPage ? 500 : 200, { 'Content-Type': 'text/html; charset=utf-8' });
      response.end(failPage ? 'Failure' : html);
    }
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(async () => {
    await new Promise((resolve) => server.close(resolve));
    await rm(directory, { recursive: true, force: true });
  });
  return { url: `http://127.0.0.1:${server.address().port}/scroll`,
    outputPath: join(directory, 'out', 'result.json'), timeout: 5_000, pages };
}

test('collects every JS-loaded page and writes UTF-8 JSON', async (t) => {
  const options = await fixture(t);
  const result = await scrapeQuotes(options);
  assert.deepEqual(result, batches.flat());
  assert.deepEqual(JSON.parse(await readFile(options.outputPath, 'utf8')), batches.flat());
  assert.deepEqual(options.pages, [1, 2, 3]);
});

test('HTTP page failure does not produce a result', async (t) => {
  const options = await fixture(t, { failPage: true });
  await assert.rejects(scrapeQuotes(options), /Page returned HTTP 500/);
  await assert.rejects(access(options.outputPath));
});

test('HTTP API failure does not silently save partial quotes', async (t) => {
  const options = await fixture(t, { failApi: true });
  await assert.rejects(scrapeQuotes(options), /Quotes API returned HTTP 500/);
  await assert.rejects(access(options.outputPath));
});
