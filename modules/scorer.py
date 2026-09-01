"""
Simple Score Calculator & Plain-English Explainer
------------------------------------------------
PURPOSE (Simple 30-Second Explanation):
This module takes the news articles found by our search and calculates a simple
Trust Score from 0 to 100 based on 3 simple questions:
1. Did major newsrooms report this exact story? (Up to 50 points)
2. How many different independent newsrooms reported it? (Up to 30 points)
3. Did the numbers/dates match what newsrooms published? (+10 bonus or -35 penalty if numbers are wrong)

Score Categories:
- 75 - 100: "Verified True" (Green)
- 50 - 74:  "Partially True" (Yellow)
- 25 - 49:  "Unverified" (Orange)
- 0 - 24:   "False / Misleading" (Red)
"""

from typing import List, Dict, Any


def compute_corroboration_score(
    similarity_results: List[Dict[str, Any]],
    fact_check_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculates a simple 0-100 Trust Score and a plain-English explanation.
    """
    # If no news articles were found at all
    if not similarity_results:
        return {
            "score": 0,
            "category": "Unverified (No News Found)",
            "explanation": (
                "No matching reports were found in any major news outlet. "
                "This claim appears to be unverified or fabricated."
            ),
            "match_count": 0,
            "distinct_sources": [],
            "component_breakdown": {
                "similarity_points": 0,
                "coverage_points": 0,
                "depth_points": 0,
                "fact_modifier": 0
            }
        }

    # Find articles that actually talk about the topic
    matching_articles = [
        art for art in similarity_results
        if art.get("similarity_score", 0.0) >= 0.15
    ]

    top_match = similarity_results[0].get("similarity_score", 0.0) if similarity_results else 0.0

    # List of unique news outlets found
    unique_sources = list({
        art.get("source", "Unknown")
        for art in matching_articles
        if art.get("source")
    })

    # Step 1: Story Match Quality (Up to 50 points)
    story_match_points = min(50.0, top_match * 70.0)

    # Step 2: Number of Outlets Covering It (Up to 30 points)
    source_count = len(unique_sources)
    if source_count >= 3:
        source_points = 30.0
    elif source_count == 2:
        source_points = 20.0
    elif source_count == 1:
        source_points = 12.0
    else:
        source_points = 0.0

    # Step 3: Consistency Bonus (Up to 20 points)
    consistency_points = 20.0 if top_match >= 0.35 else (top_match * 30.0)

    # Step 4: Fact Check Adjustment (+10 for verified numbers, -35 for wrong numbers)
    fact_modifier = 0.0
    has_conflicts = fact_check_result.get("conflicts_found", False)
    has_agreements = fact_check_result.get("agreements_found", False)

    if has_conflicts:
        fact_modifier = -35.0  # Big penalty if numbers are exaggerated or wrong
    elif has_agreements:
        fact_modifier = 10.0   # Bonus if numbers match perfectly

    # Calculate final total
    total_raw = story_match_points + source_points + consistency_points + fact_modifier
    final_score = int(max(0, min(100, round(total_raw))))

    # Simple, clear status names
    if final_score >= 75:
        category = "Verified True"
        summary = "Confirmed by multiple trusted news outlets."
    elif final_score >= 50:
        category = "Partially True"
        summary = "Related news was found, but some details or context may be missing."
    elif final_score >= 25:
        category = "Unverified"
        summary = "Very little news coverage found to support this claim."
    else:
        category = "False / Misleading"
        summary = "This claim contradicts verified reporting or has zero supporting coverage."

    # Simple explanation sentence
    if unique_sources:
        sources_str = ", ".join(unique_sources[:3])
        if len(unique_sources) > 3:
            sources_str += f", and {len(unique_sources) - 3} more"
        narrative = f"{summary} Covered by {sources_str} with {int(top_match * 100)}% story match."
    else:
        narrative = summary

    # Append simple fact notes if available
    fact_details = fact_check_result.get("details", [])
    if fact_details:
        narrative += " " + fact_details[0]

    return {
        "score": final_score,
        "category": category,
        "explanation": narrative,
        "match_count": len(matching_articles),
        "distinct_sources": unique_sources,
        "component_breakdown": {
            "similarity_points": round(story_match_points, 1),
            "coverage_points": round(source_points, 1),
            "depth_points": round(consistency_points, 1),
            "fact_modifier": round(fact_modifier, 1)
        }
    }
