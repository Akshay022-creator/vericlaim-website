"""
Corroboration Scorer & Plain-English Explainer Module

This module integrates the results from both the Similarity Engine and the Fact Checker
to compute a final Corroboration Score from 0 to 100. It translates complex statistical
and matching metrics into an easy-to-understand plain-English explanation that anyone can read.

Why this formula: Instead of an opaque black-box neural net, our scoring formula uses an
explainable multi-factor model mirroring real-world journalistic fact-checking practices:
1. Content Alignment (Top source similarity)
2. Breadth of Coverage (Number of independent publishers reporting on it)
3. Average High Match Depth (Consistency across top reporting outlets)
4. Factual Accuracy (Rewards confirmed numbers/dates, heavily penalizes contradictions)
"""

from typing import List, Dict, Any


def compute_corroboration_score(
    similarity_results: List[Dict[str, Any]],
    fact_check_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes a comprehensive Corroboration Score (0–100) and plain-English narrative.

    Think of this like a courtroom evaluation:
    - How many independent witnesses testified? (Source diversity)
    - How closely do their stories match? (TF-IDF Similarity)
    - Did the specific details and numbers add up? (Fact-check consistency)

    Input:
        similarity_results (List[Dict[str, Any]]): Candidate articles with 'similarity_score'.
        fact_check_result (Dict[str, Any]): The output from check_fact_conflicts().

    Output:
        Dict[str, Any]: Detailed scoring summary containing:
            - 'score' (int): 0 to 100 overall corroboration rating.
            - 'category' (str): Descriptive credibility tier.
            - 'explanation' (str): Plain-English narrative breakdown.
            - 'match_count' (int): Number of relevant corroborating articles found.
            - 'distinct_sources' (List[str]): Unique news organizations reporting the story.
            - 'component_breakdown' (Dict[str, float]): Points awarded for each factor.
    """
    # If no articles were found at all
    if not similarity_results:
        return {
            "score": 5,
            "category": "Uncorroborated (No Matching Sources)",
            "explanation": (
                "No matching or related news coverage was found across independent news organizations. "
                "This claim lacks corroboration from established reporting outlets."
            ),
            "match_count": 0,
            "distinct_sources": [],
            "component_breakdown": {
                "similarity_points": 0.0,
                "coverage_points": 0.0,
                "depth_points": 0.0,
                "fact_modifier": 0.0
            }
        }

    # Filter articles with meaningful similarity (score >= 0.15)
    meaningful_matches = [
        article for article in similarity_results
        if article.get("similarity_score", 0.0) >= 0.15
    ]

    top_similarity = similarity_results[0].get("similarity_score", 0.0) if similarity_results else 0.0

    # Collect distinct reporting publishers with meaningful match
    distinct_sources = list({
        article.get("source", "Unknown")
        for article in meaningful_matches
        if article.get("source")
    })

    # Factor 1: Top Content Similarity (Up to 45 points)
    # Reflects how closely the best matching article mirrors the claim
    similarity_points = min(45.0, top_similarity * 65.0)

    # Factor 2: Breadth of Multi-Source Coverage (Up to 30 points)
    # More independent newsrooms reporting = higher confidence
    source_count = len(distinct_sources)
    if source_count >= 3:
        coverage_points = 30.0
    elif source_count == 2:
        coverage_points = 22.0
    elif source_count == 1:
        coverage_points = 14.0
    else:
        coverage_points = 0.0

    # Factor 3: Depth of Meaningful Matches (Up to 15 points)
    # Average of only meaningful matches (>= 0.15), avoiding unmatching zeros
    if meaningful_matches:
        meaningful_scores = [article.get("similarity_score", 0.0) for article in meaningful_matches[:3]]
        average_match_score = sum(meaningful_scores) / len(meaningful_scores)
        depth_points = min(15.0, average_match_score * 20.0)
    else:
        depth_points = 0.0

    # Base alignment bonus: if top match is strong (>= 0.40)
    base_alignment_bonus = 10.0 if top_similarity >= 0.40 else 0.0

    # Factor 4: Fact-Check Consistency Modifier (+10 bonus for confirmed facts, -35 penalty for conflicts)
    fact_modifier = 0.0
    has_conflicts = fact_check_result.get("conflicts_found", False)
    has_agreements = fact_check_result.get("agreements_found", False)
    conflict_count = fact_check_result.get("conflict_count", 0)

    if has_conflicts:
        # Severe penalty: the claim is mentioning the event but with contradictory numbers/dates
        fact_modifier -= min(45.0, 30.0 + (conflict_count * 10.0))
    elif has_agreements:
        # Bonus: specific numbers or dates in the headline were confirmed by sources
        fact_modifier += 10.0

    # Calculate raw composite score
    raw_composite_score = similarity_points + coverage_points + depth_points + base_alignment_bonus + fact_modifier

    # Ensure score stays within the 0 to 100 range
    final_score = int(max(0, min(100, round(raw_composite_score))))

    # Categorize score into plain-English credibility tiers
    if final_score >= 75:
        category = "Strongly Corroborated"
        tier_summary = "High credibility with multiple independent sources confirming the claim."
    elif final_score >= 50:
        category = "Partially Corroborated"
        tier_summary = "Moderate evidence found; related coverage exists, but some details may be unconfirmed or limited."
    elif final_score >= 25:
        category = "Low Corroboration"
        tier_summary = "Weak evidence; few matching sources or low semantic alignment."
    else:
        category = "Uncorroborated or Contradicted"
        tier_summary = "Severe lack of corroboration or direct factual discrepancies detected against known reports."

    # Build human-readable narrative explanation
    sources_text = ", ".join(distinct_sources[:3]) if distinct_sources else "None"
    if len(distinct_sources) > 3:
        sources_text += f", and {len(distinct_sources) - 3} others"

    fact_details = fact_check_result.get("details", [])
    fact_notes = " ".join(fact_details[:2]) if fact_details else ""

    narrative_explanation = (
        f"{tier_summary} We identified {len(meaningful_matches)} relevant article(s) across "
        f"{len(distinct_sources)} distinct outlet(s) (including {sources_text}). "
        f"Top semantic similarity reached {int(top_similarity * 100)}%. {fact_notes}"
    )

    return {
        "score": final_score,
        "category": category,
        "explanation": narrative_explanation.strip(),
        "match_count": len(meaningful_matches),
        "distinct_sources": distinct_sources,
        "component_breakdown": {
            "similarity_points": round(similarity_points, 1),
            "coverage_points": round(coverage_points, 1),
            "depth_points": round(depth_points + base_alignment_bonus, 1),
            "fact_modifier": round(fact_modifier, 1)
        }
    }
