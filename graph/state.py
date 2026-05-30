"""
graph/state.py — LangGraph shared state.
Updated: Added active_flow and flow_answers for guided conversations.
"""

from typing import TypedDict, Optional, Any


class SLTState(TypedDict):
    user_input:      str
    model:           str
    vision_model:    str
    intent:          Optional[str]
    confidence:      Optional[str]
    active_flow:     Optional[str]   # e.g. "fiber_package", "peotv_package"
    flow_answers:    Optional[dict]  # collected answers {"members": "4", ...}
    has_image:       bool
    has_pdf:         bool
    has_excel:       bool
    has_kb:          bool
    vectorstore:     Optional[Any]
    kb_vectorstore:  Optional[Any]
    df:              Optional[Any]
    image_file:      Optional[Any]
    response:        Optional[str]
    figure:          Optional[Any]
    sources:         Optional[list]
    history:         list
    error:           Optional[str]