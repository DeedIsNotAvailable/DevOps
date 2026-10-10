import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def scrape():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path="/usr/bin/chromium", headless=True
        )
        try:
            page = browser.new_page()
            page.set_default_timeout(30_000)
            with page.expect_response("**/api/quotes?*") as pending:
                response = page.goto("https://quotes.toscrape.com/scroll")
                if not response or not response.ok:
                    raise RuntimeError("Failed to open quotes page")

            count = 0
            for _ in range(100):
                response = pending.value
                if not response.ok:
                    raise RuntimeError(f"Quotes API returned HTTP {response.status}")
                data = response.json()
                count += len(data["quotes"])
                page.wait_for_function(
                    "n => document.querySelectorAll('.quote').length === n", arg=count
                )
                page.locator("#loading").wait_for(state="hidden")
                if not data["has_next"]:
                    break
                with page.expect_response("**/api/quotes?*") as pending:
                    page.evaluate("window.scrollTo(0, 0)")
                    page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            else:
                raise RuntimeError("Pagination limit exceeded")

            quotes = []
            for quote in page.locator(".quote").all():
                quotes.append({
                    "text": quote.locator(".text").inner_text().strip(),
                    "author": quote.locator(".author").inner_text().strip(),
                    "tags": quote.locator(".tags .tag").all_text_contents(),
                })
            if not quotes or any(not q["text"] or not q["author"] for q in quotes):
                raise RuntimeError("Empty or incomplete quotes")
        finally:
            browser.close()

    output = Path("out/result.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(quotes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(f"Saved {len(quotes)} quotes to {output}")


if __name__ == "__main__":
    scrape()
