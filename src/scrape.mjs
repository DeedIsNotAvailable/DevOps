import { chromium } from 'playwright';
import { mkdir, writeFile, rename } from 'node:fs/promises';
import { dirname } from 'node:path';

export const TARGET_URL = 'https://quotes.toscrape.com/scroll';

export async function scrapeQuotes({
  url = TARGET_URL,
  outputPath = 'out/result.json',
  timeout = 30_000,
} = {}) {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(timeout);
    const isQuotesResponse = (response) =>
      new URL(response.url()).pathname === '/api/quotes';
    const waitForQuotesResponse = () => {
      const pending = page.waitForResponse(isQuotesResponse);
      pending.catch(() => {}); // Browser close can reject while navigation fails.
      return pending;
    };
    let nextResponse = waitForQuotesResponse();
    const response = await page.goto(url, { waitUntil: 'domcontentloaded' });
    if (!response?.ok()) {
      throw new Error(`Page returned HTTP ${response?.status() ?? 'unknown'}`);
    }

    let expectedCount = 0;
    // Observe the requests made by the page; has_next is its actual end signal.
    // A timeout or failed AJAX request must fail instead of saving partial data.
    for (let batch = 0; batch < 100; batch += 1) {
      const apiResponse = await nextResponse;
      if (!apiResponse.ok()) {
        throw new Error(`Quotes API returned HTTP ${apiResponse.status()}`);
      }
      const payload = await apiResponse.json();
      if (!Array.isArray(payload.quotes) || typeof payload.has_next !== 'boolean') {
        throw new Error('Unexpected pagination response');
      }
      expectedCount += payload.quotes.length;
      await page.waitForFunction((count) =>
        document.querySelectorAll('.quote').length === count,
      expectedCount, { timeout });
      await page.locator('#loading').waitFor({ state: 'hidden' });
      if (!payload.has_next) {
        const quotes = await page.locator('.quote').evaluateAll((elements) =>
          elements.map((element) => ({
            text: element.querySelector('.text')?.textContent?.trim(),
            author: element.querySelector('.author')?.textContent?.trim(),
            tags: [...element.querySelectorAll('.tags .tag')]
              .map((tag) => tag.textContent.trim()),
          })),
        );
        if (!quotes.length || quotes.some((quote) => !quote.text || !quote.author)) {
          throw new Error('The page contains empty or incomplete quotes');
        }
        await mkdir(dirname(outputPath), { recursive: true });
        await writeFile(`${outputPath}.tmp`, `${JSON.stringify(quotes, null, 2)}\n`, 'utf8');
        await rename(`${outputPath}.tmp`, outputPath);
        return quotes;
      }
      nextResponse = waitForQuotesResponse();
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    }
    throw new Error('Pagination exceeded 100 batches; result was not saved');
  } finally {
    await browser.close();
  }
}
