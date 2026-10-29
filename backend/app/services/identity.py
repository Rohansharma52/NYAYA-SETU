"""
Institution Identity Resolution Engine (IRE) — NYAYA SETU
=========================================================

Answers the question at the heart of PS 26264:

    "Which institution is this complaint about — even when the complainant
     writes the name differently, in Hindi, as an acronym, or not at all?"

Design principles
-----------------
* Fully offline and deterministic. No model download, no external API, no
  complaint text ever leaves AICTE infrastructure.
* Explainable: every candidate carries the evidence that produced its score.
* Evidence fusion: independent signals are combined with a noisy-OR, so two
  weak signals (city + acronym) can corroborate each other, while a single
  hard identifier (AICTE Permanent ID) is decisive on its own.
* Conflicting hard identifiers are treated as negative evidence.

Signals
-------
  AICTE Permanent ID  · AISHE code · e-mail / website domain · phone
  pincode · city / district · acronym · fuzzy name (abbreviation expansion,
  Devanagari transliteration, typo-tolerant token matching)

This module has NO database or framework imports, so it can be unit-tested
and benchmarked in isolation (see ``identity_benchmark.py``).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ENGINE_VERSION = "IRE-2.0"

# ─── Vocabulary ───────────────────────────────────────────────────────────────

ABBREVIATIONS: Dict[str, str] = {
    "engg": "engineering", "engr": "engineering", "eng": "engineering", "engineerig": "engineering",
    "inst": "institute", "instt": "institute", "institue": "institute", "insti": "institute",
    "tech": "technology", "techn": "technology", "technol": "technology", "techno": "technology",
    "univ": "university", "uni": "university", "coll": "college", "clg": "college", "colg": "college",
    "mgmt": "management", "mgt": "management", "mngt": "management",
    "sci": "science", "sc": "science", "govt": "government", "gov": "government",
    "natl": "national", "intl": "international", "res": "research", "poly": "polytechnic",
    "pharm": "pharmacy", "edu": "education", "dept": "department", "sr": "sri", "shri": "sri", "shree": "sri",
}

CITY_ALIASES: Dict[str, str] = {
    "gzb": "ghaziabad", "fbd": "faridabad", "bangalore": "bengaluru", "blr": "bengaluru",
    "bombay": "mumbai", "madras": "chennai", "calcutta": "kolkata", "gurgaon": "gurugram",
    "hyd": "hyderabad", "mysore": "mysuru", "calicut": "kozhikode", "allahabad": "prayagraj",
    "ddn": "dehradun", "trichy": "tiruchirappalli", "vizag": "visakhapatnam", "chinsura": "chinsurah",
}

# Generic words that do not identify a specific institution.
GENERIC = {
    "institute", "college", "engineering", "technology", "university", "of", "and", "the",
    "school", "academy", "group", "institutions", "institution", "campus", "pvt", "private",
    "ltd", "limited", "trust", "society", "for", "in", "at", "sciences", "science", "management",
    "studies", "research", "centre", "center", "technical", "education", "polytechnic", "sri",
    "government", "national", "pharmacy", "department", "faculty", "students", "student",
}

STOP_FOR_ACRONYM = {"of", "and", "the", "for", "in", "at", "&"}

# Common Hindi words seen in complaint letters, mapped to their English form.
HINDI_WORDS: Dict[str, str] = {
    "इंस्टीट्यूट": "institute", "इंस्टिट्यूट": "institute", "संस्थान": "institute",
    "कॉलेज": "college", "कालेज": "college", "महाविद्यालय": "college",
    "विश्वविद्यालय": "university", "यूनिवर्सिटी": "university",
    "इंजीनियरिंग": "engineering", "अभियांत्रिकी": "engineering",
    "टेक्नोलॉजी": "technology", "प्रौद्योगिकी": "technology", "तकनीकी": "technical",
    "मैनेजमेंट": "management", "प्रबंधन": "management", "साइंस": "science", "विज्ञान": "science",
    "फार्मेसी": "pharmacy", "रिसर्च": "research", "पॉलिटेक्निक": "polytechnic",
    "ऑफ": "of", "एंड": "and", "एवं": "and", "और": "and", "श्री": "sri", "राजकीय": "government",
    "वैली": "valley",
}

_DEV_VOWELS = {
    "अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ऋ": "ri",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऑ": "o",
}
_DEV_MATRAS = {
    "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "ृ": "ri",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "e",
}
_DEV_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh",
    "ञ": "n", "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d",
    "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r",
    "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h", "ळ": "l",
    "क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f",
    "\u0958": "q", "\u0959": "kh", "\u095A": "g", "\u095B": "z", "\u095C": "r", "\u095D": "rh", "\u095E": "f",
}
_VIRAMA = "्"
_ANUSVARA = {"ं", "ँ"}
_NUKTA = "़"

AICTE_ID_RE = re.compile(r"\b1\s*-\s*\d{6,11}\b")
AISHE_RE = re.compile(r"\b[CUS]\s*-\s*\d{4,6}\b", re.IGNORECASE)
PIN_RE = re.compile(r"(?<!\d)[1-9]\d{5}(?!\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
WEB_RE = re.compile(r"(?:https?://)?(?:www\.)?([a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:ac\.in|edu\.in|org\.in|co\.in|in|org|com|edu))\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:0\d{2,4}[-\s]?\d{6,8}|[6-9]\d{9})(?!\d)")


# ─── Text normalisation ───────────────────────────────────────────────────────

def transliterate_devanagari(text: str) -> str:
    """Rule-based Devanagari → Latin transliteration with schwa deletion.

    Known institutional vocabulary is translated (संस्थान → institute) before
    phonetic transliteration of proper nouns (गंगोत्री → gangotri).
    """
    if not any("ऀ" <= ch <= "ॿ" for ch in text):
        return text
    words = text.split()
    out: List[str] = []
    for word in words:
        bare = word.strip(".,;:()[]{}\"'")
        if bare in HINDI_WORDS:
            out.append(HINDI_WORDS[bare])
            continue
        out.append(_transliterate_word(word))
    return " ".join(out)


def _transliterate_word(word: str) -> str:
    res: List[str] = []
    chars = list(unicodedata.normalize("NFC", word))
    i = 0
    while i < len(chars):
        ch = chars[i]
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if ch in _DEV_CONSONANTS:
            if nxt == _NUKTA:
                res.append(_DEV_CONSONANTS.get(ch + _NUKTA, _DEV_CONSONANTS[ch]))
                i += 1
                nxt = chars[i + 1] if i + 1 < len(chars) else ""
            else:
                res.append(_DEV_CONSONANTS[ch])
            if nxt == _VIRAMA:
                i += 2
                continue
            if nxt in _DEV_MATRAS:
                res.append(_DEV_MATRAS[nxt])
                i += 2
                continue
            res.append("a")  # inherent vowel
        elif ch in _DEV_VOWELS:
            res.append(_DEV_VOWELS[ch])
        elif ch in _DEV_MATRAS:
            res.append(_DEV_MATRAS[ch])
        elif ch in _ANUSVARA:
            res.append("n")
        elif ch == "ः":
            res.append("h")
        elif ch == _NUKTA:
            pass
        elif ch.isascii():
            res.append(ch)
        i += 1
    latin = "".join(res)
    # Schwa deletion at word end ("gangotra" stays, "kaveri" stays, "aravala" -> "araval")
    if len(latin) > 3 and latin.endswith("a") and not latin.endswith("aa") and unicodedata.normalize("NFD", word).rstrip(_NUKTA)[-1:] in _DEV_CONSONANTS:
        latin = latin[:-1]
    latin = re.sub(r"aa+", "a", latin)
    latin = re.sub(r"ii+", "i", latin)
    return latin


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def tokenize(text: str) -> List[str]:
    """Lower-case, transliterate, collapse acronyms with dots, expand abbreviations."""
    if not text:
        return []
    text = transliterate_devanagari(text)
    text = _strip_accents(text).lower()
    # A.I.E.T. -> aiet ; keeps single-letter-dot sequences together
    text = re.sub(r"\b(?:[a-z]\.){2,}[a-z]?\.?", lambda m: m.group(0).replace(".", ""), text)
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = []
    for tok in text.split():
        tok = ABBREVIATIONS.get(tok, tok)
        tok = CITY_ALIASES.get(tok, tok)
        tokens.append(tok)
    return tokens


def normalize_name(name: str) -> str:
    return " ".join(tokenize(name))


def core_tokens(tokens: Iterable[str]) -> List[str]:
    return [t for t in tokens if t not in GENERIC and len(t) > 1 and not t.isdigit()]


def acronym_of(name: str) -> str:
    words = [w for w in re.split(r"[\s\-]+", _strip_accents(name).lower().replace("&", " ")) if w]
    letters = [w[0] for w in words if w not in STOP_FOR_ACRONYM and w[0].isalpha()]
    return "".join(letters)


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def token_set_ratio(a_tokens: Sequence[str], b_tokens: Sequence[str]) -> float:
    """Order-insensitive similarity (same construction as fuzzywuzzy token_set_ratio)."""
    sa, sb = set(a_tokens), set(b_tokens)
    if not sa or not sb:
        return 0.0
    inter = " ".join(sorted(sa & sb))
    diff_a = " ".join(sorted(sa - sb))
    diff_b = " ".join(sorted(sb - sa))
    t1 = f"{inter} {diff_a}".strip()
    t2 = f"{inter} {diff_b}".strip()
    scores = [_ratio(t1, t2)]
    if inter:
        scores += [_ratio(inter, t1), _ratio(inter, t2)]
    return max(scores)


def _osa_distance(a: str, b: str) -> int:
    """Optimal-string-alignment (Damerau-Levenshtein) distance — handles transposed letters."""
    la, lb = len(a), len(b)
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[la][lb]


def token_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    edit = 1.0 - _osa_distance(a, b) / max(len(a), len(b))
    return max(edit, _ratio(a, b))


def _best_token_match(token: str, pool: Sequence[str]) -> float:
    best = 0.0
    for cand in pool:
        if cand == token:
            return 1.0
        if abs(len(cand) - len(token)) > 3:
            continue
        best = max(best, token_similarity(token, cand))
    return best


def _domain(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.lower().strip()
    if "@" in value:
        value = value.split("@", 1)[1]
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"^www\.", "", value)
    return value.split("/")[0] or None


def _digits(value: Optional[str]) -> str:
    return re.sub(r"\D", "", value or "")


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class InstitutionProfile:
    id: int
    canonical_name: str
    short_name: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    pincode: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    identifiers: Dict[str, str] = field(default_factory=dict)

    # Derived features (computed lazily)
    _features: Optional[dict] = field(default=None, repr=False)

    def features(self) -> dict:
        if self._features is None:
            names = [self.canonical_name] + list(self.aliases or [])
            name_tokens = [tokenize(n) for n in names]
            cores = set()
            for toks in name_tokens:
                cores.update(core_tokens(toks))
            acronyms = {acronym_of(self.canonical_name)}
            if self.short_name:
                acronyms.add(re.sub(r"[^a-z0-9]", "", self.short_name.lower()))
            domains = {d for d in (_domain(self.email), _domain(self.website)) if d}
            places = {t for t in tokenize(" ".join(filter(None, [self.city, self.district]))) if t}
            ids = {}
            for k, v in (self.identifiers or {}).items():
                ids[k] = re.sub(r"[^a-z0-9]", "", str(v).lower())
            self._features = {
                "name_tokens": name_tokens,
                "core": sorted(cores),
                "primary_core": core_tokens(name_tokens[0]),
                "acronyms": {a for a in acronyms if len(a) >= 2},
                "domains": domains,
                "places": places,
                "state": (self.state or "").lower(),
                "pincode": (self.pincode or "").strip(),
                "phone": _digits(self.phone)[-8:],
                "ids": ids,
            }
        return self._features


@dataclass
class Evidence:
    signal: str
    detail: str
    strength: float

    def as_dict(self) -> dict:
        return {"signal": self.signal, "detail": self.detail, "strength": round(self.strength, 3)}


@dataclass
class Candidate:
    institution_id: int
    canonical_name: str
    confidence: float
    band: str
    evidence: List[Evidence]
    conflicts: List[str]

    def as_dict(self) -> dict:
        return {
            "institution_id": self.institution_id,
            "canonical_name": self.canonical_name,
            "confidence": round(self.confidence, 4),
            "band": self.band,
            "evidence": [e.as_dict() for e in self.evidence],
            "conflicts": self.conflicts,
        }


@dataclass
class QuerySignals:
    raw: str
    tokens: List[str]
    name_tokens: List[str]
    aicte_ids: List[str]
    aishe_ids: List[str]
    pincodes: List[str]
    domains: List[str]
    phones: List[str]

    def as_dict(self) -> dict:
        return {
            "normalized_text": " ".join(self.tokens)[:400],
            "aicte_ids": self.aicte_ids,
            "aishe_ids": self.aishe_ids,
            "pincodes": self.pincodes,
            "domains": self.domains,
            "phones": self.phones,
            "transliterated": transliterate_devanagari(self.raw) != self.raw,
        }


# ─── Engine ───────────────────────────────────────────────────────────────────

def extract_signals(
    text: str = "",
    name: Optional[str] = None,
    email: Optional[str] = None,
    website: Optional[str] = None,
    pincode: Optional[str] = None,
    phone: Optional[str] = None,
    aicte_id: Optional[str] = None,
) -> QuerySignals:
    blob = " ".join(filter(None, [text, name, email, website, pincode, phone, aicte_id]))
    aicte = {re.sub(r"\s", "", m.group(0)) for m in AICTE_ID_RE.finditer(blob)}
    aishe = {re.sub(r"\s", "", m.group(0)).upper() for m in AISHE_RE.finditer(blob)}
    pins = set(PIN_RE.findall(blob))
    domains = {m.group(1).lower() for m in EMAIL_RE.finditer(blob)}
    domains |= {m.group(1).lower() for m in WEB_RE.finditer(blob)}
    phones = {_digits(m.group(0))[-8:] for m in PHONE_RE.finditer(blob)}
    # A 6-digit pincode inside an AICTE id or phone is not a pincode
    pins = {p for p in pins if not any(p in a for a in aicte) and not any(p in ph for ph in phones)}
    tokens = tokenize(blob)
    return QuerySignals(
        raw=blob,
        tokens=tokens,
        name_tokens=tokenize(name) if name else [],
        aicte_ids=sorted(aicte),
        aishe_ids=sorted(aishe),
        pincodes=sorted(pins),
        domains=sorted(domains),
        phones=sorted(p for p in phones if p),
    )


def _band(conf: float) -> str:
    if conf >= 0.90:
        return "confirmed"
    if conf >= 0.75:
        return "high"
    if conf >= 0.55:
        return "probable"
    return "weak"


def score_profile(q: QuerySignals, profile: InstitutionProfile) -> Candidate:
    f = profile.features()
    evidence: List[Evidence] = []
    conflicts: List[str] = []
    norm_ids = {re.sub(r"[^a-z0-9]", "", x.lower()) for x in q.aicte_ids}
    norm_aishe = {re.sub(r"[^a-z0-9]", "", x.lower()) for x in q.aishe_ids}

    # 1 — hard identifiers
    inst_aicte = f["ids"].get("aicte_permanent_id")
    if inst_aicte and norm_ids:
        if inst_aicte in norm_ids:
            evidence.append(Evidence("aicte_permanent_id", f"AICTE Permanent ID {profile.identifiers.get('aicte_permanent_id')} quoted in complaint", 0.99))
        else:
            conflicts.append("Complaint quotes a different AICTE Permanent ID")
    inst_aishe = f["ids"].get("aishe_code")
    if inst_aishe and norm_aishe:
        if inst_aishe in norm_aishe:
            evidence.append(Evidence("aishe_code", f"AISHE code {profile.identifiers.get('aishe_code')} matched", 0.97))
        else:
            conflicts.append("Complaint quotes a different AISHE code")

    # 2 — contact identifiers
    shared_domains = f["domains"] & set(q.domains)
    if shared_domains:
        evidence.append(Evidence("domain", f"Official domain {sorted(shared_domains)[0]} referenced", 0.88))
    if f["phone"] and f["phone"] in q.phones:
        evidence.append(Evidence("phone", "Institution phone number referenced", 0.8))

    # 3 — location
    if f["pincode"] and f["pincode"] in q.pincodes:
        evidence.append(Evidence("pincode", f"Pincode {f['pincode']} matched", 0.5))
    place_hits = sorted(p for p in f["places"] if _best_token_match(p, q.tokens) >= 0.86)
    if place_hits:
        evidence.append(Evidence("location", f"Location '{place_hits[0].title()}' mentioned", 0.35))

    # 4 — acronym (needs to appear as a standalone token)
    acr_hits = sorted(a for a in f["acronyms"] if a in q.tokens and len(a) >= 3)
    if acr_hits:
        evidence.append(Evidence("acronym", f"Acronym '{acr_hits[0].upper()}' matched", 0.62))

    # 5 — name similarity
    query_pool = q.name_tokens or q.tokens
    pool_core = core_tokens(query_pool)
    name_strength = 0.0
    name_detail = ""
    if f["core"]:
        pool_set = set(query_pool)
        best = (0.0, 0.0, 0.0, 0)  # strength, coverage, soft, n
        for variant in f["name_tokens"]:
            primary = [t for t in core_tokens(variant) if t not in f["places"]] or core_tokens(variant)
            if not primary:
                continue
            matches = [_best_token_match(t, pool_core) for t in primary]
            coverage = sum(
                1 for t, m in zip(primary, matches) if m >= (0.8 if len(t) >= 5 else 0.9)
            ) / len(primary)
            if coverage == 0:
                continue
            soft = sum(matches) / len(primary)
            # Generic words ("college" vs "institute") break ties between
            # institutions that share a distinctive token (e.g. two "Aravali"s).
            full = [t for t in variant if t not in STOP_FOR_ACRONYM and t not in f["places"]]
            structure = sum(1 for t in full if t in pool_set) / len(full) if full else 0.0
            strength = 0.88 * coverage ** 1.5 * (0.65 + 0.35 * structure)
            if strength > best[0]:
                best = (strength, coverage, soft, len(primary))
        if best[0] > 0:
            name_strength = best[0]
            name_detail = f"{int(round(best[1] * best[3]))}/{best[3]} distinctive name tokens found"
            if best[2] < 0.999 and best[1] == 1:
                name_detail += " (typo/transliteration tolerant)"
        if q.name_tokens:
            best_full = max(token_set_ratio(q.name_tokens, toks) for toks in f["name_tokens"])
            full_strength = max(0.0, (best_full - 0.62) / 0.38) * 0.9
            if full_strength > name_strength:
                name_strength = full_strength
                name_detail = f"Name similarity {best_full:.2f} (token-set, abbreviation-aware)"
    if name_strength > 0.05:
        evidence.append(Evidence("name", name_detail, name_strength))

    # 6 — state (weak corroboration only)
    if f["state"] and f["state"] in " ".join(q.tokens) and evidence:
        evidence.append(Evidence("state", f"State '{profile.state}' mentioned", 0.08))

    # Noisy-OR fusion
    remaining = 1.0
    for ev in evidence:
        remaining *= (1.0 - ev.strength)
    confidence = 1.0 - remaining
    if conflicts:
        confidence *= 0.35
    evidence.sort(key=lambda e: e.strength, reverse=True)
    return Candidate(
        institution_id=profile.id,
        canonical_name=profile.canonical_name,
        confidence=confidence,
        band=_band(confidence),
        evidence=evidence,
        conflicts=conflicts,
    )


def resolve(
    profiles: Sequence[InstitutionProfile],
    text: str = "",
    top_k: int = 5,
    min_confidence: float = 0.2,
    **fields,
) -> dict:
    """Rank institutions for a complaint text / structured fields."""
    q = extract_signals(text=text, **fields)
    candidates = [score_profile(q, p) for p in profiles]
    candidates = [c for c in candidates if c.confidence >= min_confidence]
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    top = candidates[:top_k]
    hard = {"aicte_permanent_id", "aishe_code", "domain", "phone"}
    top_has_hard = bool(top) and any(e.signal in hard for e in top[0].evidence)
    ambiguous = (
        len(top) >= 2
        and (top[0].confidence - top[1].confidence) < 0.035
        and not top_has_hard
    )
    decision = "no_match"
    if top:
        if top[0].band in ("confirmed", "high") and not ambiguous:
            decision = "auto_link_suggested"
        elif top[0].band in ("confirmed", "high", "probable"):
            decision = "human_confirmation_required"
    return {
        "engine": ENGINE_VERSION,
        "signals": q.as_dict(),
        "candidates": [c.as_dict() for c in top],
        "ambiguous": ambiguous,
        "decision": decision,
        "note": "Suggestion only — an officer confirms the link. Source records are never altered.",
    }


def profile_from_orm(inst) -> InstitutionProfile:
    """Build a profile from an Institution ORM object (identifiers eager-loaded)."""
    identifiers = {}
    for ident in getattr(inst, "identifiers", []) or []:
        identifiers[ident.id_type] = ident.id_value
    aliases: List[str] = []
    if getattr(inst, "short_name", None):
        aliases.append(inst.short_name)
    for ident in getattr(inst, "identifiers", []) or []:
        if ident.id_type in ("alias", "former_name", "hindi_name"):
            aliases.append(ident.id_value)
    return InstitutionProfile(
        id=inst.id,
        canonical_name=inst.canonical_name,
        short_name=inst.short_name,
        aliases=aliases,
        city=inst.city,
        district=inst.district,
        state=inst.state,
        region=inst.region,
        pincode=inst.pincode,
        email=inst.email,
        website=inst.website,
        phone=inst.phone,
        identifiers=identifiers,
    )


def institution_similarity(a: InstitutionProfile, b: InstitutionProfile) -> Tuple[float, List[str]]:
    """Profile-to-profile similarity used to detect duplicate institution records."""
    fa, fb = a.features(), b.features()
    reasons: List[str] = []
    shared_ids = {k for k in fa["ids"] if k in fb["ids"] and fa["ids"][k] == fb["ids"][k]}
    if shared_ids:
        return 1.0, [f"Shared identifier: {', '.join(sorted(shared_ids))}"]
    name = max(token_set_ratio(x, y) for x in fa["name_tokens"] for y in fb["name_tokens"])
    score = name * 0.7
    reasons.append(f"Name similarity {name:.2f}")
    if fa["domains"] & fb["domains"]:
        score += 0.3
        reasons.append("Shared web/e-mail domain")
    if fa["pincode"] and fa["pincode"] == fb["pincode"]:
        score += 0.1
        reasons.append("Same pincode")
    return min(score, 1.0), reasons
