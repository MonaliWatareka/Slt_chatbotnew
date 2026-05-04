"""
SLT Insight AI Chatbot — app.py
New features: multi-PDF upload, feedback logging, data preview stats,
              export chat, improved voice input, intent detection
"""

import streamlit as st
import os, tempfile, base64, io, csv, datetime

from rag.pdf_loader      import load_and_split_pdf
from rag.embedder        import create_vectorstore
from rag.retriever       import get_answer
from rag.knowledge_base  import load_knowledge_base, build_knowledge_base
from rag.image_reader    import ask_image_question
from analysis.excel_reader import load_excel, get_quick_stats
from analysis.chart_builder import build_chart

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
LOGO_PATH     = "F:/Slt_chatbotnew/sltlogo.png"
FEEDBACK_LOG  = "F:/Slt_chatbotnew/feedback_log.csv"

st.set_page_config(
    page_title = "SLT Insight",
    page_icon  = LOGO_PATH,
    layout     = "wide",
)

st.markdown("""
<style>
  .stChatMessage { border-radius: 10px; }
  div[data-testid="stSidebarContent"] { background: #f8faff; }
  .metric-card {
      background: white; border: 1px solid #e0e7ff;
      border-radius: 8px; padding: 12px 16px; text-align: center;
  }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Session defaults
# ─────────────────────────────────────────────────────────────────────────────
DEFAULTS = {
    "messages":       [],
    "vectorstore":    None,
    "df":             None,
    "mode":           "chat",
    "pdf_names":      [],          # list of uploaded PDF names (multi-PDF)
    "excel_name":     None,
    "model":          "llama3.2",
    "kb_vectorstore": None,
    "kb_loaded":      False,
    "image_file":     None,
    "image_name":     None,
    "vision_model": "llava",
    "msg_id_counter": 0,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# Feedback logger (define before use above)
# ─────────────────────────────────────────────────────────────────────────────
def _log_feedback(msg_id, content_preview, rating, path):
    row = [
        datetime.datetime.now().isoformat(),
        msg_id,
        rating,
        content_preview.replace("\n", " "),
    ]
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["timestamp", "msg_id", "rating", "content_preview"])
        w.writerow(row)

# ─────────────────────────────────────────────────────────────────────────────
# Load knowledge base once
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.kb_loaded:
    try:
        with st.spinner("Loading SLT knowledge base..."):
            st.session_state.kb_vectorstore = load_knowledge_base()
    except Exception as e:
        st.session_state.kb_vectorstore = None
        print(f"[app] KB error: {e}")
    finally:
        st.session_state.kb_loaded = True

# ─────────────────────────────────────────────────────────────────────────────
# Logo
# ─────────────────────────────────────────────────────────────────────────────
try:
    with open(LOGO_PATH, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{img_data}" style="width:100%;height:100%;object-fit:contain;" />'
except Exception:
    logo_html = "🤖"

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
            <div style="width:42px;height:42px;min-width:42px;border-radius:50%;
                        overflow:hidden;background:white;border:2px solid #ddd;">
                {logo_html}
            </div>
            <div style="font-size:1.7rem;font-weight:700;color:#1a1a2e;">SLT Insight</div>
        </div><hr style="margin:0 0 1rem 0;">""",
        unsafe_allow_html=True,
    )

    # Model selector
    model = st.selectbox("🧠 LLM Model", ["llama3.2", "llama3"], index=0)
    st.session_state.model = model
    st.markdown("---")

    # Mode selector
    st.markdown("### 🔀 Mode")
    mode_choice = st.radio(
        "Select mode",
        ["💬 General chat", "📄 PDF Q&A", "📊 Excel charts", "🖼️ Image Q&A"],
        index=0,
    )
    st.session_state.mode = (
        "pdf"   if "PDF"   in mode_choice else
        "excel" if "Excel" in mode_choice else
        "image" if "Image" in mode_choice else
        "chat"
    )
    st.markdown("---")

    # Knowledge base status
    if st.session_state.kb_vectorstore is not None:
        st.success("✅ Knowledge base ready")
    else:
        st.warning("⚠️ No knowledge base")
        if st.button("🔄 Build from PDFs"):
            try:
                with st.spinner("Building..."):
                    st.session_state.kb_vectorstore = build_knowledge_base()
                st.success("✅ Built!")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    st.markdown("---")

    # ── PDF mode ───────────────────────────────────────────────
    if st.session_state.mode == "pdf":
        st.markdown("### 📄 Upload PDF(s)")
        pdf_files = st.file_uploader(
            "Upload one or more PDFs",
            type=["pdf"],
            accept_multiple_files=True,
        )
        if pdf_files:
            new_names = [f.name for f in pdf_files]
            if new_names != st.session_state.pdf_names:
                with st.spinner("Indexing PDFs..."):
                    all_chunks = []
                    for pf in pdf_files:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(pf.read())
                            tmp_path = tmp.name
                        chunks = load_and_split_pdf(tmp_path)
                        all_chunks.extend(chunks)
                        os.unlink(tmp_path)
                    st.session_state.vectorstore = create_vectorstore(all_chunks, model=model)
                    st.session_state.pdf_names   = new_names
                st.success(f"✅ Indexed {len(pdf_files)} PDF(s)")
            else:
                st.success(f"✅ {len(pdf_files)} PDF(s) loaded")

    # ── Excel mode ─────────────────────────────────────────────
    if st.session_state.mode == "excel":
        st.markdown("### 📊 Upload Excel / CSV")
        excel_file = st.file_uploader("Upload file", type=["xlsx", "xls", "csv"])
        if excel_file:
            if excel_file.name != st.session_state.excel_name:
                with st.spinner("Loading..."):
                    df, _ = load_excel(excel_file)
                    st.session_state.df         = df
                    st.session_state.excel_name = excel_file.name
                st.success(f"✅ {excel_file.name}")
            else:
                st.success(f"✅ {excel_file.name}")

    # ── Image mode ─────────────────────────────────────────────
    if st.session_state.mode == "image":
        st.markdown("### 🖼️ Upload Image")
        image_file = st.file_uploader(
            "Bill, receipt, or photo",
            type=["jpg", "jpeg", "png", "webp", "bmp"],
        )
        if image_file:
            st.image(image_file, use_container_width=True)
            st.session_state.image_file = image_file
            st.session_state.image_name = image_file.name
            st.success(f"✅ {image_file.name}")

        vision_model = st.selectbox(
            "Vision model",
            ["llava", "moondream", "llava:13b"],
            index=0,
        )
        st.session_state.vision_model = vision_model
        captions = {
            "moondream": "⚡ Fast, lightweight. `ollama pull moondream`",
            "llava":     "🎯 More accurate. `ollama pull llava`",
            "llava:13b": "🔬 Best quality, needs 16GB RAM.",
        }
        st.caption(captions.get(vision_model, ""))
        st.caption("💡 If vision fails, OCR fallback activates automatically.")

    # ── Clear chat ─────────────────────────────────────────────
    if st.button("🗑️ Clear chat"):
        st.session_state.messages   = []
        st.session_state.image_file = None
        st.session_state.image_name = None
        st.rerun()

    # ── Export chat ────────────────────────────────────────────
    if st.session_state.messages:
        st.markdown("---")
        if st.button("📥 Export chat as TXT"):
            chat_text = "\n\n".join(
                f"[{m['role'].upper()}]\n{m['content']}"
                for m in st.session_state.messages
            )
            st.download_button(
                label    = "⬇️ Download",
                data     = chat_text,
                file_name= f"slt_chat_{datetime.datetime.now():%Y%m%d_%H%M}.txt",
                mime     = "text/plain",
            )

    st.markdown("---")
    st.caption("• Powered by Ollama + LangChain")

# ─────────────────────────────────────────────────────────────────────────────
# Welcome screen (no messages yet)
# ─────────────────────────────────────────────────────────────────────────────
if len(st.session_state.messages) == 0:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
            <div style="text-align:center;margin-top:80px;margin-bottom:60px;">
                <div style="display:flex;justify-content:center;margin-bottom:25px;">
                    <div style="width:90px;height:90px;
                                background:linear-gradient(135deg,#00c6ff,#0072ff);
                                border-radius:50%;display:flex;align-items:center;
                                justify-content:center;
                                box-shadow:0 10px 30px rgba(0,198,255,0.3);">
                        <span style="font-size:50px;">🤖</span>
                    </div>
                </div>
                <h1 style="font-size:2.4rem;font-weight:700;color:#1a1a2e;margin:0 0 12px 0;">
                    Hello, I'm SLT Insight
                </h1>
                <p style="font-size:1.3rem;color:#555;margin:0 0 24px 0;">
                    Your AI assistant for SLT Mobitel
                </p>
                <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;">
                    {''.join(f'<div style="background:#f0f4ff;border:1px solid #c7d4f5;border-radius:8px;padding:8px 16px;font-size:0.85rem;color:#1a3c8c;">{t}</div>' for t in [
                        "📶 SLT fiber packages",
                        "📊 Excel chart builder",
                        "📄 Annual report Q&A",
                        "🖼️ Read SLT bill image",
                        "🔍 Correlation heatmap",
                    ])}
                </div>
            </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Excel data stats panel
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.mode == "excel" and st.session_state.df is not None:
    df = st.session_state.df
    stats = get_quick_stats(df)

    with st.expander("📋 Dataset Overview", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows",        stats["rows"])
        c2.metric("Columns",     stats["columns"])
        c3.metric("Numeric cols", len(stats["numeric_cols"]))
        c4.metric("Missing %",   f"{stats['missing_pct']}%")

        tab1, tab2 = st.tabs(["📊 Numeric Summary", "🏷️ Top Categories"])
        with tab1:
            if stats["numeric_summary"]:
                import pandas as pd
                st.dataframe(pd.DataFrame(stats["numeric_summary"]).round(2), use_container_width=True)
            else:
                st.info("No numeric columns.")
        with tab2:
            for col, counts in stats["top_categories"].items():
                st.markdown(f"**{col}**")
                for val, cnt in list(counts.items())[:5]:
                    st.markdown(f"&nbsp;&nbsp;`{val}` — {cnt:,}")

# ─────────────────────────────────────────────────────────────────────────────
# Chat history
# ─────────────────────────────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "chart" in msg:
            st.plotly_chart(msg["chart"], use_container_width=True)

        # Feedback buttons for assistant messages
        if msg["role"] == "assistant":
            col_a, col_b, col_c = st.columns([1, 1, 10])
            msg_id = msg.get("id", i)
            with col_a:
                if st.button("👍", key=f"up_{msg_id}"):
                    _log_feedback(msg_id, msg["content"][:80], "up", FEEDBACK_LOG)
                    st.toast("Thanks for the feedback!", icon="✅")
            with col_b:
                if st.button("👎", key=f"dn_{msg_id}"):
                    _log_feedback(msg_id, msg["content"][:80], "down", FEEDBACK_LOG)
                    st.toast("We'll work to improve!", icon="🔧")

# ─────────────────────────────────────────────────────────────────────────────
# Voice input (improved: audio_recorder_streamlit)
# ─────────────────────────────────────────────────────────────────────────────
voice_input = None

st.markdown("---")
st.markdown("#### 🎙️ Voice Input")

try:
    from audio_recorder_streamlit import audio_recorder
    import speech_recognition as sr
    from pydub import AudioSegment

    col_mic, col_status = st.columns([1, 4])
    with col_mic:
        audio_bytes = audio_recorder(
            text            = "",
            recording_color = "#e8123c",
            neutral_color   = "#0072ff",
            icon_size       = "2x",
            pause_threshold = 2.0,
        )
    with col_status:
        if audio_bytes:
            st.info("🎙️ Processing your voice...")
        else:
            st.caption("Click the mic to speak your question")

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
            st.warning("⚠️ Could not understand audio. Please speak clearly and try again.")
        except sr.RequestError:
            st.warning("⚠️ Voice recognition service unavailable. Check your internet connection.")
        except Exception as e:
            st.warning(f"⚠️ Voice error: {e}")

except ImportError:
    st.warning(
        "⚠️ Voice input not available. Install it with:\n"
        "```\npip install audio-recorder-streamlit SpeechRecognition pydub\n```"
    )
# ─────────────────────────────────────────────────────────────────────────────
# Chat input
# ─────────────────────────────────────────────────────────────────────────────
PLACEHOLDERS = {
    "chat":  "Ask about SLT (e.g. What are SLT fiber plans?)",
    "pdf":   "Ask about your PDF (e.g. What is SLT's net revenue?)",
    "excel": "Ask for a chart (e.g. Bar chart of Churn by Contract)",
    "image": "Ask about the image (e.g. What is my total bill?)",
}
user_input = st.chat_input(PLACEHOLDERS[st.session_state.mode])
if voice_input and not user_input:
    user_input = voice_input

# ─────────────────────────────────────────────────────────────────────────────
# Handle input
# ─────────────────────────────────────────────────────────────────────────────
if user_input:
    msg_id = st.session_state.msg_id_counter
    st.session_state.msg_id_counter += 1

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        mode = st.session_state.mode

        # ── PDF mode ───────────────────────────────────────────
        if mode == "pdf":
            if st.session_state.vectorstore is None and st.session_state.kb_vectorstore is None:
                reply = "⚠️ Please upload a PDF or build the knowledge base first."
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply, "id": msg_id})
            else:
                vs = st.session_state.vectorstore or st.session_state.kb_vectorstore
                with st.spinner("Searching document..."):
                    reply = get_answer(user_input, vs, model=st.session_state.model)
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply, "id": msg_id})

        # ── Excel mode ─────────────────────────────────────────
        elif mode == "excel":
            if st.session_state.df is None:
                reply = "⚠️ Please upload an Excel or CSV file first."
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply, "id": msg_id})
            else:
                with st.spinner("Building chart..."):
                    reply_text, fig = build_chart(
                        user_input,
                        st.session_state.df,
                        model=st.session_state.model,
                    )
                st.markdown(reply_text)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    st.session_state.messages.append({
                        "role": "assistant", "content": reply_text,
                        "chart": fig, "id": msg_id,
                    })
                else:
                    st.session_state.messages.append({
                        "role": "assistant", "content": reply_text, "id": msg_id,
                    })

        # ── Image mode ─────────────────────────────────────────
        elif mode == "image":
            if st.session_state.image_file is None:
                reply = "⚠️ Please upload an image first."
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply, "id": msg_id})
            else:
                vision_model = st.session_state.get("vision_model", "moondream")
                with st.spinner(
                    f"Analyzing image with {vision_model}... "
                    "(OCR fallback will activate if needed)"
                ):
                    try:
                        st.session_state.image_file.seek(0)
                    except Exception:
                        pass
                    reply = ask_image_question(
                        st.session_state.image_file,
                        user_input,
                        model=vision_model,
                    )
                st.markdown(reply)
                st.session_state.messages.append({
                    "role": "assistant", "content": reply, "id": msg_id,
                })

        # ── General chat mode ──────────────────────────────────
        else:
            with st.spinner("Thinking..."):
                from langchain_ollama import OllamaLLM
                llm = OllamaLLM(model=st.session_state.model)

                # Sliding window conversation history
                history = ""
                for m in st.session_state.messages[-8:]:
                    role     = "User" if m["role"] == "user" else "Assistant"
                    history += f"{role}: {m['content']}\n"

                # KB context
                kb_context = ""
                if st.session_state.kb_vectorstore is not None:
                    try:
                        docs = st.session_state.kb_vectorstore.as_retriever(
                            search_kwargs={"k": 4}
                        ).invoke(user_input)
                        kb_context = "\n\n".join(d.page_content for d in docs)
                    except Exception:
                        kb_context = ""

                if kb_context:
                    prompt = f"""You are SLT Insight — a professional AI assistant for SLT Mobitel Sri Lanka.
Use the knowledge base below for accurate answers.
Only answer questions about SLT, Sri Lanka Telecom, telecom products, or SLT financials.
For anything unrelated, say: "I can only assist with SLT-related topics."

Knowledge Base:
{kb_context}

Conversation:
{history}
User: {user_input}
Assistant:"""
                else:
                    prompt = f"""You are SLT Insight — a professional AI assistant for SLT Mobitel Sri Lanka.
Only answer questions about SLT, Sri Lanka Telecom, telecom services, or SLT financials.
For anything unrelated, say: "I can only assist with SLT-related topics."

Conversation:
{history}
User: {user_input}
Assistant:"""

                reply = llm.invoke(prompt)

            st.markdown(reply)
            st.session_state.messages.append({
                "role": "assistant", "content": reply, "id": msg_id,
            })