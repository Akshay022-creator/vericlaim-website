"""
7-Provider Real-Time News Fetcher Module
(NewsAPI, The Guardian, Currents API, Mediastack, GNews, NewsData.io, WorldNewsAPI & Local Archive)

This module aggregates real-time news coverage concurrently across 7 global news APIs:
1. NewsAPI.org (Global news wire coverage)
2. The Guardian Open Platform (Global quality journalism)
3. Currents API (Fast global news aggregator)
4. Mediastack API (Live worldwide media data feed)
5. GNews.io (Fast real-time breaking news search)
6. NewsData.io (International & regional news)
7. WorldNewsAPI.com (Worldwide multilingual news coverage)
8. Local Verified News Dataset (Zero-dependency offline fallback)

All 7 providers are queried in parallel using ThreadPoolExecutor for sub-second latency
and robust multi-source cross-verification resilience.
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

# Load environment variables
load_dotenv()

# Active default 7 API keys
DEFAULT_KEYS = {
    "news_api": "6b0350e2801b499cbcecbed4e47b58af",
    "newsdata_io": "pub_6ddcccb1251442399feb9d515407eb0b",
    "gnews_io": "2144d15567584bbe3a36a582c25dcee3",
    "worldnews_api": "9ef63c5d9e87447291614b690dcd1b72",
    "guardian_api": "509a239d-5252-4a54-b7b2-dee3fc9cc066",
    "currents_api": "ZM9sIxYq_VrDdIDniDwAFYFEVe3f1HrGzsdLscgCpxjfknrs",
    "mediastack_api": "c909b318144464243727bb0feaf824e4"
}

# Provider Metadata Configuration
PROVIDERS_CONFIG = [
    {
        "id": "guardian_api",
        "name": "The Guardian",
        "badge": "Guardian",
        "color": "#052962",
        "textColor": "#ffffff",
        "type": "Quality Journalism Wire",
        "env_var": "GUARDIAN_API_KEY"
    },
    {
        "id": "news_api",
        "name": "NewsAPI.org",
        "badge": "NewsAPI",
        "color": "#2563eb",
        "textColor": "#ffffff",
        "type": "Global News Wire",
        "env_var": "NEWS_API_KEY"
    },
    {
        "id": "currents_api",
        "name": "Currents API",
        "badge": "Currents",
        "color": "#0d9488",
        "textColor": "#ffffff",
        "type": "Real-Time News Stream",
        "env_var": "CURRENTS_API_KEY"
    },
    {
        "id": "mediastack_api",
        "name": "Mediastack",
        "badge": "Mediastack",
        "color": "#e11d48",
        "textColor": "#ffffff",
        "type": "Global Media Feed",
        "env_var": "MEDIASTACK_API_KEY"
    },
    {
        "id": "gnews_io",
        "name": "GNews.io",
        "badge": "GNews",
        "color": "#7c3aed",
        "textColor": "#ffffff",
        "type": "Breaking News Search",
        "env_var": "GNEWS_API_KEY"
    },
    {
        "id": "newsdata_io",
        "name": "NewsData.io",
        "badge": "NewsData",
        "color": "#059669",
        "textColor": "#ffffff",
        "type": "Regional & Intl News",
        "env_var": "NEWSDATA_API_KEY"
    },
    {
        "id": "worldnews_api",
        "name": "WorldNewsAPI",
        "badge": "WorldNews",
        "color": "#d97706",
        "textColor": "#ffffff",
        "type": "Multilingual Global Wire",
        "env_var": "WORLDNEWS_API_KEY"
    }
]


def get_default_dataset_path() -> Path:
    """Locates the default news dataset CSV file."""
    current_module_directory = Path(__file__).resolve().parent
    dataset_file_path = current_module_directory.parent / "data" / "news_dataset.csv"
    return dataset_file_path


def get_all_providers_status() -> List[Dict[str, Any]]:
    """Returns list of all configured providers and their configuration status."""
    status_list = []
    for prov in PROVIDERS_CONFIG:
        env_val = os.getenv(prov["env_var"], "").strip()
        default_val = DEFAULT_KEYS.get(prov["id"], "")
        active_key = env_val or default_val
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
# PROVIDER 1: The Guardian Open Platform
# =============================================================================
def fetch_from_guardian_api(query_string: str, api_key: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """Queries The Guardian Open Platform API."""
    if not query_string or not api_key:
        return []

    url = "https://content.guardianapis.com/search"
    clean_query = " ".join(query_string.split()[:4])
    params = {
        "q": clean_query,
        "api-key": api_key,
        "show-fields": "headline,trailText,byline,publication",
        "page-size": min(max_results, 8),
        "order-by": "relevance"
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code != 200:
            return []

        data = response.json().get("response", {})
        results = data.get("results", [])
        standardized = []

        for item in results:
            fields = item.get("fields", {}) or {}
            title = fields.get("headline") or item.get("webTitle", "")
            if not title:
                continue

            trail = fields.get("trailText", "") or ""
            # Strip HTML tags from trail text
            clean_trail = re.sub(r'<[^>]+>', '', trail).strip()
            article_url = item.get("webUrl", "")
            pub_date = item.get("webPublicationDate", "")
            section = item.get("sectionName", "The Guardian")

            standardized.append({
                "title": title,
                "source": "The Guardian",
                "source_badge": "Guardian",
                "url": article_url,
                "text": clean_trail if clean_trail else title,
                "published_at": pub_date,
                "source_type": "The Guardian",
                "section": section
            })

        return standardized
    except Exception:
        return []


# =============================================================================
# PROVIDER 2: Currents API
# =============================================================================
def fetch_from_currents_api(query_string: str, api_key: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """Queries Currents API for real-time news."""
    if not query_string or not api_key:
        return []

    url = "https://api.currentsapi.services/v1/search"
    clean_query = " ".join(query_string.split()[:4])
    params = {
        "keywords": clean_query,
        "apiKey": api_key,
        "language": "en",
        "limit": min(max_results, 8)
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code != 200:
            return []

        data = response.json()
        news_items = data.get("news", [])
        standardized = []

        for item in news_items:
            title = item.get("title", "")
            if not title:
                continue

            author = item.get("author", "")
            source_name = author if author and len(author) < 25 and not author.startswith("http") else "Currents Wire"
            article_url = item.get("url", "")
            if article_url:
                try:
                    domain = urlparse(article_url).netloc.replace("www.", "")
                    if domain:
                        source_name = domain.split(".")[0].capitalize()
                except Exception:
                    pass

            desc = item.get("description", "") or ""
            pub_date = item.get("published", "")

            standardized.append({
                "title": title,
                "source": source_name,
                "source_badge": "Currents",
                "url": article_url,
                "text": desc if desc else title,
                "published_at": pub_date,
                "source_type": "Currents API"
            })

        return standardized
    except Exception:
        return []


# =============================================================================
# PROVIDER 3: Mediastack API
# =============================================================================
def fetch_from_mediastack_api(query_string: str, api_key: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """Queries Mediastack API for real-time global news feed."""
    if not query_string or not api_key:
        return []

    url = "http://api.mediastack.com/v1/news"
    clean_query = " ".join(query_string.split()[:4])
    params = {
        "access_key": api_key,
        "keywords": clean_query,
        "languages": "en",
        "limit": min(max_results, 8)
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code != 200:
            return []

        data = response.json()
        data_items = data.get("data", [])
        standardized = []

        for item in data_items:
            title = item.get("title", "")
            if not title:
                continue

            source_name = item.get("source", "") or "Mediastack Feed"
            article_url = item.get("url", "")
            desc = item.get("description", "") or ""
            pub_date = item.get("published_at", "")

            standardized.append({
                "title": title,
                "source": source_name,
                "source_badge": "Mediastack",
                "url": article_url,
                "text": desc if desc else title,
                "published_at": pub_date,
                "source_type": "Mediastack"
            })

        return standardized
    except Exception:
        return []


# =============================================================================
# PROVIDER 4: NewsAPI.org
# =============================================================================
def fetch_from_news_api(query_string: str, api_key: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """Queries NewsAPI.org for global news wire coverage."""
    if not query_string or not api_key:
        return []

    news_api_url = "https://newsapi.org/v2/everything"
    request_parameters = {
        "q": query_string,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": min(max_results, 10),
        "apiKey": api_key
    }
    request_headers = {
        "User-Agent": "VeriClaim-Checker/2.0 (Python News Client)"
    }

    try:
        response = requests.get(
            news_api_url,
            params=request_parameters,
            headers=request_headers,
            timeout=5
        )
        response_data = response.json()

        if response.status_code != 200 or response_data.get("status") != "ok":
            return []

        raw_articles = response_data.get("articles", [])
        standardized_articles = []

        for item in raw_articles:
            article_title = item.get("title", "")
            if not article_title or "[Removed]" in article_title:
                continue

            article_source_dict = item.get("source", {})
            article_source_name = article_source_dict.get("name", "NewsAPI Source") if isinstance(article_source_dict, dict) else "NewsAPI Source"
            article_description = item.get("description", "") or ""
            article_content = item.get("content", "") or ""
            article_url = item.get("url", "")
            published_timestamp = item.get("publishedAt", "")

            full_snippet = f"{article_description} {article_content}".strip()

            standardized_articles.append({
                "title": article_title,
                "source": article_source_name,
                "source_badge": "NewsAPI",
                "url": article_url,
                "text": full_snippet if full_snippet else article_title,
                "published_at": published_timestamp,
                "source_type": "NewsAPI.org"
            })

        return standardized_articles
    except Exception:
        return []


# =============================================================================
# PROVIDER 5: GNews.io
# =============================================================================
def fetch_from_gnews_io(query_string: str, api_key: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """Queries GNews.io for fast real-time breaking news."""
    if not query_string or not api_key:
        return []

    gnews_url = "https://gnews.io/api/v4/search"
    clean_query = " ".join(query_string.split()[:4])
    request_parameters = {
        "q": clean_query,
        "token": api_key,
        "lang": "en",
        "max": min(max_results, 8)
    }

    try:
        response = requests.get(gnews_url, params=request_parameters, timeout=5)
        response_data = response.json()

        if response.status_code != 200:
            return []

        raw_articles = response_data.get("articles", [])
        standardized_articles = []

        for item in raw_articles:
            article_title = item.get("title", "")
            if not article_title:
                continue

            article_source_dict = item.get("source", {})
            article_source_name = article_source_dict.get("name", "GNews Source") if isinstance(article_source_dict, dict) else "GNews Source"
            article_description = item.get("description", "") or ""
            article_content = item.get("content", "") or ""
            article_url = item.get("url", "")
            published_timestamp = item.get("publishedAt", "")

            full_snippet = f"{article_description} {article_content}".strip()

            standardized_articles.append({
                "title": article_title,
                "source": article_source_name,
                "source_badge": "GNews",
                "url": article_url,
                "text": full_snippet if full_snippet else article_title,
                "published_at": published_timestamp,
                "source_type": "GNews.io"
            })

        return standardized_articles
    except Exception:
        return []


# =============================================================================
# PROVIDER 6: NewsData.io
# =============================================================================
def fetch_from_newsdata_io(query_string: str, api_key: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """Queries NewsData.io for international and regional news."""
    if not query_string or not api_key:
        return []

    newsdata_url = "https://newsdata.io/api/1/news"
    clean_query = " ".join(query_string.split()[:4])
    request_parameters = {
        "apikey": api_key,
        "q": clean_query,
        "language": "en"
    }

    try:
        response = requests.get(newsdata_url, params=request_parameters, timeout=5)
        response_data = response.json()

        if response.status_code != 200 or response_data.get("status") != "success":
            return []

        raw_results = response_data.get("results", [])
        standardized_articles = []

        for item in raw_results:
            article_title = item.get("title", "")
            if not article_title:
                continue

            source_id = item.get("source_id", "NewsData Source")
            source_name = source_id.capitalize() if isinstance(source_id, str) else "NewsData Source"
            article_description = item.get("description", "") or ""
            article_content = item.get("content", "") or ""
            article_url = item.get("link", "")
            published_timestamp = item.get("pubDate", "")

            full_snippet = f"{article_description} {article_content}".strip()

            standardized_articles.append({
                "title": article_title,
                "source": source_name,
                "source_badge": "NewsData",
                "url": article_url,
                "text": full_snippet if full_snippet else article_title,
                "published_at": published_timestamp,
                "source_type": "NewsData.io"
            })

        return standardized_articles[:max_results]
    except Exception:
        return []


# =============================================================================
# PROVIDER 7: WorldNewsAPI.com
# =============================================================================
def fetch_from_worldnews_api(query_string: str, api_key: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """Queries WorldNewsAPI.com for worldwide news coverage."""
    if not query_string or not api_key:
        return []

    worldnews_url = "https://api.worldnewsapi.com/search-news"
    clean_query = " ".join(query_string.split()[:4])
    request_parameters = {
        "text": clean_query,
        "language": "en",
        "number": min(max_results, 8),
        "api-key": api_key
    }
    request_headers = {
        "x-api-key": api_key
    }

    try:
        response = requests.get(
            worldnews_url,
            params=request_parameters,
            headers=request_headers,
            timeout=5
        )
        response_data = response.json()

        if response.status_code != 200:
            return []

        raw_articles = response_data.get("news", [])
        standardized_articles = []

        for item in raw_articles:
            article_title = item.get("title", "")
            if not article_title:
                continue

            article_url = item.get("url", "")
            domain_name = "WorldNews Source"
            if article_url:
                try:
                    parsed_domain = urlparse(article_url).netloc
                    domain_name = parsed_domain.replace("www.", "").capitalize()
                except Exception:
                    domain_name = "WorldNews Source"

            article_text = item.get("text", "") or ""
            article_summary = item.get("summary", "") or ""
            published_timestamp = item.get("publish_date", "")

            full_snippet = f"{article_summary} {article_text}".strip()[:300]

            standardized_articles.append({
                "title": article_title,
                "source": domain_name,
                "source_badge": "WorldNews",
                "url": article_url,
                "text": full_snippet if full_snippet else article_title,
                "published_at": published_timestamp,
                "source_type": "WorldNewsAPI"
            })

        return standardized_articles
    except Exception:
        return []


# =============================================================================
# OFFLINE DATASET FALLBACK
# =============================================================================
def fetch_from_local_dataset(
    search_terms: List[str],
    dataset_path: Optional[Path] = None,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """Searches local verified CSV archive when live search returns zero results."""
    if dataset_path is None:
        dataset_path = get_default_dataset_path()

    if not dataset_path.exists():
        return []

    try:
        news_dataframe = pd.read_csv(dataset_path)
    except Exception:
        return []

    if news_dataframe.empty or not search_terms:
        sample_rows = news_dataframe.head(max_results)
        articles = []
        for _, row in sample_rows.iterrows():
            articles.append({
                "title": str(row.get("title", "")),
                "source": str(row.get("source", "Local Archive")),
                "source_badge": "Archive",
                "url": str(row.get("url", "")),
                "text": str(row.get("text", "")),
                "published_at": str(row.get("published_at", "")),
                "source_type": "Local Dataset (Offline Fallback)"
            })
        return articles

    scored_articles = []
    lower_search_terms = [term.lower() for term in search_terms if len(term) > 2]

    for _, row in news_dataframe.iterrows():
        article_title = str(row.get("title", ""))
        article_text = str(row.get("text", ""))
        combined_content = f"{article_title} {article_text}".lower()

        match_count = 0
        for term in lower_search_terms:
            if term in combined_content:
                match_count += 3 if term in article_title.lower() else 1

        if match_count > 0:
            scored_articles.append({
                "title": article_title,
                "source": str(row.get("source", "Local Archive")),
                "source_badge": "Archive",
                "url": str(row.get("url", "")),
                "text": article_text,
                "published_at": str(row.get("published_at", "")),
                "source_type": "Local Dataset (Offline Fallback)",
                "_match_score": match_count
            })

    scored_articles.sort(key=lambda item: item["_match_score"], reverse=True)

    final_results = []
    for article in scored_articles[:max_results]:
        article_copy = dict(article)
        article_copy.pop("_match_score", None)
        final_results.append(article_copy)

    return final_results


def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Removes duplicate articles across multiple news providers."""
    seen_titles = set()
    unique_articles = []

    for art in articles:
        title = art.get("title", "").strip().lower()
        clean_snippet = re.sub(r'[^\w\s]', '', title)[:45]
        if clean_snippet and clean_snippet not in seen_titles:
            seen_titles.add(clean_snippet)
            unique_articles.append(art)

    return unique_articles


# =============================================================================
# CONCURRENT 7-PROVIDER COORDINATOR
# =============================================================================
def fetch_related_articles(
    keywords_info: Dict[str, Any],
    max_results: int = 16,
    api_key: Optional[str] = None,
    enabled_providers: Optional[List[str]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Queries all 7 global news providers in parallel using ThreadPoolExecutor.
    Returns:
        (articles_list, telemetry_dict)
    """
    search_query = keywords_info.get("search_query", "")
    topic_words = keywords_info.get("topic_words", [])

    # Resolve active keys
    guardian_key = os.getenv("GUARDIAN_API_KEY", "").strip() or DEFAULT_KEYS["guardian_api"]
    currents_key = os.getenv("CURRENTS_API_KEY", "").strip() or DEFAULT_KEYS["currents_api"]
    mediastack_key = os.getenv("MEDIASTACK_API_KEY", "").strip() or DEFAULT_KEYS["mediastack_api"]
    news_key = api_key or os.getenv("NEWS_API_KEY", "").strip() or DEFAULT_KEYS["news_api"]
    gnews_key = os.getenv("GNEWS_API_KEY", "").strip() or DEFAULT_KEYS["gnews_io"]
    newsdata_key = os.getenv("NEWSDATA_API_KEY", "").strip() or DEFAULT_KEYS["newsdata_io"]
    worldnews_key = os.getenv("WORLDNEWS_API_KEY", "").strip() or DEFAULT_KEYS["worldnews_api"]

    # Provider tasks dictionary
    providers_tasks = [
        ("The Guardian", "guardian_api", fetch_from_guardian_api, search_query, guardian_key),
        ("NewsAPI.org", "news_api", fetch_from_news_api, search_query, news_key),
        ("Currents API", "currents_api", fetch_from_currents_api, search_query, currents_key),
        ("Mediastack", "mediastack_api", fetch_from_mediastack_api, search_query, mediastack_key),
        ("GNews.io", "gnews_io", fetch_from_gnews_io, search_query, gnews_key),
        ("NewsData.io", "newsdata_io", fetch_from_newsdata_io, search_query, newsdata_key),
        ("WorldNewsAPI", "worldnews_api", fetch_from_worldnews_api, search_query, worldnews_key)
    ]

    # Filter enabled if user selected specific providers
    if enabled_providers:
        providers_tasks = [task for task in providers_tasks if task[1] in enabled_providers]

    aggregated_articles: List[Dict[str, Any]] = []
    telemetry: Dict[str, Any] = {
        "providers_queried": len(providers_tasks),
        "providers_responding": 0,
        "total_fetched": 0,
        "query_time_ms": 0,
        "provider_details": {}
    }

    start_total_time = time.time()

    if search_query:
        # Launch concurrent execution
        with ThreadPoolExecutor(max_workers=len(providers_tasks)) as executor:
            future_to_provider = {}
            for name, pid, fetch_func, query, key in providers_tasks:
                if key:
                    start_t = time.time()
                    future = executor.submit(fetch_func, query, key, 6)
                    future_to_provider[future] = (name, pid, start_t)

            for future in as_completed(future_to_provider):
                name, pid, start_t = future_to_provider[future]
                elapsed_ms = int((time.time() - start_t) * 1000)
                try:
                    results = future.result() or []
                    if results:
                        telemetry["providers_responding"] += 1
                        aggregated_articles.extend(results)
                    telemetry["provider_details"][pid] = {
                        "name": name,
                        "status": "online" if results else "no_results",
                        "latency_ms": elapsed_ms,
                        "articles_found": len(results)
                    }
                except Exception as err:
                    telemetry["provider_details"][pid] = {
                        "name": name,
                        "status": f"error: {str(err)[:30]}",
                        "latency_ms": elapsed_ms,
                        "articles_found": 0
                    }

    total_time_ms = int((time.time() - start_total_time) * 1000)
    telemetry["query_time_ms"] = total_time_ms
    telemetry["total_fetched"] = len(aggregated_articles)

    # Deduplicate
    unique_articles = deduplicate_articles(aggregated_articles)

    # Fallback to local dataset if all live providers returned 0 articles
    is_fallback = False
    if not unique_articles:
        is_fallback = True
        unique_articles = fetch_from_local_dataset(search_terms=topic_words, max_results=max_results)

    telemetry["is_fallback"] = is_fallback
    telemetry["unique_count"] = len(unique_articles)

    return unique_articles[:max_results], telemetry
