"""
Accurate & Calibrated Trust Score Calculator
--------------------------------------------
PURPOSE:
Accurately scores news claims from 0 to 100 while eliminating false positives
on fabricated claims (e.g. "Elon Musk buys Google" -> 0 to 15 / 100 False).

Scoring Rules:
1. Genuine Match Gate: An article only counts as supporting if similarity >= 0.40.
2. Low Top Match Cap:
   - Top match < 0.25 -> Score strictly capped at 0 - 15 (False / Misleading).
   - Top match < 0.45 -> Score strictly capped at 20 - 35 (Unverified).
3. Verified True requires:
   - High top match (>= 0.55) AND confirmed across 2+ independent outlets.
"""

from typing import List, Dict, Any


def compute_corroboration_score(
    similarity_results: List[Dict[str, Any]],
    fact_check_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculates an accurate, calibrated 0-100 Trust Score and a plain-English explanation.
    """
    # Guard: If no news articles were found at all
    if not similarity_results:
        return {
            "score": 0,
            "category": "False / Misleading",
            "explanation": (
                "No matching news reports were found across any major news agency. "
                "This claim lacks any verified reporting to support it."
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

    top_match = similarity_results[0].get("similarity_score", 0.0) if similarity_results else 0.0

    # ONLY count articles that actually match the story (similarity >= 0.35)
    genuinely_matching_articles = [
        art for art in similarity_results
        if art.get("similarity_score", 0.0) >= 0.35
    ]

    # Collect distinct news outlets that actually confirm the story
    confirming_sources = list({
        art.get("source", "Unknown")
        for art in genuinely_matching_articles
        if art.get("source")
    })

    # Strict false-positive guard:
    # If the top article similarity is very weak (< 0.25), this story was NOT reported.
    if top_match < 0.25 or not genuinely_matching_articles:
        return {
            "score": int(top_match * 30),  # Max 0 - 8 pts
            "category": "False / Misleading",
            "explanation": (
                "No major news outlets have reported this story. "
                "The retrieved articles only mention related individuals or general background, "
                "with zero confirmation of this specific claim."
            ),
            "match_count": 0,
            "distinct_sources": [],
            "component_breakdown": {
                "similarity_points": round(top_match * 20, 1),
                "coverage_points": 0,
                "depth_points": 0,
                "fact_modifier": 0
            }
        }

    # Step 1: Story Match Quality (Up to 45 points)
    story_match_points = min(45.0, top_match * 55.0)

    # Step 2: Number of Outlets Genuinely Confirming (Up to 35 points)
    source_count = len(confirming_sources)
    if source_count >= 3:
        source_points = 35.0
    elif source_count == 2:
        source_points = 25.0
    elif source_count == 1:
        source_points = 15.0
    else:
        source_points = 0.0

    # Step 3: Match Consistency (Up to 20 points)
    if len(genuinely_matching_articles) >= 2:
        avg_top = sum(a.get("similarity_score", 0.0) for a in genuinely_matching_articles[:3]) / min(3, len(genuinely_matching_articles))
        consistency_points = min(20.0, avg_top * 22.0)
    else:
        consistency_points = top_match * 10.0

    # Step 4: Fact Check Adjustment (+10 for verified numbers, -35 for wrong numbers)
    fact_modifier = 0.0
    has_conflicts = fact_check_result.get("conflicts_found", False)
    has_agreements = fact_check_result.get("agreements_found", False)

    if has_conflicts:
        fact_modifier = -35.0
    elif has_agreements:
        fact_modifier = 10.0

    # Calculate final total
    total_raw = story_match_points + source_points + consistency_points + fact_modifier

    # Cap scores if top match is only moderate
    if top_match < 0.40:
        final_score = int(min(35, max(0, round(total_raw))))
    elif top_match < 0.55 and source_count < 2:
        final_score = int(min(55, max(0, round(total_raw))))
    else:
        final_score = int(max(0, min(100, round(total_raw))))

    # Simple, clear status names
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
        summary = "This claim contradicts verified reporting or has zero supporting coverage."

    # Construct clean narrative explanation
    if confirming_sources:
        sources_str = ", ".join(confirming_sources[:3])
        if len(confirming_sources) > 3:
            sources_str += f", and {len(confirming_sources) - 3} more"
        narrative = f"{summary} Covered by {sources_str} with {int(top_match * 100)}% story match."
    else:
        narrative = summary

    fact_details = fact_check_result.get("details", [])
    if fact_details:
        narrative += " " + fact_details[0]

    return {
        "score": final_score,
        "category": category,
        "explanation": narrative,
        "match_count": len(genuinely_matching_articles),
        "distinct_sources": confirming_sources,
        "component_breakdown": {
            "similarity_points": round(story_match_points, 1),
            "coverage_points": round(source_points, 1),
            "depth_points": round(consistency_points, 1),
            "fact_modifier": round(fact_modifier, 1)
        }
    }
