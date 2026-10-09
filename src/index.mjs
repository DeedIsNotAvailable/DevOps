import { scrapeQuotes } from './scrape.mjs';

try {
  const quotes = await scrapeQuotes();
  console.log(`Saved ${quotes.length} quotes to out/result.json`);
} catch (error) {
  console.error(`Scraping failed: ${error.message}`);
  process.exitCode = 1;
}
