"""
graph/slt_graph.py — Builds and compiles the LangGraph state machine.
Updated: Added flow node for guided conversations.
"""

from langgraph.graph import StateGraph, END
from graph.state import SLTState
from graph.nodes import (
    router_node, flow_node, pdf_node,
    excel_node, image_node, chat_node, response_node,
)


def _route_to_node(state: SLTState) -> str:
    return state.get("intent", "chat")


def build_slt_graph():
    graph = StateGraph(SLTState)

    graph.add_node("router",   router_node)
    graph.add_node("flow",     flow_node)      # NEW — guided conversations
    graph.add_node("pdf",      pdf_node)
    graph.add_node("excel",    excel_node)
    graph.add_node("image",    image_node)
    graph.add_node("chat",     chat_node)
    graph.add_node("response", response_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        _route_to_node,
        {
            "flow":  "flow",
            "pdf":   "pdf",
            "excel": "excel",
            "image": "image",
            "chat":  "chat",
        },
    )

    graph.add_edge("flow",  "response")
    graph.add_edge("pdf",   "response")
    graph.add_edge("excel", "response")
    graph.add_edge("image", "response")
    graph.add_edge("chat",  "response")
    graph.add_edge("response", END)

    return graph.compile()


slt_graph = build_slt_graph()
print("[LangGraph] SLT graph compiled with conversational flow support.")


def run_graph(user_input: str, session: dict) -> dict:

    # ── Read flow state directly from session ──────────────────
    active_flow  = session.get("active_flow")
    flow_answers = dict(session.get("flow_answers") or {})

    print(f"[run_graph] active_flow={active_flow} | flow_answers={flow_answers}")

    initial_state: SLTState = {
        "user_input":     user_input,
        "model":          session.get("model", "llama3.2"),
        "vision_model":   session.get("vision_model", "llava"),
        "intent":         None,
        "confidence":     None,
        "active_flow":    active_flow,    # ← pass directly
        "flow_answers":   flow_answers,   # ← pass directly as fresh dict copy
        "has_image":      session.get("image_file") is not None,
        "has_pdf":        session.get("vectorstore") is not None,
        "has_excel":      session.get("df") is not None,
        "has_kb":         session.get("kb_vectorstore") is not None,
        "vectorstore":    session.get("vectorstore"),
        "kb_vectorstore": session.get("kb_vectorstore"),
        "df":             session.get("df"),
        "image_file":     session.get("image_file"),
        "response":       None,
        "figure":         None,
        "sources":        None,
        "history":        session.get("messages", []),
        "error":          None,
    }

    try:
        result = slt_graph.invoke(initial_state)
        print(f"[run_graph] Result flow state: active={result.get('active_flow')} answers={result.get('flow_answers')}")
        return result
    except Exception as e:
        print(f"[LangGraph] Error: {e}")
        return {**initial_state, "response": f"❌ System error: {str(e)}", "error": str(e)}