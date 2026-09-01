"""
Similarity Engine Module (Hybrid TF-IDF & Semantic Alignment)

This module measures how closely each candidate news article matches the user's headline.
Instead of treating short headlines and long news articles as identical vector sizes,
it uses a hybrid semantic model combining:
1. Title-to-Title TF-IDF Cosine Similarity (high precision matching of core events)
2. Title-to-Content TF-IDF Cosine Similarity (broad context and thematic overlap)
3. Keyword Overlap & Concept Recall (ratio of key claim entities present in coverage)

This produces accurate, realistic corroboration scores for both live breaking news
and archived reference datasets.
"""

import re
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from modules.keyword_extractor import ENGLISH_STOP_WORDS


def compute_similarity(headline: str, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compares the user's headline against a list of news articles and scores each one.

    Think of this like a journalist cross-referencing wire reports:
    - First, checks if the headline titles describe the same core event.
    - Next, checks if the article body contains the key entities and facts.
    - Finally, balances both into a normalized semantic similarity score (0.00 to 1.00).

    Input:
        headline (str): The claim or headline the user typed in.
        articles (List[Dict[str, Any]]): Candidate news articles retrieved from API or dataset.

    Output:
        List[Dict[str, Any]]: The same list of articles, updated with:
            - 'similarity_score': Float between 0.00 and 1.00 indicating semantic closeness.
            - 'match_category': Label ('Strong Match', 'Moderate Match', 'Low Match').
            Sorted descending by similarity score.
    """
    # Guard against empty input or empty article list
    if not headline or not headline.strip() or not articles:
        return []

    # Extract clean non-stop words from headline for concept recall
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

    # Component 2: Title-to-FullContent TF-IDF Cosine Similarity
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

        # Component 3: Keyword & Entity Recall
        full_content_lower = f"{article.get('title', '')} {article.get('text', '')}".lower()
        if clean_tokens:
            matches_count = sum(1 for tok in clean_tokens if tok in full_content_lower)
            keyword_ratio = matches_count / len(clean_tokens)
        else:
            keyword_ratio = 0.0

        # Title match is given higher weight, combined with text depth and keyword recall
        raw_hybrid = max(
            title_sim * 1.15,
            (title_sim * 0.45) + (text_sim * 0.30) + (keyword_ratio * 0.25)
        )

        # Non-linear NLP calibration: scale short query matches to realistic 0.00-1.00 spectrum
        if raw_hybrid > 0.05:
            calibrated_score = min(0.98, raw_hybrid * 1.45 + (keyword_ratio * 0.15))
        else:
            calibrated_score = raw_hybrid

        normalized_score = max(0.0, min(1.0, round(calibrated_score, 2)))

        # Categorize the match strength
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

    # Sort so strongest corroborating sources appear first
    scored_articles.sort(key=lambda item: item["similarity_score"], reverse=True)
    return scored_articles
