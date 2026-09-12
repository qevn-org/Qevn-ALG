"""LangGraph workflow assembly for LinkedIn Intelligence Engine."""

from langgraph.graph import END, START, StateGraph

from linkedin_intelligence.agents.contact_discovery import contact_discovery_node
from linkedin_intelligence.agents.decision_maker import decision_maker_node
from linkedin_intelligence.agents.enrichment import enrichment_node
from linkedin_intelligence.agents.intent import intent_node
from linkedin_intelligence.agents.lead_analysis import lead_analysis_node
from linkedin_intelligence.agents.lead_scoring_node import lead_scoring_node
from linkedin_intelligence.agents.normalization_dedup import (
    deduplication_node,
    normalization_node,
)
from linkedin_intelligence.agents.opportunity import opportunity_node
from linkedin_intelligence.agents.qualification import qualification_node
from linkedin_intelligence.agents.query_expansion import query_expansion_node
from linkedin_intelligence.agents.query_validation import query_validation_node
from linkedin_intelligence.agents.retrieval import retrieval_node
from linkedin_intelligence.agents.signal_detection import signal_detection_node
from linkedin_intelligence.models.state import IntelligenceState


def build_graph() -> StateGraph:
    """Construct the compiled LangGraph workflow."""
    workflow = StateGraph(IntelligenceState)

    # Add Nodes
    workflow.add_node("intent", intent_node)
    workflow.add_node("query_expansion", query_expansion_node)
    workflow.add_node("query_validation", query_validation_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("normalization", normalization_node)
    workflow.add_node("deduplication", deduplication_node)
    workflow.add_node("signal_detection", signal_detection_node)
    workflow.add_node("qualification", qualification_node)
    workflow.add_node("lead_scoring", lead_scoring_node)
    workflow.add_node("enrichment", enrichment_node)
    workflow.add_node("decision_maker", decision_maker_node)
    workflow.add_node("contact_discovery", contact_discovery_node)
    workflow.add_node("lead_analysis", lead_analysis_node)
    workflow.add_node("opportunity", opportunity_node)

    # Linear Pipeline from Discovery to Enrichment and Scoring
    workflow.add_edge(START, "intent")
    workflow.add_edge("intent", "query_expansion")
    workflow.add_edge("query_expansion", "query_validation")
    workflow.add_edge("query_validation", "retrieval")
    workflow.add_edge("retrieval", "normalization")
    workflow.add_edge("normalization", "deduplication")
    workflow.add_edge("deduplication", "signal_detection")
    workflow.add_edge("signal_detection", "qualification")
    workflow.add_edge("qualification", "enrichment")
    workflow.add_edge("enrichment", "decision_maker")
    workflow.add_edge("decision_maker", "contact_discovery")
    workflow.add_edge("contact_discovery", "lead_analysis")
    workflow.add_edge("lead_analysis", "lead_scoring")
    workflow.add_edge("lead_scoring", "opportunity")
    workflow.add_edge("opportunity", END)

    return workflow




# Compiled graph instance ready for export and dev server
graph = build_graph().compile()
