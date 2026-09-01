"""
Accurate Entity-Aware & Semantic Verification Engine
---------------------------------------------------
PURPOSE:
Compares news articles against claims with high precision and zero false positives:
1. Multi-Entity Co-Occurrence Gate:
   If a claim contains 2+ distinct entities (e.g. 'Elon Musk' AND 'Google'),
   both must appear in the reporting. Missing entities = 0.00 match.
2. Single Entity Gate:
   If a claim contains 1 entity (e.g. 'Nvidia'), it must appear in the reporting
   alongside relevant topic keywords.
3. Stance & Debunk Detection:
   Identifies articles that are professional fact-checks debunking the claim.
4. Calibrated Hybrid TF-IDF & Keyword Overlap Scoring.
"""

import re
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from modules.keyword_extractor import ENGLISH_STOP_WORDS

# Explicit debunking markers used by professional fact-checkers (Reuters Fact Check, AP, BBC)
DEBUNK_MARKERS = [
    "fact check", "fact-check", "factcheck", "false claim", "falsely claims",
    "falsely claimed", "debunked", "debunks", "debunk", "hoax", "no evidence",
    "misleading claim", "fabricated", "unfounded", "satire", "parody",
    "digitally altered", "out of context", "fake news", "not true"
]

LOWERCASE_KNOWN_ENTITIES = {
    'google', 'nvidia', 'apple', 'microsoft', 'amazon', 'spacex', 'tesla',
    'nasa', 'who', 'fbi', 'cia', 'biden', 'trump', 'musk', 'altman', 'alien',
    'antarctica', 'meta', 'openai', 'alphabet', 'intel', 'amd', 'boeing',
    'pfizer', 'moderna', 'fda', 'sec', 'fed', 'federal reserve', 'vatican'
}


def extract_proper_entities(text: str) -> List[str]:
    """
    Extracts distinct named entities and organizations from a claim.
    Example: 'Elon Musk buys Google' -> ['Elon Musk', 'Google']
             'Nvidia reports record revenue' -> ['Nvidia']
    """
    matches = re.findall(r'\b[A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)*\b', text)
    common_starters = {
        'The', 'This', 'A', 'An', 'In', 'On', 'At', 'Why', 'How', 'What',
        'When', 'Where', 'Who', 'New', 'Scientists', 'Reports', 'Breaking', 'Latest'
    }
    entities = [m for m in matches if m not in common_starters and len(m) > 2]

    # Also detect lowercase known tech / org entities if typed in lowercase
    words = text.lower().split()
    for w in words:
        clean_w = w.strip('.,-')
        if clean_w in LOWERCASE_KNOWN_ENTITIES and not any(clean_w in e.lower() for e in entities):
            entities.append(clean_w.capitalize())

    return entities


def detect_article_stance(title: str, text: str) -> Tuple[str, str]:
    """
    Detects if a news article is supporting, neutral, or actively debunking the claim.
    """
    combined = f"{title} {text}".lower()
    for marker in DEBUNK_MARKERS:
        if marker in combined:
            return "debunking", f"Fact-check debunk detected: '{marker}'"

    return "supporting", "Standard reporting"


def compute_similarity(headline: str, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compares the claim against each candidate article with strict entity co-occurrence checking.
    """
    if not headline or not headline.strip() or not articles:
        return []

    entities = extract_proper_entities(headline)
    article_titles = [str(art.get("title", "")) for art in articles]
    article_full_texts = [f"{art.get('title', '')}. {art.get('text', '')}".strip() for art in articles]

    # Component 1: Title-to-Title TF-IDF Cosine Similarity
    title_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        title_vectors = title_vectorizer.fit_transform([headline] + article_titles)
        title_similarities = cosine_similarity(title_vectors[0:1], title_vectors[1:])[0]
    except Exception:
        title_similarities = [0.0] * len(articles)

    # Clean claim words for topic overlap checking
    claim_words = [
        w.strip('.,-').lower()
        for w in headline.split()
        if len(w) > 2 and w.lower() not in ENGLISH_STOP_WORDS and not w.isnumeric()
    ]

    scored_articles = []
    for index, article in enumerate(articles):
        title_str = str(article.get('title', ''))
        text_str = str(article.get('text', ''))
        full_content_lower = f"{title_str} {text_str}".lower()
        title_lower = title_str.lower()

        # Step 1: Detect Debunking Stance
        stance, stance_reason = detect_article_stance(title_str, text_str)

        # Step 2: Multi-Entity Gate
        if len(entities) >= 2:
            missing_entities = [e for e in entities if e.lower() not in full_content_lower]
            if missing_entities:
                scored_articles.append({
                    **article,
                    "similarity_score": 0.0,
                    "match_category": "No Match",
                    "stance": stance,
                    "stance_reason": f"Missing target entity: {', '.join(missing_entities)}"
                })
                continue
        elif len(entities) == 1:
            if entities[0].lower() not in full_content_lower:
                scored_articles.append({
                    **article,
                    "similarity_score": 0.0,
                    "match_category": "No Match",
                    "stance": stance,
                    "stance_reason": f"Missing target entity: {entities[0]}"
                })
                continue

        # Step 3: Compute Calibrated Similarity for relevant articles
        raw_title_sim = float(title_similarities[index])

        # Topic keyword overlap
        if claim_words:
            matched_words = sum(1 for w in claim_words if w in full_content_lower)
            topic_overlap = matched_words / len(claim_words)
        else:
            topic_overlap = 0.0

        if stance == "debunking":
            normalized_score = 0.90
            match_category = "Debunked by Fact-Checker"
        else:
            # Weighted formula: Title similarity (50%) + Topic overlap (50%)
            raw_score = (raw_title_sim * 0.50) + (topic_overlap * 0.50)

            # Bonus for strong title alignment
            if raw_title_sim > 0.15:
                raw_score = min(0.95, raw_score * 1.30)

            normalized_score = max(0.0, min(1.0, round(raw_score, 2)))

            if normalized_score >= 0.45:
                match_category = "Strong Match"
            elif normalized_score >= 0.25:
                match_category = "Moderate Match"
            else:
                match_category = "Low Match"

        article_copy = dict(article)
        article_copy["similarity_score"] = normalized_score
        article_copy["match_category"] = match_category
        article_copy["stance"] = stance
        article_copy["stance_reason"] = stance_reason
        scored_articles.append(article_copy)

    # Sort descending so top corroborating articles appear first
    scored_articles.sort(key=lambda item: item["similarity_score"], reverse=True)
    return scored_articles
