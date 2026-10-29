"""Unit tests for the Institution Identity Resolution Engine (pure python, no DB)."""
from app.services.identity import resolve, transliterate_devanagari, tokenize, acronym_of
from app.services.identity_benchmark import build_profiles, run_benchmark

PROFILES = build_profiles()
AIET, ACEM, GIT, MEC, KIT = 1, 2, 3, 17, 10


def _top(text, **kw):
    res = resolve(PROFILES, text=text, **kw)
    return res, (res["candidates"][0]["institution_id"] if res["candidates"] else None)


def test_transliteration_handles_institution_vocabulary():
    assert transliterate_devanagari("अरावली इंस्टीट्यूट ऑफ इंजीनियरिंग") == "aravali institute of engineering"
    assert transliterate_devanagari("मारवाड़") == "marvar" or transliterate_devanagari("मारवाड़").startswith("mar")


def test_tokenize_expands_abbreviations_and_dotted_acronyms():
    assert tokenize("A.I.E.T. Faridabad") == ["aiet", "faridabad"]
    assert tokenize("Aravali Inst. of Engg. & Tech.") == ["aravali", "institute", "of", "engineering", "and", "technology"]
    assert acronym_of("Aravali Institute of Engineering & Technology") == "aiet"


def test_aicte_id_is_decisive():
    res, top = _top("Institution with AICTE ID 1-2847561093 is not refunding fee")
    assert top == AIET
    assert res["candidates"][0]["band"] == "confirmed"


def test_conflicting_identifier_is_negative_evidence():
    res = resolve(PROFILES, text="Aravali Institute of Engineering & Technology, AICTE ID 1-3390218874")
    by_id = {c["institution_id"]: c for c in res["candidates"]}
    assert by_id[AIET]["conflicts"]
    assert res["candidates"][0]["institution_id"] == ACEM


def test_acronym_plus_city():
    _, top = _top("Students of AIET Faridabad allege extra fees")
    assert top == AIET


def test_hindi_complaint_resolves():
    _, top = _top("मारवाड़ इंजीनियरिंग कॉलेज जोधपुर के विरुद्ध शिकायत")
    assert top == MEC


def test_typo_tolerance():
    _, top = _top("Kavery Instt of Tech, Mysore")
    assert top == KIT


def test_unknown_institution_does_not_match():
    res, _ = _top("Delhi Engineering College hostel food complaint")
    assert res["decision"] == "no_match"


def test_benchmark_beats_baselines():
    bench = run_benchmark()
    m = bench["methods"]
    assert m["ire"]["f1"] > m["exact"]["f1"] + 0.3
    assert m["ire"]["precision"] >= 0.95
    assert m["ire"]["recall"] >= 0.9
