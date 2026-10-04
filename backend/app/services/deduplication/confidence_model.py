import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.services.deduplication.url_normalizer import normalize_url
from app.services.deduplication.normalizers import (
    normalize_company,
    normalize_title,
    normalize_location,
    extract_requisition_id,
)
from app.services.deduplication.text_similarity import (
    text_jaccard_similarity,
    char_ngram_similarity,
    cosine_token_similarity,
)
from app.services.deduplication.contradiction_checker import check_contradictions


class DuplicateEvaluationResult(BaseModel):
    confidence: str = Field(..., description="VERY_HIGH, HIGH, MEDIUM, LOW, or NO_MATCH")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    match_method: str = Field(..., description="Method that produced the match")
    should_merge: bool = Field(..., description="True if automatic merge is warranted (VERY_HIGH or HIGH without contradictions)")
    status: str = Field(..., description="auto_merged, possible_duplicate, or separate")
    matched_signals: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    similarity_metrics: Dict[str, float] = Field(default_factory=dict)
    evidence: Dict[str, Any] = Field(default_factory=dict)


def evaluate_job_pair(
    job_a_dict: Dict[str, Any],
    job_b_dict: Dict[str, Any],
) -> DuplicateEvaluationResult:
    """
    Evaluates multi-signal duplicate confidence between two jobs.
    Implements a strict, conservative hierarchy:
    1. Exact canonical URL identity
    2. Company + Requisition / Reference ID identity
    3. Normalized Company + Normalized Title + Normalized Location + Description
    4. Contradiction evaluation (blocks automatic merge if any contradiction exists)
    """
    matched_signals: List[str] = []
    evidence: Dict[str, Any] = {}
    metrics: Dict[str, float] = {}

    # Check for contradictions first
    contradictions = check_contradictions(job_a_dict, job_b_dict)

    # 1. Level 2: Canonical Application URL Match
    url_a = normalize_url(job_a_dict.get("application_url"))
    url_b = normalize_url(job_b_dict.get("application_url"))

    if url_a and url_b and url_a == url_b:
        matched_signals.append("exact_canonical_url")
        evidence["canonical_url"] = url_a
        # If URLs match exactly and no contradictory country, this is VERY_HIGH
        if not contradictions:
            return DuplicateEvaluationResult(
                confidence="VERY_HIGH",
                confidence_score=1.0,
                match_method="exact_canonical_url",
                should_merge=True,
                status="auto_merged",
                matched_signals=matched_signals,
                contradictions=contradictions,
                similarity_metrics={"url_exact": 1.0},
                evidence=evidence,
            )

    # 2. Company Normalization
    comp_a = normalize_company(job_a_dict.get("company"))
    comp_b = normalize_company(job_b_dict.get("company"))
    company_match = bool(comp_a and comp_b and comp_a == comp_b)

    if not company_match and comp_a and comp_b:
        # Check high char ngram for company (e.g. slight typo)
        comp_sim = char_ngram_similarity(comp_a, comp_b, n=3)
        metrics["company_similarity"] = comp_sim
        if comp_sim >= 0.85:
            company_match = True
            matched_signals.append("high_company_similarity")
    elif company_match:
        matched_signals.append("exact_normalized_company")
        metrics["company_similarity"] = 1.0

    evidence["normalized_company_a"] = comp_a
    evidence["normalized_company_b"] = comp_b

    # 3. Level 3: Company + Requisition ID Match
    req_a = extract_requisition_id(
        raw_payload=job_a_dict.get("raw_payload"),
        external_id=job_a_dict.get("external_job_id"),
        url=job_a_dict.get("application_url"),
        text=job_a_dict.get("description"),
    )
    req_b = extract_requisition_id(
        raw_payload=job_b_dict.get("raw_payload"),
        external_id=job_b_dict.get("external_job_id"),
        url=job_b_dict.get("application_url"),
        text=job_b_dict.get("description"),
    )

    if company_match and req_a and req_b and req_a.upper() == req_b.upper():
        matched_signals.append("company_and_requisition_id")
        evidence["requisition_id"] = req_a
        if not contradictions:
            return DuplicateEvaluationResult(
                confidence="VERY_HIGH",
                confidence_score=0.96,
                match_method="company_and_requisition_id",
                should_merge=True,
                status="auto_merged",
                matched_signals=matched_signals,
                contradictions=contradictions,
                similarity_metrics={"requisition_exact": 1.0},
                evidence=evidence,
            )

    # If company does not match at all, they cannot be duplicate vacancies
    if not company_match:
        return DuplicateEvaluationResult(
            confidence="NO_MATCH",
            confidence_score=0.0,
            match_method="different_companies",
            should_merge=False,
            status="separate",
            matched_signals=matched_signals,
            contradictions=contradictions,
            similarity_metrics=metrics,
            evidence=evidence,
        )

    # 4. Title Normalization & Similarity (Preserving Seniority)
    title_a_norm, sen_a = normalize_title(job_a_dict.get("title"))
    title_b_norm, sen_b = normalize_title(job_b_dict.get("title"))

    title_exact = bool(title_a_norm and title_b_norm and title_a_norm == title_b_norm)
    title_cosine = cosine_token_similarity(title_a_norm, title_b_norm)
    metrics["title_cosine_similarity"] = title_cosine

    evidence["title_a"] = title_a_norm
    evidence["title_b"] = title_b_norm
    evidence["seniority_a"] = sen_a
    evidence["seniority_b"] = sen_b

    if title_exact:
        matched_signals.append("exact_normalized_title_with_seniority")
    elif title_cosine >= 0.75:
        matched_signals.append("high_title_similarity")

    # 5. Location Comparison
    loc_a = normalize_location(job_a_dict.get("location"))
    loc_b = normalize_location(job_b_dict.get("location"))
    evidence["location_a"] = loc_a["raw"]
    evidence["location_b"] = loc_b["raw"]

    location_consistent = False
    if loc_a["country"] and loc_b["country"] and loc_a["country"] == loc_b["country"]:
        matched_signals.append("matching_country")
        location_consistent = True
    elif loc_a["scope"] == "worldwide" or loc_b["scope"] == "worldwide":
        matched_signals.append("worldwide_remote_scope")
        location_consistent = True
    elif not loc_a["raw"] or not loc_b["raw"]:
        # One or both locations are unstated (not explicitly conflicting)
        location_consistent = True
    elif loc_a["normalized"] == loc_b["normalized"]:
        matched_signals.append("exact_normalized_location")
        location_consistent = True

    # 6. Description Similarity (Supporting Evidence)
    desc_a = job_a_dict.get("description") or ""
    desc_b = job_b_dict.get("description") or ""
    desc_jaccard = text_jaccard_similarity(desc_a, desc_b)
    metrics["description_jaccard_similarity"] = desc_jaccard

    if desc_jaccard >= 0.50:
        matched_signals.append("high_description_similarity")
    elif desc_jaccard >= 0.30:
        matched_signals.append("moderate_description_similarity")

    # Decision Matrix
    # Case A: Any contradiction present -> Strictly BLOCKS auto-merge
    if contradictions:
        # If title or description has some overlap, mark as separate or low
        return DuplicateEvaluationResult(
            confidence="LOW",
            confidence_score=0.25,
            match_method="blocked_by_contradiction",
            should_merge=False,
            status="separate",
            matched_signals=matched_signals,
            contradictions=contradictions,
            similarity_metrics=metrics,
            evidence=evidence,
        )

    # Case B: Identical title (with same seniority), location consistent, high/moderate description
    if title_exact and location_consistent:
        has_both_desc = bool(desc_a.strip() and desc_b.strip())
        if (has_both_desc and desc_jaccard >= 0.35) or (not has_both_desc):
            # Strong match across company, title, location, description
            return DuplicateEvaluationResult(
                confidence="HIGH",
                confidence_score=0.88,
                match_method="company_title_location_description",
                should_merge=True,
                status="auto_merged",
                matched_signals=matched_signals,
                contradictions=contradictions,
                similarity_metrics=metrics,
                evidence=evidence,
            )
        else:
            # Identical title and company, but description differs noticeably -> Possible duplicate (review)
            return DuplicateEvaluationResult(
                confidence="MEDIUM",
                confidence_score=0.65,
                match_method="company_and_title_only",
                should_merge=False,
                status="possible_duplicate",
                matched_signals=matched_signals,
                contradictions=contradictions,
                similarity_metrics=metrics,
                evidence=evidence,
            )

    # Case C: High title similarity (>=0.75) and moderate description -> Possible duplicate
    if title_cosine >= 0.75 and location_consistent and desc_jaccard >= 0.30:
        return DuplicateEvaluationResult(
            confidence="MEDIUM",
            confidence_score=0.60,
            match_method="similar_title_and_description",
            should_merge=False,
            status="possible_duplicate",
            matched_signals=matched_signals,
            contradictions=contradictions,
            similarity_metrics=metrics,
            evidence=evidence,
        )

    # Case D: Weak similarity
    return DuplicateEvaluationResult(
        confidence="LOW",
        confidence_score=round(max(0.1, title_cosine * 0.4), 2),
        match_method="weak_similarity",
        should_merge=False,
        status="separate",
        matched_signals=matched_signals,
        contradictions=contradictions,
        similarity_metrics=metrics,
        evidence=evidence,
    )
