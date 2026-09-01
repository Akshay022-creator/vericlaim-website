"""
Keyword & Fact Extraction Module

This module takes a headline typed by the user and extracts the most important
elements: key topic words (nouns and descriptive terms), numerical figures
(such as prices, percentages, quantities), and dates or timeframes.

Think of it like highlighting the essential facts on a physical newspaper clipping
before heading to the library to search for corroborating records.
"""

import re
from typing import Dict, List, Any


# Standard English stop words list (lightweight without requiring heavy NLTK downloads)
ENGLISH_STOP_WORDS = {
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
    "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't",
    "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's",
    "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom",
    "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves", "says", "claims",
    "reported", "reports", "new", "announces", "announced", "confirms", "confirmed",
    "unveils", "unveiled", "surges", "shows", "revealed", "reveals", "hits", "plans"
}

# Month names and time references for date recognition
CALENDAR_MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
]


def extract_numbers_and_units(text: str) -> List[str]:
    """
    Extracts numerical figures, currency amounts, percentages, and unit measurements from text.

    For example, '$5 billion', '25 percent', '5000 megawatts', '1000 kilometers', or '4.50'.

    Input:
        text (str): The sentence or headline to parse for numbers and quantifiable claims.

    Output:
        List[str]: A list of detected numerical phrases preserved with their context/units.
    """
    # Regex pattern matching currency ($5B, $1.2 billion, €500M), percentages (25%, 2.8 percent),
    # and numbers attached to units or magnitude words (5000 MW, 2 million, 1000 km)
    number_pattern = re.compile(
        r'(?:\$[\d,]+(?:\.\d+)?(?:\s*(?:billion|million|trillion|k|m|b))?|'
        r'[\d,]+(?:\.\d+)?\s*(?:percent|%|basis points|bps|billion|million|trillion|thousand|'
        r'gigawatts|megawatts|gw|mw|kilometers|km|miles|light years|light-years|'
        r'years?|months?|days?|hours?|minutes?|seconds?|patients?|species|satellites?|'
        r'gpus?|qubits?|basis|dollars?)|'
        r'\b\d+(?:\.\d+)?\b)',
        re.IGNORECASE
    )

    found_matches = number_pattern.findall(text)
    # Clean whitespace and strip stray punctuation
    cleaned_numbers = [match.strip() for match in found_matches if match.strip()]
    return cleaned_numbers


def extract_dates_and_timeframes(text: str) -> List[str]:
    """
    Finds explicit years (e.g. 2025, 2029, 2030), month names, and quarters (e.g. Q3).

    Input:
        text (str): The sentence or headline to parse.

    Output:
        List[str]: A list of identified calendar dates and temporal references.
    """
    found_dates = []

    # Find 4-digit years between 1900 and 2099
    year_matches = re.findall(r'\b(19\d\d|20\d\d)\b', text)
    for year in year_matches:
        if year not in found_dates:
            found_dates.append(year)

    # Find month references (e.g. 'October', 'Sept 2025')
    for month in CALENDAR_MONTHS:
        pattern = rf'\b{month}\b(?:\s+\d{{1,2}}(?:st|nd|rd|th)?)?(?:\s*,\s*\d{{4}})?'
        month_matches = re.findall(pattern, text, re.IGNORECASE)
        for match in month_matches:
            if match.lower() not in [item.lower() for item in found_dates]:
                found_dates.append(match)

    # Find quarterly references like Q1, Q2, Q3, Q4
    quarter_matches = re.findall(r'\b(?:Q[1-4]|third quarter|fourth quarter|first quarter|second quarter)\b', text, re.IGNORECASE)
    for quarter in quarter_matches:
        if quarter not in found_dates:
            found_dates.append(quarter)

    return found_dates


def extract_keywords(headline: str) -> Dict[str, Any]:
    """
    Main extraction function: parses a headline to identify topic keywords, numbers, and dates.

    Think of this as the 'indexer' that identifies what the claim is actually about
    so we can build an effective search query to find other independent news coverage.

    Input:
        headline (str): The full news headline or forwarded claim to examine.

    Output:
        Dict[str, Any]: A structured dictionary containing:
            - "topic_words": Cleaned descriptive words (stop words removed).
            - "numbers": Extracted numerical amounts, prices, or percentages.
            - "dates": Extracted years, months, or quarters.
            - "search_query": A clean search string ready for API and database queries.
    """
    if not headline or not headline.strip():
        return {
            "topic_words": [],
            "numbers": [],
            "dates": [],
            "search_query": ""
        }

    # Clean punctuation except currency, hyphens, and percent signs
    clean_text = re.sub(r'[^\w\s\$\%\.\-]', ' ', headline)

    # Split into individual lowercase tokens
    raw_tokens = clean_text.split()

    # Filter out common stop words and very short 1-letter tokens
    topic_words = []
    for token in raw_tokens:
        clean_token = token.strip('.,-').lower()
        if len(clean_token) > 1 and clean_token not in ENGLISH_STOP_WORDS and not clean_token.isnumeric():
            topic_words.append(clean_token)

    # Extract quantifiable facts (numbers and dates)
    numbers_found = extract_numbers_and_units(headline)
    dates_found = extract_dates_and_timeframes(headline)

    # Build an optimized search query using top topic keywords (up to 5 most significant words)
    top_search_keywords = topic_words[:5]
    search_query = " ".join(top_search_keywords)

    return {
        "topic_words": topic_words,
        "numbers": numbers_found,
        "dates": dates_found,
        "search_query": search_query
    }
