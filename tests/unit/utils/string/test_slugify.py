import pytest
from utils.string.slugify import slugify

@pytest.mark.parametrize("input_str, expected", [
    ("Dragon Turtle",       "dragon-turtle"),
    ("  Leading Trailing  ", "leading-trailing"),
    ("Special! @# Chars",   "special-chars"),
    ("Multiple   Spaces",   "multiple-spaces"),
    ("Already-slugified",    "already-slugified"),
    ("Mixed_Case Name",      "mixed_case-name"),
    ("Under_score OK",       "under_score-ok"),
    ("",                     ""),
    ("   ",                  ""),
    ("123 Numbers 456",      "123-numbers-456"),
    ("Tabs\tand\nNewlines",  "tabs-and-newlines"),
    ("Emoji 😊 Removed",     "emoji-removed"),
])
def test_slugify_various(input_str, expected):
    assert slugify(input_str) == expected

def test_slugify_idempotent_on_slugs():
    # once slugified, running again should be no-op
    s = "already-a-slug"
    assert slugify(s) == s
    assert slugify(slugify(s)) == s

def test_slugify_strips_non_word_non_space_non_hyphen():
    # punctuation and symbols dropped
    inp = "Hello, world! (test) #1"
    # comma, exclamation, parentheses, hash removed; spaces → dashes
    assert slugify(inp) == "hello-world-test-1"

def test_slugify_trims_and_lowercases():
    assert slugify("  MIXED Case 123  ") == "mixed-case-123"
