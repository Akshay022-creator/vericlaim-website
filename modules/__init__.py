"""
Headline Cross-Verification & Corroboration Checker Modules Package

Exports the key pipeline functions for extracting keywords, fetching related news,
computing semantic TF-IDF similarity, checking factual consistency, and scoring corroboration.
"""

from modules.keyword_extractor import extract_keywords
from modules.news_fetcher import fetch_related_articles
from modules.similarity_engine import compute_similarity
from modules.fact_checker import check_fact_conflicts
from modules.scorer import compute_corroboration_score
from modules.visualizer import generate_chart

__all__ = [
    "extract_keywords",
    "fetch_related_articles",
    "compute_similarity",
    "check_fact_conflicts",
    "compute_corroboration_score",
    "generate_chart",
]
