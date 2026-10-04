import re
import math
from collections import Counter
from typing import Set, Optional, List


STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than",
    "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
    "what's", "when", "when's", "where", "where's", "which", "while", "who",
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you",
    "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}


def tokenize(text: Optional[str]) -> List[str]:
    """Extract clean lowercase tokens of length >= 2, excluding common stopwords."""
    if not text or not isinstance(text, str):
        return []
    # Strip HTML tags if present
    cleaned = re.sub(r"<[^>]+>", " ", text)
    tokens = re.findall(r"\b[a-zA-Z0-9+#.-]{2,}\b", cleaned.lower())
    return [t for t in tokens if t not in STOPWORDS]


def token_set(text: Optional[str]) -> Set[str]:
    """Set of unique meaningful tokens."""
    return set(tokenize(text))


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Calculate Jaccard index between two token sets: |A ∩ B| / |A ∪ B|."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return round(intersection / union, 4) if union > 0 else 0.0


def text_jaccard_similarity(text_a: Optional[str], text_b: Optional[str]) -> float:
    """Calculate token Jaccard similarity directly from two text strings."""
    return jaccard_similarity(token_set(text_a), token_set(text_b))


def char_ngram_similarity(text_a: Optional[str], text_b: Optional[str], n: int = 3) -> float:
    """Calculate character n-gram Jaccard similarity for short strings (titles)."""
    if not text_a and not text_b:
        return 1.0
    if not text_a or not text_b:
        return 0.0

    a_clean = re.sub(r"\s+", " ", text_a.strip().lower())
    b_clean = re.sub(r"\s+", " ", text_b.strip().lower())

    if a_clean == b_clean:
        return 1.0

    ngrams_a = {a_clean[i:i+n] for i in range(max(0, len(a_clean) - n + 1))}
    ngrams_b = {b_clean[i:i+n] for i in range(max(0, len(b_clean) - n + 1))}

    return jaccard_similarity(ngrams_a, ngrams_b)


def cosine_token_similarity(text_a: Optional[str], text_b: Optional[str]) -> float:
    """Deterministic TF cosine similarity using term frequencies."""
    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)

    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0

    counts_a = Counter(tokens_a)
    counts_b = Counter(tokens_b)

    all_keys = set(counts_a.keys()).union(set(counts_b.keys()))
    dot_product = sum(counts_a.get(k, 0) * counts_b.get(k, 0) for k in all_keys)

    norm_a = math.sqrt(sum(v * v for v in counts_a.values()))
    norm_b = math.sqrt(sum(v * v for v in counts_b.values()))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return round(dot_product / (norm_a * norm_b), 4)
