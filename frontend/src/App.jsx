import { useState, useEffect, useRef } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Plot from "react-plotly.js";

const API        = "http://localhost:8000";
const SESSION_ID = "user_" + Math.random().toString(36).substr(2, 9);
const LOGO_URL   = `${API}/logo`;

const INTENT_COLORS = {
  pdf:   { bg: "#e8f4fd", border: "#3498db", label: "📄 PDF Knowledge Base" },
  excel: { bg: "#e8fdf0", border: "#2ecc71", label: "📊 Excel Data" },
  image: { bg: "#fdf0e8", border: "#e67e22", label: "🖼️ Image Analysis" },
  chat:  { bg: "#f0e8fd", border: "#9b59b6", label: "💬 SLT Knowledge" },
  flow:  { bg: "#fdfde8", border: "#f39c12", label: "🎯 Guided Flow" },
};

function SltLogo({ size = 42, style = {} }) {
  const [err, setErr] = useState(false);
  return (
    <div style={{
      width: size, height: size, borderRadius: "50%", flexShrink: 0,
      background: "white", border: "2px solid #e2e8f0",
      display: "flex", alignItems: "center", justifyContent: "center",
      overflow: "hidden", ...style,
    }}>
      {!err
        ? <img src={LOGO_URL} alt="SLT" onError={() => setErr(true)}
            style={{ width: "85%", height: "85%", objectFit: "contain" }} />
        : <span style={{ fontSize: size * 0.45 }}>🤖</span>
      }
    </div>
  );
}

export default function App() {
  const [messages,     setMessages]     = useState([]);
  const [input,        setInput]        = useState("");
  const [loading,      setLoading]      = useState(false);
  const [sessionInfo,  setSessionInfo]  = useState(null);
  const [activeFlow,   setActiveFlow]   = useState(null);
  const [model,        setModel]        = useState("llama3.2");
  const [visionModel,  setVisionModel]  = useState("llava");
  const [kbStatus,     setKbStatus]     = useState(false);
  const [buildingKb,   setBuildingKb]   = useState(false);
  const [imagePreview, setImagePreview] = useState(null);
  const [sidebarOpen,  setSidebarOpen]  = useState(true);
  const [recording,    setRecording]    = useState(false);
  const [dragOver,     setDragOver]     = useState(null);
  const [toast,        setToast]        = useState(null);

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const pdfInputRef    = useRef(null);
  const excelInputRef  = useRef(null);
  const imageInputRef  = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    fetchSessionInfo();
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const res = await axios.get(`${API}/health`);
      setKbStatus(res.data.kb_loaded);
    } catch {}
  };

  const fetchSessionInfo = async () => {
    try {
      const res = await axios.get(`${API}/session/${SESSION_ID}`);
      setSessionInfo(res.data);
      setActiveFlow(res.data.active_flow);
    } catch {}
  };

  const sendMessage = async (text) => {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: msg, id: Date.now() }]);
    setLoading(true);
    try {
      const res  = await axios.post(`${API}/chat`, {
        session_id: SESSION_ID, message: msg, model, vision_model: visionModel,
      });
      const data = res.data;
      setActiveFlow(data.active_flow || null);
      setMessages(prev => [...prev, {
        role: "assistant", content: data.response, intent: data.intent,
        figure: data.figure ? JSON.parse(data.figure) : null,
        sources: data.sources, id: Date.now() + 1,
      }]);
      await fetchSessionInfo();
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "❌ Error connecting to server. Make sure the backend is running.",
        intent: "chat", id: Date.now() + 1,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const uploadPdf = async (files) => {
    const fd = new FormData();
    fd.append("session_id", SESSION_ID);
    Array.from(files).forEach(f => fd.append("files", f));
    try {
      await axios.post(`${API}/upload/pdf`, fd);
      await fetchSessionInfo();
      addSys(`✅ ${files.length} PDF(s) indexed successfully!`);
    } catch { addSys("❌ PDF upload failed."); }
  };

  const uploadExcel = async (file) => {
    const fd = new FormData();
    fd.append("session_id", SESSION_ID);
    fd.append("file", file);
    try {
      const res = await axios.post(`${API}/upload/excel`, fd);
      await fetchSessionInfo();
      const s = res.data.stats;
      addSys(`✅ **${file.name}** loaded — ${s.rows} rows, ${s.columns} columns`);
    } catch { addSys("❌ Excel upload failed."); }
  };

  const uploadImage = async (file) => {
    const fd = new FormData();
    fd.append("session_id", SESSION_ID);
    fd.append("file", file);
    try {
      const res = await axios.post(`${API}/upload/image`, fd);
      setImagePreview(res.data.preview);
      await fetchSessionInfo();
      addSys(`✅ **${file.name}** uploaded — ask me anything about it!`);
    } catch { addSys("❌ Image upload failed."); }
  };

  const addSys = (text) =>
    setMessages(prev => [...prev, { role: "system", content: text, id: Date.now() }]);

  const showToast = (msg, duration = 3000) => {
    setToast(msg);
    setTimeout(() => setToast(null), duration);
  };

  const toggleVoice = () => {
    const isBrave = navigator.brave !== undefined;
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      if (isBrave) {
        alert("Voice input is blocked in Brave.\n\nFix: Go to brave://settings/privacy and enable Google services.\n\nOr use Google Chrome.");
      } else {
        alert("Voice not supported. Use Chrome.");
      }
      return;
    }
    if (recording) { recognitionRef.current?.stop(); setRecording(false); return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const r  = new SR();
    r.lang = "en-US"; r.interimResults = false; r.continuous = false;
    r.onresult = (e) => { setInput(e.results[0][0].transcript); setRecording(false); };
    r.onerror  = (e) => {
      if (e.error === "not-allowed") alert("Microphone access denied. Allow microphone in browser settings.");
      setRecording(false);
    };
    r.onend = () => setRecording(false);
    recognitionRef.current = r;
    r.start();
    setRecording(true);
  };

  const sendFeedback = async (msgId, content, rating) => {
    try {
      await axios.post(`${API}/feedback`, {
        session_id: SESSION_ID, msg_id: String(msgId), rating,
        content: content.slice(0, 100),
      });
      showToast(rating === "up" ? "👍 Thanks for your feedback!" : "👎 Thanks! We'll work to improve.");
    } catch {
      showToast("❌ Feedback failed. Please try again.");
    }
  };

  const clearChat = async () => {
    await axios.delete(`${API}/session/${SESSION_ID}`);
    setMessages([]); setActiveFlow(null); setImagePreview(null);
    await fetchSessionInfo();
  };

  const exportChat = () => window.open(`${API}/export/${SESSION_ID}`, "_blank");

  const buildKb = async () => {
    setBuildingKb(true);
    try {
      await axios.post(`${API}/kb/build`);
      setKbStatus(true);
      addSys("✅ Knowledge base built successfully!");
    } catch { addSys("❌ KB build failed. Add PDFs to knowledge_base/ folder."); }
    finally { setBuildingKb(false); }
  };

  const handleDrop = async (e, type) => {
    e.preventDefault(); setDragOver(null);
    const files = e.dataTransfer.files;
    if (!files.length) return;
    if (type === "pdf")   await uploadPdf(files);
    if (type === "excel") await uploadExcel(files[0]);
    if (type === "image") await uploadImage(files[0]);
  };

  const SUGGESTIONS = [
    "How to select fiber package?",
    "What is my total bill amount?",
    "Bar chart of Churn by Contract",
    "Which PeoTV package suits me?",
    "SLT hotline number",
    "Show correlation heatmap",
  ];

  return (
    <div style={S.app}>
      {/* ── SIDEBAR ───────────────────────────────────────── */}
      <aside style={{ ...S.sidebar, width: sidebarOpen ? 280 : 0, overflow: sidebarOpen ? "auto" : "hidden" }}>
        <div style={S.sidebarHeader}>
          <SltLogo size={44} />
          <div>
            <div style={S.logoTitle}>SLT Insight</div>
            <div style={S.logoSub}>Powered by LangGraph</div>
          </div>
        </div>

        <div style={S.section}>
          <div style={S.secTitle}>⚙️ Settings</div>
          <label style={S.label}>LLM Model</label>
          <select style={S.select} value={model} onChange={e => setModel(e.target.value)}>
            <option value="llama3.2">llama3.2</option>
            <option value="llama3">llama3</option>
          </select>
          <label style={S.label}>Vision Model</label>
          <select style={S.select} value={visionModel} onChange={e => setVisionModel(e.target.value)}>
            <option value="llava">llava</option>
            <option value="moondream">moondream</option>
            <option value="llava:13b">llava:13b</option>
          </select>
        </div>

        <div style={S.section}>
          <div style={S.secTitle}>🧠 Knowledge Base</div>
          {kbStatus
            ? <div style={S.successBadge}>✅ SLT Knowledge Base ready</div>
            : <div style={S.warnBadge}>⚠️ No knowledge base</div>}
          {!kbStatus && (
            <button style={S.btnSec} onClick={buildKb} disabled={buildingKb}>
              {buildingKb ? "⏳ Building..." : "🔄 Build from PDFs"}
            </button>
          )}
        </div>

        <div style={S.section}>
          <div style={S.secTitle}>📁 Upload Files</div>
          <div style={{ ...S.dropZone, borderColor: dragOver === "pdf" ? "#3498db" : "#ddd" }}
            onDragOver={e => { e.preventDefault(); setDragOver("pdf"); }}
            onDragLeave={() => setDragOver(null)}
            onDrop={e => handleDrop(e, "pdf")}
            onClick={() => pdfInputRef.current.click()}>
            <div style={S.dropIcon}>📄</div>
            <div style={S.dropText}>PDF Documents</div>
            <div style={S.dropSub}>Drop here or click</div>
            {sessionInfo?.pdf_names?.length > 0 &&
              <div style={S.uploadedBadge}>✅ {sessionInfo.pdf_names.length} PDF(s)</div>}
          </div>
          <input ref={pdfInputRef} type="file" accept=".pdf" multiple hidden
            onChange={e => uploadPdf(e.target.files)} />

          <div style={{ ...S.dropZone, borderColor: dragOver === "excel" ? "#2ecc71" : "#ddd" }}
            onDragOver={e => { e.preventDefault(); setDragOver("excel"); }}
            onDragLeave={() => setDragOver(null)}
            onDrop={e => handleDrop(e, "excel")}
            onClick={() => excelInputRef.current.click()}>
            <div style={S.dropIcon}>📊</div>
            <div style={S.dropText}>Excel / CSV</div>
            <div style={S.dropSub}>Drop here or click</div>
            {sessionInfo?.excel_name &&
              <div style={S.uploadedBadge}>✅ {sessionInfo.excel_name}</div>}
          </div>
          <input ref={excelInputRef} type="file" accept=".xlsx,.xls,.csv" hidden
            onChange={e => uploadExcel(e.target.files[0])} />

          <div style={{ ...S.dropZone, borderColor: dragOver === "image" ? "#e67e22" : "#ddd" }}
            onDragOver={e => { e.preventDefault(); setDragOver("image"); }}
            onDragLeave={() => setDragOver(null)}
            onDrop={e => handleDrop(e, "image")}
            onClick={() => imageInputRef.current.click()}>
            <div style={S.dropIcon}>🖼️</div>
            <div style={S.dropText}>Bill / Image</div>
            <div style={S.dropSub}>Drop here or click</div>
            {imagePreview && <img src={imagePreview} style={S.imgThumb} alt="preview" />}
          </div>
          <input ref={imageInputRef} type="file" accept=".jpg,.jpeg,.png,.webp,.bmp" hidden
            onChange={e => uploadImage(e.target.files[0])} />
        </div>

        {sessionInfo && (
          <div style={S.section}>
            <div style={S.secTitle}>📌 Active Context</div>
            {kbStatus              && <div style={S.ctxItem}>🧠 SLT Knowledge Base</div>}
            {sessionInfo.has_pdf   && <div style={S.ctxItem}>📄 {sessionInfo.pdf_names?.join(", ")}</div>}
            {sessionInfo.has_excel && <div style={S.ctxItem}>📊 {sessionInfo.excel_name}</div>}
            {sessionInfo.has_image && <div style={S.ctxItem}>🖼️ {sessionInfo.image_name}</div>}
            {activeFlow && <div style={S.flowBadge}>🎯 Guided flow active</div>}
          </div>
        )}

        <div style={S.section}>
          <div style={{ display: "flex", gap: 8 }}>
            <button style={S.btnDanger} onClick={clearChat}>🗑️ Clear</button>
            <button style={S.btnSec}    onClick={exportChat}>📥 Export</button>
          </div>
        </div>

        <div style={S.sidebarFooter}>Powered by LangGraph · Ollama · LangChain</div>
      </aside>

      {/* ── MAIN AREA ─────────────────────────────────────── */}
      <main style={S.main}>
        <div style={S.topBar}>
          <button style={S.menuBtn} onClick={() => setSidebarOpen(o => !o)}>☰</button>
          <SltLogo size={32} style={{ marginRight: 4 }} />
          <div style={S.topTitle}>SLT Insight AI</div>
          <div style={S.topStatus}>
            <span style={{ ...S.dot, background: "#2ecc71" }} />
            Online
          </div>
        </div>

        <div style={S.messages}>
          {messages.length === 0 && (
            <div style={S.welcome}>
              <SltLogo size={90} style={{
                margin: "0 auto 24px",
                boxShadow: "0 10px 30px rgba(0,114,255,0.2)",
                border: "3px solid #e2e8f0",
              }} />
              <h1 style={S.welcomeTitle}>Hello, I'm SLT Insight</h1>
              <p style={S.welcomeSub}>Just ask — I'll figure out where to look automatically</p>
              <div style={S.suggestions}>
                {SUGGESTIONS.map((s, i) => (
                  <button key={i} style={S.suggBtn} onClick={() => sendMessage(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={msg.id || idx} style={{
              ...S.msgRow,
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
            }}>
              {msg.role === "assistant" && <SltLogo size={32} />}
              {msg.role === "system"    && <div style={S.avatarSys}>⚙️</div>}

              <div style={{
                ...S.bubble,
                ...(msg.role === "user"      ? S.bubbleUser   : {}),
                ...(msg.role === "system"    ? S.bubbleSystem : {}),
                ...(msg.role === "assistant" ? S.bubbleBot    : {}),
              }}>
                {msg.role === "assistant" && msg.intent && INTENT_COLORS[msg.intent] && (
                  <div style={{
                    ...S.intentBadge,
                    background: INTENT_COLORS[msg.intent].bg,
                    borderLeft: `3px solid ${INTENT_COLORS[msg.intent].border}`,
                  }}>
                    {INTENT_COLORS[msg.intent].label}
                  </div>
                )}

                {/* ── ReactMarkdown with remarkGfm for table support ── */}
                <div style={S.msgContent}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>

                {msg.figure && (
                  <div style={S.chartWrap}>
                    <Plot
                      data={msg.figure.data}
                      layout={{
                        ...msg.figure.layout,
                        autosize: true,
                        margin: { t: 50, b: 40, l: 40, r: 20 },
                        font:   { family: "DM Sans, sans-serif" },
                      }}
                      useResizeHandler
                      style={{ width: "100%", minHeight: 380 }}
                      config={{ responsive: true, displayModeBar: false }}
                    />
                  </div>
                )}

                {msg.role === "assistant" && (
                  <div style={S.feedbackRow}>
                    <button style={S.fbBtn} onClick={() => sendFeedback(msg.id, msg.content, "up")} title="Good response">👍</button>
                    <button style={S.fbBtn} onClick={() => sendFeedback(msg.id, msg.content, "down")} title="Bad response">👎</button>
                  </div>
                )}
              </div>

              {msg.role === "user" && <div style={S.avatarUser}>👤</div>}
            </div>
          ))}

          {loading && (
            <div style={{ ...S.msgRow, justifyContent: "flex-start" }}>
              <SltLogo size={32} />
              <div style={{ ...S.bubble, ...S.bubbleBot }}>
                <div className="typing"><span /><span /><span /></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={S.inputArea}>
          {activeFlow && (
            <div style={S.flowHint}>🎯 Guided flow active — type your answer below</div>
          )}
          <div style={S.inputRow}>
            <button
              style={{ ...S.iconBtn, background: recording ? "#fee2e2" : "#f0f4ff" }}
              onClick={toggleVoice}
              title={navigator.brave ? "Voice blocked in Brave — use Chrome" : "Voice input"}
            >
              {recording ? "⏹️" : "🎙️"}
            </button>
            <input
              style={S.input}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
              placeholder={activeFlow ? "Type your answer here..." : "Ask anything about SLT — I'll figure out where to look..."}
              disabled={loading}
            />
            <button style={{ ...S.sendBtn, opacity: loading ? 0.5 : 1 }}
              onClick={() => sendMessage()} disabled={loading}>
              {loading ? "⏳" : "➤"}
            </button>
          </div>
        </div>
      </main>

      {/* ── Toast popup ─────────────────────────────────── */}
      {toast && <div style={S.toast}>{toast}</div>}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'DM Sans', sans-serif; background: #f8faff; }
        .typing { display: flex; align-items: center; height: 20px; gap: 2px; }
        .typing span {
          display: inline-block; width: 8px; height: 8px;
          background: #94a3b8; border-radius: 50%; margin: 0 2px;
          animation: bounce 1.2s infinite;
        }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
          0%,80%,100% { transform: translateY(0); }
          40%         { transform: translateY(-8px); }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        select,input,button { font-family: 'DM Sans', sans-serif; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
        p  { margin: 4px 0; line-height: 1.6; }
        ul,ol { padding-left: 20px; }

        /* ── Table styles — clean and professional ── */
        table {
          border-collapse: collapse;
          width: 100%;
          font-size: 13px;
          margin: 12px 0;
          border-radius: 10px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        }
        th {
          background: linear-gradient(135deg, #0072ff, #00c6ff);
          color: white;
          font-weight: 600;
          padding: 10px 14px;
          text-align: left;
          font-size: 12px;
          letter-spacing: 0.3px;
        }
        td {
          border-bottom: 1px solid #e2e8f0;
          padding: 9px 14px;
          color: #1e293b;
          vertical-align: middle;
        }
        tr:last-child td { border-bottom: none; }
        tr:nth-child(even) td { background: #f8faff; }
        tr:hover td { background: #f0f4ff; transition: background 0.15s; }

        code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; font-family: 'DM Mono',monospace; font-size: 0.85em; }
        pre  { background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 8px; overflow-x: auto; }
        pre code { background: none; color: inherit; }
        strong { font-weight: 600; }
        h1,h2,h3 { margin: 8px 0 4px; line-height: 1.3; }
        hr { border: none; border-top: 1px solid #e2e8f0; margin: 10px 0; }
      `}</style>
    </div>
  );
}

const S = {
  app:          { display:"flex", height:"100vh", overflow:"hidden", fontFamily:"'DM Sans',sans-serif", background:"#f8faff" },
  sidebar:      { background:"white", borderRight:"1px solid #e8ecf4", display:"flex", flexDirection:"column", transition:"width 0.3s ease", minWidth:0, flexShrink:0 },
  sidebarHeader:{ display:"flex", alignItems:"center", gap:10, padding:"20px 16px 16px", borderBottom:"1px solid #f0f2f8" },
  logoTitle:    { fontSize:18, fontWeight:700, color:"#1a1a2e" },
  logoSub:      { fontSize:11, color:"#94a3b8" },
  section:      { padding:"12px 16px", borderBottom:"1px solid #f0f2f8", display:"flex", flexDirection:"column", gap:6 },
  secTitle:     { fontSize:12, fontWeight:700, color:"#64748b", textTransform:"uppercase", letterSpacing:1, marginBottom:4 },
  label:        { fontSize:12, color:"#64748b", fontWeight:500 },
  select:       { padding:"6px 10px", borderRadius:8, border:"1px solid #e2e8f0", background:"#f8faff", fontSize:13, color:"#1e293b", cursor:"pointer", outline:"none" },
  successBadge: { background:"#f0fdf4", border:"1px solid #bbf7d0", borderRadius:8, padding:"6px 10px", fontSize:12, color:"#166534" },
  warnBadge:    { background:"#fffbeb", border:"1px solid #fde68a", borderRadius:8, padding:"6px 10px", fontSize:12, color:"#92400e" },
  btnSec:       { padding:"7px 12px", borderRadius:8, border:"1px solid #e2e8f0", background:"white", fontSize:12, cursor:"pointer", color:"#475569", fontWeight:500 },
  btnDanger:    { padding:"7px 12px", borderRadius:8, border:"1px solid #fecaca", background:"#fff5f5", fontSize:12, cursor:"pointer", color:"#dc2626", fontWeight:500, flex:1 },
  dropZone:     { border:"2px dashed #ddd", borderRadius:10, padding:"12px 10px", textAlign:"center", cursor:"pointer", transition:"all 0.2s", background:"#fafbff" },
  dropIcon:     { fontSize:22, marginBottom:4 },
  dropText:     { fontSize:13, fontWeight:600, color:"#374151" },
  dropSub:      { fontSize:11, color:"#9ca3af" },
  uploadedBadge:{ marginTop:4, fontSize:11, color:"#059669", fontWeight:600 },
  imgThumb:     { width:"100%", borderRadius:6, marginTop:6, maxHeight:80, objectFit:"cover" },
  ctxItem:      { fontSize:12, color:"#475569", padding:"2px 0" },
  flowBadge:    { background:"#fefce8", border:"1px solid #fde047", borderRadius:8, padding:"6px 10px", fontSize:12, color:"#854d0e", fontWeight:600 },
  sidebarFooter:{ padding:12, fontSize:11, color:"#94a3b8", textAlign:"center", marginTop:"auto" },
  main:         { flex:1, display:"flex", flexDirection:"column", overflow:"hidden", minWidth:0 },
  topBar:       { display:"flex", alignItems:"center", gap:10, padding:"12px 20px", borderBottom:"1px solid #e8ecf4", background:"white" },
  menuBtn:      { background:"none", border:"none", fontSize:20, cursor:"pointer", color:"#64748b", padding:"4px 8px" },
  topTitle:     { fontSize:17, fontWeight:700, color:"#1a1a2e", flex:1 },
  topStatus:    { display:"flex", alignItems:"center", gap:6, fontSize:12, color:"#64748b" },
  dot:          { width:8, height:8, borderRadius:"50%", display:"inline-block" },
  messages:     { flex:1, overflowY:"auto", padding:"20px 24px", display:"flex", flexDirection:"column", gap:16 },
  welcome:      { textAlign:"center", margin:"auto", maxWidth:600, padding:"40px 20px" },
  welcomeTitle: { fontSize:32, fontWeight:700, color:"#1a1a2e", marginBottom:10 },
  welcomeSub:   { fontSize:16, color:"#64748b", marginBottom:28 },
  suggestions:  { display:"flex", flexWrap:"wrap", gap:8, justifyContent:"center" },
  suggBtn:      { background:"#f0f4ff", border:"1px solid #c7d4f5", borderRadius:20, padding:"8px 16px", fontSize:13, cursor:"pointer", color:"#1a3c8c", fontWeight:500 },
  msgRow:       { display:"flex", alignItems:"flex-end", gap:10, maxWidth:"100%" },
  avatarUser:   { width:32, height:32, borderRadius:"50%", background:"#e2e8f0", display:"flex", alignItems:"center", justifyContent:"center", fontSize:15, flexShrink:0 },
  avatarSys:    { width:32, height:32, borderRadius:"50%", background:"#f1f5f9", display:"flex", alignItems:"center", justifyContent:"center", fontSize:15, flexShrink:0 },
  bubble:       { maxWidth:"72%", borderRadius:16, padding:"12px 16px", fontSize:14, lineHeight:1.6 },
  bubbleBot:    { background:"white", border:"1px solid #e8ecf4", borderBottomLeftRadius:4, boxShadow:"0 1px 4px rgba(0,0,0,0.05)" },
  bubbleUser:   { background:"linear-gradient(135deg,#0072ff,#00c6ff)", color:"white", borderBottomRightRadius:4 },
  bubbleSystem: { background:"#f0fdf4", border:"1px solid #bbf7d0", borderRadius:10, fontSize:13, color:"#166534" },
  intentBadge:  { fontSize:11, padding:"3px 8px", borderRadius:6, marginBottom:8, fontWeight:600, display:"inline-block" },
  msgContent:   { color:"inherit" },
  chartWrap:    { marginTop:12, borderRadius:10, overflow:"hidden", border:"1px solid #e8ecf4" },
  feedbackRow:  { display:"flex", gap:6, marginTop:10, paddingTop:8, borderTop:"1px solid #f0f2f8" },
  fbBtn:        { background:"#f8faff", border:"1px solid #e2e8f0", borderRadius:8, padding:"3px 10px", cursor:"pointer", fontSize:14, transition:"all 0.15s" },
  inputArea:    { padding:"12px 24px 20px", background:"white", borderTop:"1px solid #e8ecf4" },
  flowHint:     { fontSize:12, color:"#854d0e", background:"#fefce8", border:"1px solid #fde047", borderRadius:8, padding:"6px 12px", marginBottom:8, fontWeight:500 },
  inputRow:     { display:"flex", gap:8, alignItems:"center" },
  iconBtn:      { width:40, height:40, borderRadius:10, border:"none", cursor:"pointer", fontSize:18, display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 },
  input:        { flex:1, padding:"11px 16px", borderRadius:12, fontSize:14, border:"1.5px solid #e2e8f0", outline:"none", background:"#f8faff", color:"#1e293b" },
  sendBtn:      { width:44, height:44, borderRadius:12, border:"none", background:"linear-gradient(135deg,#0072ff,#00c6ff)", color:"white", fontSize:18, cursor:"pointer", flexShrink:0, display:"flex", alignItems:"center", justifyContent:"center" },
  toast:        { position:"fixed", bottom:32, right:32, background:"white", border:"1px solid #e2e8f0", borderRadius:14, padding:"14px 22px", boxShadow:"0 8px 30px rgba(0,0,0,0.12)", fontSize:14, fontWeight:600, color:"#1e293b", zIndex:9999, display:"flex", alignItems:"center", gap:10, animation:"slideUp 0.3s ease" },
};