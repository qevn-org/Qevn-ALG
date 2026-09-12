"""Component for displaying transparent mathematical score breakdowns."""

import pandas as pd
import streamlit as st

from linkedin_intelligence.models.opportunities import ScoreBreakdown


def render_score_breakdown(breakdown: ScoreBreakdown) -> None:
    """Render table and explanation of the 6 score components."""
    data = [
        {
            "Signal Component": "Hiring Intent",
            "Weight": f"{int(breakdown.hiring_intent_weight * 100)}%",
            "Score": f"{breakdown.hiring_intent_score:.1f}",
            "Contribution": f"{breakdown.hiring_intent_score * breakdown.hiring_intent_weight:.1f}",
        },
        {
            "Signal Component": "Decision Maker",
            "Weight": f"{int(breakdown.decision_maker_weight * 100)}%",
            "Score": f"{breakdown.decision_maker_score:.1f}",
            "Contribution": f"{breakdown.decision_maker_score * breakdown.decision_maker_weight:.1f}",
        },
        {
            "Signal Component": "Company Fit",
            "Weight": f"{int(breakdown.company_fit_weight * 100)}%",
            "Score": f"{breakdown.company_fit_score:.1f}",
            "Contribution": f"{breakdown.company_fit_score * breakdown.company_fit_weight:.1f}",
        },
        {
            "Signal Component": "Freshness",
            "Weight": f"{int(breakdown.freshness_weight * 100)}%",
            "Score": f"{breakdown.freshness_score:.1f}",
            "Contribution": f"{breakdown.freshness_score * breakdown.freshness_weight:.1f}",
        },
        {
            "Signal Component": "Urgency",
            "Weight": f"{int(breakdown.urgency_weight * 100)}%",
            "Score": f"{breakdown.urgency_score:.1f}",
            "Contribution": f"{breakdown.urgency_score * breakdown.urgency_weight:.1f}",
        },
        {
            "Signal Component": "Evidence Confidence",
            "Weight": f"{int(breakdown.evidence_confidence_weight * 100)}%",
            "Score": f"{breakdown.evidence_confidence_score:.1f}",
            "Contribution": f"{breakdown.evidence_confidence_score * breakdown.evidence_confidence_weight:.1f}",
        },
    ]

    df = pd.DataFrame(data)
    st.table(df)
    st.caption(
        f"**Calculated Score:** `{breakdown.total_score:.1f} / 100` "
        f"(Threshold: HOT >= 80 | WARM >= 60 | LOW < 60)"
    )
