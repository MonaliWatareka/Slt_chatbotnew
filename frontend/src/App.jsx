import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Plot from "react-plotly.js";

const API        = "http://localhost:8000";
const SESSION_ID = "user_" + Math.random().toString(36).substr(2, 9);
const LOGO_URL = `${API}/logo2`;

const INTENT_COLORS = {
  pdf:   { bg: "#e8f4fd", border: "#3498db", label: "📄 PDF Knowledge Base" },
  excel: { bg: "#e8fdf0", border: "#2ecc71", label: "📊 Excel Data" },
  image: { bg: "#fdf0e8", border: "#e67e22", label: "🖼️ Image Analysis" },
  chat:  { bg: "#f0e8fd", border: "#9b59b6", label: "💬 SLT Knowledge" },
  flow:  { bg: "#fdfde8", border: "#f39c12", label: "🎯 Guided Flow" },
};

const INTENT_COLORS_DARK = {
  pdf:   { bg: "#1a2e3d", border: "#3498db", label: "📄 PDF Knowledge Base" },
  excel: { bg: "#1a2d25", border: "#2ecc71", label: "📊 Excel Data" },
  image: { bg: "#2d1f10", border: "#e67e22", label: "🖼️ Image Analysis" },
  chat:  { bg: "#251a33", border: "#9b59b6", label: "💬 SLT Knowledge" },
  flow:  { bg: "#2d2b10", border: "#f39c12", label: "🎯 Guided Flow" },
};

// ── Theme tokens ───────────────────────────────────────────────
const theme = {
  light: {
    appBg:               "#e8eef8",
    sidebarBg:           "#f0f4ff",
    sidebarBorder:       "#d8e2f5",
    sectionBorder:       "#e2e8f4",
    topBarBg:            "#edf1fb",
    topBarBorder:        "#d8e2f5",
    messagesBg:          "#e8eef8",
    inputAreaBg:         "#edf1fb",
    inputAreaBorder:     "#d8e2f5",
    inputBg:             "#f8faff",
    inputBorder:         "#e2e8f0",
    inputColor:          "#1e293b",
    bubbleBotBg:         "#ffffff",
    bubbleBotBorder:     "#d8e2f5",
    bubbleBotShadow:     "0 1px 6px rgba(100,130,200,0.10)",
    titleColor:          "#1a1a2e",
    subColor:            "#64748b",
    labelColor:          "#64748b",
    secTitleColor:       "#64748b",
    selectBg:            "#f8faff",
    selectBorder:        "#e2e8f0",
    selectColor:         "#1e293b",
    historyItemBg:       "#ffffff",
    historyItemBorder:   "#e2e8f0",
    historySnippet:      "#475569",
    iconBtnBg:           "#f0f4ff",
    iconBtnColor:        "#64748b",
    feedbackBtnBg:       "#f8faff",
    feedbackBtnBorder:   "#e2e8f0",
    feedbackBorder:      "#f0f2f8",
    toastBg:             "#ffffff",
    toastBorder:         "#e2e8f0",
    toastColor:          "#1e293b",
    menuBtnColor:        "#64748b",
    ctxColor:            "#475569",
    scrollThumb:         "#cbd5e1",
    toggleBg:            "#e2e8f0",
    toggleColor:         "#475569",
    uploadMenuBg:        "#ffffff",
    uploadMenuBorder:    "#e2e8f0",
    uploadMenuLabelColor:"#1e293b",
    chartBorder:         "#e8ecf4",
    hrColor:             "#e2e8f0",
    tableTdColor:        "#1e293b",
    tableEvenBg:         "#f8faff",
    tableHoverBg:        "#f0f4ff",
    suggBg:              "#f0f4ff",
    suggBorder:          "#c7d4f5",
    suggColor:           "#1a3c8c",
    kbReadyBg:           "#f0fdf4",
    kbReadyBorder:       "#bbf7d0",
    kbReadyColor:        "#166534",
    kbWarnBg:            "#fffbeb",
    kbWarnBorder:        "#fde68a",
    kbWarnColor:         "#92400e",
    sysBubbleBg:         "#f0fdf4",
    sysBubbleBorder:     "#bbf7d0",
    sysBubbleColor:      "#166534",
    flowHintBg:          "#fefce8",
    flowHintBorder:      "#fde047",
    flowHintColor:       "#854d0e",
    flowBadgeBg:         "#fefce8",
    flowBadgeBorder:     "#fde047",
    flowBadgeColor:      "#854d0e",
    clearBtnBg:          "#fff5f5",
    clearBtnBorder:      "#fecaca",
    clearBtnColor:       "#dc2626",
    avatarUserBg:        "#e2e8f0",
    avatarSysBg:         "#f1f5f9",
  },
  dark: {
    appBg:               "#0f1117",
    sidebarBg:           "#161b27",
    sidebarBorder:       "#1e2740",
    sectionBorder:       "#1e2740",
    topBarBg:            "#161b27",
    topBarBorder:        "#1e2740",
    messagesBg:          "#0f1117",
    inputAreaBg:         "#161b27",
    inputAreaBorder:     "#1e2740",
    inputBg:             "#1e2535",
    inputBorder:         "#2a3550",
    inputColor:          "#e2e8f0",
    bubbleBotBg:         "#1a2035",
    bubbleBotBorder:     "#2a3550",
    bubbleBotShadow:     "0 1px 8px rgba(0,0,0,0.4)",
    titleColor:          "#e2e8f0",
    subColor:            "#94a3b8",
    labelColor:          "#94a3b8",
    secTitleColor:       "#64748b",
    selectBg:            "#1e2535",
    selectBorder:        "#2a3550",
    selectColor:         "#e2e8f0",
    historyItemBg:       "#1a2035",
    historyItemBorder:   "#2a3550",
    historySnippet:      "#94a3b8",
    iconBtnBg:           "#1e2535",
    iconBtnColor:        "#94a3b8",
    feedbackBtnBg:       "#1e2535",
    feedbackBtnBorder:   "#2a3550",
    feedbackBorder:      "#1e2740",
    toastBg:             "#1a2035",
    toastBorder:         "#2a3550",
    toastColor:          "#e2e8f0",
    menuBtnColor:        "#94a3b8",
    ctxColor:            "#94a3b8",
    scrollThumb:         "#2a3550",
    toggleBg:            "#0072ff",
    toggleColor:         "#ffffff",
    uploadMenuBg:        "#1a2035",
    uploadMenuBorder:    "#2a3550",
    uploadMenuLabelColor:"#e2e8f0",
    chartBorder:         "#2a3550",
    hrColor:             "#1e2740",
    tableTdColor:        "#cbd5e1",
    tableEvenBg:         "#1a2035",
    tableHoverBg:        "#1e2740",
    suggBg:              "#1e2535",
    suggBorder:          "#2a3550",
    suggColor:           "#93c5fd",
    kbReadyBg:           "#0d2318",
    kbReadyBorder:       "#1a4a30",
    kbReadyColor:        "#4ade80",
    kbWarnBg:            "#2d2008",
    kbWarnBorder:        "#5a3e0a",
    kbWarnColor:         "#fbbf24",
    sysBubbleBg:         "#0d2318",
    sysBubbleBorder:     "#1a4a30",
    sysBubbleColor:      "#4ade80",
    flowHintBg:          "#1a1500",
    flowHintBorder:      "#4a3800",
    flowHintColor:       "#fbbf24",
    flowBadgeBg:         "#1a1500",
    flowBadgeBorder:     "#4a3800",
    flowBadgeColor:      "#fbbf24",
    clearBtnBg:          "#1a0a0a",
    clearBtnBorder:      "#3d1515",
    clearBtnColor:       "#f87171",
    avatarUserBg:        "#2a3550",
    avatarSysBg:         "#1e2535",
  },
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
  const [messages,       setMessages]       = useState([]);
  const [input,          setInput]          = useState("");
  const [loading,        setLoading]        = useState(false);
  const [sessionInfo,    setSessionInfo]    = useState(null);
  const [activeFlow,     setActiveFlow]     = useState(null);
  const [model,          setModel]          = useState("llama3.2");
  const [visionModel,    setVisionModel]    = useState("llava");
  const [kbStatus,       setKbStatus]       = useState(false);
  const [buildingKb,     setBuildingKb]     = useState(false);
  const [imagePreview,   setImagePreview]   = useState(null);
  const [sidebarOpen,    setSidebarOpen]    = useState(true);
  const [recording,      setRecording]      = useState(false);
  const [toast,          setToast]          = useState(null);
  const [uploadMenuOpen, setUploadMenuOpen] = useState(false);
  const [darkMode,       setDarkMode]       = useState(false);

  const [historySearch,  setHistorySearch]  = useState("");
  const [historyResults, setHistoryResults] = useState([]);
  const [highlightId,    setHighlightId]    = useState(null);

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const quickPdfRef    = useRef(null);
  const quickExcelRef  = useRef(null);
  const quickImageRef  = useRef(null);
  const uploadMenuRef  = useRef(null);
  const msgRefs        = useRef({});

  const t = darkMode ? theme.dark : theme.light;
  const intentColors = darkMode ? INTENT_COLORS_DARK : INTENT_COLORS;

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => { fetchSessionInfo(); checkHealth(); }, []);

  useEffect(() => {
    const handler = (e) => {
      if (uploadMenuRef.current && !uploadMenuRef.current.contains(e.target))
        setUploadMenuOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    const q = historySearch.trim().toLowerCase();
    if (!q) { setHistoryResults([]); return; }
    setHistoryResults(
      messages.filter(m => m.role === "user" && m.content?.toLowerCase().includes(q))
        .slice().reverse().slice(0, 12)
    );
  }, [historySearch, messages]);

  const jumpToMessage = useCallback((id) => {
    setHighlightId(id);
    msgRefs.current[id]?.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => setHighlightId(null), 2200);
  }, []);

  const checkHealth = async () => {
    try { const r = await axios.get(`${API}/health`); setKbStatus(r.data.kb_loaded); } catch {}
  };

  const fetchSessionInfo = async () => {
    try {
      const r = await axios.get(`${API}/session/${SESSION_ID}`);
      setSessionInfo(r.data); setActiveFlow(r.data.active_flow);
    } catch {}
  };

  const sendMessage = async (text) => {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role:"user", content:msg, id:Date.now() }]);
    setLoading(true);
    try {
      const res  = await axios.post(`${API}/chat`, { session_id:SESSION_ID, message:msg, model, vision_model:visionModel });
      const data = res.data;
      setActiveFlow(data.active_flow || null);
      setMessages(prev => [...prev, { role:"assistant", content:data.response, intent:data.intent, figure:data.figure ? JSON.parse(data.figure) : null, sources:data.sources, id:Date.now()+1 }]);
      await fetchSessionInfo();
    } catch {
      setMessages(prev => [...prev, { role:"assistant", content:"❌ Error connecting to server. Make sure the backend is running.", intent:"chat", id:Date.now()+1 }]);
    } finally { setLoading(false); }
  };

  const uploadPdf = async (files) => {
    if (!files?.length) return; setUploadMenuOpen(false);
    const fd = new FormData(); fd.append("session_id", SESSION_ID);
    Array.from(files).forEach(f => fd.append("files", f));
    try { await axios.post(`${API}/upload/pdf`, fd); await fetchSessionInfo(); addSys(`✅ ${files.length} PDF(s) indexed successfully!`); showToast(`📄 ${files.length} PDF(s) uploaded!`); }
    catch { addSys("❌ PDF upload failed."); }
  };

  const uploadExcel = async (file) => {
    if (!file) return; setUploadMenuOpen(false);
    const fd = new FormData(); fd.append("session_id", SESSION_ID); fd.append("file", file);
    try { const res = await axios.post(`${API}/upload/excel`, fd); await fetchSessionInfo(); const s = res.data.stats; addSys(`✅ **${file.name}** loaded — ${s.rows} rows, ${s.columns} columns`); showToast(`📊 ${file.name} uploaded!`); }
    catch { addSys("❌ Excel upload failed."); }
  };

  const uploadImage = async (file) => {
    if (!file) return; setUploadMenuOpen(false);
    const fd = new FormData(); fd.append("session_id", SESSION_ID); fd.append("file", file);
    try { const res = await axios.post(`${API}/upload/image`, fd); setImagePreview(res.data.preview); await fetchSessionInfo(); addSys(`✅ **${file.name}** uploaded — ask me anything about it!`); showToast(`🖼️ ${file.name} uploaded!`); }
    catch { addSys("❌ Image upload failed."); }
  };

  const addSys    = (text) => setMessages(prev => [...prev, { role:"system", content:text, id:Date.now() }]);
  const showToast = (msg, dur=3000) => { setToast(msg); setTimeout(() => setToast(null), dur); };

  const toggleVoice = () => {
    const isBrave = navigator.brave !== undefined;
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      alert(isBrave ? "Voice input is blocked in Brave.\n\nFix: Go to brave://settings/privacy and enable Google services.\n\nOr use Google Chrome." : "Voice not supported. Use Chrome.");
      return;
    }
    if (recording) { recognitionRef.current?.stop(); setRecording(false); return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const r  = new SR();
    r.lang="en-US"; r.interimResults=false; r.continuous=false;
    r.onresult = (e) => { setInput(e.results[0][0].transcript); setRecording(false); };
    r.onerror  = (e) => { if (e.error==="not-allowed") alert("Microphone access denied."); setRecording(false); };
    r.onend    = () => setRecording(false);
    recognitionRef.current = r; r.start(); setRecording(true);
  };

  const sendFeedback = async (msgId, content, rating) => {
    try { await axios.post(`${API}/feedback`, { session_id:SESSION_ID, msg_id:String(msgId), rating, content:content.slice(0,100) }); showToast(rating==="up" ? "👍 Thanks for your feedback!" : "👎 Thanks! We'll work to improve."); }
    catch { showToast("❌ Feedback failed. Please try again."); }
  };

  const clearChat = async () => {
    await axios.delete(`${API}/session/${SESSION_ID}`);
    setMessages([]); setActiveFlow(null); setImagePreview(null); setHistorySearch(""); setHistoryResults([]);
    await fetchSessionInfo();
  };

  const exportChat = () => window.open(`${API}/export/${SESSION_ID}`, "_blank");

  const buildKb = async () => {
    setBuildingKb(true);
    try { await axios.post(`${API}/kb/build`); setKbStatus(true); addSys("✅ Knowledge base built successfully!"); }
    catch { addSys("❌ KB build failed. Add PDFs to knowledge_base/ folder."); }
    finally { setBuildingKb(false); }
  };

  const snippet = (content, query) => {
    const idx = content.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return content.slice(0,80)+"…";
    const start = Math.max(0, idx-30), end = Math.min(content.length, idx+query.length+50);
    return (start>0?"…":"") + content.slice(start,end) + (end<content.length?"…":"");
  };

  const highlightSnippet = (text, query) => {
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return <span>{text}</span>;
    return <span>{text.slice(0,idx)}<mark style={{ background:"#fde047", borderRadius:3, padding:"0 2px", color:"#1e293b" }}>{text.slice(idx,idx+query.length)}</mark>{text.slice(idx+query.length)}</span>;
  };

  const SUGGESTIONS = ["How to select fiber package?","What is my total bill amount?","Bar chart of Churn by Contract","Which PeoTV package suits me?","SLT hotline number","Show correlation heatmap"];

  const sec = (children) => ({ padding:"12px 16px", borderBottom:`1px solid ${t.sectionBorder}`, display:"flex", flexDirection:"column", gap:6, ...children });

  return (
    <div style={{ display:"flex", height:"100vh", overflow:"hidden", fontFamily:"'DM Sans',sans-serif", background:t.appBg }}>

      {/* ── SIDEBAR ── */}
      <aside style={{ background:t.sidebarBg, borderRight:`1px solid ${t.sidebarBorder}`, display:"flex", flexDirection:"column", transition:"width 0.3s ease", minWidth:0, flexShrink:0, width:sidebarOpen?280:0, overflow:sidebarOpen?"auto":"hidden" }}>

        {/* Header */}
        <div style={{ display:"flex", alignItems:"center", gap:10, padding:"20px 16px 16px", borderBottom:`1px solid ${t.sectionBorder}` }}>
          <SltLogo size={44} />
          <div style={{ fontSize:18, fontWeight:700, color:t.titleColor }}>SLT Insight</div>
        </div>

        {/* Settings */}
        <div style={{ padding:"12px 16px", borderBottom:`1px solid ${t.sectionBorder}`, display:"flex", flexDirection:"column", gap:6 }}>
          <div style={{ fontSize:12, fontWeight:700, color:t.secTitleColor, textTransform:"uppercase", letterSpacing:1, marginBottom:4 }}>⚙️ Settings</div>
          <label style={{ fontSize:12, color:t.labelColor, fontWeight:500 }}>LLM Model</label>
          <select style={{ padding:"6px 10px", borderRadius:8, border:`1px solid ${t.selectBorder}`, background:t.selectBg, fontSize:13, color:t.selectColor, cursor:"pointer", outline:"none" }} value={model} onChange={e=>setModel(e.target.value)}>
            <option value="llama3.2">llama3.2</option><option value="llama3">llama3</option>
          </select>
          <label style={{ fontSize:12, color:t.labelColor, fontWeight:500 }}>Vision Model</label>
          <select style={{ padding:"6px 10px", borderRadius:8, border:`1px solid ${t.selectBorder}`, background:t.selectBg, fontSize:13, color:t.selectColor, cursor:"pointer", outline:"none" }} value={visionModel} onChange={e=>setVisionModel(e.target.value)}>
            <option value="llava">llava</option><option value="moondream">moondream</option><option value="llava:13b">llava:13b</option>
          </select>
        </div>

        {/* Knowledge Base */}
        <div style={{ padding:"12px 16px", borderBottom:`1px solid ${t.sectionBorder}`, display:"flex", flexDirection:"column", gap:6 }}>
          <div style={{ fontSize:12, fontWeight:700, color:t.secTitleColor, textTransform:"uppercase", letterSpacing:1, marginBottom:4 }}>🧠 Knowledge Base</div>
          {kbStatus
            ? <div style={{ background:t.kbReadyBg, border:`1px solid ${t.kbReadyBorder}`, borderRadius:8, padding:"6px 10px", fontSize:12, color:t.kbReadyColor }}>✅ SLT Knowledge Base ready</div>
            : <div style={{ background:t.kbWarnBg, border:`1px solid ${t.kbWarnBorder}`, borderRadius:8, padding:"6px 10px", fontSize:12, color:t.kbWarnColor }}>⚠️ No knowledge base</div>}
          {!kbStatus && (
            <button style={{ padding:"7px 12px", borderRadius:8, border:`1px solid ${t.inputBorder}`, background:t.inputBg, fontSize:12, cursor:"pointer", color:t.subColor, fontWeight:500 }} onClick={buildKb} disabled={buildingKb}>
              {buildingKb ? "⏳ Building..." : "🔄 Build from PDFs"}
            </button>
          )}
        </div>

        {/* Chat History Search */}
        <div style={{ padding:"12px 16px", borderBottom:`1px solid ${t.sectionBorder}`, display:"flex", flexDirection:"column", gap:6 }}>
          <div style={{ fontSize:12, fontWeight:700, color:t.secTitleColor, textTransform:"uppercase", letterSpacing:1, marginBottom:4 }}>🔍 Search Chat History</div>
          <div style={{ display:"flex", alignItems:"center", background:t.inputBg, border:`1.5px solid ${t.inputBorder}`, borderRadius:10, padding:"0 8px", gap:4 }}>
            <span style={{ fontSize:13, color:"#94a3b8" }}>🔎</span>
            <input style={{ flex:1, border:"none", outline:"none", background:"transparent", fontSize:13, padding:"7px 4px", color:t.inputColor }} placeholder="Search messages…" value={historySearch} onChange={e=>setHistorySearch(e.target.value)} />
            {historySearch && <button style={{ background:"none", border:"none", cursor:"pointer", fontSize:11, color:"#94a3b8", padding:"2px 4px" }} onClick={()=>{setHistorySearch("");setHistoryResults([]);}}>✕</button>}
          </div>

          {!historySearch && messages.filter(m=>m.role==="user").length===0 && (
            <div style={{ textAlign:"center", padding:"20px 0 8px" }}>
              <div style={{ fontSize:28, marginBottom:6 }}>💬</div>
              <div style={{ fontSize:13, fontWeight:600, color:t.subColor }}>No questions yet</div>
              <div style={{ fontSize:11, color:"#94a3b8", marginTop:2 }}>Your questions will appear here</div>
            </div>
          )}

          {!historySearch && messages.filter(m=>m.role==="user").length>0 && (
            <>
              <div style={{ fontSize:11, fontWeight:700, color:"#94a3b8", textTransform:"uppercase", letterSpacing:0.8 }}>Recent</div>
              {messages.filter(m=>m.role==="user").slice(-6).reverse().map(m=>(
                <button key={m.id} onClick={()=>jumpToMessage(m.id)}
                  style={{ display:"flex", alignItems:"flex-start", gap:8, width:"100%", padding:"8px 10px", borderRadius:10, border:`1px solid ${t.historyItemBorder}`, background:t.historyItemBg, cursor:"pointer", textAlign:"left" }}>
                  <span style={{ fontSize:14, flexShrink:0 }}>👤</span>
                  <span style={{ fontSize:12, color:t.historySnippet, lineHeight:1.5, overflow:"hidden", display:"-webkit-box", WebkitLineClamp:2, WebkitBoxOrient:"vertical" }}>
                    {m.content.slice(0,60)}{m.content.length>60?"…":""}
                  </span>
                </button>
              ))}
            </>
          )}

          {historySearch && historyResults.length>0 && (
            <>
              <div style={{ fontSize:11, fontWeight:700, color:"#94a3b8", textTransform:"uppercase", letterSpacing:0.8 }}>{historyResults.length} result{historyResults.length!==1?"s":""}</div>
              {historyResults.map(m=>(
                <button key={m.id} onClick={()=>jumpToMessage(m.id)}
                  style={{ display:"flex", alignItems:"flex-start", gap:8, width:"100%", padding:"8px 10px", borderRadius:10, border:`1px solid ${t.historyItemBorder}`, background:t.historyItemBg, cursor:"pointer", textAlign:"left" }}>
                  <span style={{ fontSize:14, flexShrink:0 }}>👤</span>
                  <span style={{ fontSize:12, color:t.historySnippet, lineHeight:1.5, overflow:"hidden", display:"-webkit-box", WebkitLineClamp:2, WebkitBoxOrient:"vertical" }}>
                    {highlightSnippet(snippet(m.content, historySearch), historySearch)}
                  </span>
                </button>
              ))}
            </>
          )}

          {historySearch && historyResults.length===0 && (
            <div style={{ fontSize:12, color:"#94a3b8", textAlign:"center", padding:"12px 0", fontStyle:"italic" }}>No messages match "{historySearch}"</div>
          )}
        </div>

        {/* Active Context */}
        {sessionInfo && (
          <div style={{ padding:"12px 16px", borderBottom:`1px solid ${t.sectionBorder}`, display:"flex", flexDirection:"column", gap:6 }}>
            <div style={{ fontSize:12, fontWeight:700, color:t.secTitleColor, textTransform:"uppercase", letterSpacing:1, marginBottom:4 }}>📌 Active Context</div>
            {kbStatus              && <div style={{ fontSize:12, color:t.ctxColor }}>🧠 SLT Knowledge Base</div>}
            {sessionInfo.has_pdf   && <div style={{ fontSize:12, color:t.ctxColor }}>📄 {sessionInfo.pdf_names?.join(", ")}</div>}
            {sessionInfo.has_excel && <div style={{ fontSize:12, color:t.ctxColor }}>📊 {sessionInfo.excel_name}</div>}
            {sessionInfo.has_image && <div style={{ fontSize:12, color:t.ctxColor }}>🖼️ {sessionInfo.image_name}</div>}
            {activeFlow && <div style={{ background:t.flowBadgeBg, border:`1px solid ${t.flowBadgeBorder}`, borderRadius:8, padding:"6px 10px", fontSize:12, color:t.flowBadgeColor, fontWeight:600 }}>🎯 Guided flow active</div>}
          </div>
        )}

        {/* Actions */}
        <div style={{ padding:"12px 16px", borderBottom:`1px solid ${t.sectionBorder}`, display:"flex", gap:8 }}>
          <button style={{ padding:"7px 12px", borderRadius:8, border:`1px solid ${t.clearBtnBorder}`, background:t.clearBtnBg, fontSize:12, cursor:"pointer", color:t.clearBtnColor, fontWeight:500, flex:1 }} onClick={clearChat}>🗑️ Clear</button>
          <button style={{ padding:"7px 12px", borderRadius:8, border:`1px solid ${t.inputBorder}`, background:t.inputBg, fontSize:12, cursor:"pointer", color:t.subColor, fontWeight:500 }} onClick={exportChat}>📥 Export</button>
        </div>
      </aside>

      {/* ── MAIN ── */}
      <main style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden", minWidth:0 }}>

        {/* Top bar */}
        <div style={{ display:"flex", alignItems:"center", gap:10, padding:"12px 20px", borderBottom:`1px solid ${t.topBarBorder}`, background:t.topBarBg }}>
          <button style={{ background:"none", border:"none", fontSize:20, cursor:"pointer", color:t.menuBtnColor, padding:"4px 8px" }} onClick={()=>setSidebarOpen(o=>!o)}>☰</button>
          <SltLogo size={32} style={{ marginRight:4 }} />
          <div style={{ fontSize:17, fontWeight:700, color:t.titleColor, flex:1 }}>SLT Insight AI</div>

          {/* 🌙 / ☀️ toggle */}
          <button onClick={()=>setDarkMode(d=>!d)}
            style={{ display:"flex", alignItems:"center", gap:6, background:t.toggleBg, border:"none", borderRadius:20, padding:"5px 12px 5px 8px", cursor:"pointer", color:t.toggleColor, fontWeight:600, fontSize:12, flexShrink:0, transition:"all 0.25s" }}>
            <span style={{ fontSize:16 }}>{darkMode?"☀️":"🌙"}</span>
            {darkMode?"Light":"Dark"}
          </button>

          <div style={{ display:"flex", alignItems:"center", gap:6, fontSize:12, color:t.subColor }}>
            <span style={{ width:8, height:8, borderRadius:"50%", display:"inline-block", background:"#2ecc71" }} />
            Online
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex:1, overflowY:"auto", padding:"20px 24px", display:"flex", flexDirection:"column", gap:16, background:t.messagesBg }}>
          {messages.length===0 && (
            <div style={{ textAlign:"center", margin:"auto", maxWidth:600, padding:"40px 20px" }}>
              <SltLogo size={90} style={{ margin:"0 auto 24px", boxShadow:"0 10px 30px rgba(0,114,255,0.2)", border:"3px solid #e2e8f0" }} />
              <h1 style={{ fontSize:32, fontWeight:700, color:t.titleColor, marginBottom:10 }}>Hello, I'm SLT Insight</h1>
              <p style={{ fontSize:16, color:t.subColor, marginBottom:28 }}>Just ask — I'll figure out where to look automatically</p>
              <div style={{ display:"flex", flexWrap:"wrap", gap:8, justifyContent:"center" }}>
                {SUGGESTIONS.map((s,i)=>(
                  <button key={i} style={{ background:t.suggBg, border:`1px solid ${t.suggBorder}`, borderRadius:20, padding:"8px 16px", fontSize:13, cursor:"pointer", color:t.suggColor, fontWeight:500 }} onClick={()=>sendMessage(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg,idx)=>(
            <div key={msg.id||idx} ref={el=>{if(msg.id) msgRefs.current[msg.id]=el;}}
              style={{ display:"flex", alignItems:"flex-end", gap:10, maxWidth:"100%", padding:"2px 4px", justifyContent:msg.role==="user"?"flex-end":"flex-start", transition:"background 0.4s ease", borderRadius:12, background:highlightId===msg.id?"rgba(253,224,71,0.18)":"transparent" }}>

              {msg.role==="assistant" && <SltLogo size={32} />}
              {msg.role==="system"    && <div style={{ width:32, height:32, borderRadius:"50%", background:t.avatarSysBg, display:"flex", alignItems:"center", justifyContent:"center", fontSize:15, flexShrink:0 }}>⚙️</div>}

              <div style={{
                maxWidth:"72%", borderRadius:16, padding:"12px 16px", fontSize:14, lineHeight:1.6,
                ...(msg.role==="user"      ? { background:"linear-gradient(135deg,#0072ff,#00c6ff)", color:"white", borderBottomRightRadius:4 } : {}),
                ...(msg.role==="system"    ? { background:t.sysBubbleBg, border:`1px solid ${t.sysBubbleBorder}`, borderRadius:10, fontSize:13, color:t.sysBubbleColor } : {}),
                ...(msg.role==="assistant" ? { background:t.bubbleBotBg, border:`1px solid ${t.bubbleBotBorder}`, borderBottomLeftRadius:4, boxShadow:t.bubbleBotShadow, color:t.inputColor } : {}),
                ...(highlightId===msg.id   ? { boxShadow:"0 0 0 2px #fde047" } : {}),
              }}>
                {msg.role==="assistant" && msg.intent && intentColors[msg.intent] && (
                  <div style={{ fontSize:11, padding:"3px 8px", borderRadius:6, marginBottom:8, fontWeight:600, display:"inline-block", background:intentColors[msg.intent].bg, borderLeft:`3px solid ${intentColors[msg.intent].border}`, color:darkMode?"#e2e8f0":"inherit" }}>
                    {intentColors[msg.intent].label}
                  </div>
                )}

                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>

                {msg.figure && (
                  <div style={{ marginTop:12, borderRadius:10, overflow:"hidden", border:`1px solid ${t.chartBorder}` }}>
                    <Plot data={msg.figure.data}
                      layout={{ ...msg.figure.layout, autosize:true, margin:{t:50,b:40,l:40,r:20}, font:{family:"DM Sans, sans-serif"}, paper_bgcolor:darkMode?"#1a2035":"white", plot_bgcolor:darkMode?"#1a2035":"white" }}
                      useResizeHandler style={{ width:"100%", minHeight:380 }} config={{ responsive:true, displayModeBar:false }} />
                  </div>
                )}

                {msg.role==="assistant" && (
                  <div style={{ display:"flex", gap:6, marginTop:10, paddingTop:8, borderTop:`1px solid ${t.feedbackBorder}` }}>
                    <button style={{ background:t.feedbackBtnBg, border:`1px solid ${t.feedbackBtnBorder}`, borderRadius:8, padding:"3px 10px", cursor:"pointer", fontSize:14 }} onClick={()=>sendFeedback(msg.id,msg.content,"up")}>👍</button>
                    <button style={{ background:t.feedbackBtnBg, border:`1px solid ${t.feedbackBtnBorder}`, borderRadius:8, padding:"3px 10px", cursor:"pointer", fontSize:14 }} onClick={()=>sendFeedback(msg.id,msg.content,"down")}>👎</button>
                  </div>
                )}
              </div>

              {msg.role==="user" && <div style={{ width:32, height:32, borderRadius:"50%", background:t.avatarUserBg, display:"flex", alignItems:"center", justifyContent:"center", fontSize:15, flexShrink:0 }}>👤</div>}
            </div>
          ))}

          {loading && (
            <div style={{ display:"flex", alignItems:"flex-end", gap:10, justifyContent:"flex-start" }}>
              <SltLogo size={32} />
              <div style={{ maxWidth:"72%", borderRadius:16, padding:"12px 16px", background:t.bubbleBotBg, border:`1px solid ${t.bubbleBotBorder}`, borderBottomLeftRadius:4, boxShadow:t.bubbleBotShadow }}>
                <div className="typing"><span /><span /><span /></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div style={{ padding:"12px 24px 20px", background:t.inputAreaBg, borderTop:`1px solid ${t.inputAreaBorder}` }}>
          {activeFlow && (
            <div style={{ fontSize:12, color:t.flowHintColor, background:t.flowHintBg, border:`1px solid ${t.flowHintBorder}`, borderRadius:8, padding:"6px 12px", marginBottom:8, fontWeight:500 }}>
              🎯 Guided flow active — type your answer below
            </div>
          )}
          <div style={{ display:"flex", gap:8, alignItems:"center" }}>
            <button style={{ width:40, height:40, borderRadius:10, border:"none", cursor:"pointer", fontSize:18, display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, background:recording?"#fee2e2":t.iconBtnBg }} onClick={toggleVoice}>
              {recording?"⏹️":"🎙️"}
            </button>

            <div style={{ position:"relative" }} ref={uploadMenuRef}>
              <button style={{ width:40, height:40, borderRadius:10, cursor:"pointer", fontSize:22, fontWeight:300, display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, background:uploadMenuOpen?(darkMode?"#1a2e3d":"#e8f4fd"):t.iconBtnBg, border:uploadMenuOpen?"1.5px solid #3498db":"none", color:uploadMenuOpen?"#3498db":t.iconBtnColor }}
                onClick={()=>setUploadMenuOpen(o=>!o)}>
                {uploadMenuOpen?"✕":"+"}
              </button>

              {uploadMenuOpen && (
                <div style={{ position:"absolute", bottom:52, left:0, background:t.uploadMenuBg, border:`1px solid ${t.uploadMenuBorder}`, borderRadius:14, padding:"8px", boxShadow:"0 8px 30px rgba(0,0,0,0.2)", zIndex:1000, minWidth:220, animation:"popUp 0.2s ease" }}>
                  <div style={{ fontSize:11, fontWeight:700, color:"#94a3b8", textTransform:"uppercase", letterSpacing:1, padding:"4px 8px 8px", borderBottom:`1px solid ${t.sectionBorder}`, marginBottom:4 }}>Upload a file</div>
                  {[
                    { ref:quickPdfRef,   icon:"📄", label:"PDF Document", sub:"For Q&A and search" },
                    { ref:quickExcelRef, icon:"📊", label:"Excel / CSV",  sub:"For charts and analysis" },
                    { ref:quickImageRef, icon:"🖼️", label:"Image / Bill", sub:"For bill reading" },
                  ].map(item=>(
                    <button key={item.label} style={{ display:"flex", alignItems:"center", gap:12, width:"100%", padding:"10px 12px", borderRadius:10, border:"none", background:"none", cursor:"pointer", textAlign:"left" }} onClick={()=>item.ref.current.click()}>
                      <span style={{ fontSize:24, flexShrink:0 }}>{item.icon}</span>
                      <div>
                        <div style={{ fontSize:13, fontWeight:600, color:t.uploadMenuLabelColor }}>{item.label}</div>
                        <div style={{ fontSize:11, color:"#94a3b8", marginTop:1 }}>{item.sub}</div>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              <input ref={quickPdfRef}   type="file" accept=".pdf" multiple hidden onChange={e=>uploadPdf(e.target.files)} />
              <input ref={quickExcelRef} type="file" accept=".xlsx,.xls,.csv" hidden onChange={e=>uploadExcel(e.target.files[0])} />
              <input ref={quickImageRef} type="file" accept=".jpg,.jpeg,.png,.webp,.bmp" hidden onChange={e=>uploadImage(e.target.files[0])} />
            </div>

            <input style={{ flex:1, padding:"11px 16px", borderRadius:12, fontSize:14, border:`1.5px solid ${t.inputBorder}`, outline:"none", background:t.inputBg, color:t.inputColor }}
              value={input} onChange={e=>setInput(e.target.value)}
              onKeyDown={e=>e.key==="Enter"&&!e.shiftKey&&sendMessage()}
              placeholder={activeFlow?"Type your answer here...":"Ask anything about SLT — I'll figure out where to look..."}
              disabled={loading} />

            <button style={{ width:44, height:44, borderRadius:12, border:"none", background:"linear-gradient(135deg,#0072ff,#00c6ff)", color:"white", fontSize:18, cursor:"pointer", flexShrink:0, display:"flex", alignItems:"center", justifyContent:"center", opacity:loading?0.5:1 }}
              onClick={()=>sendMessage()} disabled={loading}>
              {loading?"⏳":"➤"}
            </button>
          </div>
        </div>
      </main>

      {toast && (
        <div style={{ position:"fixed", bottom:32, right:32, background:t.toastBg, border:`1px solid ${t.toastBorder}`, borderRadius:14, padding:"14px 22px", boxShadow:"0 8px 30px rgba(0,0,0,0.18)", fontSize:14, fontWeight:600, color:t.toastColor, zIndex:9999, display:"flex", alignItems:"center", gap:10, animation:"slideUp 0.3s ease" }}>
          {toast}
        </div>
      )}

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'DM Sans', sans-serif; background: ${t.appBg}; transition: background 0.3s; }
        .typing { display: flex; align-items: center; height: 20px; gap: 2px; }
        .typing span { display: inline-block; width: 8px; height: 8px; background: #94a3b8; border-radius: 50%; margin: 0 2px; animation: bounce 1.2s infinite; }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-8px)} }
        @keyframes slideUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
        @keyframes popUp  { from{opacity:0;transform:translateY(8px) scale(0.97)} to{opacity:1;transform:translateY(0) scale(1)} }
        select,input,button { font-family: 'DM Sans', sans-serif; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-thumb { background: ${t.scrollThumb}; border-radius: 10px; }
        p  { margin: 4px 0; line-height: 1.6; }
        ul,ol { padding-left: 20px; }
        table { border-collapse: collapse; width: 100%; font-size: 13px; margin: 12px 0; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
        th { background: linear-gradient(135deg,#0072ff,#00c6ff); color: white; font-weight: 600; padding: 10px 14px; text-align: left; font-size: 12px; letter-spacing: 0.3px; }
        td { border-bottom: 1px solid ${t.hrColor}; padding: 9px 14px; color: ${t.tableTdColor}; }
        tr:last-child td { border-bottom: none; }
        tr:nth-child(even) td { background: ${t.tableEvenBg}; }
        tr:hover td { background: ${t.tableHoverBg}; transition: background 0.15s; }
        code { background: ${t.inputBg}; padding: 1px 5px; border-radius: 4px; font-family: 'DM Mono',monospace; font-size: 0.85em; color: ${t.inputColor}; }
        pre  { background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 8px; overflow-x: auto; }
        pre code { background: none; color: inherit; }
        strong { font-weight: 600; }
        h1,h2,h3 { margin: 8px 0 4px; line-height: 1.3; color: ${t.titleColor}; }
        hr { border: none; border-top: 1px solid ${t.hrColor}; margin: 10px 0; }
        a  { color: #3b82f6; }
      `}</style>
    </div>
  );
}