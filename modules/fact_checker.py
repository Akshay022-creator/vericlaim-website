"""
Fact-Conflict & Quantitative Consistency Checker Module
--------------------------------------------------------
PURPOSE:
Compares numbers, currency values, and percentages between the claim and news articles.
- High-confidence discrepancy detection: Catches exaggerated amounts (e.g. $50B vs $5B).
- Avoids false conflicts on different metrics (e.g. interest rate cuts vs inflation targets).
- Provides a clean Claim vs Reality Audit Matrix.
"""

import re
from typing import Dict, List, Any, Tuple
from modules.keyword_extractor import extract_numbers_and_units, extract_dates_and_timeframes


def parse_numeric_with_unit(token: str) -> Tuple[float, str]:
    """
    Extracts numerical value and standardized unit category.
    """
    clean = token.lower().replace(",", "").strip()

    # Determine Category
    if any(c in clean for c in ['$', '€', '£', 'dollar', 'usd', 'eur', 'gbp', 'inr']):
        unit_type = 'currency'
    elif any(c in clean for c in ['percent', '%', 'percentage']):
        unit_type = 'percentage'
    elif any(c in clean for c in ['basis point', 'bps']):
        unit_type = 'basis_points'
    elif any(c in clean for c in ['year', 'month', 'day', 'hour', 'minute', 'decade']):
        unit_type = 'time'
    else:
        unit_type = 'count'

    number_match = re.search(r'(\d+(?:\.\d+)?)', clean)
    if not number_match:
        return -1.0, unit_type

    base_number = float(number_match.group(1))

    if "trillion" in clean:
        magnitude = base_number * 1_000_000_000_000
    elif "billion" in clean or clean.endswith("b"):
        magnitude = base_number * 1_000_000_000
    elif "million" in clean or clean.endswith("m"):
        magnitude = base_number * 1_000_000
    elif "thousand" in clean or clean.endswith("k"):
        magnitude = base_number * 1_000
    else:
        magnitude = base_number

    return magnitude, unit_type


def check_fact_conflicts(headline: str, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compares facts in the headline against facts in matching news articles.
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

    # Filter to articles that have genuine similarity
    relevant_articles = [
        article for article in articles
        if article.get("similarity_score", 0.0) >= 0.30
    ]

    if not relevant_articles:
        finding_details.append(
            "No closely matching news coverage found to cross-reference these specific facts against."
        )
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

    for headline_num_str in headline_numbers:
        headline_val, headline_unit = parse_numeric_with_unit(headline_num_str)
        matched_in_any_source = False
        conflicting_in_source = False
        conflict_source = ""
        conflict_val_str = ""
        matched_source = ""

        clean_hl_num = headline_num_str.lower().strip('.,')

        for article in relevant_articles[:6]:
            article_content = f"{article.get('title', '')} {article.get('text', '')}"
            source_name = article.get("source", "News Source")

            # Check direct textual presence of the exact number/percentage
            if clean_hl_num in article_content.lower():
                matched_in_any_source = True
                matched_source = source_name
                agreement_count += 1
                finding_details.append(
                    f"Verified fact: '{headline_num_str}' is confirmed by {source_name}."
                )
                break

            # For large currency amounts (e.g. $50 billion vs $5 billion), detect magnitude distortions
            if headline_unit == 'currency' and headline_val >= 1_000_000:
                art_numbers = extract_numbers_and_units(article_content)
                for art_num in art_numbers:
                    art_val, art_unit = parse_numeric_with_unit(art_num)
                    if art_unit == 'currency' and art_val >= 1_000_000:
                        discrepancy_ratio = abs(headline_val - art_val) / max(headline_val, art_val)
                        if discrepancy_ratio >= 0.50:
                            conflicting_in_source = True
                            conflict_source = source_name
                            conflict_val_str = art_num
                            conflict_count += 1
                            finding_details.append(
                                f"Discrepancy detected: Claim cited '{headline_num_str}', but {source_name} reported '{art_num}'."
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

    return {
        "conflicts_found": has_conflicts,
        "agreements_found": has_agreements,
        "details": finding_details if finding_details else ["Facts checked against news reporting."],
        "audit_matrix": audit_matrix,
        "headline_numbers": headline_numbers,
        "headline_dates": headline_dates,
        "conflict_count": conflict_count,
        "agreement_count": agreement_count
    }
