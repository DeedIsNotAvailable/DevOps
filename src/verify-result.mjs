import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const quotes = JSON.parse(await readFile('out/result.json', 'utf8'));
assert.ok(Array.isArray(quotes) && quotes.length > 0, 'Expected a nonempty array');
for (const quote of quotes) {
  assert.equal(typeof quote.text, 'string');
  assert.ok(quote.text.trim());
  assert.equal(typeof quote.author, 'string');
  assert.ok(quote.author.trim());
  assert.ok(Array.isArray(quote.tags));
  assert.ok(quote.tags.every((tag) => typeof tag === 'string' && tag.trim()));
}
assert.equal(new Set(quotes.map((q) => `${q.author}\0${q.text}`)).size, quotes.length,
  'Duplicate quotes');
console.log(`Validated ${quotes.length} quotes`);
