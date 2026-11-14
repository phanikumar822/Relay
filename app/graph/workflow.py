from langgraph.graph import StateGraph, START, END
from app.graph.state import AgentState
from app.graph.nodes import parser_node, search_node, verifier_node, ranker_node

builder = StateGraph(AgentState)

builder.add_node("parser", parser_node)
builder.add_node("searcher", search_node)
builder.add_node("verifier", verifier_node)
builder.add_node("ranker", ranker_node)

builder.add_edge(START, "parser")
builder.add_edge("parser", "searcher")
builder.add_edge("searcher", "verifier")
builder.add_edge("verifier", "ranker")
builder.add_edge("ranker", END)

event_discovery_graph = builder.compile()
