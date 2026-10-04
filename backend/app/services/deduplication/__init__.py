from app.services.deduplication.url_normalizer import normalize_url, extract_domain, extract_url_job_identifier
from app.services.deduplication.normalizers import (
    normalize_company,
    normalize_title,
    normalize_location,
    extract_requisition_id,
    extract_seniority,
)
from app.services.deduplication.text_similarity import (
    text_jaccard_similarity,
    char_ngram_similarity,
    cosine_token_similarity,
)
from app.services.deduplication.contradiction_checker import check_contradictions
from app.services.deduplication.confidence_model import (
    evaluate_job_pair,
    DuplicateEvaluationResult,
)
from app.services.deduplication.canonical_selector import (
    select_canonical_record,
    score_job_completeness_and_authority,
)
from app.services.deduplication.anti_duplicate_engine import AntiDuplicateEngine

__all__ = [
    "normalize_url",
    "extract_domain",
    "extract_url_job_identifier",
    "normalize_company",
    "normalize_title",
    "normalize_location",
    "extract_requisition_id",
    "extract_seniority",
    "text_jaccard_similarity",
    "char_ngram_similarity",
    "cosine_token_similarity",
    "check_contradictions",
    "evaluate_job_pair",
    "DuplicateEvaluationResult",
    "select_canonical_record",
    "score_job_completeness_and_authority",
    "AntiDuplicateEngine",
]
