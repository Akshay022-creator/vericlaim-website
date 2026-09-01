"""
Module 4: Deterministic Corroboration Scorer & Narrative Explainer
------------------------------------------------------------------
PURPOSE (Easy to explain in an interview or presentation):
This module integrates all evidence from the Similarity Engine and Fact Checker
to calculate a final Corroboration Score from 0 to 100 and generates a transparent,
human-readable explanation.

The Deterministic 4-Factor Formula:
1. Top Match Content Alignment (up to 45 pts): How well does the best article mirror the claim?
2. Multi-Source Coverage Breadth (up to 30 pts): How many distinct publishers reported it?
3. Match Depth & Consistency (up to 25 pts): Average alignment across the top 3 supporting stories.
4. Fact Consistency Modifier (±45 pts):
   - Confirmed numbers/dates: +10 bonus points.
   - Contradictory/distorted numbers: -35 to -45 severe penalty.
"""

from typing import List, Dict, Any


def compute_corroboration_score(
    similarity_results: List[Dict[str, Any]],
    fact_check_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes a composite 0-100 credibility rating and plain-English narrative explanation.
    """
    # Guard: If no articles were retrieved across all APIs
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

    # Collect distinct news organizations
    distinct_sources = list({
        article.get("source", "Unknown")
        for article in meaningful_matches
        if article.get("source")
    })

    # Factor 1: Top Content Similarity (Up to 45 points)
    similarity_points = min(45.0, top_similarity * 65.0)

    # Factor 2: Breadth of Multi-Source Coverage (Up to 30 points)
    source_count = len(distinct_sources)
    if source_count >= 3:
        coverage_points = 30.0
    elif source_count == 2:
        coverage_points = 22.0
    elif source_count == 1:
        coverage_points = 14.0
    else:
        coverage_points = 0.0

    # Factor 3: Depth of Meaningful Matches (Up to 15 points + 10 pts alignment bonus)
    if meaningful_matches:
        meaningful_scores = [article.get("similarity_score", 0.0) for article in meaningful_matches[:3]]
        average_match_score = sum(meaningful_scores) / len(meaningful_scores)
        depth_points = min(15.0, average_match_score * 20.0)
    else:
        depth_points = 0.0

    base_alignment_bonus = 10.0 if top_similarity >= 0.40 else 0.0

    # Factor 4: Fact-Check Consistency Modifier (+10 bonus for confirmed, -35 penalty for conflict)
    fact_modifier = 0.0
    has_conflicts = fact_check_result.get("conflicts_found", False)
    has_agreements = fact_check_result.get("agreements_found", False)
    conflict_count = fact_check_result.get("conflict_count", 0)

    if has_conflicts:
        fact_modifier -= min(45.0, 30.0 + (conflict_count * 10.0))
    elif has_agreements:
        fact_modifier += 10.0

    # Sum composite total
    raw_composite = similarity_points + coverage_points + depth_points + base_alignment_bonus + fact_modifier
    final_score = int(max(0, min(100, round(raw_composite))))

    # Credibility Tier Classification
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

    # Construct plain-English narrative explanation
    sources_text = ", ".join(distinct_sources[:3]) if distinct_sources else "None"
    if len(distinct_sources) > 3:
        sources_text += f", and {len(distinct_sources) - 3} others"

    fact_details = fact_check_result.get("details", [])
    fact_notes = " ".join(fact_details[:2]) if fact_details else ""

    narrative = (
        f"{tier_summary} We identified {len(meaningful_matches)} relevant article(s) across "
        f"{len(distinct_sources)} distinct outlet(s) (including {sources_text}). "
        f"Top semantic similarity reached {int(top_similarity * 100)}%. {fact_notes}"
    )

    return {
        "score": final_score,
        "category": category,
        "explanation": narrative.strip(),
        "match_count": len(meaningful_matches),
        "distinct_sources": distinct_sources,
        "component_breakdown": {
            "similarity_points": round(similarity_points, 1),
            "coverage_points": round(coverage_points, 1),
            "depth_points": round(depth_points + base_alignment_bonus, 1),
            "fact_modifier": round(fact_modifier, 1)
        }
    }
