from prompting_cases import CASES, keyword_hits

def test_keyword_hits_case_insensitive_substrings():
    desc = "Two characters face each other and throw PUNCHES with raised arms."
    hits = keyword_hits(desc, ["two", "punch", "arms", "salsa"])
    assert set(hits) == {"two", "punch", "arms"}

def test_cases_well_formed_and_complete():
    names = set()
    for c in CASES:
        assert {"name", "prompt", "chars", "keywords", "min_hits"} <= set(c)
        assert c["chars"], "each case names its characters"
        assert 1 <= c["min_hits"] <= len(c["keywords"])
        assert c["name"] not in names
        names.add(c["name"])
    assert {"boxing", "running", "walking", "burpees", "salsa"} <= names
