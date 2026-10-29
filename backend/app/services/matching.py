"""
Baseline case relationship matching service for NYAYA SETU.

Algorithm version: v1.0-baseline

Detects potential relationships between cases using:
- Institution co-occurrence
- Category matching
- Normalized text similarity (word-overlap ratio on title)

Scoring thresholds:
  score > 0.8  → POSSIBLE_DUPLICATE
  0.5 ≤ score ≤ 0.8 → RELATED_COMPLAINT
  same institution only → SAME_INSTITUTION_UNRELATED (score=0)

This service is fully offline and makes no external calls.
"""
import re
import logging
from typing import List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ALGORITHM_VERSION = "v1.0-baseline"


def _normalize(text: str) -> List[str]:
    """Lowercase, remove punctuation, return word list."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return [w for w in text.split() if len(w) > 2]


def _word_overlap_ratio(a: str, b: str) -> float:
    """Jaccard-like word overlap ratio between two strings."""
    words_a = set(_normalize(a))
    words_b = set(_normalize(b))
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def detect_relationships(case, db: Session) -> List[dict]:
    """Detect case relationships for the given case against existing cases.

    Args:
        case: The Case ORM object (the new/updated case).
        db: SQLAlchemy Session.

    Returns:
        List of dicts with keys:
            case_b_id, relationship_type, score, reasons, matching_evidence
    """
    from app.models.case import Case
    from app.models.relationship import CaseRelationship, RelationshipType, ReviewStatus

    results: List[dict] = []

    # Missing institution identity cannot produce a trustworthy candidate.
    if not case.institution_id:
        return results

    try:
        # Fetch sibling cases at same institution (exclude self)
        siblings = (
            db.query(Case)
            .filter(
                Case.institution_id == case.institution_id,
                Case.id != case.id,
                Case.is_active == True,
            )
            .all()
        )

        for sibling in siblings:
            # --- Check idempotency ---
            existing = (
                db.query(CaseRelationship)
                .filter(
                    (
                        (CaseRelationship.case_a_id == case.id) &
                        (CaseRelationship.case_b_id == sibling.id)
                    ) | (
                        (CaseRelationship.case_a_id == sibling.id) &
                        (CaseRelationship.case_b_id == case.id)
                    )
                )
                .first()
            )
            if existing:
                continue

            score = 0.0
            reasons: List[str] = []
            evidence = {}

            # --- Category match ---
            same_category = (
                case.category and sibling.category and
                case.category.strip().lower() == sibling.category.strip().lower()
            )
            if same_category:
                score += 0.3
                reasons.append("Same complaint category")
                evidence["category_match"] = case.category

            # --- Title similarity ---
            title_score = 0.0
            if case.title and sibling.title:
                title_score = _word_overlap_ratio(case.title, sibling.title)
                evidence["title_overlap_ratio"] = round(title_score, 4)
                if title_score > 0:
                    score += title_score * 0.7
                    reasons.append(f"Title overlap ratio: {title_score:.2f}")

            # --- Determine relationship type ---
            if score > 0.8:
                rel_type = RelationshipType.POSSIBLE_DUPLICATE
            elif score >= 0.5:
                rel_type = RelationshipType.RELATED_COMPLAINT
            else:
                # Same institution but low similarity
                rel_type = RelationshipType.SAME_INSTITUTION_UNRELATED
                reasons = ["Same institution, different complaints"]
                evidence["institution_id"] = case.institution_id

            result = {
                "case_b_id": sibling.id,
                "relationship_type": rel_type,
                "score": round(min(score, 1.0), 4),
                "reasons": reasons,
                "matching_evidence": evidence,
            }
            results.append(result)

            # --- Persist the relationship ---
            rel = CaseRelationship(
                case_a_id=case.id,
                case_b_id=sibling.id,
                relationship_type=rel_type,
                score=round(min(score, 1.0), 4),
                reasons=reasons,
                matching_evidence=evidence,
                algorithm_version=ALGORITHM_VERSION,
                review_status=ReviewStatus.PENDING,
            )
            db.add(rel)

        db.commit()

    except Exception as exc:
        logger.error("Relationship detection failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass

    return results


def detect_cross_bureau_relationships(db: Session) -> dict:
    """Detect cross-bureau relationships for all active institutions.

    Finds institutions with active cases in more than one bureau and
    creates SAME_INSTITUTION_UNRELATED or ACTION_CONFLICT relationships
    if they don't already exist.

    Uses rapidfuzz for institution name fuzzy matching (optional fallback
    to word-overlap if rapidfuzz unavailable).

    Returns: dict with keys: new_relationships_created, institutions_checked,
             skipped_existing, errors
    """
    from app.models.case import Case
    from app.models.relationship import CaseRelationship, RelationshipType, ReviewStatus
    from sqlalchemy import text

    # Try to import rapidfuzz; fall back to word-overlap if unavailable
    try:
        from rapidfuzz import fuzz as _fuzz
        def _title_similarity(a: str, b: str) -> float:
            return _fuzz.token_set_ratio(a, b) / 100.0
    except ImportError:
        logger.warning("rapidfuzz not available; falling back to word-overlap ratio")
        def _title_similarity(a: str, b: str) -> float:  # type: ignore[misc]
            return _word_overlap_ratio(a, b)

    ALGORITHM_VERSION_CB = "v1.1-cross-bureau"

    new_relationships_created = 0
    institutions_checked = 0
    skipped_existing = 0
    errors = 0

    # The current matcher intentionally uses a pairwise, explainable scan so
    # that differently imported institution records can still be compared by
    # identifier and canonical-name similarity.  The legacy grouped query is
    # retained below for reference, but this path is the authoritative one.
    return _detect_cross_bureau_fuzzy(db)

    try:
        # Find institutions with active cases in more than one bureau
        rows = db.execute(
            text(
                "SELECT institution_id, COUNT(DISTINCT bureau_id) AS bureau_count "
                "FROM cases "
                "WHERE is_active = true AND bureau_id IS NOT NULL "
                "GROUP BY institution_id "
                "HAVING COUNT(DISTINCT bureau_id) > 1"
            )
        ).fetchall()
    except Exception as exc:
        logger.error("Cross-bureau query failed: %s", exc)
        return {
            "new_relationships_created": 0,
            "institutions_checked": 0,
            "skipped_existing": 0,
            "errors": 1,
        }

    for row in rows:
        institution_id = row[0]
        institutions_checked += 1

        try:
            # Fetch all active cases for this institution that belong to some bureau
            inst_cases = (
                db.query(Case)
                .filter(
                    Case.institution_id == institution_id,
                    Case.is_active == True,
                    Case.bureau_id.isnot(None),
                )
                .all()
            )

            # Build pairs from different bureaus
            for i, case_a in enumerate(inst_cases):
                for case_b in inst_cases[i + 1:]:
                    if case_a.bureau_id == case_b.bureau_id:
                        continue  # same bureau — skip

                    # Idempotency check
                    existing = (
                        db.query(CaseRelationship)
                        .filter(
                            (
                                (CaseRelationship.case_a_id == case_a.id) &
                                (CaseRelationship.case_b_id == case_b.id)
                            ) | (
                                (CaseRelationship.case_a_id == case_b.id) &
                                (CaseRelationship.case_b_id == case_a.id)
                            )
                        )
                        .first()
                    )
                    if existing:
                        skipped_existing += 1
                        continue

                    score = 0.0
                    reasons: List[str] = []
                    evidence: dict = {"cross_bureau": True, "institution_id": institution_id}

                    # Category match
                    same_category = (
                        case_a.category and case_b.category and
                        case_a.category.strip().lower() == case_b.category.strip().lower()
                    )
                    if same_category:
                        score += 0.3
                        reasons.append("Same complaint category")
                        evidence["category_match"] = case_a.category

                    # Title similarity
                    title_overlap_ratio = 0.0
                    if case_a.title and case_b.title:
                        title_overlap_ratio = _title_similarity(case_a.title, case_b.title)
                        evidence["title_overlap_ratio"] = round(title_overlap_ratio, 4)
                        if title_overlap_ratio > 0:
                            score += title_overlap_ratio * 0.7
                            reasons.append(f"Title overlap ratio: {title_overlap_ratio:.2f}")

                    # Determine relationship type based on title overlap
                    if title_overlap_ratio > 0.8:
                        rel_type = RelationshipType.POSSIBLE_DUPLICATE
                    elif title_overlap_ratio > 0.5:
                        rel_type = RelationshipType.RELATED_COMPLAINT
                    else:
                        rel_type = RelationshipType.SAME_INSTITUTION_UNRELATED
                        if not reasons:
                            reasons = ["Same institution, different bureaus, low title similarity"]

                    rel = CaseRelationship(
                        case_a_id=case_a.id,
                        case_b_id=case_b.id,
                        relationship_type=rel_type,
                        score=round(min(score, 1.0), 4),
                        reasons=reasons,
                        matching_evidence=evidence,
                        algorithm_version=ALGORITHM_VERSION_CB,
                        review_status=ReviewStatus.PENDING,
                    )
                    db.add(rel)
                    new_relationships_created += 1

            # Commit per institution to keep batches small
            db.commit()

        except Exception as exc:
            logger.error(
                "Cross-bureau detection failed for institution_id=%s: %s",
                institution_id, exc
            )
            try:
                db.rollback()
            except Exception:
                pass
            errors += 1

    return {
        "new_relationships_created": new_relationships_created,
        "institutions_checked": institutions_checked,
        "skipped_existing": skipped_existing,
        "errors": errors,
    }


def _detect_cross_bureau_fuzzy(db: Session) -> dict:
    """Run the explainable cross-bureau matcher without changing source cases."""
    from rapidfuzz import fuzz
    from sqlalchemy.orm import joinedload
    from app.models.case import Case
    from app.models.institution import InstitutionIdentifier
    from app.models.relationship import CaseRelationship, RelationshipType, ReviewStatus

    cases = (
        db.query(Case)
        .options(joinedload(Case.institution))
        .filter(Case.is_active == True, Case.bureau_id.isnot(None))
        .all()
    )
    institution_ids = {case.institution_id for case in cases if case.institution_id}
    identifier_rows = db.query(InstitutionIdentifier).filter(
        InstitutionIdentifier.institution_id.in_(institution_ids or {-1})
    ).all()
    identifier_map = {}
    for identifier in identifier_rows:
        key = (
            identifier.id_type.strip().lower(),
            re.sub(r"[^a-z0-9]", "", identifier.id_value.lower()),
        )
        identifier_map.setdefault(identifier.institution_id, set()).add(key)

    created = 0
    skipped = 0
    errors = 0
    for index, case_a in enumerate(cases):
        for case_b in cases[index + 1:]:
            if case_a.bureau_id == case_b.bureau_id:
                continue
            existing = db.query(CaseRelationship).filter(
                ((CaseRelationship.case_a_id == case_a.id) & (CaseRelationship.case_b_id == case_b.id)) |
                ((CaseRelationship.case_a_id == case_b.id) & (CaseRelationship.case_b_id == case_a.id))
            ).first()
            if existing:
                skipped += 1
                continue

            name_a = (case_a.institution.canonical_name if case_a.institution else "").strip()
            name_b = (case_b.institution.canonical_name if case_b.institution else "").strip()
            name_score = fuzz.token_set_ratio(name_a, name_b) if name_a and name_b else 0
            shared_ids = sorted(
                identifier_map.get(case_a.institution_id, set()) &
                identifier_map.get(case_b.institution_id, set())
            )
            same_record = case_a.institution_id == case_b.institution_id
            if not (same_record or shared_ids or name_score >= 85):
                continue

            score = 0.0
            reasons: List[str] = []
            missing: List[str] = []
            evidence = {
                "cross_bureau": True,
                "institution_name_a": name_a or None,
                "institution_name_b": name_b or None,
                "institution_name_similarity": round(name_score / 100, 4),
                "fuzzy_threshold": 0.85,
                "shared_identifiers": [f"{kind}:{value}" for kind, value in shared_ids],
            }
            if same_record:
                score += 0.45
                reasons.append("Same institution record")
            if shared_ids:
                score += 0.45
                reasons.append("Matching institution identifier")
            if name_score >= 85:
                score += 0.35
                reasons.append(f"Institution name similarity: {name_score}/100")
            if not name_a or not name_b:
                missing.append("institution_name")

            same_category = bool(
                case_a.category and case_b.category and
                case_a.category.strip().casefold() == case_b.category.strip().casefold()
            )
            if same_category:
                score += 0.15
                reasons.append("Same complaint category")
                evidence["category_match"] = case_a.category
            else:
                missing.append("category_match")

            title_score = (
                fuzz.token_set_ratio(case_a.title or "", case_b.title or "") / 100
                if case_a.title and case_b.title else 0
            )
            evidence["title_similarity"] = round(title_score, 4)
            if title_score >= 0.5:
                score += title_score * 0.2
                reasons.append(f"Complaint text similarity: {title_score:.2f}")
            else:
                missing.append("title_similarity")
            evidence["missing_identity_fields"] = missing

            final_score = round(min(score, 1.0), 4)
            if final_score >= 0.8:
                relationship_type = RelationshipType.POSSIBLE_DUPLICATE
            elif final_score >= 0.5:
                relationship_type = RelationshipType.RELATED_COMPLAINT
            else:
                relationship_type = RelationshipType.SAME_INSTITUTION_UNRELATED
            if not reasons:
                reasons.append("Potential cross-bureau identity match requires review")

            db.add(CaseRelationship(
                case_a_id=case_a.id,
                case_b_id=case_b.id,
                relationship_type=relationship_type,
                score=final_score,
                reasons=reasons,
                matching_evidence=evidence,
                algorithm_version="v1.2-cross-bureau-explainable",
                review_status=ReviewStatus.PENDING,
            ))
            created += 1

    try:
        db.commit()
    except Exception as exc:
        logger.error("Cross-bureau fuzzy detection failed: %s", exc)
        db.rollback()
        errors = 1
    return {
        "new_relationships_created": created,
        "institutions_checked": len(institution_ids),
        "skipped_existing": skipped,
        "errors": errors,
    }
