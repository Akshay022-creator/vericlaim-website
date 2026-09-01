"""
7-Provider Real-Time News Cross-Verification Web Server & REST API

This lightweight web server serves the modern frontend interface and exposes a rich
JSON REST API for running the real-time cross-verification pipeline.
It aggregates live reporting across 7 global news providers:
1. The Guardian Open Platform
2. NewsAPI.org
3. Currents API
4. Mediastack API
5. GNews.io
6. NewsData.io
7. WorldNewsAPI.com
(with zero-dependency local dataset fallback)

Usage:
    python server.py
    or
    python web/server.py
    (Opens on http://localhost:8000)
"""

import sys
import os
import json
import time
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

# Add parent directory to path so modules can be imported
current_directory = Path(__file__).resolve().parent
if str(current_directory) not in sys.path:
    sys.path.insert(0, str(current_directory))
parent_directory = current_directory.parent
if str(parent_directory) not in sys.path:
    sys.path.insert(0, str(parent_directory))

from dotenv import load_dotenv
load_dotenv()

from modules.keyword_extractor import extract_keywords
from modules.news_fetcher import (
    fetch_related_articles,
    get_default_dataset_path,
    get_all_providers_status,
    PROVIDERS_CONFIG
)
from modules.similarity_engine import compute_similarity
from modules.fact_checker import check_fact_conflicts
from modules.scorer import compute_corroboration_score

# Sample curated trending presets
TRENDING_PRESETS = [
    {
        "category": "Tech & AI",
        "badge": "Technology",
        "headline": "Nvidia reports record revenue growth in AI data center chips",
        "description": "Examine live reporting on AI hardware earnings and market demand."
    },
    {
        "category": "Space & Science",
        "badge": "Science",
        "headline": "NASA successfully lands Artemis robotic rover on Moon south pole to search for water ice",
        "description": "Cross-reference lunar exploration and Artemis space missions."
    },
    {
        "category": "Economy & Finance",
        "badge": "Finance",
        "headline": "Federal Reserve cuts benchmark interest rate by 25 basis points to 4.50 percent",
        "description": "Verify central bank monetary policy decisions across global wires."
    },
    {
        "category": "Discrepancy Audit",
        "badge": "Conflict Test",
        "headline": "Alphabet announces $50 billion investment in renewable energy for data centers",
        "description": "Test fact-conflict detection on exaggerated investment figures ($50B vs $5B)."
    },
    {
        "category": "Global Health",
        "badge": "Health",
        "headline": "World Health Organization approves new universal malaria vaccine showing 85 percent efficacy",
        "description": "Verify clinical trials and global health organization approvals."
    },
    {
        "category": "Fabrication Test",
        "badge": "Debunk",
        "headline": "Scientists discover secret underground alien civilization beneath Antarctica ice sheet",
        "description": "Test uncorroborated conspiracy and fabricated viral claims."
    }
]


class HeadlineCheckerAPIHandler(SimpleHTTPRequestHandler):
    """HTTP request handler providing static file serving and JSON API endpoints."""

    def __init__(self, *args, **kwargs):
        # Serve static web assets from current directory (or web/ if in web directory)
        static_dir = Path(__file__).resolve().parent
        super().__init__(*args, directory=str(static_dir), **kwargs)

    def _send_json_response(self, data: dict, status_code: int = 200):
        """Sends a formatted JSON response with CORS headers."""
        try:
            response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(response_bytes)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests for static files and data API endpoints."""
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/api/health":
            providers = get_all_providers_status()
            self._send_json_response({
                "status": "healthy",
                "service": "VeriClaim 7-Provider Cross-Verification Engine",
                "active_providers_count": len([p for p in providers if p.get("configured")]),
                "providers": providers
            })
            return

        if parsed_url.path == "/api/providers":
            self._send_json_response({
                "providers": get_all_providers_status()
            })
            return

        if parsed_url.path == "/api/trending":
            self._send_json_response({
                "trending": TRENDING_PRESETS
            })
            return

        if parsed_url.path == "/api/dataset":
            csv_path = get_default_dataset_path()
            if csv_path.exists():
                import pandas as pd
                try:
                    dataset_df = pd.read_csv(csv_path)
                    articles_list = dataset_df.to_dict(orient="records")
                    self._send_json_response({"total": len(articles_list), "articles": articles_list})
                    return
                except Exception:
                    pass
            self._send_json_response({"total": 0, "articles": []})
            return

        # Default to standard static file serving (index.html, css, js)
        super().do_GET()

    def do_POST(self):
        """Handle POST requests for real-time headline verification."""
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/api/verify":
            content_length = int(self.headers.get("Content-Length", 0))
            request_body = self.rfile.read(content_length).decode("utf-8")

            try:
                payload = json.loads(request_body) if request_body else {}
                headline_text = payload.get("headline", "").strip()
                enabled_providers = payload.get("enabled_providers", None)
                custom_api_key = payload.get("api_key", "").strip() or None

                if not headline_text:
                    self._send_json_response({"error": "Headline text cannot be empty"}, status_code=400)
                    return

                pipeline_start = time.time()

                # Step 1: Extract keywords, numbers, dates
                keywords_data = extract_keywords(headline_text)

                # Step 2: Concurrently query all 7 news providers
                candidate_articles, telemetry = fetch_related_articles(
                    keywords_info=keywords_data,
                    max_results=16,
                    api_key=custom_api_key,
                    enabled_providers=enabled_providers
                )

                # Step 3: Compute hybrid TF-IDF similarity
                similarity_results = compute_similarity(headline_text, candidate_articles)

                # Step 4: Quantitative fact discrepancy check & audit matrix
                fact_check_result = check_fact_conflicts(headline_text, similarity_results)

                # Step 5: Composite corroboration scoring & narrative
                scoring_summary = compute_corroboration_score(similarity_results, fact_check_result)

                total_latency_ms = int((time.time() - pipeline_start) * 1000)
                telemetry["total_pipeline_time_ms"] = total_latency_ms

                # Construct rich response payload
                response_payload = {
                    "headline": headline_text,
                    "score": scoring_summary.get("score", 0),
                    "category": scoring_summary.get("category", "Unverified"),
                    "explanation": scoring_summary.get("explanation", ""),
                    "distinct_sources": scoring_summary.get("distinct_sources", []),
                    "component_breakdown": scoring_summary.get("component_breakdown", {}),
                    "keywords": keywords_data,
                    "fact_check": fact_check_result,
                    "articles": similarity_results,
                    "telemetry": telemetry,
                    "providers_summary": f"{telemetry.get('providers_responding', 0)} of {telemetry.get('providers_queried', 7)} Live News Providers responded in {telemetry.get('query_time_ms', 0)}ms"
                }

                self._send_json_response(response_payload)

            except Exception as execution_error:
                self._send_json_response({"error": str(execution_error)}, status_code=500)
            return

        if parsed_url.path == "/api/extract_url":
            content_length = int(self.headers.get("Content-Length", 0))
            request_body = self.rfile.read(content_length).decode("utf-8")

            try:
                import re
                import requests
                payload = json.loads(request_body) if request_body else {}
                target_url = payload.get("url", "").strip()

                if not target_url or not target_url.startswith(("http://", "https://")):
                    self._send_json_response({"error": "Please provide a valid web URL starting with http:// or https://"}, status_code=400)
                    return

                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                resp = requests.get(target_url, headers=headers, timeout=6)
                html_text = resp.text

                # Extract OpenGraph title or standard title tag
                og_title_match = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
                if not og_title_match:
                    og_title_match = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:title["\']', html_text, re.IGNORECASE)

                title_tag_match = re.search(r'<title[^>]*>([^<]+)</title>', html_text, re.IGNORECASE)

                if og_title_match:
                    raw_title = og_title_match.group(1).strip()
                elif title_tag_match:
                    raw_title = title_tag_match.group(1).strip()
                else:
                    raw_title = ""

                # Clean common suffixes like " | BBC News", " - The Guardian", " | Reuters"
                clean_title = re.sub(r'\s*[\-\|\–\—]\s*(?:BBC News|The Guardian|Reuters|CNN|The New York Times|Bloomberg|Daily Mail|Fox News|NDTV|TechCrunch).*$', '', raw_title, flags=re.IGNORECASE).strip()

                # Extract description
                og_desc_match = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
                if not og_desc_match:
                    og_desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
                desc = og_desc_match.group(1).strip() if og_desc_match else ""

                domain = urlparse(target_url).netloc.replace("www.", "")

                self._send_json_response({
                    "url": target_url,
                    "title": clean_title if clean_title else raw_title,
                    "description": desc,
                    "source": domain.split(".")[0].capitalize() if domain else "Web Article",
                    "domain": domain
                })
            except Exception as extract_err:
                self._send_json_response({"error": f"Could not read article: {str(extract_err)}"}, status_code=500)
            return

        self.send_error(404, "Endpoint not found")


def start_server(port: int = 8000):
    """Starts the HTTP server on specified port."""
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, HeadlineCheckerAPIHandler)
    print("=" * 75)
    print("  VERICLAIM — 7-PROVIDER REAL-TIME NEWS CROSS-VERIFICATION SERVER")
    print(f"  * Website URL: http://localhost:{port}")
    print("  * Active News APIs: Guardian, NewsAPI, Currents, Mediastack, GNews, NewsData, WorldNews")
    print(f"  * REST API: http://localhost:{port}/api/verify")
    print("=" * 75)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()


if __name__ == "__main__":
    port_env = os.getenv("PORT", "").strip()
    if port_env and port_env.isdigit():
        port_arg = int(port_env)
    elif len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_arg = int(sys.argv[1])
    else:
        port_arg = 8000
    start_server(port_arg)
