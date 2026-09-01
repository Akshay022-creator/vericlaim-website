"""
Module 1: Keyword & Quantitative Fact Extractor
------------------------------------------------
PURPOSE (Easy to explain in an interview or presentation):
Before searching for evidence across global news wires, this module acts like a
journalist highlighting key facts on a notepad:
1. Topic Words: Filters out filler words ("the", "is", "a") to isolate the core subject.
2. Numerical Claims: Extracts prices, percentages, quantities (e.g. "$50 billion", "25 bps", "85%").
3. Dates & Timeframes: Extracts years, months, and quarters (e.g. "2026", "October", "Q3").
4. Clean Search Query: Assembles the top topic words into an optimized search query for news APIs.
"""

import re
from typing import Dict, List, Any


# Common English stop words list (lightweight, zero external dependencies required)
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

CALENDAR_MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
]


def extract_numbers_and_units(text: str) -> List[str]:
    """
    Step A: Extracts currency amounts, percentages, quantities, and numeric metrics.
    Example: "$50 billion", "25 basis points", "85%", "5000 megawatts"
    """
    pattern = re.compile(
        r'(?:[\$€£]\s*[\d,]+(?:\.\d+)?(?:\s*(?:billion|million|trillion|thousand|k|m|b))?|'
        r'[\d,]+(?:\.\d+)?\s*(?:percent|%|basis points|bps|billion|million|trillion|thousand|'
        r'gigawatts|megawatts|gw|mw|kilometers|km|miles|years?|months?|days?|patients?|satellites?|'
        r'gpus?|qubits?|basis|dollars?)|'
        r'\b\d+(?:\.\d+)?\b)',
        re.IGNORECASE
    )
    found_matches = [m.group(0).strip() for m in pattern.finditer(text)]
    return [item for item in found_matches if item]


def extract_dates_and_timeframes(text: str) -> List[str]:
    """
    Step B: Identifies explicit years (e.g. 2024, 2025, 2026), months, and quarters.
    """
    found_dates = []

    # 4-digit years between 1900 and 2099
    year_matches = re.findall(r'\b(19\d\d|20\d\d)\b', text)
    for year in year_matches:
        if year not in found_dates:
            found_dates.append(year)

    # Calendar months
    for month in CALENDAR_MONTHS:
        pattern = rf'\b{month}\b(?:\s+\d{{1,2}}(?:st|nd|rd|th)?)?(?:\s*,\s*\d{{4}})?'
        month_matches = re.findall(pattern, text, re.IGNORECASE)
        for match in month_matches:
            if match.lower() not in [d.lower() for d in found_dates]:
                found_dates.append(match)

    # Quarters (Q1, Q2, Q3, Q4)
    quarter_matches = re.findall(r'\b(?:Q[1-4]|third quarter|fourth quarter|first quarter|second quarter)\b', text, re.IGNORECASE)
    for quarter in quarter_matches:
        if quarter not in found_dates:
            found_dates.append(quarter)

    return found_dates


def extract_keywords(headline: str) -> Dict[str, Any]:
    """
    Step C (Main Coordinator): Parses input text and returns structured keywords & facts.
    """
    if not headline or not headline.strip():
        return {
            "topic_words": [],
            "numbers": [],
            "dates": [],
            "search_query": ""
        }

    # Clean punctuation while preserving currency and percentage symbols
    clean_text = re.sub(r'[^\w\s\$\%\.\-]', ' ', headline)
    raw_tokens = clean_text.split()

    # Filter out stop words and short 1-letter tokens
    topic_words = []
    for token in raw_tokens:
        clean_token = token.strip('.,-').lower()
        if len(clean_token) > 1 and clean_token not in ENGLISH_STOP_WORDS and not clean_token.isnumeric():
            topic_words.append(clean_token)

    # Extract quantitative facts
    numbers_found = extract_numbers_and_units(headline)
    dates_found = extract_dates_and_timeframes(headline)

    # Build optimized search query (up to 5 most significant keywords)
    top_search_keywords = topic_words[:5]
    search_query = " ".join(top_search_keywords)

    return {
        "topic_words": topic_words,
        "numbers": numbers_found,
        "dates": dates_found,
        "search_query": search_query
    }
