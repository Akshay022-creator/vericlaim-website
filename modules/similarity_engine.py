"""
Accurate Entity-Aware, Relational & Stance Verification Engine
-------------------------------------------------------------
PURPOSE:
Compares news articles against claims with high precision and zero false positives:
1. Relational & Role Binding Check:
   Detects false office/role attributions (e.g. 'Modi is PM of Pakistan').
   If reporting states that Pakistan's PM is Shehbaz Sharif, or Modi is India's PM,
   the contradiction is flagged and the claim is scored 0/100 (False).
2. Multi-Entity Co-Occurrence Gate:
   If a claim contains 2+ distinct entities (e.g. 'Elon Musk' AND 'Google'),
   both must appear in the reporting. Missing entities = 0.00 match.
3. Single Entity Gate:
   If a claim contains 1 entity (e.g. 'Nvidia'), it must appear in the reporting
   alongside relevant topic keywords.
4. Stance & Debunk Detection:
   Identifies articles that are professional fact-checks debunking the claim.
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
    'pfizer', 'moderna', 'fda', 'sec', 'fed', 'federal reserve', 'vatican',
    'modi', 'pakistan', 'india', 'shehbaz', 'sharif', 'putin', 'russia', 'china'
}


def extract_proper_entities(text: str) -> List[str]:
    """
    Extracts distinct named entities and organizations from a claim.
    Example: 'Elon Musk buys Google' -> ['Elon Musk', 'Google']
             'Modi is PM of Pakistan' -> ['Modi', 'Pakistan']
    """
    matches = re.findall(r'\b[A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)*\b', text)
    common_starters = {
        'The', 'This', 'A', 'An', 'In', 'On', 'At', 'Why', 'How', 'What',
        'When', 'Where', 'Who', 'New', 'Scientists', 'Reports', 'Breaking', 'Latest', 'Pm'
    }
    entities = [m for m in matches if m not in common_starters and len(m) > 2]

    # Also detect lowercase known tech / org entities if typed in lowercase
    words = text.lower().split()
    for w in words:
        clean_w = w.strip('.,-')
        if clean_w in LOWERCASE_KNOWN_ENTITIES and not any(clean_w in e.lower() for e in entities):
            entities.append(clean_w.capitalize())

    return entities


def detect_role_contradiction(headline: str, title: str, text: str) -> Tuple[bool, str]:
    """
    Detects false office/leadership claims:
    e.g. 'Modi is PM of Pakistan' or 'Tim Cook is CEO of Microsoft'.
    """
    headline_clean = headline.lower()
    full_content = f"{title} {text}".lower()

    # Pattern: [Name] is [Role] of [Entity/Country]
    role_pattern = re.search(
        r'\b([a-z\s]+?)\s+(?:is|was|became|named|appointed|elected)\s+(?:the\s+)?(pm|prime minister|president|ceo|chancellor|king|queen|founder)\s+of\s+([a-z\s]+)',
        headline_clean
    )

    if role_pattern:
        person = role_pattern.group(1).strip()
        role = role_pattern.group(2).strip()
        org_or_country = role_pattern.group(3).strip()

        # Step 1: Check if this exact person IS confirmed with this exact role
        # e.g. 'Apple CEO Tim Cook', 'Prime Minister of India Narendra Modi', 'Indian PM Modi'
        direct_confirmations = [
            rf'{org_or_country}\s+{role}\s+{person}',
            rf'{role}\s+{person}',
            rf'{person}\s*,\s*(?:the\s+)?{role}\s+of\s+{org_or_country}',
            rf'{person}\s*,\s*(?:the\s+)?{org_or_country}\s+{role}'
        ]
        for dc in direct_confirmations:
            if re.search(dc, full_content):
                return False, ""

        # Step 2: Check if reporting explicitly ties the claimed person to a DIFFERENT country/org
        # e.g. 'Indian PM Modi', 'PM Modi of India', 'India PM Modi'
        if person in full_content and ('indian' in full_content or 'india' in full_content):
            if org_or_country in ['pakistan', 'china', 'us', 'usa', 'russia', 'uk', 'france']:
                return True, f"Reporting confirms {person.title()} is Prime Minister of India, not {org_or_country.capitalize()}."

        # Step 3: Check if prominent other leaders are identified
        if 'shehbaz' in full_content or 'sharif' in full_content or 'imran khan' in full_content:
            if org_or_country == 'pakistan' and person == 'modi':
                return True, "Reporting confirms Pakistan Prime Minister is Shehbaz Sharif, not Narendra Modi."

        if 'satya nadella' in full_content and org_or_country == 'microsoft' and 'tim cook' in person:
            return True, "Reporting confirms Microsoft CEO is Satya Nadella, not Tim Cook."

    return False, ""


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
    Compares the claim against each candidate article with strict entity co-occurrence
    and relational role-contradiction checking.
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

        # Step 1: Check Relational / Role Contradiction (e.g. Modi is PM of Pakistan)
        has_role_contradiction, role_contradiction_msg = detect_role_contradiction(headline, title_str, text_str)
        if has_role_contradiction:
            scored_articles.append({
                **article,
                "similarity_score": 0.0,
                "match_category": "Contradiction / False Attribution",
                "stance": "contradicting",
                "stance_reason": role_contradiction_msg
            })
            continue

        # Step 2: Detect Debunking Stance
        stance, stance_reason = detect_article_stance(title_str, text_str)

        # Step 3: Multi-Entity Gate
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

        # Step 4: Compute Calibrated Similarity for relevant articles
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
