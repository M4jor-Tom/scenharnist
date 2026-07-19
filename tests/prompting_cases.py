"""Case data + keyword-match logic for the live prompting eval tests."""

CHARS = ["Augusta", "Baizhi"]

CASES = [
    {"name": "boxing", "prompt": "Augusta and Baizhi are boxing", "chars": CHARS,
     "keywords": ["two", "fighting", "punch", "boxing", "arms", "fists", "facing"],
     "min_hits": 3},
    {"name": "running", "prompt": "Augusta and Baizhi are running next to each other", "chars": CHARS,
     "keywords": ["two", "running", "run", "legs", "forward", "side"],
     "min_hits": 3},
    {"name": "walking", "prompt": "Augusta and Baizhi are walking next to each other", "chars": CHARS,
     "keywords": ["two", "walking", "walk", "legs", "side", "together"],
     "min_hits": 3},
    {"name": "burpees", "prompt": "Augusta and Baizhi are making burpees", "chars": CHARS,
     "keywords": ["two", "squat", "jump", "down", "up", "exercise", "floor"],
     "min_hits": 3},
    {"name": "salsa", "prompt": "Augusta and Baizhi are dancing salsa together", "chars": CHARS,
     "keywords": ["two", "dancing", "dance", "salsa", "partner", "arms"],
     "min_hits": 3},
]

def keyword_hits(description, keywords):
    """Case-insensitive substring hits of `keywords` within `description`."""
    d = (description or "").lower()
    return [k for k in keywords if k.lower() in d]
