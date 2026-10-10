import json
from pathlib import Path

quotes = json.loads(Path("out/result.json").read_text(encoding="utf-8"))
assert isinstance(quotes, list) and quotes, "Expected a nonempty array"
for quote in quotes:
    assert isinstance(quote, dict), "Expected quote objects"
    assert isinstance(quote.get("text"), str) and quote["text"].strip(), "Missing text"
    assert isinstance(quote.get("author"), str) and quote["author"].strip(), "Missing author"
    assert isinstance(quote.get("tags"), list), "Missing tags array"
    assert all(isinstance(tag, str) and tag.strip() for tag in quote["tags"]), "Invalid tag"
assert len({(q["text"], q["author"]) for q in quotes}) == len(quotes), "Duplicate quotes"
print(f"Validated {len(quotes)} quotes")
