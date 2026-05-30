"""
app.py — SLT Insight AI Chatbot powered by LangGraph
Updated: Added active_flow and flow_answers session state for guided conversations.
"""

import streamlit as st
import os
import tempfile
import base64
import io
import csv
import datetime

from graph.slt_graph       import run_graph
from rag.pdf_loader        import load_and_split_pdf
from rag.embedder          import create_vectorstore
from rag.knowledge_base    import load_knowledge_base, build_knowledge_base
from analysis.excel_reader import load_excel, get_quick_stats

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
LOGO_PATH    = "F:/Slt_chatbotnew/sltlogo.png"
FEEDBACK_LOG = "F:/Slt_chatbotnew/feedback_log.csv"

st.set_page_config(
    page_title = "SLT Insight",
    page_icon  = LOGO_PATH,
    layout     = "wide",
)

st.markdown("""
<style>
  .stChatMessage { border-radius: 10px; }
  div[data-testid="stSidebarContent"] { background: #f8faff; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Feedback logger — defined FIRST to avoid NameError
# ─────────────────────────────────────────────────────────────────────────────
def _log_feedback(msg_id, content_preview, rating):
    row         = [datetime.datetime.now().isoformat(), msg_id, rating,
                   content_preview.replace("\n", " ")]
    file_exists = os.path.exists(FEEDBACK_LOG)
    with open(FEEDBACK_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["timestamp", "msg_id", "rating", "content_preview"])
        w.writerow(row)


# ─────────────────────────────────────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────────────────────────────────────
DEFAULTS = {
    "messages":       [],
    "vectorstore":    None,
    "df":             None,
    "pdf_names":      [],
    "excel_name":     None,
    "model":          "llama3.2",
    "vision_model":   "llava",
    "kb_vectorstore": None,
    "kb_loaded":      False,
    "image_file":     None,
    "image_name":     None,
    "msg_counter":    0,
    "active_flow":    None,   # ← NEW: tracks which guided flow is active
    "flow_answers":   {},     # ← NEW: stores collected answers during flow
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# Load knowledge base once on startup
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.kb_loaded:
    try:
        with st.spinner("Loading SLT knowledge base..."):
            st.session_state.kb_vectorstore = load_knowledge_base()
    except Exception as e:
        print(f"[app] KB error: {e}")
    finally:
        st.session_state.kb_loaded = True


# ─────────────────────────────────────────────────────────────────────────────
# Logo
# ─────────────────────────────────────────────────────────────────────────────
try:
    with open(LOGO_PATH, "rb") as f:
        img_b64  = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{img_b64}" style="width:100%;height:100%;object-fit:contain;"/>'
except Exception:
    logo_html = "🤖"


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
            <div style="width:42px;height:42px;border-radius:50%;overflow:hidden;
                        background:white;border:2px solid #ddd;">{logo_html}</div>
            <div style="font-size:1.7rem;font-weight:700;color:#1a1a2e;">SLT Insight</div>
        </div><hr style="margin:0 0 1rem 0;">""",
        unsafe_allow_html=True,
    )

    # ── Model selectors ────────────────────────────────────────
    st.markdown("### ⚙️ Settings")
    st.session_state.model        = st.selectbox("LLM Model", ["llama3.2", "llama3"], index=0)
    st.session_state.vision_model = st.selectbox("Vision Model", ["llava", "moondream", "llava:13b"], index=0)
    st.markdown("---")

    # ── Knowledge base ─────────────────────────────────────────
    st.markdown("### 🧠 Knowledge Base")
    if st.session_state.kb_vectorstore is not None:
        st.success("✅ SLT Knowledge Base ready")
    else:
        st.warning("⚠️ No knowledge base found")
        if st.button("🔄 Build from PDFs"):
            try:
                with st.spinner("Building..."):
                    st.session_state.kb_vectorstore = build_knowledge_base()
                st.success("✅ Built!")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    st.markdown("---")

    # ── File uploads ───────────────────────────────────────────
    st.markdown("### 📁 Upload Files")

    # PDF upload (multiple)
    pdf_files = st.file_uploader(
        "📄 PDF Documents",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload SLT reports, tariffs, any PDF"
    )
    if pdf_files:
        names = [f.name for f in pdf_files]
        if names != st.session_state.pdf_names:
            with st.spinner(f"Indexing {len(pdf_files)} PDF(s)..."):
                all_chunks = []
                for pf in pdf_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(pf.read())
                        tmp_path = tmp.name
                    all_chunks.extend(load_and_split_pdf(tmp_path))
                    os.unlink(tmp_path)
                st.session_state.vectorstore = create_vectorstore(
                    all_chunks, model=st.session_state.model
                )
                st.session_state.pdf_names = names
            st.success(f"✅ {len(pdf_files)} PDF(s) indexed")
        else:
            st.success(f"✅ {len(pdf_files)} PDF(s) ready")

    # Excel upload
    excel_file = st.file_uploader(
        "📊 Excel / CSV",
        type=["xlsx", "xls", "csv"],
        help="Upload data for chart generation"
    )
    if excel_file:
        if excel_file.name != st.session_state.excel_name:
            with st.spinner("Loading spreadsheet..."):
                df, _ = load_excel(excel_file)
                st.session_state.df         = df
                st.session_state.excel_name = excel_file.name
            st.success(f"✅ {excel_file.name}")
        else:
            st.success(f"✅ {excel_file.name}")

    # Image upload
    image_file = st.file_uploader(
        "🖼️ Image (Bill / Receipt)",
        type=["jpg", "jpeg", "png", "webp", "bmp"],
        help="Upload SLT bill or any image to ask questions"
    )
    if image_file:
        st.image(image_file, use_container_width=True)
        st.session_state.image_file = image_file
        st.session_state.image_name = image_file.name
        st.success(f"✅ {image_file.name}")

    st.markdown("---")

    # ── Active context indicator ───────────────────────────────
    st.markdown("### 📌 Active Context")
    ctx_items = []
    if st.session_state.kb_vectorstore:
        ctx_items.append("🧠 SLT Knowledge Base")
    if st.session_state.vectorstore:
        ctx_items.append(f"📄 {len(st.session_state.pdf_names)} PDF(s)")
    if st.session_state.df is not None:
        ctx_items.append(f"📊 {st.session_state.excel_name}")
    if st.session_state.image_file:
        ctx_items.append(f"🖼️ {st.session_state.image_name}")

    # ── Show active flow indicator if mid-conversation ─────────
    if st.session_state.active_flow:
        flow_labels = {
            "fiber_package":  "🌐 Fiber Package Finder",
            "peotv_package":  "📺 PeoTV Package Finder",
            "mobile_package": "📱 Mobile Package Finder",
            "bill_query":     "🧾 Bill Help Guide",
        }
        flow_label = flow_labels.get(st.session_state.active_flow, "🎯 Guided Flow")
        st.info(f"**Active:** {flow_label}\nAnswering questions step by step...")

    if ctx_items:
        for item in ctx_items:
            st.markdown(f"- {item}")
        st.caption("LangGraph will auto-route your questions to the right source.")
    else:
        st.info("Upload files above to get started, or ask an SLT question directly.")

    st.markdown("---")

    # ── Clear & Export ─────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ Clear"):
            st.session_state.messages    = []
            st.session_state.image_file  = None
            st.session_state.active_flow = None   # ← reset flow on clear
            st.session_state.flow_answers = {}    # ← reset answers on clear
            st.rerun()
    with col_b:
        if st.session_state.messages:
            chat_txt = "\n\n".join(
                f"[{m['role'].upper()}]\n{m['content']}"
                for m in st.session_state.messages
            )
            st.download_button(
                "📥 Export",
                data      = chat_txt,
                file_name = f"slt_chat_{datetime.datetime.now():%Y%m%d_%H%M}.txt",
                mime      = "text/plain",
            )

    st.markdown("---")
    st.caption("Powered by LangGraph · Ollama · LangChain")


# ─────────────────────────────────────────────────────────────────────────────
# Welcome screen
# ─────────────────────────────────────────────────────────────────────────────
if len(st.session_state.messages) == 0:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"""
            <div style="text-align:center;margin-top:80px;margin-bottom:40px;">
                <div style="display:flex;justify-content:center;margin-bottom:20px;">
                    <div style="width:90px;height:90px;
                                background:linear-gradient(135deg,#00c6ff,#0072ff);
                                border-radius:50%;display:flex;align-items:center;
                                justify-content:center;
                                box-shadow:0 10px 30px rgba(0,198,255,0.3);">
                        <span style="font-size:50px;">🤖</span>
                    </div>
                </div>
                <h1 style="font-size:2.4rem;font-weight:700;color:#1a1a2e;margin:0 0 8px 0;">
                    SLT Insight
                </h1>
                <p style="font-size:1.1rem;color:#888;margin:0 0 6px 0;">
                    Powered by LangGraph · Fully Offline AI
                </p>
                <p style="font-size:1.2rem;color:#555;margin:0 0 24px 0;">
                    Just ask — I'll figure out where to look automatically.
                </p>
                <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;">
                    {''.join(f'<div style="background:#f0f4ff;border:1px solid #c7d4f5;border-radius:8px;padding:8px 16px;font-size:0.85rem;color:#1a3c8c;">{t}</div>' for t in [
                        "📶 How to select fiber package?",
                        "📺 Which PeoTV package suits me?",
                        "🖼️ What is my total bill amount?",
                        "📊 Bar chart of Churn by Contract",
                        "📱 Which mobile package is best?",
                    ])}
                </div>
            </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Excel data preview panel
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.df is not None:
    stats = get_quick_stats(st.session_state.df)
    with st.expander("📋 Dataset Overview", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows",         stats["rows"])
        c2.metric("Columns",      stats["columns"])
        c3.metric("Numeric cols", len(stats["numeric_cols"]))
        c4.metric("Missing %",    f"{stats['missing_pct']}%")

        t1, t2 = st.tabs(["Numeric Summary", "Top Categories"])
        with t1:
            if stats["numeric_summary"]:
                import pandas as pd
                st.dataframe(pd.DataFrame(stats["numeric_summary"]).round(2),
                             use_container_width=True)
        with t2:
            for col, counts in stats["top_categories"].items():
                st.markdown(f"**{col}**")
                for val, cnt in list(counts.items())[:5]:
                    st.markdown(f"&nbsp;&nbsp;`{val}` — {cnt:,}")


# ─────────────────────────────────────────────────────────────────────────────
# Chat history display
# ─────────────────────────────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "chart" in msg and msg["chart"] is not None:
            st.plotly_chart(msg["chart"], use_container_width=True)

        if msg["role"] == "assistant":
            msg_id    = msg.get("id", i)
            ca, cb, _ = st.columns([1, 1, 10])
            with ca:
                if st.button("👍", key=f"up_{msg_id}"):
                    _log_feedback(msg_id, msg["content"][:80], "up")
                    st.toast("Thanks!", icon="✅")
            with cb:
                if st.button("👎", key=f"dn_{msg_id}"):
                    _log_feedback(msg_id, msg["content"][:80], "down")
                    st.toast("We'll improve!", icon="🔧")


# ─────────────────────────────────────────────────────────────────────────────
# Voice input
# ─────────────────────────────────────────────────────────────────────────────
voice_input = None
st.markdown("---")

try:
    from audio_recorder_streamlit import audio_recorder
    import speech_recognition as sr
    from pydub import AudioSegment

    col_mic, col_hint = st.columns([1, 5])
    with col_mic:
        audio_bytes = audio_recorder(
            text            = "",
            recording_color = "#e8123c",
            neutral_color   = "#0072ff",
            icon_size       = "2x",
            pause_threshold = 2.0,
        )
    with col_hint:
        st.caption("🎙️ Click mic to speak — works in all modes")

    if audio_bytes:
        try:
            seg     = AudioSegment.from_file(io.BytesIO(audio_bytes))
            wav_buf = io.BytesIO()
            seg.export(wav_buf, format="wav")
            wav_buf.seek(0)
            r = sr.Recognizer()
            with sr.AudioFile(wav_buf) as src:
                data = r.record(src)
            voice_input = r.recognize_google(data, language="en-US")
            st.success(f"🎙️ Heard: **{voice_input}**")
        except sr.UnknownValueError:
            st.warning("⚠️ Could not understand. Please speak clearly.")
        except Exception as e:
            st.warning(f"Voice error: {e}")

except ImportError:
    st.caption("💡 Install voice: `pip install audio-recorder-streamlit SpeechRecognition pydub`")


# ─────────────────────────────────────────────────────────────────────────────
# Chat input
# ─────────────────────────────────────────────────────────────────────────────
# Change placeholder when a flow is active
if st.session_state.active_flow:
    placeholder = "Type your answer here..."
else:
    placeholder = "Ask anything about SLT — I'll figure out where to look..."

user_input = st.chat_input(placeholder)
if voice_input and not user_input:
    user_input = voice_input


# ─────────────────────────────────────────────────────────────────────────────
# Handle input — LangGraph does all the routing
# ─────────────────────────────────────────────────────────────────────────────
if user_input:
    msg_id = st.session_state.msg_counter
    st.session_state.msg_counter += 1

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("🤖 Thinking..."):
            result = run_graph(user_input, dict(st.session_state))

        reply  = result.get("response", "⚠️ No response generated.")
        fig    = result.get("figure")
        intent = result.get("intent", "chat")

        # ── CRITICAL FIX: save flow state BEFORE anything else ────
        new_active_flow  = result.get("active_flow")
        new_flow_answers = result.get("flow_answers") or {}

        print(f"[app] Saving flow state: active={new_active_flow} answers={new_flow_answers}")

        st.session_state.active_flow  = new_active_flow
        st.session_state.flow_answers = new_flow_answers

        intent_label = {
            "pdf":   "📄 Answered from PDF / Knowledge Base",
            "excel": "📊 Generated from Excel data",
            "image": "🖼️ Read from uploaded image",
            "chat":  "💬 General SLT knowledge",
            "flow":  "🎯 Guided recommendation flow",
        }.get(intent, "💬 General")

        st.markdown(reply)

        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("ℹ️ Source", expanded=False):
            st.caption(intent_label)

        st.session_state.messages.append({
            "role":    "assistant",
            "content": reply,
            "chart":   fig,
            "id":      msg_id,
        })