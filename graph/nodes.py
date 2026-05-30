"""
graph/nodes.py — All LangGraph node functions for SLT Insight chatbot.
Fixed: flow_node uses __shown_ marker to correctly separate showing Q from receiving answer.
"""

import re
from langchain_ollama import OllamaLLM
from graph.state import SLTState


def router_node(state: SLTState) -> SLTState:
    from graph.conversation_flow import detect_flow

    user_input   = state["user_input"].lower().strip()
    active_flow  = state.get("active_flow")
    flow_answers = state.get("flow_answers") or {}

    if active_flow:
        print(f"[router] Active flow: {active_flow} | Answers so far: {flow_answers}")
        return {**state, "intent": "flow", "confidence": "high"}

    flow_name = detect_flow(user_input)
    if flow_name:
        print(f"[router] Starting new flow: {flow_name}")
        return {
            **state,
            "intent":       "flow",
            "active_flow":  flow_name,
            "flow_answers": {},
            "confidence":   "high",
        }

    chart_words = ["chart", "graph", "plot", "bar chart", "pie chart",
                   "line chart", "histogram", "scatter", "heatmap",
                   "correlation", "distribution", "visualize", "show me"]
    image_words = ["bill", "invoice", "image", "photo", "picture",
                   "total amount", "due date", "payable", "charges",
                   "account number", "receipt"]
    pdf_words   = ["report", "document", "pdf", "annual", "revenue",
                   "financial", "quarter", "profit", "loss", "balance sheet"]

    if any(w in user_input for w in chart_words) and state["has_excel"]:
        return {**state, "intent": "excel", "confidence": "high"}
    if state["has_image"] and any(w in user_input for w in image_words):
        return {**state, "intent": "image", "confidence": "high"}
    if any(w in user_input for w in pdf_words) and (state["has_pdf"] or state["has_kb"]):
        return {**state, "intent": "pdf", "confidence": "high"}
    if state["has_excel"] and not state["has_pdf"] and not state["has_image"]:
        return {**state, "intent": "excel", "confidence": "high"}
    if state["has_image"] and not state["has_pdf"] and not state["has_excel"]:
        return {**state, "intent": "image", "confidence": "high"}
    if state["has_pdf"] or state["has_kb"]:
        return {**state, "intent": "pdf", "confidence": "high"}

    try:
        llm    = OllamaLLM(model=state["model"], temperature=0)
        prompt = f"""Classify this message into one category.
User: "{state['user_input']}"
Categories: pdf, excel, image, chat
Reply with ONE word only:"""
        result = llm.invoke(prompt).strip().lower()
        intent = result if result in ["pdf", "excel", "image", "chat"] else "chat"
        return {**state, "intent": intent, "confidence": "low"}
    except Exception:
        return {**state, "intent": "chat", "confidence": "low"}


def flow_node(state: SLTState) -> SLTState:
    """
    Guided multi-turn Q&A using __shown_ markers to track question/answer turns.

    How it works:
      Turn 1: User triggers flow → show Q1, save __shown_members = "1"
      Turn 2: User answers "5"   → __shown_members exists → save members = "5"
                                 → show Q2, save __shown_usage = "1"
      Turn 3: User answers "2"   → __shown_usage exists → save usage = "2"
                                 → and so on until all steps done
    """
    from graph.conversation_flow import get_flow, generate_recommendation

    flow_name    = state.get("active_flow", "")
    flow_answers = dict(state.get("flow_answers") or {})
    user_input   = state["user_input"].strip()
    flow_data    = get_flow(flow_name)

    print(f"[flow_node] flow={flow_name} | answers={flow_answers} | input='{user_input}'")

    if not flow_data:
        print("[flow_node] No flow data — falling back to chat")
        return {**state, "intent": "chat", "active_flow": None, "flow_answers": {}}

    steps = flow_data.get("steps", [])

    # ── Find the current pending step ─────────────────────────
    # For each step, check two states:
    #   1. Not shown yet  → show the question
    #   2. Shown but not answered → save the answer, then show next question
    for i, step in enumerate(steps):
        key       = step["key"]
        shown_key = f"__shown_{key}"

        if key in flow_answers:
            # Already answered — move to next step
            continue

        if shown_key not in flow_answers:
            # ── SHOW this question ─────────────────────────────
            flow_answers[shown_key] = "1"   # mark as shown

            intro = ""
            if i == 0:
                intro = flow_data.get("intro", "Let me ask you a few questions!") + "\n\n"

            response = (
                f"{intro}"
                f"**Question {i + 1} of {len(steps)}:**\n\n"
                f"{step['question']}\n\n"
                f"_{step.get('hint', '')}_"
            )
            print(f"[flow_node] Showing Q{i + 1}: {key}")
            return {
                **state,
                "response":     response,
                "active_flow":  flow_name,
                "flow_answers": flow_answers,
                "error":        None,
            }

        else:
            # ── RECEIVE the answer for this question ───────────
            flow_answers[key] = user_input
            print(f"[flow_node] Saved: {key} = '{user_input}'")

            # Check if all real steps are now answered
            real_done = all(s["key"] in flow_answers for s in steps)

            if real_done:
                print(f"[flow_node] All steps complete! Generating recommendation...")
                clean = {k: v for k, v in flow_answers.items() if not k.startswith("__shown_")}
                recommendation = generate_recommendation(flow_name, clean)
                return {
                    **state,
                    "response":     recommendation,
                    "active_flow":  None,
                    "flow_answers": {},
                    "error":        None,
                }

            # Show the next question
            for j, next_step in enumerate(steps):
                next_key       = next_step["key"]
                next_shown_key = f"__shown_{next_key}"
                if next_key not in flow_answers and next_shown_key not in flow_answers:
                    flow_answers[next_shown_key] = "1"
                    real_answered = sum(1 for s in steps if s["key"] in flow_answers)
                    response = (
                        f"**Question {j + 1} of {len(steps)}:**\n\n"
                        f"{next_step['question']}\n\n"
                        f"_{next_step.get('hint', '')}_"
                    )
                    print(f"[flow_node] Showing Q{j + 1}: {next_key}")
                    return {
                        **state,
                        "response":     response,
                        "active_flow":  flow_name,
                        "flow_answers": flow_answers,
                        "error":        None,
                    }

    # ── Safety fallback — should not reach here ────────────────
    print("[flow_node] Safety fallback triggered")
    clean = {k: v for k, v in flow_answers.items() if not k.startswith("__shown_")}
    if clean:
        recommendation = generate_recommendation(flow_name, clean)
        return {
            **state,
            "response":     recommendation,
            "active_flow":  None,
            "flow_answers": {},
            "error":        None,
        }
    return {**state, "response": "⚠️ Something went wrong with the flow.", "active_flow": None, "flow_answers": {}}


def pdf_node(state: SLTState) -> SLTState:
    vs = state.get("vectorstore") or state.get("kb_vectorstore")

    if vs is None:
        return {
            **state,
            "response": "⚠️ No document available. Please upload a PDF first.",
            "error": "no_vectorstore",
        }

    try:
        from langchain_ollama import OllamaLLM
        from langchain_core.prompts import PromptTemplate
        from langchain_core.runnables import RunnablePassthrough
        from langchain_core.output_parsers import StrOutputParser

        llm       = OllamaLLM(model=state["model"], temperature=0.1)
        retriever = vs.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        docs      = retriever.invoke(state["user_input"])
        sources   = list(set(
            d.metadata.get("source_file", "document")
            for d in docs if d.metadata.get("source_file")
        ))
        context = "\n\n".join(
            f"[{d.metadata.get('source_file', 'doc')}]\n{d.page_content}"
            for d in docs
        )
        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are a helpful assistant for SLT (Sri Lanka Telecom).
Use ONLY the context below. Never make up facts.

Context:
{context}

Question: {question}

Answer:""",
        )
        chain = (
            {"context": lambda _: context, "question": RunnablePassthrough()}
            | prompt_template | llm | StrOutputParser()
        )
        answer = chain.invoke(state["user_input"])
        if sources:
            answer += f"\n\n📄 *Sources: {', '.join(sources)}*"
        return {**state, "response": answer, "sources": sources, "error": None}
    except Exception as e:
        return {**state, "response": f"❌ Error: {str(e)}", "error": str(e)}


def excel_node(state: SLTState) -> SLTState:
    from analysis.chart_builder import build_chart
    df = state.get("df")
    if df is None:
        return {**state, "response": "⚠️ No Excel file uploaded.", "error": "no_dataframe"}
    try:
        reply_text, fig = build_chart(state["user_input"], df, model=state["model"])
        return {**state, "response": reply_text, "figure": fig, "error": None}
    except Exception as e:
        return {**state, "response": f"❌ Chart error: {str(e)}", "error": str(e), "figure": None}


def image_node(state: SLTState) -> SLTState:
    from rag.image_reader import ask_image_question
    image_file = state.get("image_file")
    if image_file is None:
        return {**state, "response": "⚠️ No image uploaded.", "error": "no_image"}
    try:
        image_file.seek(0)
    except Exception:
        pass
    try:
        answer = ask_image_question(
            image_file, state["user_input"], model=state.get("vision_model", "llava")
        )
        return {**state, "response": answer, "error": None}
    except Exception as e:
        return {**state, "response": f"❌ Image error: {str(e)}", "error": str(e)}


def chat_node(state: SLTState) -> SLTState:
    user_input = state["user_input"].lower()

    faqs = {
        "upgrade": (
            "**To upgrade your SLT Fiber package:**\n\n"
            "1. Call SLT hotline: **1212**\n"
            "2. Visit MySLT portal: **https://myslt.slt.lk**\n"
            "3. Visit nearest SLT Customer Care Centre\n"
            "4. Use MySLT mobile app\n\nHave your **Account Number** ready."
        ),
        "hotline": "📞 SLT Customer Hotline: **1212** (24/7)",
        "pay": (
            "**SLT Bill Payment methods:**\n\n"
            "- MySLT portal: https://myslt.slt.lk\n"
            "- MySLT mobile app\n"
            "- Bank transfer / ATM\n"
            "- SLT Customer Care Centres\n"
            "- Dialog eZ Cash / mCash"
        ),
        "contact": (
            "**SLT Contact Information:**\n\n"
            "📞 Hotline: **1212**\n"
            "🌐 Website: **https://www.slt.lk**\n"
            "💻 MySLT: **https://myslt.slt.lk**\n"
            "📧 Email: **customercare@slt.com.lk**"
        ),
    }

    for keyword, answer in faqs.items():
        if keyword in user_input:
            return {**state, "response": answer, "error": None}

    llm     = OllamaLLM(model=state["model"], temperature=0.3)
    history = ""
    for m in state.get("history", [])[-8:]:
        role     = "User" if m["role"] == "user" else "Assistant"
        history += f"{role}: {m['content']}\n"

    kb_context = ""
    kb_vs = state.get("kb_vectorstore")
    if kb_vs:
        try:
            docs       = kb_vs.as_retriever(search_kwargs={"k": 4}).invoke(state["user_input"])
            kb_context = "\n\n".join(d.page_content for d in docs)
        except Exception:
            kb_context = ""

    if not kb_context:
        return {
            **state,
            "response": (
                "⚠️ I don't have specific information about that.\n\n"
                "📞 Hotline: **1212**\n"
                "🌐 Portal: **https://myslt.slt.lk**"
            ),
            "error": None,
        }

    prompt = f"""You are SLT Insight — AI assistant for SLT Mobitel Sri Lanka.
Only answer SLT-related questions.

Knowledge Base:
{kb_context}

History:
{history}
User: {state["user_input"]}
Assistant:"""

    try:
        response = llm.invoke(prompt)
        return {**state, "response": response, "error": None}
    except Exception as e:
        return {**state, "response": f"❌ Error: {str(e)}", "error": str(e)}


def response_node(state: SLTState) -> SLTState:
    response = state.get("response") or ""
    if not response.strip():
        response = "⚠️ I could not generate a response. Please try rephrasing."

    badges = {"pdf": "📄", "excel": "📊", "image": "🖼️", "chat": "💬", "flow": "🎯"}
    badge  = badges.get(state.get("intent", "chat"), "💬")

    if not response.startswith(("❌", "⚠️", "✅", "📄", "📊", "🖼️", "💬", "🎯", "#", "*", "-", "**")):
        response = f"{badge} {response}"

    return {**state, "response": response}