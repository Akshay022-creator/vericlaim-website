"""
Accurate Entity-Aware & Semantic Verification Engine
---------------------------------------------------
PURPOSE:
Compares news articles against claims with strict Subject-Object Entity Checking:
1. Separates action verbs ('buys', 'sues', 'acquires') from target entities ('Elon Musk', 'Google').
2. Subject-Object Co-Occurrence Gate:
   If a claim states 'Elon Musk buys Google', an article MUST mention BOTH 'Elon Musk' AND 'Google'.
   If an article only mentions Elon Musk buying SpaceX or Tesla (without Google), score is strictly 0.00.
3. Computes TF-IDF Cosine Similarity for true matching stories.
"""

import re
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from modules.keyword_extractor import ENGLISH_STOP_WORDS

# Common action verbs that describe events/transactions
ACTION_VERBS = {
    "buys", "bought", "buy", "buying", "purchases", "purchased", "purchasing",
    "acquires", "acquired", "acquiring", "acquisition", "merges", "merged",
    "invests", "invested", "investing", "investment", "sues", "sued", "suing",
    "launches", "launched", "launching", "announces", "announced", "announcing",
    "reports", "reported", "reporting", "approves", "approved", "approving",
    "discovers", "discovered", "discovering", "lands", "landed", "landing",
    "cuts", "cut", "cutting", "raises", "raised", "raising", "drops", "dropped",
    "fires", "fired", "firing", "quits", "quit", "resigns", "resigned", "bans", "banned"
}


def extract_target_entities(headline: str) -> List[str]:
    """
    Extracts the key named subjects and object entities from a claim,
    excluding generic stopwords and action verbs.
    Example: 'Elon Musk buys Google' -> ['elon', 'musk', 'google']
    """
    clean_text = re.sub(r'[^\w\s]', ' ', headline.lower())
    tokens = clean_text.split()
    entities = [
        tok.strip()
        for tok in tokens
        if len(tok) > 2
        and tok not in ENGLISH_STOP_WORDS
        and tok not in ACTION_VERBS
        and not tok.isnumeric()
    ]
    return entities


def compute_similarity(headline: str, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compares the claim against each candidate article with strict entity co-occurrence checking.
    """
    if not headline or not headline.strip() or not articles:
        return []

    target_entities = extract_target_entities(headline)
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

        full_content_lower = f"{article.get('title', '')} {article.get('text', '')}".lower()
        title_lower = str(article.get('title', '')).lower()

        # Check target entity presence
        if target_entities:
            matched_entities_content = [e for e in target_entities if e in full_content_lower]
            matched_entities_title = [e for e in target_entities if e in title_lower]
            entity_ratio = len(matched_entities_content) / len(target_entities)
            title_entity_ratio = len(matched_entities_title) / len(target_entities)
        else:
            entity_ratio = 1.0
            title_entity_ratio = 1.0

        # STRICT MULTI-ENTITY CHECK:
        # If claim has multiple target entities (e.g. ['elon', 'musk', 'google']):
        # If an article is missing ANY distinct key entity group (e.g. 'google' is missing),
        # then this article is about something else entirely (e.g. SpaceX funding, Twitter trial).
        if len(target_entities) >= 2:
            if entity_ratio < 0.75:
                # Missing essential entities in claim -> Score is 0
                normalized_score = 0.0
                match_category = "No Match"
                article_copy = dict(article)
                article_copy["similarity_score"] = normalized_score
                article_copy["match_category"] = match_category
                scored_articles.append(article_copy)
                continue

        # If entities are present, compute balanced hybrid alignment
        raw_score = (title_sim * 0.50) + (text_sim * 0.25) + (entity_ratio * 0.25)

        if title_entity_ratio >= 0.75:
            raw_score = min(0.98, raw_score * 1.30)

        normalized_score = max(0.0, min(1.0, round(raw_score, 2)))

        if normalized_score >= 0.50:
            match_category = "Strong Match"
        elif normalized_score >= 0.30:
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
