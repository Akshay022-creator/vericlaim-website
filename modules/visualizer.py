"""
Visualizer Module (Data Visualization & Chart Generator)

This module produces clear visual charts showing the Corroboration Score meter,
component breakdown, and similarity comparison across all matching news organizations.

It generates matplotlib figures that can be saved as image files, viewed in the terminal,
or directly rendered in the interactive Streamlit web dashboard.
"""

from typing import List, Dict, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def generate_chart(
    similarity_results: List[Dict[str, Any]],
    fact_check_result: Dict[str, Any],
    corroboration_summary: Optional[Dict[str, Any]] = None,
    save_filepath: Optional[str] = None
) -> plt.Figure:
    """
    Creates a visual 2-panel dashboard summarizing the corroboration findings.

    Panel 1 (Left): Corroboration Score Meter & Credibility Status Badge.
    Panel 2 (Right): Source Similarity Comparison Bar Chart.

    Input:
        similarity_results (List[Dict[str, Any]]): Matching articles with similarity scores.
        fact_check_result (Dict[str, Any]): Fact checking consistency findings.
        corroboration_summary (Optional[Dict[str, Any]]): The output from compute_corroboration_score().
        save_filepath (Optional[str]): If provided, saves the chart to this PNG file path.

    Output:
        plt.Figure: The constructed matplotlib figure object ready for display or embedding.
    """
    # Extract overall score and category
    score_value = corroboration_summary.get("score", 0) if corroboration_summary else 0
    category_title = corroboration_summary.get("category", "Unverified") if corroboration_summary else "Unverified"

    # Select color theme based on score value
    if score_value >= 75:
        score_color = "#10B981"   # Emerald Green
        status_label = "HIGH CORROBORATION"
    elif score_value >= 50:
        score_color = "#F59E0B"   # Amber / Orange
        status_label = "PARTIAL CORROBORATION"
    elif score_value >= 25:
        score_color = "#F97316"   # Deep Orange
        status_label = "LOW CORROBORATION"
    else:
        score_color = "#EF4444"   # Bright Red
        status_label = "UNCORROBORATED"

    # Create figure with 2 subplots side by side
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    figure, (axis_left, axis_right) = plt.subplots(1, 2, figsize=(11, 4.5), gridspec_kw={"width_ratios": [1, 1.4]})
    figure.patch.set_facecolor("#FAFAFA")

    # =========================================================================
    # Panel 1: Corroboration Score Dial / Card
    # =========================================================================
    axis_left.set_facecolor("#FAFAFA")
    axis_left.set_xlim(0, 10)
    axis_left.set_ylim(0, 10)
    axis_left.axis("off")

    # Draw rounded background card
    card_box = patches.FancyBboxPatch(
        (0.5, 0.5), 9.0, 9.0,
        boxstyle="round,pad=0.3",
        ec="#E5E7EB",
        fc="white",
        lw=1.5
    )
    axis_left.add_patch(card_box)

    # Add Corroboration Score numerical display
    axis_left.text(5.0, 6.6, f"{score_value}", fontsize=44, fontweight="bold", color=score_color, ha="center", va="center")
    axis_left.text(5.0, 5.0, "out of 100", fontsize=12, color="#6B7280", ha="center", va="center")

    # Add Status Badge
    badge_box = patches.FancyBboxPatch(
        (1.5, 3.2), 7.0, 1.2,
        boxstyle="round,pad=0.2",
        ec=score_color,
        fc=score_color,
        lw=1.0
    )
    axis_left.add_patch(badge_box)
    axis_left.text(5.0, 3.8, status_label, fontsize=10, fontweight="bold", color="white", ha="center", va="center")

    # Fact Check Indicator at bottom (using standard ASCII symbols for cross-platform compatibility)
    has_conflicts = fact_check_result.get("conflicts_found", False)
    has_agreements = fact_check_result.get("agreements_found", False)
    if has_conflicts:
        fact_status_text = "[!] Number/Date Discrepancies Detected"
        fact_status_color = "#DC2626"
    elif has_agreements:
        fact_status_text = "[+] Key Facts Independently Verified"
        fact_status_color = "#059669"
    else:
        fact_status_text = "[*] Qualitative claim cross-check"
        fact_status_color = "#4B5563"

    axis_left.text(5.0, 1.8, fact_status_text, fontsize=9.5, fontweight="bold", color=fact_status_color, ha="center", va="center")

    # =========================================================================
    # Panel 2: Source Similarity Comparison Bar Chart
    # =========================================================================
    axis_right.set_facecolor("white")

    # Take top 5 matching sources
    top_articles = similarity_results[:5] if similarity_results else []

    if top_articles:
        source_labels = []
        similarity_percentages = []

        for article in reversed(top_articles):
            source_name = article.get("source", "Unknown Source")
            # Truncate long source names for clean chart alignment
            if len(source_name) > 20:
                source_name = source_name[:18] + "..."
            source_labels.append(source_name)
            similarity_percentages.append(article.get("similarity_score", 0.0) * 100)

        # Plot horizontal bars
        bar_colors = ["#3B82F6" if pct >= 35 else "#93C5FD" if pct >= 15 else "#D1D5DB" for pct in similarity_percentages]
        horizontal_bars = axis_right.barh(source_labels, similarity_percentages, color=bar_colors, height=0.55, edgecolor="#9CA3AF", linewidth=0.5)

        # Annotate exact percentage at the end of each bar
        for bar in horizontal_bars:
            bar_width = bar.get_width()
            axis_right.text(
                bar_width + 2,
                bar.get_y() + bar.get_height() / 2,
                f"{int(bar_width)}%",
                va="center",
                ha="left",
                fontsize=9.5,
                fontweight="bold",
                color="#1F2937"
            )

        axis_right.set_xlim(0, 115)
        axis_right.set_xlabel("Content Similarity Score (%)", fontsize=10, fontweight="bold", color="#374151")
        axis_right.set_title("Matching News Outlets & Alignment", fontsize=12, fontweight="bold", color="#111827", pad=10)
    else:
        axis_right.text(0.5, 0.5, "No Matching Sources Found", ha="center", va="center", fontsize=12, color="#9CA3AF")
        axis_right.set_axis_off()

    # Clean up layout
    plt.tight_layout()

    # Save to file if requested
    if save_filepath:
        figure.savefig(save_filepath, dpi=180, bbox_inches="tight")

    return figure
