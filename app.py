import streamlit as st
import os
import tempfile
import base64
import io

from rag.pdf_loader import load_and_split_pdf
from rag.embedder import create_vectorstore
from rag.retriever import get_answer
from rag.knowledge_base import load_knowledge_base, build_knowledge_base
from rag.image_reader import ask_image_question
from analysis.excel_reader import load_excel
from analysis.chart_builder import build_chart

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SLT AI Chatbot",
    page_icon="F:/Slt_chatbotnew/sltlogo.png",
    layout="wide",
)

st.markdown("""
<style>
    .main-title { font-size: 1.5rem; font-weight: 700; color: #1a1a2e; }
    .sub-title  { font-size: 1.0rem; color: #555; margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
defaults = {
    "messages":       [],
    "vectorstore":    None,
    "df":             None,
    "mode":           "chat",
    "pdf_name":       None,
    "excel_name":     None,
    "model":          "llama3.2",
    "kb_vectorstore": None,
    "kb_loaded":      False,
    "image_file":     None,
    "image_name":     None,
    "vision_model":   "llava",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Load knowledge base once ───────────────────────────────────────────────────
if not st.session_state.kb_loaded:
    try:
        with st.spinner("Loading SLT knowledge base..."):
            st.session_state.kb_vectorstore = load_knowledge_base(
                model=st.session_state.model
            )
    except Exception as e:
        st.session_state.kb_vectorstore = None
        print(f"[app] KB load error: {e}")
    finally:
        st.session_state.kb_loaded = True

# ── Logo ───────────────────────────────────────────────────────────────────────
with open("F:/Slt_chatbotnew/sltlogo.png", "rb") as f:
    img_data = base64.b64encode(f.read()).decode()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
            <div style="width:42px;height:42px;min-width:42px;border-radius:50%;
                        overflow:hidden;background-color:white;border:2px solid #ddd;">
                <img src="data:image/png;base64,{img_data}"
                     style="width:100%;height:100%;object-fit:contain;" />
            </div>
            <div style="font-size:1.7rem;font-weight:700;color:#1a1a2e;">SLT Insight</div>
        </div>
        <hr style="margin:0 0 1rem 0;">
        """,
        unsafe_allow_html=True,
    )

    model = st.selectbox("Ollama Model", ["llama3.2", "llama3"], index=0)
    st.session_state.model = model
    st.markdown("---")

    # ── Mode selector ──────────────────────────────────────────
    st.markdown("### Mode")
    mode_choice = st.radio(
        "Select what you want to do",
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

    # ── Knowledge base status ──────────────────────────────────
    if st.session_state.kb_vectorstore is not None:
        st.success("✅ Knowledge base loaded")
    else:
        st.warning("⚠️ No knowledge base found")
        if st.button("🔄 Build knowledge base"):
            try:
                with st.spinner("Building knowledge base from PDFs..."):
                    st.session_state.kb_vectorstore = build_knowledge_base(
                        model=st.session_state.model
                    )
                st.success("✅ Knowledge base built!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    st.markdown("---")

    # ── PDF upload ─────────────────────────────────────────────
    if st.session_state.mode == "pdf":
        st.markdown("### 📄 Upload PDF")
        pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
        if pdf_file:
            if pdf_file.name != st.session_state.pdf_name:
                with st.spinner("Reading & indexing PDF..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(pdf_file.read())
                        tmp_path = tmp.name
                    chunks = load_and_split_pdf(tmp_path)
                    st.session_state.vectorstore = create_vectorstore(chunks, model=model)
                    st.session_state.pdf_name    = pdf_file.name
                    os.unlink(tmp_path)
                st.success(f"✅ Indexed: {pdf_file.name}")
            else:
                st.success(f"✅ Loaded: {pdf_file.name}")

    # ── Excel upload ───────────────────────────────────────────
    if st.session_state.mode == "excel":
        st.markdown("### 📊 Upload Excel")
        excel_file = st.file_uploader(
            "Upload Excel file", type=["xlsx", "xls", "csv"]
        )
        if excel_file:
            if excel_file.name != st.session_state.excel_name:
                with st.spinner("Loading spreadsheet..."):
                    df, _ = load_excel(excel_file)
                    st.session_state.df         = df
                    st.session_state.excel_name = excel_file.name
                st.success(f"✅ Loaded: {excel_file.name}")
            else:
                st.success(f"✅ Loaded: {excel_file.name}")

    # ── Image upload ───────────────────────────────────────────
    if st.session_state.mode == "image":
        st.markdown("### 🖼️ Upload Image")
        image_file = st.file_uploader(
            "Upload image (bill, receipt, photo)",
            type=["jpg", "jpeg", "png", "webp", "bmp"],
        )
        if image_file:
            st.image(image_file, caption="Uploaded image", use_container_width=True)
            st.session_state.image_file = image_file
            st.session_state.image_name = image_file.name
            st.success(f"✅ Loaded: {image_file.name}")

        # ── Vision model selector ──────────────────────────────
        st.markdown("**Vision model**")
        vision_model = st.selectbox(
            "Vision model",
            ["llava", "moondream", "llava:13b"],
            index=0,
            label_visibility="collapsed",
        )
        st.session_state.vision_model = vision_model

        if vision_model == "llava":
            st.caption("Accurate but slow. Run: `ollama pull llava`")
        elif vision_model == "moondream":
            st.caption("Fast and lightweight. Run: `ollama pull moondream`")
        else:
            st.caption("High quality, needs 16GB RAM. Run: `ollama pull llava:13b`")

    # ── Clear chat ─────────────────────────────────────────────
    if st.button("🗑️ Clear chat"):
        st.session_state.messages  = []
        st.session_state.image_file = None
        st.session_state.image_name = None
        st.rerun()

    st.markdown("---")
    st.caption("• Powered by Ollama")

# ── Main area ──────────────────────────────────────────────────────────────────
if len(st.session_state.messages) == 0:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
            <div style="text-align:center;margin-top:100px;margin-bottom:60px;">
                <div style="display:flex;justify-content:center;margin-bottom:25px;">
                    <div style="width:90px;height:90px;
                                background:linear-gradient(135deg,#00c6ff,#0072ff);
                                border-radius:50%;display:flex;align-items:center;
                                justify-content:center;
                                box-shadow:0 10px 30px rgba(0,198,255,0.3);">
                        <span style="font-size:50px;">🤖</span>
                    </div>
                </div>
                <h1 style="font-size:2.6rem;font-weight:700;color:#1a1a2e;margin:0 0 12px 0;">
                    Hello, I'm SLT Insight
                </h1>
                <p style="font-size:1.45rem;color:#555;margin:0;">
                    How can I help you today?
                </p>
                <div style="display:flex;gap:10px;flex-wrap:wrap;
                            justify-content:center;margin-top:24px;">
                    <div style="background:#f0f4ff;border:1px solid #c7d4f5;
                                border-radius:8px;padding:8px 16px;
                                font-size:0.85rem;color:#1a3c8c;">
                        📶 SLT fiber packages
                    </div>
                    <div style="background:#f0f4ff;border:1px solid #c7d4f5;
                                border-radius:8px;padding:8px 16px;
                                font-size:0.85rem;color:#1a3c8c;">
                        📊 Upload Excel for charts
                    </div>
                    <div style="background:#f0f4ff;border:1px solid #c7d4f5;
                                border-radius:8px;padding:8px 16px;
                                font-size:0.85rem;color:#1a3c8c;">
                        📄 Ask about annual report
                    </div>
                    <div style="background:#f0f4ff;border:1px solid #c7d4f5;
                                border-radius:8px;padding:8px 16px;
                                font-size:0.85rem;color:#1a3c8c;">
                        🖼️ Upload SLT bill image
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# ── Excel data preview ─────────────────────────────────────────────────────────
if st.session_state.mode == "excel" and st.session_state.df is not None:
    with st.expander("📋 Data preview", expanded=False):
        st.dataframe(st.session_state.df.head(20))

# ── Chat history ───────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "chart" in msg:
            st.plotly_chart(msg["chart"])
        if "image" in msg:
            st.image(msg["image"], width=300)

# ── Voice input ────────────────────────────────────────────────────────────────
voice_input = None
if st.session_state.mode in ["chat", "pdf"]:
    try:
        from streamlit_mic_recorder import mic_recorder
        st.markdown("#### 🎙️ Or speak your question")
        audio = mic_recorder(
            start_prompt="🎙️ Click to speak",
            stop_prompt="⏹️ Stop recording",
            just_once=True,
            use_container_width=False,
            key="mic",
        )
    except ImportError:
        audio = None
else:
    audio = None

if audio and audio.get("bytes"):
    try:
        from pydub import AudioSegment
        import speech_recognition as sr

        audio_segment = AudioSegment.from_file(io.BytesIO(audio["bytes"]))
        wav_buffer    = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        wav_buffer.seek(0)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_buffer) as source:
            audio_data = recognizer.record(source)
        voice_input = recognizer.recognize_google(audio_data, language="en-US")
        st.info(f"🎙️ You said: **{voice_input}**")
    except Exception as e:
        st.warning(f"Voice error: {e}")

# ── Chat input ─────────────────────────────────────────────────────────────────
placeholder_map = {
    "chat":  "Ask about SLT (e.g. What are SLT fiber packages?)",
    "pdf":   "Ask about the PDF (e.g. What is SLT's net revenue?)",
    "excel": "Ask for a chart (e.g. Bar chart of Churn by InternetService)",
    "image": "Ask about the image (e.g. What is my total bill amount?)",
}
user_input = st.chat_input(placeholder_map[st.session_state.mode])
if voice_input and not user_input:
    user_input = voice_input

# ── Handle user input ──────────────────────────────────────────────────────────
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        mode = st.session_state.mode

        # ── PDF mode ───────────────────────────────────────────
        if mode == "pdf":
            if st.session_state.vectorstore is None:
                reply = "⚠️ Please upload a PDF first using the sidebar."
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            else:
                with st.spinner("Searching document..."):
                    reply = get_answer(
                        user_input,
                        st.session_state.vectorstore,
                        model=st.session_state.model,
                    )
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

        # ── Excel mode ─────────────────────────────────────────
        elif mode == "excel":
            if st.session_state.df is None:
                reply = "⚠️ Please upload an Excel file first using the sidebar."
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            else:
                with st.spinner("Building chart and generating summary..."):
                    reply_text, fig = build_chart(
                        user_input,
                        st.session_state.df,
                        model=st.session_state.model,
                    )
                st.markdown(reply_text)
                if fig:
                    st.plotly_chart(fig)
                    st.session_state.messages.append({
                        "role": "assistant", "content": reply_text, "chart": fig
                    })
                else:
                    st.session_state.messages.append({
                        "role": "assistant", "content": reply_text
                    })

        # ── Image mode ─────────────────────────────────────────
        elif mode == "image":
            if st.session_state.image_file is None:
                reply = "⚠️ Please upload an image first using the sidebar."
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            else:
                vision_model = st.session_state.get("vision_model", "llava")
                with st.spinner(
                    f"Analyzing image with {vision_model}... "
                    f"This may take 1–3 minutes. Please wait."
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
                    "role": "assistant",
                    "content": reply,
                })

        # ── General chat mode ──────────────────────────────────
        else:
            with st.spinner("Thinking..."):
                from langchain_ollama import OllamaLLM
                llm = OllamaLLM(model=st.session_state.model)

                history = ""
                for m in st.session_state.messages[-6:]:
                    role     = "User" if m["role"] == "user" else "Assistant"
                    history += f"{role}: {m['content']}\n"

                kb_context = ""
                if st.session_state.kb_vectorstore is not None:
                    try:
                        kb_docs = st.session_state.kb_vectorstore.as_retriever(
                            search_kwargs={"k": 3}
                        ).invoke(user_input)
                        kb_context = "\n\n".join(d.page_content for d in kb_docs)
                    except Exception:
                        kb_context = ""

                if kb_context:
                    prompt = f"""You are SLT Insight AI, a dedicated assistant for SLT (Sri Lanka Telecom).
Use the knowledge base context below to answer accurately.
You ONLY answer questions related to SLT products, services, financials, network, or Sri Lanka telecom.
If unrelated, reply: "I can only assist with SLT related questions."

Knowledge Base Context:
{kb_context}

Conversation history:
{history}
User: {user_input}
Assistant:"""
                else:
                    prompt = f"""You are a dedicated AI assistant for SLT (Sri Lanka Telecom).
You ONLY answer questions related to SLT products, services, financials, network, or Sri Lanka telecom.
If unrelated, reply: "I can only assist with SLT related questions."

Conversation history:
{history}
User: {user_input}
Assistant:"""

                reply = llm.invoke(prompt)

            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})