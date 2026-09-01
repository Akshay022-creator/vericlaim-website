"""
Module 5: 0 to 100 Truth Score Calculator
-----------------------------------------
WHAT THIS FILE DOES (Simple 1-Sentence Explanation):
This file calculates the final 0 to 100 Truth Score and gives a plain-English explanation.

THE 4-PART SCORING FORMULA:
1. Story Match (Up to 45 pts): How closely the news topic matches the claim.
2. Independent Sources (Up to 35 pts): More major newsrooms covering it = higher trust.
3. Consistency (Up to 20 pts): How consistently the outlets report the same facts.
4. Fact Adjustment (+10 pts / -35 pts): Bonus for matching numbers, penalty for distorted facts.

VERDICTS:
- 75 to 100: Verified True 🟢
- 50 to 74:  Partially True 🟡
- 25 to 49:  Unverified 🟠
- 0 to 24:   False / Misleading 🔴
"""

from typing import List, Dict, Any


def compute_corroboration_score(
    similarity_results: List[Dict[str, Any]],
    fact_check_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Main function: Combines all matching articles and facts into a 0-100 score.
    """
    # Guard: If no articles found at all
    if not similarity_results:
        return {
            "score": 0,
            "category": "False / Misleading",
            "explanation": "No matching news reports were found across any major news agency.",
            "match_count": 0,
            "distinct_sources": [],
            "debunked": False
        }

    # Check 1: Role Contradiction (e.g. 'Modi is PM of Pakistan' -> 0/100 False)
    contradictions = [a for a in similarity_results if a.get("stance") == "contradicting"]
    if contradictions:
        src = contradictions[0].get("source", "News Source")
        reason = contradictions[0].get("stance_reason", "Reporting contradicts this claim.")
        return {
            "score": 0,
            "category": "False / Contradicted",
            "explanation": f"⚠️ Fact Contradiction ({src}): {reason}",
            "match_count": 0,
            "distinct_sources": [src],
            "debunked": True
        }

    # Check 2: Professional Fact-Check Debunk (e.g. 'Reuters Fact Check' -> 0/100 False)
    debunks = [a for a in similarity_results if a.get("stance") == "debunking" and a.get("similarity_score", 0.0) >= 0.30]
    if debunks:
        src = debunks[0].get("source", "Fact-Checker")
        title = debunks[0].get("title", "")
        return {
            "score": 0,
            "category": "Debunked False",
            "explanation": f"⚠️ Actively Debunked: {src} published a fact-check refuting this claim ('{title}').",
            "match_count": len(debunks),
            "distinct_sources": [src],
            "debunked": True
        }

    # Check 3: Filter genuinely matching articles (similarity >= 0.28)
    matching_articles = [
        a for a in similarity_results
        if a.get("similarity_score", 0.0) >= 0.28 and a.get("stance") not in ["debunking", "contradicting"]
    ]

    top_match = matching_articles[0].get("similarity_score", 0.0) if matching_articles else 0.0
    confirming_sources = list({a.get("source") for a in matching_articles if a.get("source")})

    # If top match is weak (< 0.25), the story was never reported
    if top_match < 0.25 or not matching_articles:
        return {
            "score": int(top_match * 30),
            "category": "False / Misleading",
            "explanation": "No major news outlets have reported this story.",
            "match_count": 0,
            "distinct_sources": [],
            "debunked": False
        }

    # --- SCORE CALCULATION ---
    # 1. Story Match Points (Up to 45 pts)
    match_points = min(45.0, top_match * 55.0)

    # 2. Source Count Points (Up to 35 pts)
    source_count = len(confirming_sources)
    source_points = 35.0 if source_count >= 3 else (25.0 if source_count == 2 else 15.0)

    # 3. Consistency Points (Up to 20 pts)
    consistency_points = min(20.0, top_match * 20.0)

    # 4. Fact-check Modifier (+10 pts or -35 pts)
    fact_modifier = 0.0
    if fact_check_result.get("conflicts_found"):
        fact_modifier = -35.0
    elif fact_check_result.get("agreements_found"):
        fact_modifier = 10.0

    # Calculate total
    total = match_points + source_points + consistency_points + fact_modifier
    final_score = int(max(0, min(100, round(total))))

    # Assign category
    if final_score >= 75:
        category = "Verified True"
        summary = "Confirmed by multiple trusted news outlets."
    elif final_score >= 50:
        category = "Partially True"
        summary = "Related news was found, but some details or full confirmation are limited."
    elif final_score >= 25:
        category = "Unverified"
        summary = "Minimal news coverage found to support this claim."
    else:
        category = "False / Misleading"
        summary = "This claim lacks verified news coverage."

    sources_str = ", ".join(confirming_sources[:3])
    explanation = f"{summary} Covered by {sources_str} with {int(top_match * 100)}% story match."

    fact_details = fact_check_result.get("details", [])
    if fact_details:
        explanation += " " + fact_details[0]

    return {
        "score": final_score,
        "category": category,
        "explanation": explanation,
        "match_count": len(matching_articles),
        "distinct_sources": confirming_sources,
        "debunked": False,
        "component_breakdown": {
            "similarity_points": round(match_points, 1),
            "coverage_points": round(source_points, 1),
            "depth_points": round(consistency_points, 1),
            "fact_modifier": round(fact_modifier, 1)
        }
    }
