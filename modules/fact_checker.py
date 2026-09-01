"""
Module 4: Numbers & Facts Checker
---------------------------------
WHAT THIS FILE DOES (Simple 1-Sentence Explanation):
This file checks whether prices, quantities, and dates in the user's claim
match the real numbers reported in the news articles (e.g. $50B vs $5B).

HOW IT WORKS:
1. Extracts numbers and currency from the user's headline ($50 billion, 25 bps).
2. Looks for those exact numbers in the news articles.
3. If an article reports a different price/amount for the same story, it flags a discrepancy (-35 point penalty).
"""

import re
from typing import Dict, List, Any, Tuple
from modules.keyword_extractor import extract_numbers_and_units, extract_dates_and_timeframes


def parse_numeric_with_unit(token: str) -> Tuple[float, str]:
    """Helper: Converts words like '$50 billion' into the number 50,000,000,000 and unit 'currency'."""
    clean = token.lower().replace(",", "").strip()

    # Detect unit type
    if any(c in clean for c in ['$', '€', '£', 'dollar', 'usd', 'eur', 'gbp', 'inr']):
        unit_type = 'currency'
    elif any(c in clean for c in ['percent', '%']):
        unit_type = 'percentage'
    elif any(c in clean for c in ['basis point', 'bps']):
        unit_type = 'basis_points'
    else:
        unit_type = 'count'

    match = re.search(r'(\d+(?:\.\d+)?)', clean)
    if not match:
        return -1.0, unit_type

    num = float(match.group(1))

    if "trillion" in clean:
        magnitude = num * 1_000_000_000_000
    elif "billion" in clean or clean.endswith("b"):
        magnitude = num * 1_000_000_000
    elif "million" in clean or clean.endswith("m"):
        magnitude = num * 1_000_000
    elif "thousand" in clean or clean.endswith("k"):
        magnitude = num * 1_000
    else:
        magnitude = num

    return magnitude, unit_type


def check_fact_conflicts(headline: str, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Main function: Checks numbers and dates in the headline against the articles.
    Returns: A summary dictionary with verified facts and detected conflicts.
    """
    headline_numbers = extract_numbers_and_units(headline)
    headline_dates = extract_dates_and_timeframes(headline)

    findings: List[str] = []
    audit_matrix: List[Dict[str, Any]] = []
    has_conflicts = False
    has_agreements = False

    # If the headline has no numbers or dates to check
    if not headline_numbers and not headline_dates:
        findings.append("The headline makes qualitative claims without specific numbers or dates to cross-verify.")
        return {
            "conflicts_found": False,
            "agreements_found": False,
            "details": findings,
            "audit_matrix": [],
            "headline_numbers": [],
            "headline_dates": [],
            "conflict_count": 0,
            "agreement_count": 0
        }

    # Filter to articles that actually match the story
    relevant_articles = [a for a in articles if a.get("similarity_score", 0.0) >= 0.30]

    if not relevant_articles:
        findings.append("No closely matching news coverage found to cross-reference these specific facts against.")
        return {
            "conflicts_found": False,
            "agreements_found": False,
            "details": findings,
            "audit_matrix": [],
            "headline_numbers": headline_numbers,
            "headline_dates": headline_dates,
            "conflict_count": 0,
            "agreement_count": 0
        }

    # Step: Check each number in the headline against the articles
    for num_str in headline_numbers:
        val, unit = parse_numeric_with_unit(num_str)
        matched = False
        conflict = False
        matched_source = ""
        conflict_source = ""
        conflict_val = ""

        clean_num = num_str.lower().strip('.,')

        for article in relevant_articles[:6]:
            content = f"{article.get('title', '')} {article.get('text', '')}".lower()
            source = article.get("source", "News Source")

            # Check if exact number appears in the article
            if clean_num in content:
                matched = True
                matched_source = source
                findings.append(f"Verified fact: '{num_str}' is confirmed by {source}.")
                break

            # If currency is distorted (e.g. claim said $50B, but news said $5B)
            if unit == 'currency' and val >= 1_000_000:
                art_numbers = extract_numbers_and_units(content)
                for a_num in art_numbers:
                    a_val, a_unit = parse_numeric_with_unit(a_num)
                    if a_unit == 'currency' and a_val >= 1_000_000:
                        diff_ratio = abs(val - a_val) / max(val, a_val)
                        if diff_ratio >= 0.50:
                            conflict = True
                            conflict_source = source
                            conflict_val = a_num
                            findings.append(f"Discrepancy detected: Claim cited '{num_str}', but {source} reported '{a_num}'.")
                            break
            if conflict:
                break

        if matched:
            has_agreements = True
            audit_matrix.append({
                "fact_type": "Number / Amount",
                "claim_fact": num_str,
                "status": "verified",
                "source": matched_source,
                "source_fact": num_str,
                "explanation": f"Matches reported figure in {matched_source}."
            })
        elif conflict:
            has_conflicts = True
            audit_matrix.append({
                "fact_type": "Number / Amount",
                "claim_fact": num_str,
                "status": "conflict",
                "source": conflict_source,
                "source_fact": conflict_val,
                "explanation": f"Differs from figure reported by {conflict_source}."
            })

    return {
        "conflicts_found": has_conflicts,
        "agreements_found": has_agreements,
        "details": findings,
        "audit_matrix": audit_matrix,
        "headline_numbers": headline_numbers,
        "headline_dates": headline_dates,
        "conflict_count": len([m for m in audit_matrix if m["status"] == "conflict"]),
        "agreement_count": len([m for m in audit_matrix if m["status"] == "verified"])
    }
