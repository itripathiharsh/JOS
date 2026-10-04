# Phase 4 — Job Intelligence & Deterministic Matching Engine

## 1. Overview & Core Principles

The **Intelligence Module** provides local, zero-cost (₹0 budget), explainable, deterministic matching between stored jobs and the candidate profile.

### Core Architecture:
```text
Stored Jobs (PostgreSQL)
    ↓
Deterministic Requirement Extractor (intelligence/extractor.py)
    ↓
Skill & Role Normalizer (intelligence/normalization.py)
    ↓
Candidate Profile Evaluator (intelligence/candidate.py)
    ↓
8-Dimension Evaluation & Scoring Engine (intelligence/engine.py)
    ↓
Explainability & Concern Generator
    ↓
Persistent MatchResult Model (app/models/matching.py)
    ↓
REST APIs & Frontend UI Dashboard (app/api/routes/matching.py & JobsPage.tsx)
```

### Immutable Constraints:
- **Zero Paid LLM APIs**: No OpenAI, Gemini, Groq, Anthropic, or external inference calls.
- **Explainable & Traceable**: Every score and gap links directly to concrete fields in the job and candidate profile.
- **Fair to Unknown Data**: Undisclosed salary or missing experience requirements lower *data completeness* rather than destroying the match score.
- **No Hallucinations**: Candidate skills are strictly validated against existing profile entries.

---

## 2. Controlled Skill Normalization

Defined in [`intelligence/normalization.py`](file:///F:/job%20wala%20project/intelligence/normalization.py):
- Maintains a bidirectional canonical concept dictionary (`source_skill` -> `canonical_skill`).
- Equivalences are conservative and defensible:
  - `RAG`, `Retrieval-Augmented Generation`, `Retrieval Augmented Generation` -> `RAG`
  - `Transformers`, `Hugging Face Transformers`, `HuggingFace Transformers` -> `Hugging Face Transformers`
  - `Large Language Models`, `LLMs`, `LLM` -> `LLMs`
  - `PyTorch`, `Torch` -> `PyTorch`
  - `Scikit-learn`, `sklearn` -> `Scikit-learn`
  - `PostgreSQL`, `Postgres` -> `PostgreSQL`
  - `FastAPI` -> `FastAPI`
  - `Kubernetes`, `K8s` -> `Kubernetes`
- Strictly prohibits over-generalization (e.g., Python is never normalized to Backend Engineer).

---

## 3. Controlled Role Normalization & Priority

Defined in [`intelligence/normalization.py`](file:///F:/job%20wala%20project/intelligence/normalization.py):
- Evaluates job titles against candidate target role priorities:
  1. `AI Engineer` (Rank 1: 100 pts)
  2. `ML Engineer` (Rank 2: 92 pts)
  3. `Backend Engineer` (Rank 3: 85 pts)
  4. `Forward Deployed Engineer (FDE)` (Rank 4: 78 pts)
  5. `Technical Consultant` (Rank 5: 72 pts)
- Related domains (General Software Engineering, Full-Stack): 55 pts (`MODERATE`).
- Unrelated domains (Content Reviewer, Kundenservice, Sales, etc.): 15 pts (`WEAK`).
- Unknown / Empty: 50 pts (`UNKNOWN`, non-penalizing).

---

## 4. Requirement Extraction Layer

Defined in [`intelligence/extractor.py`](file:///F:/job%20wala%20project/intelligence/extractor.py):
- Extracts structured requirements from `title`, `description`, `requirements`, `responsibilities`, `location`, `work_mode`, and `salary`:
  - **Required vs Preferred Skills**: Distinguishes between required and nice-to-have/bonus sections. Excludes marketing/boilerplate sections (e.g. "Not your tech stack?").
  - **Experience**: Regex parsing for min/max years (e.g. `3+ years`, `1-3 years`). If missing -> `None` (`UNKNOWN`).
  - **Education**: Degree/field patterns (Bachelor's, Master's, STEM). If missing -> `NOT_SPECIFIED`.
  - **Work Mode**: Detects `remote`, `hybrid`, `on-site`.
  - **Salary**: Disclosed min/max/currency. If missing -> `None` (`UNKNOWN`).

---

## 5. Candidate Profile Extraction

Defined in [`intelligence/candidate.py`](file:///F:/job%20wala%20project/intelligence/candidate.py):
- **Single Source of Truth**: Reads from `CandidateProfile` in PostgreSQL.
- **Actual Experience Calculation**: Total experience is computed exclusively from `Experience` records (start date, end date, current flag), adding up to ~2.0 years.
- **Distinction**: The user's preference field of `0-1 years` is NOT treated as actual experience.
- **Salary Status**: Candidate minimum of ₹3,50,000 INR retains status `NEEDS_CONFIRMATION`.

---

## 6. 8 Matching Dimensions & Scoring Formula

Defined in [`intelligence/engine.py`](file:///F:/job%20wala%20project/intelligence/engine.py):

| Dimension | Base Weight | Known Evaluation Logic | Unknown / Missing Handling |
| :--- | :---: | :--- | :--- |
| **Role Fit** | 30% | Direct target role alignment & priority rank (100-72 pts) | `UNKNOWN` (neutral) |
| **Skill Fit** | 35% | Required match ratio (85%) + Preferred match ratio (15%) | `UNKNOWN` (neutral) |
| **Experience Fit** | 15% | Met: 100 pts; Partial: 60 pts; Gap: 25 pts | `UNKNOWN` (non-penalizing) |
| **Location Fit** | 8% | Remote/India: 100 pts; Regional remote: 55 pts; Relocation: 50 pts | `UNKNOWN` (neutral) |
| **Work Mode Fit** | 4% | Matches candidate preference (Remote/Hybrid/On-site): 100 pts | `UNKNOWN` (neutral) |
| **Salary Fit** | 3% | Disclosed salary >= baseline: 100 pts; Below: 30 pts | `UNKNOWN` (non-penalizing) |
| **Education Fit** | 3% | Satisfied by candidate B.Tech / BS degrees: 100 pts | `NOT_SPECIFIED` (neutral) |
| **Employment Type Fit** | 2% | Matches accepted types (Full-time/Contract/Internship): 100 pts | `UNKNOWN` (neutral) |

### Fair Unknown-Data Normalization:
When a dimension has `is_known == False`, its weight is excluded from the denominator. Known dimension weights are rescaled so the candidate is evaluated fairly on available facts without arbitrary point deductions for undisclosed employer data.

### Data Completeness Metric:
$$\text{Completeness} = \frac{\text{Known Dimensions}}{8} \times 100\%$$
- `>= 75.0%`: `HIGH`
- `50.0% - 74.9%`: `MEDIUM`
- `< 50.0%`: `LOW`

### Fit Categories:
- `INSUFFICIENT_DATA`: Completeness < 30%
- `HIGH_RELEVANCE`: Overall Score >= 80.0 (Strictly prohibited if hard requirement mismatch exists)
- `GOOD_RELEVANCE`: Overall Score 65.0 - 79.9
- `PARTIAL_RELEVANCE`: Overall Score 45.0 - 64.9
- `LOW_RELEVANCE`: Overall Score < 45.0

---

## 7. Phase 4.1 — Hard Requirement Evaluation Layer

To prevent misleading high relevance scores (e.g. 91.1/100 HIGH_RELEVANCE for a Senior vacancy requiring 4+ years when candidate has ~2.0 years), a separate evaluation layer evaluates explicit constraints before final score assignment:

```text
Job Postings
     ↓
Requirement Extraction
     ↓
Hard Requirement Evaluation
  ├── 1. Experience Check: min_exp vs candidate actual experience (~2.0 yrs from Experience records)
  ├── 2. Required Skills Check: missing explicit mandatory technical skills
  ├── 3. Location Restriction Check: explicit regional restriction excluding India
  └── 4. Education Degree Check: explicit unmet degrees (e.g. PhD)
     ↓
8-Dimension Normal Weighted Scoring
     ↓
Hard Requirement Score Cap, Penalty (-15 to -25 pts), and Category Capping
     ↓
Final Score & Max Fit Category Enforcement (CANNOT be HIGH_RELEVANCE)
```

### Deterministic Rules & Severity:
- **Experience**:
  - `min_exp >= 5.0` & `cand_exp <= 2.5`: `CRITICAL` mismatch (-25 penalty, cap 54.0, max `PARTIAL_RELEVANCE`).
  - Gap $\ge 1.5$ yrs (e.g. 4+ yrs vs 2.0 yrs): `MAJOR` mismatch (-15 penalty, cap 64.0, max `PARTIAL_RELEVANCE`).
  - Gap $< 1.5$ yrs (e.g. 3+ yrs vs 2.0 yrs): `MAJOR` warning (-10 penalty, cap 78.0, max `GOOD_RELEVANCE`).
  - Unstated: Neutral (`UNKNOWN`).
- **Required Skills**:
  - Missing $\ge 2$ required skills: `MAJOR` mismatch (cap 64.0, max `PARTIAL_RELEVANCE`).
  - Missing 1 required skill: `MAJOR` warning (cap 78.0, max `GOOD_RELEVANCE`).
  - Missing preferred skills: `MINOR` / informational. Never triggers hard mismatch.
- **Location**:
  - Explicit geographic restriction excluding India: `MAJOR` mismatch (cap 64.0, max `PARTIAL_RELEVANCE`).
  - Unstated: Neutral (`UNKNOWN`).
- **Education**:
  - Explicit unmet degree (e.g. PhD): `MAJOR` mismatch (cap 64.0, max `PARTIAL_RELEVANCE`).
  - Unstated: Neutral (`NOT_SPECIFIED`).
- **Golden Rule**:
  - Any job with an explicit major/critical hard requirement mismatch **CANNOT** receive `HIGH_RELEVANCE`.

---

## 8. Engine Versioning & Cache Invalidation

- Current version: `ENGINE_VERSION = "1.1.0"`.
- Match results are cached in the `match_results` table.
- Cache is invalidated and recomputed if:
  1. `force_recompute == True`
  2. `job.updated_at > match_result.calculated_at`
  3. `candidate.updated_at > match_result.calculated_at`
  4. `match_result.engine_version != CURRENT_ENGINE_VERSION` (all 1.0.0 matches invalidated on 1.1.0 upgrade)

---

## 9. REST APIs

- `POST /api/jobs/{job_id}/match?force={bool}`: Compute/retrieve match for a job.
- `GET /api/jobs/{job_id}/match`: Retrieve persistent match result for a job.
- `POST /api/jobs/match/bulk`: Bulk analyze multiple stored jobs.
- `GET /api/jobs`: Returns jobs list including `match_score`, `fit_category`, `has_hard_mismatch`.
