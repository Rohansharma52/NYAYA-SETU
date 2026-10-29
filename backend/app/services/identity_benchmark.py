"""
Identity-resolution benchmark — reproducible evidence for the judges.

Builds a labelled set of complaint snippets from the demo registry using the
ways real complainants actually refer to institutions (acronyms, abbreviations,
typos, Hindi, only an e-mail, only an address …) plus negative snippets that
mention institutions NOT in the registry. Three methods are scored:

  * exact      — status quo: exact name / ID lookup
  * fuzzy      — plain token-set fuzzy match on raw text (old v1.2 matcher, threshold 0.85)
  * ire        — NYAYA SETU Identity Resolution Engine (this project)

Run:  python -m app.services.identity_benchmark
"""
from __future__ import annotations

import random
import re
from typing import Dict, List, Optional, Sequence

from app.data.registry import INSTITUTIONS
from app.services.identity import (
    ENGINE_VERSION, InstitutionProfile, resolve, token_set_ratio,
)

SEED = 26264  # PS number — keeps the benchmark deterministic

VARIANT_LABELS = {
    "canonical": "Full official name",
    "acronym_city": "Acronym + city",
    "abbreviated": "Abbreviated name (Engg., Inst., Tech.)",
    "typo": "Misspelt name",
    "hindi": "Name written in Hindi",
    "aicte_id": "AICTE Permanent ID only",
    "email": "Only an official e-mail",
    "address": "Address + pincode, no name",
    "colloquial": "Colloquial reference",
}

NEGATIVES = [
    "Complaint against Faridabad Polytechnic Institute regarding attendance",
    "Delhi Engineering College hostel food complaint",
    "Rajpur Tech Academy Dehradun withheld my certificates",
    "Jodhpur Institute of Pharmacy is charging capitation fee",
    "Mysuru Management College did not refund caution money",
    "Pune Valley College of Engineering faculty salary not paid",
    "Kolkata Science Institute ragging incident",
    "Hyderabad Technical University admission fraud",
    "Tirupati Polytechnic exam result delayed",
    "Guwahati Engineering College library closed for months",
    "Solan Management Institute fake placement claims",
    "Chennai institute of technology demanding extra fees",
]

_ABBR = [("Institute", "Inst."), ("Engineering", "Engg."), ("Technology", "Tech."),
         ("College", "Clg."), ("Management", "Mgmt."), ("Science", "Sc."), ("Research", "Res.")]


def build_profiles() -> List[InstitutionProfile]:
    profiles = []
    for i, d in enumerate(INSTITUTIONS, start=1):
        profiles.append(InstitutionProfile(
            id=i, canonical_name=d["canonical_name"], short_name=d["short_name"],
            aliases=list(d.get("aliases", [])) + [d["hindi_name"]],
            city=d["city"], district=d["district"], state=d["state"], region=d["region"],
            pincode=d["pincode"], email=d["email"], website=d["website"], phone=d["phone"],
            identifiers={"aicte_permanent_id": d["aicte_id"], "aishe_code": d["aishe"]},
        ))
    return profiles


def _typo(word: str, rng: random.Random) -> str:
    if len(word) < 5:
        return word
    i = rng.randint(1, len(word) - 3)
    ops = rng.choice(["swap", "drop", "double"])
    if ops == "swap":
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if ops == "drop":
        return word[:i] + word[i + 1:]
    return word[:i] + word[i] + word[i:]


def build_dataset() -> List[Dict]:
    rng = random.Random(SEED)
    rows: List[Dict] = []
    for i, d in enumerate(INSTITUTIONS, start=1):
        name, city = d["canonical_name"], d["city"]
        distinctive = name.split()[0] if name.split()[0] not in ("Sri", "Shri") else name.split()[1]
        abbreviated = name
        for full, short in _ABBR:
            abbreviated = abbreviated.replace(full, short)
        typo_name = name.replace(distinctive, _typo(distinctive, rng)).lower()
        rows += [
            {"truth": i, "variant": "canonical", "text": f"Complaint regarding {name} about non-payment of scholarship"},
            {"truth": i, "variant": "acronym_city", "text": f"Students of {d['short_name']} {city} allege extra fee collection"},
            {"truth": i, "variant": "abbreviated", "text": f"Grievance: {abbreviated} has not issued migration certificate"},
            {"truth": i, "variant": "typo", "text": f"I am student of {typo_name} and labs are not working"},
            {"truth": i, "variant": "hindi", "text": f"{d['hindi_name']} के विरुद्ध शिकायत — फीस वापस नहीं की गई"},
            {"truth": i, "variant": "aicte_id", "text": f"Institution with AICTE Permanent ID {d['aicte_id']} has not refunded fees"},
            {"truth": i, "variant": "email", "text": f"Reply received from {d['email']} rejecting our representation"},
            {"truth": i, "variant": "address", "text": f"The college located at {d['address']} {d['pincode']} is harassing students"},
            {"truth": i, "variant": "colloquial", "text": f"that {distinctive.lower()} college in {city.lower()} is not giving degrees"},
        ]
    rows += [{"truth": None, "variant": "negative", "text": t} for t in NEGATIVES]
    return rows


# ─── Methods ──────────────────────────────────────────────────────────────────

def _exact(text: str, profiles: Sequence[InstitutionProfile]) -> Optional[int]:
    low = text.lower()
    for p in profiles:
        if p.canonical_name.lower() in low:
            return p.id
        if p.identifiers.get("aicte_permanent_id", "#") in text:
            return p.id
    return None


def _plain_fuzzy(text: str, profiles: Sequence[InstitutionProfile]) -> Optional[int]:
    toks = re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
    best, best_id = 0.0, None
    for p in profiles:
        ptoks = re.sub(r"[^a-z0-9\s]", " ", p.canonical_name.lower()).split()
        score = token_set_ratio(toks, ptoks)
        if score > best:
            best, best_id = score, p.id
    return best_id if best >= 0.85 else None


def _ire(text: str, profiles: Sequence[InstitutionProfile]) -> Optional[int]:
    res = resolve(profiles, text=text, top_k=3)
    if not res["candidates"] or res["ambiguous"]:
        return None
    top = res["candidates"][0]
    return top["institution_id"] if top["band"] in ("confirmed", "high", "probable") else None


METHODS = {"exact": _exact, "fuzzy": _plain_fuzzy, "ire": _ire}
METHOD_LABELS = {
    "exact": "Exact name / ID lookup (status quo)",
    "fuzzy": "Plain fuzzy matching",
    "ire": f"NYAYA SETU {ENGINE_VERSION}",
}


def run_benchmark() -> Dict:
    profiles = build_profiles()
    data = build_dataset()
    positives = sum(1 for r in data if r["truth"] is not None)
    results = {}
    for key, fn in METHODS.items():
        tp = fp = 0
        by_variant: Dict[str, List[int]] = {}
        for row in data:
            pred = fn(row["text"], profiles)
            ok = pred is not None and pred == row["truth"]
            if pred is not None:
                if ok:
                    tp += 1
                else:
                    fp += 1
            if row["truth"] is not None:
                by_variant.setdefault(row["variant"], []).append(1 if ok else 0)
            else:
                by_variant.setdefault("negative", []).append(1 if pred is None else 0)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / positives if positives else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        results[key] = {
            "label": METHOD_LABELS[key],
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "true_positives": tp,
            "false_positives": fp,
            "by_variant": {
                v: round(sum(xs) / len(xs), 4) for v, xs in by_variant.items()
            },
        }
    samples = []
    for row in data[:: max(1, len(data) // 12)][:12]:
        samples.append({"variant": row["variant"], "text": row["text"]})
    return {
        "engine": ENGINE_VERSION,
        "dataset": {
            "size": len(data),
            "positives": positives,
            "negatives": len(data) - positives,
            "institutions": len(profiles),
            "seed": SEED,
            "variant_labels": {**VARIANT_LABELS, "negative": "Institution NOT in registry (must not match)"},
        },
        "methods": results,
        "samples": samples,
        "note": "Synthetic labelled set generated from the demo registry; reproducible with the fixed seed. "
                "Real-world accuracy must be re-measured on AICTE historical data.",
    }


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(run_benchmark(), indent=2, ensure_ascii=False))
