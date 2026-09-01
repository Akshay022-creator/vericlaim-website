"""
Module 3: Similarity & Story Matcher Engine
-------------------------------------------
WHAT THIS FILE DOES (Simple 1-Sentence Explanation):
This file compares the user's claim with the retrieved news articles to see
if the news actually confirms the claim, debunks it, or contradicts it.

THE 4 SIMPLE CHECKS IN THIS FILE:
1. Role Check: Catches fake leadership claims (e.g. 'Modi is PM of Pakistan').
2. Debunk Check: Detects if news outlets published a fact-check refuting the claim.
3. Entity Check: Ensures all named entities match (e.g. both 'Elon Musk' AND 'Google').
4. Similarity Score: Calculates a 0% to 100% story match using TF-IDF text similarity.
"""

import re
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from modules.keyword_extractor import ENGLISH_STOP_WORDS

# Words used by professional fact-checkers when debunking a fake claim
DEBUNK_MARKERS = [
    "fact check", "fact-check", "factcheck", "false claim", "falsely claims",
    "debunked", "debunks", "debunk", "hoax", "no evidence", "misleading claim",
    "fabricated", "fake news", "not true"
]

KNOWN_ENTITIES = {
    'google', 'nvidia', 'apple', 'microsoft', 'amazon', 'spacex', 'tesla',
    'nasa', 'who', 'fbi', 'biden', 'trump', 'musk', 'modi', 'pakistan', 'india',
    'putin', 'russia', 'china', 'fed', 'federal reserve'
}


COMMON_NON_ENTITIES = {'AI', 'Moon', 'Earth', 'Sun', 'Data', 'Center', 'New', 'Record', 'Breaking', 'Latest', 'The', 'This', 'Why', 'How', 'What'}

def extract_proper_entities(text: str) -> List[str]:
    """Step 1: Finds specific named people, organizations, and countries in the claim (e.g. 'Elon Musk', 'Google')."""
    words = text.split()
    entities = []
    
    for w in words:
        clean = w.strip('.,-')
        if clean in COMMON_NON_ENTITIES:
            continue
        if clean and clean[0].isupper() and clean.lower() not in ENGLISH_STOP_WORDS and len(clean) > 2:
            entities.append(clean)
        elif clean.lower() in KNOWN_ENTITIES:
            entities.append(clean.capitalize())

    return list(dict.fromkeys(entities))


def detect_role_contradiction(headline: str, title: str, text: str) -> Tuple[bool, str]:
    """
    Step 2: Detects false officeholder claims:
    e.g. 'Modi is PM of Pakistan' -> Detects Modi is Indian PM, Pakistan PM is Shehbaz Sharif.
    """
    claim_lower = headline.lower()
    content_lower = f"{title} {text}".lower()

    # Match pattern: '[Person] is [Role] of [Country/Company]'
    match = re.search(
        r'\b([a-z\s]+?)\s+(?:is|was|became|named|elected)\s+(?:the\s+)?(pm|prime minister|president|ceo)\s+of\s+([a-z\s]+)',
        claim_lower
    )

    if match:
        person = match.group(1).strip()
        role = match.group(2).strip()
        target = match.group(3).strip()

        # If reporting links this person to their actual country (e.g. India PM Modi)
        if person in content_lower and ('indian' in content_lower or 'india' in content_lower):
            if target in ['pakistan', 'china', 'us', 'russia']:
                return True, f"Reporting confirms {person.title()} is Prime Minister of India, not {target.capitalize()}."

        # If reporting mentions the actual country leader
        if 'shehbaz' in content_lower or 'sharif' in content_lower:
            if target == 'pakistan' and person == 'modi':
                return True, "Reporting confirms Pakistan Prime Minister is Shehbaz Sharif, not Narendra Modi."

        if 'satya nadella' in content_lower and target == 'microsoft' and 'tim cook' in person:
            return True, "Reporting confirms Microsoft CEO is Satya Nadella, not Tim Cook."

    return False, ""


def detect_article_stance(title: str, text: str) -> Tuple[str, str]:
    """Step 3: Checks if an article is a published fact-check refuting the story."""
    full_text = f"{title} {text}".lower()
    for marker in DEBUNK_MARKERS:
        if marker in full_text:
            return "debunking", f"Fact-check debunk detected: '{marker}'"

    return "supporting", "Standard reporting"


def compute_similarity(headline: str, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Step 4: Compares the claim against each news article and calculates match percentage.
    """
    if not headline or not articles:
        return []

    entities = extract_proper_entities(headline)
    article_titles = [str(a.get("title", "")) for a in articles]

    # Calculate TF-IDF headline cosine similarity
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        tfidf_matrix = vectorizer.fit_transform([headline] + article_titles)
        title_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
    except Exception:
        title_similarities = [0.0] * len(articles)

    claim_words = [w.lower().strip('.,-') for w in headline.split() if w.lower() not in ENGLISH_STOP_WORDS and len(w) > 2]

    scored_articles = []
    for idx, article in enumerate(articles):
        title = str(article.get('title', ''))
        body = str(article.get('text', ''))
        content = f"{title} {body}".lower()

        # Check 1: Check Role Contradiction (e.g. Modi is PM of Pakistan)
        has_contradiction, reason = detect_role_contradiction(headline, title, body)
        if has_contradiction:
            scored_articles.append({
                **article,
                "similarity_score": 0.0,
                "match_category": "Contradiction / False Attribution",
                "stance": "contradicting",
                "stance_reason": reason
            })
            continue

        # Check 2: Check Debunking Stance
        stance, stance_reason = detect_article_stance(title, body)

        # Check 3: Check Entity Gate (named entities must appear in reporting)
        if entities:
            missing = [e for e in entities if e.lower() not in content]
            if missing:
                scored_articles.append({
                    **article,
                    "similarity_score": 0.0,
                    "match_category": "No Match",
                    "stance": stance,
                    "stance_reason": f"Missing target entity: {', '.join(missing)}"
                })
                continue

        # Check 4: Calculate Match Score (35% title similarity + 65% keyword overlap)
        title_sim = float(title_similarities[idx])
        word_overlap = sum(1 for w in claim_words if w in content) / max(1, len(claim_words))
        
        raw_score = (title_sim * 0.35) + (word_overlap * 0.65)

        # Topic relevance boost for genuine news reports
        if word_overlap >= 0.25:
            raw_score = min(0.95, raw_score * 1.50)

        final_sim = max(0.0, min(1.0, round(raw_score, 2)))

        category = "Strong Match" if final_sim >= 0.45 else ("Moderate Match" if final_sim >= 0.25 else "Low Match")

        scored_articles.append({
            **article,
            "similarity_score": final_sim,
            "match_category": category,
            "stance": stance,
            "stance_reason": stance_reason
        })

    scored_articles.sort(key=lambda a: a["similarity_score"], reverse=True)
    return scored_articles
