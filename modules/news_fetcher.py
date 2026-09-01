"""
Module 2: 7-Provider Real-Time News Fetcher
-------------------------------------------
WHAT THIS FILE DOES (Simple 1-Sentence Explanation):
This file connects to 7 major news APIs at the exact same time using Python threads
and returns matching news articles with their title, source, date, and author.

THE 7 NEWS PROVIDERS:
1. The Guardian Open Platform (Global quality journalism)
2. NewsAPI.org (Major international news wire)
3. Currents API (Live breaking news feed)
4. Mediastack API (Worldwide media streams)
5. GNews.io (Fast real-time news search)
6. NewsData.io (Regional & world news)
7. WorldNewsAPI.com (Multilingual global news)
+ Offline local news dataset fallback (if internet is unavailable)
"""

import os
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Active API Keys configuration
DEFAULT_KEYS = {
    "guardian_api": "509a239d-5252-4a54-b7b2-dee3fc9cc066",
    "news_api": "6b0350e2801b499cbcecbed4e47b58af",
    "currents_api": "ZM9sIxYq_VrDdIDniDwAFYFEVe3f1HrGzsdLscgCpxjfknrs",
    "mediastack_api": "c909b318144464243727bb0feaf824e4",
    "gnews_io": "2144d15567584bbe3a36a582c25dcee3",
    "newsdata_io": "pub_6ddcccb1251442399feb9d515407eb0b",
    "worldnews_api": "9ef63c5d9e87447291614b690dcd1b72"
}

PROVIDERS_CONFIG = [
    {"id": "guardian_api", "name": "The Guardian", "badge": "Guardian", "color": "#052962", "textColor": "#ffffff", "type": "Quality Journalism Wire", "env_var": "GUARDIAN_API_KEY"},
    {"id": "news_api", "name": "NewsAPI.org", "badge": "NewsAPI", "color": "#2563eb", "textColor": "#ffffff", "type": "Global News Wire", "env_var": "NEWS_API_KEY"},
    {"id": "currents_api", "name": "Currents API", "badge": "Currents", "color": "#0d9488", "textColor": "#ffffff", "type": "Real-Time News Stream", "env_var": "CURRENTS_API_KEY"},
    {"id": "mediastack_api", "name": "Mediastack", "badge": "Mediastack", "color": "#e11d48", "textColor": "#ffffff", "type": "Global Media Feed", "env_var": "MEDIASTACK_API_KEY"},
    {"id": "gnews_io", "name": "GNews.io", "badge": "GNews", "color": "#7c3aed", "textColor": "#ffffff", "type": "Breaking News Search", "env_var": "GNEWS_API_KEY"},
    {"id": "newsdata_io", "name": "NewsData.io", "badge": "NewsData", "color": "#059669", "textColor": "#ffffff", "type": "Regional & Intl News", "env_var": "NEWSDATA_API_KEY"},
    {"id": "worldnews_api", "name": "WorldNewsAPI", "badge": "WorldNews", "color": "#d97706", "textColor": "#ffffff", "type": "Multilingual Global Wire", "env_var": "WORLDNEWS_API_KEY"}
]


def make_article_dict(title: str, source: str, badge: str, url: str, text: str, published_at: str, author: str = "") -> Dict[str, Any]:
    """Helper: Standardizes article data into a clean, unified dictionary."""
    return {
        "title": title.strip(),
        "source": source.strip() or badge,
        "source_badge": badge,
        "author": author.strip() or source.strip() or "News Desk",
        "url": url.strip() or "#",
        "text": text.strip() if text else title.strip(),
        "published_at": published_at or "Recently Published",
        "source_type": badge
    }


# =============================================================================
# INDIVIDUAL API FETCHERS (One simple function per news provider)
# =============================================================================

def fetch_from_guardian_api(query: str, api_key: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """Provider 1: Fetches articles from The Guardian."""
    try:
        url = "https://content.guardianapis.com/search"
        params = {"q": " ".join(query.split()[:4]), "api-key": api_key, "show-fields": "headline,trailText,byline", "page-size": max_results}
        res = requests.get(url, params=params, timeout=3.5).json()
        articles = []
        for item in res.get("response", {}).get("results", []):
            fields = item.get("fields", {})
            articles.append(make_article_dict(
                title=item.get("webTitle", ""),
                source="The Guardian",
                badge="Guardian",
                url=item.get("webUrl", ""),
                text=fields.get("trailText", ""),
                published_at=item.get("webPublicationDate", ""),
                author=fields.get("byline", "The Guardian Staff")
            ))
        return articles
    except Exception:
        return []


def fetch_from_news_api(query: str, api_key: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """Provider 2: Fetches articles from NewsAPI.org."""
    try:
        url = "https://newsapi.org/v2/everything"
        params = {"q": " ".join(query.split()[:4]), "apiKey": api_key, "language": "en", "sortBy": "relevancy", "pageSize": max_results}
        res = requests.get(url, params=params, timeout=3.5).json()
        articles = []
        for item in res.get("articles", []):
            src_name = item.get("source", {}).get("name", "NewsAPI Source")
            articles.append(make_article_dict(
                title=item.get("title", ""),
                source=src_name,
                badge="NewsAPI",
                url=item.get("url", ""),
                text=item.get("description", "") or item.get("content", ""),
                published_at=item.get("publishedAt", ""),
                author=item.get("author") or src_name
            ))
        return articles
    except Exception:
        return []


def fetch_from_currents_api(query: str, api_key: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """Provider 3: Fetches articles from Currents API."""
    try:
        url = "https://api.currentsapi.services/v1/search"
        params = {"keywords": " ".join(query.split()[:4]), "apiKey": api_key, "language": "en", "limit": max_results}
        res = requests.get(url, params=params, timeout=3.5).json()
        articles = []
        for item in res.get("news", []):
            author = item.get("author", "")
            src = author if author and len(author) < 25 else "Currents Wire"
            articles.append(make_article_dict(
                title=item.get("title", ""),
                source=src,
                badge="Currents",
                url=item.get("url", ""),
                text=item.get("description", ""),
                published_at=item.get("published", ""),
                author=author or src
            ))
        return articles
    except Exception:
        return []


def fetch_from_mediastack_api(query: str, api_key: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """Provider 4: Fetches articles from Mediastack API."""
    try:
        url = "http://api.mediastack.com/v1/news"
        params = {"access_key": api_key, "keywords": " ".join(query.split()[:4]), "languages": "en", "limit": max_results}
        res = requests.get(url, params=params, timeout=3.5).json()
        articles = []
        for item in res.get("data", []):
            src = item.get("source", "Mediastack Source")
            articles.append(make_article_dict(
                title=item.get("title", ""),
                source=src,
                badge="Mediastack",
                url=item.get("url", ""),
                text=item.get("description", ""),
                published_at=item.get("published_at", ""),
                author=item.get("author") or src
            ))
        return articles
    except Exception:
        return []


def fetch_from_gnews_io(query: str, api_key: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """Provider 5: Fetches articles from GNews.io."""
    try:
        url = "https://gnews.io/api/v4/search"
        params = {"q": " ".join(query.split()[:4]), "apikey": api_key, "lang": "en", "max": max_results}
        res = requests.get(url, params=params, timeout=3.5).json()
        articles = []
        for item in res.get("articles", []):
            src = item.get("source", {}).get("name", "GNews Wire")
            articles.append(make_article_dict(
                title=item.get("title", ""),
                source=src,
                badge="GNews",
                url=item.get("url", ""),
                text=item.get("description", ""),
                published_at=item.get("publishedAt", ""),
                author=src
            ))
        return articles
    except Exception:
        return []


def fetch_from_newsdata_io(query: str, api_key: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """Provider 6: Fetches articles from NewsData.io."""
    try:
        url = "https://newsdata.io/api/1/latest"
        params = {"apikey": api_key, "q": " ".join(query.split()[:4]), "language": "en", "size": max_results}
        res = requests.get(url, params=params, timeout=3.5).json()
        articles = []
        for item in res.get("results", []):
            src = item.get("source_id", "NewsData Source").capitalize()
            creators = item.get("creator", [])
            author = creators[0] if creators else src
            articles.append(make_article_dict(
                title=item.get("title", ""),
                source=src,
                badge="NewsData",
                url=item.get("link", ""),
                text=item.get("description", ""),
                published_at=item.get("pubDate", ""),
                author=author
            ))
        return articles
    except Exception:
        return []


def fetch_from_worldnews_api(query: str, api_key: str, max_results: int = 6) -> List[Dict[str, Any]]:
    """Provider 7: Fetches articles from WorldNewsAPI.com."""
    try:
        url = "https://api.worldnewsapi.com/search-news"
        params = {"text": " ".join(query.split()[:4]), "language": "en", "number": max_results, "api-key": api_key}
        headers = {"x-api-key": api_key}
        res = requests.get(url, params=params, headers=headers, timeout=3.5).json()
        articles = []
        for item in res.get("news", []):
            url_str = item.get("url", "")
            domain = urlparse(url_str).netloc.replace("www.", "").capitalize() if url_str else "WorldNews"
            articles.append(make_article_dict(
                title=item.get("title", ""),
                source=domain,
                badge="WorldNews",
                url=url_str,
                text=item.get("summary", "") or item.get("text", "")[:300],
                published_at=item.get("publish_date", ""),
                author=item.get("author") or domain
            ))
        return articles
    except Exception:
        return []


# =============================================================================
# OFFLINE BACKUP DATASET (Zero-dependency fallback)
# =============================================================================

def get_default_dataset_path() -> Path:
    """Returns file path to the local offline CSV backup dataset."""
    return Path(__file__).resolve().parent.parent / "data" / "news_dataset.csv"


def fetch_from_local_dataset(search_terms: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
    """Reads local news CSV file if all online APIs fail."""
    csv_path = get_default_dataset_path()
    if not csv_path.exists():
        return []
    try:
        df = pd.read_csv(csv_path)
        matched = []
        terms = [t.lower() for t in search_terms if len(t) > 2]
        for _, row in df.iterrows():
            title = str(row.get("title", ""))
            text = str(row.get("text", ""))
            if any(t in f"{title} {text}".lower() for t in terms):
                matched.append(make_article_dict(
                    title=title,
                    source=str(row.get("source", "Archive")),
                    badge="Archive",
                    url=str(row.get("url", "#")),
                    text=text,
                    published_at=str(row.get("published_at", "Archive Record")),
                    author=str(row.get("source", "Staff"))
                ))
        return matched[:max_results]
    except Exception:
        return []


def get_all_providers_status() -> List[Dict[str, Any]]:
    """Returns the online status of all 7 news providers."""
    status_list = []
    for prov in PROVIDERS_CONFIG:
        active_key = os.getenv(prov["env_var"], "").strip() or DEFAULT_KEYS.get(prov["id"], "")
        status_list.append({
            "id": prov["id"],
            "name": prov["name"],
            "badge": prov["badge"],
            "color": prov["color"],
            "textColor": prov["textColor"],
            "type": prov["type"],
            "configured": bool(active_key),
            "key_masked": f"{active_key[:4]}...{active_key[-4:]}" if len(active_key) >= 8 else "Active"
        })
    return status_list


# =============================================================================
# MAIN COORDINATOR (Runs all 7 providers in parallel)
# =============================================================================

def fetch_related_articles(
    keywords_info: Dict[str, Any],
    max_results: int = 16,
    api_key: Optional[str] = None,
    enabled_providers: Optional[List[str]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Main function: Queries all 7 news providers concurrently in parallel threads.
    Returns: (articles_list, telemetry_details)
    """
    search_query = keywords_info.get("search_query", "")
    topic_words = keywords_info.get("topic_words", [])

    guardian_key = os.getenv("GUARDIAN_API_KEY", "").strip() or DEFAULT_KEYS["guardian_api"]
    news_key = api_key or os.getenv("NEWS_API_KEY", "").strip() or DEFAULT_KEYS["news_api"]
    currents_key = os.getenv("CURRENTS_API_KEY", "").strip() or DEFAULT_KEYS["currents_api"]
    mediastack_key = os.getenv("MEDIASTACK_API_KEY", "").strip() or DEFAULT_KEYS["mediastack_api"]
    gnews_key = os.getenv("GNEWS_API_KEY", "").strip() or DEFAULT_KEYS["gnews_io"]
    newsdata_key = os.getenv("NEWSDATA_API_KEY", "").strip() or DEFAULT_KEYS["newsdata_io"]
    worldnews_key = os.getenv("WORLDNEWS_API_KEY", "").strip() or DEFAULT_KEYS["worldnews_api"]

    tasks = [
        ("The Guardian", "guardian_api", fetch_from_guardian_api, search_query, guardian_key),
        ("NewsAPI.org", "news_api", fetch_from_news_api, search_query, news_key),
        ("Currents API", "currents_api", fetch_from_currents_api, search_query, currents_key),
        ("Mediastack", "mediastack_api", fetch_from_mediastack_api, search_query, mediastack_key),
        ("GNews.io", "gnews_io", fetch_from_gnews_io, search_query, gnews_key),
        ("NewsData.io", "newsdata_io", fetch_from_newsdata_io, search_query, newsdata_key),
        ("WorldNewsAPI", "worldnews_api", fetch_from_worldnews_api, search_query, worldnews_key)
    ]

    if enabled_providers:
        tasks = [t for t in tasks if t[1] in enabled_providers]

    aggregated = []
    telemetry = {
        "providers_queried": len(tasks),
        "providers_responding": 0,
        "total_fetched": 0,
        "query_time_ms": 0,
        "provider_details": {}
    }

    start_time = time.time()

    if search_query:
        # Query all 7 APIs simultaneously using multithreading
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            future_map = {executor.submit(fn, q, k, 6): (name, pid, time.time()) for name, pid, fn, q, k in tasks if k}
            try:
                for future in as_completed(future_map, timeout=4.5):
                    name, pid, st = future_map[future]
                    elapsed = int((time.time() - st) * 1000)
                    try:
                        results = future.result() or []
                        if results:
                            telemetry["providers_responding"] += 1
                            aggregated.extend(results)
                        telemetry["provider_details"][pid] = {
                            "name": name,
                            "status": "online" if results else "no_results",
                            "latency_ms": elapsed,
                            "articles_found": len(results)
                        }
                    except Exception as err:
                        telemetry["provider_details"][pid] = {
                            "name": name,
                            "status": f"error: {str(err)[:20]}",
                            "latency_ms": elapsed,
                            "articles_found": 0
                        }
            except Exception:
                pass

    telemetry["query_time_ms"] = int((time.time() - start_time) * 1000)
    telemetry["total_fetched"] = len(aggregated)

    # Deduplicate articles based on title snippet
    seen = set()
    unique_articles = []
    for a in aggregated:
        snippet = re.sub(r'[^\w\s]', '', a.get("title", "").lower())[:45]
        if snippet and snippet not in seen:
            seen.add(snippet)
            unique_articles.append(a)

    # If all APIs returned 0, use local dataset fallback
    is_fallback = False
    if not unique_articles:
        is_fallback = True
        unique_articles = fetch_from_local_dataset(search_terms=topic_words, max_results=max_results)

    telemetry["is_fallback"] = is_fallback
    telemetry["unique_count"] = len(unique_articles)

    return unique_articles[:max_results], telemetry
