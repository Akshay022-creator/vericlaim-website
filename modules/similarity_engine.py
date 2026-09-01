"""
Module 3: Hybrid TF-IDF & Semantic Similarity Engine
-----------------------------------------------------
PURPOSE (Easy to explain in an interview or presentation):
This module computes how mathematically similar each retrieved news article is to the user's claim.

Why Hybrid TF-IDF instead of basic string matching?
A short headline and a 500-word news article naturally have different lengths.
Our hybrid formula balances three distinct components:
1. Title-to-Title TF-IDF Cosine Similarity (High-precision matching of the core event)
2. Title-to-FullContent TF-IDF Cosine Similarity (Thematic and background overlap)
3. Concept/Entity Recall (Checks what percentage of key claim words appear in the reporting)

Final Calibrated Score: Normalized to a clean 0.00 to 1.00 scale.
"""

import re
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from modules.keyword_extractor import ENGLISH_STOP_WORDS


def compute_similarity(headline: str, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compares the claim against each candidate article and calculates a semantic similarity score.

    Input:
        headline: The user's submitted claim.
        articles: List of articles retrieved from the news APIs.

    Output:
        List of articles with 'similarity_score' (0.00 to 1.00) and 'match_category',
        sorted descending by best corroborating source.
    """
    if not headline or not headline.strip() or not articles:
        return []

    # Clean non-stop words from claim for keyword recall checking
    clean_tokens = [
        tok.lower().strip('.,-')
        for tok in re.findall(r'\b\w+\b', headline.lower())
        if len(tok) > 2 and tok.lower() not in ENGLISH_STOP_WORDS
    ]

    article_titles = [str(art.get("title", "")) for art in articles]
    article_full_texts = [f"{art.get('title', '')}. {art.get('text', '')}".strip() for art in articles]

    # Component 1: Title-to-Title TF-IDF Cosine Similarity
    title_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        title_vectors = title_vectorizer.fit_transform([headline] + article_titles)
        title_similarities = cosine_similarity(title_vectors[0:1], title_vectors[1:])[0]
    except Exception:
        title_similarities = [0.0] * len(articles)

    # Component 2: Title-to-Body TF-IDF Cosine Similarity
    text_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=2000)
    try:
        text_vectors = text_vectorizer.fit_transform([headline] + article_full_texts)
        text_similarities = cosine_similarity(text_vectors[0:1], text_vectors[1:])[0]
    except Exception:
        text_similarities = [0.0] * len(articles)

    scored_articles = []
    for index, article in enumerate(articles):
        title_sim = float(title_similarities[index])
        text_sim = float(text_similarities[index])

        # Component 3: Concept & Entity Recall
        full_content_lower = f"{article.get('title', '')} {article.get('text', '')}".lower()
        if clean_tokens:
            matches_count = sum(1 for tok in clean_tokens if tok in full_content_lower)
            keyword_ratio = matches_count / len(clean_tokens)
        else:
            keyword_ratio = 0.0

        # Weighted combination: Title alignment (45%) + Body context (30%) + Entity recall (25%)
        raw_hybrid = max(
            title_sim * 1.15,
            (title_sim * 0.45) + (text_sim * 0.30) + (keyword_ratio * 0.25)
        )

        # NLP Calibration: scale short headline matches to realistic 0.00-1.00 spectrum
        if raw_hybrid > 0.05:
            calibrated_score = min(0.98, raw_hybrid * 1.45 + (keyword_ratio * 0.15))
        else:
            calibrated_score = raw_hybrid

        normalized_score = max(0.0, min(1.0, round(calibrated_score, 2)))

        # Qualitative match tier
        if normalized_score >= 0.45:
            match_category = "Strong Match"
        elif normalized_score >= 0.20:
            match_category = "Moderate Match"
        else:
            match_category = "Low Match"

        article_copy = dict(article)
        article_copy["similarity_score"] = normalized_score
        article_copy["match_category"] = match_category
        scored_articles.append(article_copy)

    # Sort descending so top corroborating articles appear first
    scored_articles.sort(key=lambda item: item["similarity_score"], reverse=True)
    return scored_articles
