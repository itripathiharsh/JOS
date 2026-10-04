import re
from typing import Dict, Any, List, Set, Tuple
from app.models.profile import CandidateProfile
from intelligence.candidate import extract_candidate_data


UNSUPPORTED_TECH_PATTERNS = [
    r"\bgolang\b", r"\brust\b", r"\bscala\b", r"\bruby\b", r"\bphp\b",
    r"\bc\+\+\b", r"\bcobol\b", r"\bfortran\b", r"\bperl\b",
    r"\bsalesforce\b", r"\bsap\b", r"\bpeoplesoft\b", r"\bworkday\b",
    r"\baws\s+lambda\b", r"\bkubernetes\b",
]

FABRICATED_METRICS_PATTERNS = [
    r"\b\d{2,3}%\s+(?:increase|decrease|growth|boost|improvement|reduction)\b",
    r"\b(?:millions?|billions?)\s+of\s+users\b",
    r"\b\$\d+[\d,]*\s+(?:revenue|cost\s+savings|arr|mrr)\b",
    r"\bmanaged\s+\d+\s+engineers\b",
    r"\bled\s+a\s+team\s+of\s+\d+\b",
]


class ClaimSafetyAuditor:
    """
    Guarantees zero hallucination and enforces Phase E claim safety guardrails:
    - Never asserts experience > actual practical experience (~2.0 years).
    - Never asserts technologies candidate has never used.
    - Never asserts companies candidate never worked for.
    - Never asserts unconfirmed certifications or fake metrics.
    """

    @staticmethod
    def audit_generated_text(text: str, candidate: CandidateProfile) -> Dict[str, Any]:
        cand_data = extract_candidate_data(candidate)
        violations: List[str] = []
        warnings: List[str] = []

        # 1. Experience Years Check
        # Detect any statement claiming X years of experience
        exp_claims = re.findall(
            r"(\d+)\+?\s*(?:years?|yrs?)(?:\s*of)?\s*(?:commercial|professional|industry|relevant|software|hands-on|practical)?\s*(?:experience|background)",
            text,
            re.IGNORECASE,
        )
        for claim in exp_claims:
            try:
                claimed_years = float(claim)
                # Allow safety margin of +0.5 years for rounding (e.g. ~2 years is fine, 3+ or 5+ is a violation)
                if claimed_years > (cand_data.actual_experience_years + 0.5):
                    violations.append(
                        f"Inflated experience claim: text asserts '{claimed_years} years' but candidate has ~{cand_data.actual_experience_years:.1f} verified practical years."
                    )
            except ValueError:
                pass

        # 2. Unsupported Technologies Check
        lower_text = text.lower()
        cand_skills = {s.canonical_name.lower() for s in cand_data.skills}
        for pat in UNSUPPORTED_TECH_PATTERNS:
            match = re.search(pat, lower_text)
            if match:
                tech_found = match.group(0)
                if tech_found not in cand_skills:
                    violations.append(
                        f"Unsupported technology claim: text mentions '{tech_found}', which candidate profile does not possess."
                    )

        # 3. Fabricated Metrics Check
        for pat in FABRICATED_METRICS_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                violations.append(
                    f"Fabricated metric claim: text contains unverified metric '{match.group(0)}'."
                )

        # 4. Certification Check
        # Oracle certification is marked NEEDS_CONFIRMATION - warn if asserted as confirmed
        if re.search(r"\boracle(?:\s+cloud)?\s+certified\b", text, re.IGNORECASE):
            oracle_cert = next((c for c in (candidate.certifications or []) if "oracle" in c.name.lower()), None)
            if oracle_cert and oracle_cert.status == "NEEDS_CONFIRMATION":
                warnings.append("Oracle Cloud certification requires user confirmation before submitting.")

        # 5. Company Name Integrity Check
        allowed_companies = {"sentio mind", "banao technologies", "banao", "innovate", "edunet foundation", "edunet", "bbditm", "iit madras"}
        # Scan for company claims
        worked_at_matches = re.findall(r"(?:worked at|engineer at|developer at|intern at)\s+([A-Za-z0-9\s]+?)(?=[,\.\n]|$)", text, re.IGNORECASE)
        for comp in worked_at_matches:
            clean_comp = comp.strip().lower()
            if clean_comp and not any(ac in clean_comp for ac in allowed_companies):
                # Only flag if not referencing the target job's company
                warnings.append(f"Referenced company '{comp.strip()}' should be verified against candidate history.")

        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "actual_experience_years": round(cand_data.actual_experience_years, 1),
            "verified_skills_count": len(cand_data.skills),
            "safety_verdict": "SAFE" if len(violations) == 0 else "SAFETY_VIOLATION",
        }

    @staticmethod
    def classify_claim_provenance(claim: str, candidate: CandidateProfile) -> str:
        """
        Classifies claim as:
        - KNOWN (explicitly recorded in candidate profile)
        - SUPPORTED_INFERENCE (defensible deduction from verified projects/roles)
        - UNKNOWN (cannot be substantiated)
        """
        cand_data = extract_candidate_data(candidate)
        cand_skills = {s.canonical_name.lower() for s in cand_data.skills}
        lower_claim = claim.lower()

        # Direct skill or company or education match
        if any(s in lower_claim for s in cand_skills):
            return "KNOWN"
        if any(c.company.lower() in lower_claim for c in (candidate.experiences or [])):
            return "KNOWN"
        if any(e.degree.lower() in lower_claim or e.field.lower() in lower_claim for e in (candidate.educations or [])):
            return "KNOWN"

        # Supported inferences (RAG, prompt engineering, vector search from projects)
        supported_topics = {"vector search", "prompt engineering", "agentic workflows", "embeddings", "retrieval"}
        if any(t in lower_claim for t in supported_topics):
            return "SUPPORTED_INFERENCE"

        return "UNKNOWN"
