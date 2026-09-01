"""
Fact-Conflict & Consistency Checker Module

This module checks whether specific quantitative facts (such as numbers, monetary values,
percentages, and dates) in the user's headline actually agree with or contradict
the facts reported in matching news coverage.

Why this matters: A headline might share 90% of its words with real news articles,
but falsely exaggerate a number (e.g. claiming '$50 billion' instead of '$5 billion').
This module catches those critical discrepancies and outputs a structured Claim vs. Reality matrix.
"""

import re
from typing import Dict, List, Any
from modules.keyword_extractor import extract_numbers_and_units, extract_dates_and_timeframes


def parse_numeric_value(token: str) -> float:
    """
    Extracts a raw numeric float value from a text string, normalizing units like million/billion.
    """
    clean_token = token.lower().replace(",", "").replace("$", "").replace("€", "").replace("£", "").strip()

    number_match = re.search(r'(\d+(?:\.\d+)?)', clean_token)
    if not number_match:
        return -1.0

    base_number = float(number_match.group(1))

    if "trillion" in clean_token:
        return base_number * 1_000_000_000_000
    elif "billion" in clean_token or clean_token.endswith("b"):
        return base_number * 1_000_000_000
    elif "million" in clean_token or clean_token.endswith("m"):
        return base_number * 1_000_000
    elif "thousand" in clean_token or clean_token.endswith("k"):
        return base_number * 1_000

    return base_number


def check_fact_conflicts(headline: str, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compares facts in the headline against facts in top matching news articles.
    Generates plain-English findings and a structured Claim vs. Reality Audit Matrix.
    """
    headline_numbers = extract_numbers_and_units(headline)
    headline_dates = extract_dates_and_timeframes(headline)

    finding_details: List[str] = []
    audit_matrix: List[Dict[str, Any]] = []
    has_conflicts = False
    has_agreements = False
    conflict_count = 0
    agreement_count = 0

    if not headline_numbers and not headline_dates:
        finding_details.append(
            "The headline makes qualitative claims without specific numbers or dates to cross-verify."
        )
        return {
            "conflicts_found": False,
            "agreements_found": False,
            "details": finding_details,
            "audit_matrix": audit_matrix,
            "headline_numbers": [],
            "headline_dates": [],
            "conflict_count": 0,
            "agreement_count": 0
        }

    # Filter to articles that have reasonable similarity
    relevant_articles = [
        article for article in articles
        if article.get("similarity_score", 0.0) >= 0.10
    ]

    if not relevant_articles:
        finding_details.append(
            "No closely matching news coverage found to cross-reference these specific facts against."
        )
        for num in headline_numbers:
            audit_matrix.append({
                "fact_type": "Number / Amount",
                "claim_fact": num,
                "status": "unconfirmed",
                "source": "No matching wire",
                "source_fact": "N/A",
                "explanation": "No relevant coverage located to verify this figure."
            })
        for dt in headline_dates:
            audit_matrix.append({
                "fact_type": "Date / Timeframe",
                "claim_fact": dt,
                "status": "unconfirmed",
                "source": "No matching wire",
                "source_fact": "N/A",
                "explanation": "No relevant coverage located to verify this timeframe."
            })
        return {
            "conflicts_found": False,
            "agreements_found": False,
            "details": finding_details,
            "audit_matrix": audit_matrix,
            "headline_numbers": headline_numbers,
            "headline_dates": headline_dates,
            "conflict_count": 0,
            "agreement_count": 0
        }

    # Check numerical facts
    for headline_num_str in headline_numbers:
        headline_val = parse_numeric_value(headline_num_str)
        matched_in_any_source = False
        conflicting_in_source = False
        conflict_source = ""
        conflict_val_str = ""
        matched_source = ""

        for article in relevant_articles[:6]:
            article_content = f"{article.get('title', '')} {article.get('text', '')}"
            article_numbers = extract_numbers_and_units(article_content)
            source_name = article.get("source", "News Source")

            # Check if identical number string or parsed magnitude appears
            if headline_num_str.lower() in article_content.lower():
                matched_in_any_source = True
                matched_source = source_name
                agreement_count += 1
                finding_details.append(
                    f"Verified fact: '{headline_num_str}' is directly corroborated by {source_name}."
                )
                break

            # Look for conflicting numerical figures
            for art_num_str in article_numbers:
                art_val = parse_numeric_value(art_num_str)
                if headline_val > 0 and art_val > 0:
                    discrepancy_ratio = abs(headline_val - art_val) / max(headline_val, art_val)
                    if 0.15 < discrepancy_ratio < 1000:
                        conflicting_in_source = True
                        conflict_source = source_name
                        conflict_val_str = art_num_str
                        conflict_count += 1
                        finding_details.append(
                            f"Discrepancy detected: Headline claims '{headline_num_str}', but {source_name} reported '{art_num_str}'."
                        )
                        break
            if conflicting_in_source:
                break

        if matched_in_any_source:
            has_agreements = True
            audit_matrix.append({
                "fact_type": "Number / Amount",
                "claim_fact": headline_num_str,
                "status": "verified",
                "source": matched_source,
                "source_fact": headline_num_str,
                "explanation": f"Matches reported figure in {matched_source}."
            })
        elif conflicting_in_source:
            has_conflicts = True
            audit_matrix.append({
                "fact_type": "Number / Amount",
                "claim_fact": headline_num_str,
                "status": "conflict",
                "source": conflict_source,
                "source_fact": conflict_val_str,
                "explanation": f"Distortion: Claim cited {headline_num_str}, but reports show {conflict_val_str}."
            })
        else:
            audit_matrix.append({
                "fact_type": "Number / Amount",
                "claim_fact": headline_num_str,
                "status": "unconfirmed",
                "source": "Coverage Found",
                "source_fact": "Unspecified",
                "explanation": "General topic covered, but exact figure is unconfirmed in wire snippets."
            })

    # Check dates / timeframes
    for headline_date_str in headline_dates:
        matched_date = False
        matched_source = ""
        for article in relevant_articles[:6]:
            article_content = f"{article.get('title', '')} {article.get('text', '')}"
            source_name = article.get("source", "News Source")
            if headline_date_str.lower() in article_content.lower():
                matched_date = True
                matched_source = source_name
                agreement_count += 1
                finding_details.append(
                    f"Verified timeframe: '{headline_date_str}' matches coverage in {source_name}."
                )
                break

        if matched_date:
            has_agreements = True
            audit_matrix.append({
                "fact_type": "Date / Timeframe",
                "claim_fact": headline_date_str,
                "status": "verified",
                "source": matched_source,
                "source_fact": headline_date_str,
                "explanation": f"Timeframe corroborated by {matched_source}."
            })
        else:
            audit_matrix.append({
                "fact_type": "Date / Timeframe",
                "claim_fact": headline_date_str,
                "status": "unconfirmed",
                "source": "Coverage Found",
                "source_fact": "Unspecified",
                "explanation": "Topic confirmed; specific date/timeframe not explicit in summary snippets."
            })

    if not has_conflicts and not has_agreements:
        finding_details.append(
            "Relevant coverage found on the overall topic, though specific quantitative figures could not be independently confirmed or denied."
        )

    return {
        "conflicts_found": has_conflicts,
        "agreements_found": has_agreements,
        "details": finding_details,
        "audit_matrix": audit_matrix,
        "headline_numbers": headline_numbers,
        "headline_dates": headline_dates,
        "conflict_count": conflict_count,
        "agreement_count": agreement_count
    }
