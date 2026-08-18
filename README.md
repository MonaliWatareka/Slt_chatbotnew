# SLT Insight AI Customer Support Chatbot

**Fully offline AI chatbot for SLT Mobitel PLC — internship project**

SLT Insight lets customers and internal staff interact with SLT services, documents, bill images, and data through natural language. It runs entirely on local hardware using Ollama models — no internet connection, no external API costs. Built with a React frontend and FastAPI backend, replacing an earlier Streamlit prototype for much faster response times and a more polished UX.

**At a glance:** 5 core features · 3 LLM/vision models · 100% offline · $0 API cost

---

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [LangGraph Agentic Flow](#langgraph-agentic-flow)
- [Key Features](#key-features)
- [LLM Models Used](#llm-models-used)
- [Tools & Libraries](#tools--libraries)
- [Use Cases & Business Value](#use-cases--business-value)
- [Key Technical Achievements](#key-technical-achievements)

---

## Overview

SLT Insight is a fully offline, AI-powered chatbot. It reads bill images, answers questions over SLT documents (RAG), builds charts from spreadsheets in plain English, and guides customers through package selection — all routed automatically by a LangGraph state machine, with zero data leaving the SLT network.

## System Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + Vite | Chat UI, file uploads, charts, dark mode |
| Backend | FastAPI + Uvicorn | REST API, session management, file handling |
| AI Router | LangGraph | State machine — auto-routes user intent |
| LLM | Ollama (`llama3.2`) | Text generation, Q&A, summaries |
| Vision | Ollama (`llava`) | Bill image reading, OCR fallback |
| Embeddings | `nomic-embed-text` | Document vectorization for RAG |
| Vector DB | FAISS | Semantic search over PDF documents |
| Charts | Plotly + Pandas | Interactive data visualizations |
| Framework | LangChain | RAG chains, prompt templates, retrievers |

## LangGraph Agentic Flow

A multi-node state machine automatically detects user intent and routes to the right processing node — no manual mode selection needed.

| Node | Trigger | Action |
|------|---------|--------|
| Router Node | Every message | Detects intent using keywords + LLM fallback |
| PDF Node | Document questions | FAISS retrieval → LLM answer with source attribution |
| Excel Node | Chart / data requests | LLM spec → Plotly chart + AI insight summary |
| Image Node | Bill or image uploaded | `llava` vision → OCR fallback → text answer |
| Flow Node | Package / service keywords | Guided Q&A chain → personalised recommendation |
| Chat Node | General SLT questions | KB context + conversation history → LLM response |
| Response Node | All nodes | Formats final answer with intent badge |

## Key Features

### Bill Image Reading
Customers upload a photo of their SLT Mobitel bill and ask questions in natural language. The `llava` vision model reads the image and returns accurate answers, with a Tesseract OCR fallback ensuring 100% uptime even when the vision model is unavailable.

### PDF Document Q&A (RAG)
SLT documents, annual reports, and tariff guides are indexed into a FAISS vector store using `nomic-embed-text` embeddings. Users get answers with source attribution showing which PDF the information came from — multiple PDFs can be queried simultaneously.

### Excel Chart Builder
Staff upload customer data (CSV/Excel) and request charts in plain English — "pie chart of gender", "bar chart of churn by contract." The LLM generates a Plotly chart spec, and an AI insight summary is auto-generated for every chart type: pie, bar, line, scatter, histogram, and correlation heatmaps.

### Guided Conversation Flow
For package selection, the chatbot guides customers step-by-step through questions (household size, usage type, budget, PeoTV interest) and delivers a personalised recommendation. Four flows are implemented: Fiber, PeoTV, Mobile, and Bill Help.

### Voice Input
Customers can speak their questions using the browser's built-in Speech Recognition API, across all chat modes, for English queries.

### Dark Mode
A full dark mode theme with carefully designed color tokens for readability and brand consistency in both light and dark environments.

## LLM Models Used

| Model | Type | Size | Usage | Provider |
|-------|------|------|-------|----------|
| `llama3.2` | Text LLM | 2.0 GB | Chat, Q&A, chart specs, summaries, intent classification | Meta / Ollama |
| `llava` | Vision LLM | 4.7 GB | Bill image reading, visual document understanding | LLaVA / Ollama |
| `moondream` | Vision LLM | 1.7 GB | Lightweight image reading (fallback vision model) | Vikhyatk / Ollama |
| `nomic-embed-text` | Embedding Model | 274 MB | Document vectorization for FAISS semantic search | Nomic / Ollama |

## Tools & Libraries

| Category | Tool / Library | Version | Role |
|----------|----------------|---------|------|
| AI Framework | LangChain | 0.2+ | RAG chains, prompt templates, output parsers |
| AI Framework | LangGraph | 0.2+ | Multi-node state machine agent routing |
| LLM Runtime | Ollama | Latest | Local LLM inference engine |
| Vector DB | FAISS | 1.8+ | Similarity search over document embeddings |
| Backend | FastAPI | Latest | REST API server with async support |
| Backend | Uvicorn | Latest | ASGI server for FastAPI |
| Frontend | React | 18.2 | Component-based chat UI |
| Frontend | Vite | 5.0 | Fast frontend build tool |
| Charts | Plotly / react-plotly | 5.22 | Interactive data visualizations |
| Data | Pandas | 2.2+ | Excel/CSV data processing |
| PDF | PyMuPDF | 1.24+ | PDF loading and text extraction |
| OCR | Tesseract / pytesseract | Latest | Fallback text extraction from images |
| Images | Pillow | 10.3+ | Image preprocessing for vision models |
| Markdown | react-markdown + remark-gfm | 9.0 | Render markdown tables/formatting in chat |
| HTTP | Axios | 1.6 | Frontend API calls to FastAPI backend |

## Use Cases & Business Value

| # | Use Case | Who Uses It | Business Value |
|---|----------|-------------|------------------|
| 1 | Bill Image Reading | SLT Customers | Instant answers from bill photos — no hotline wait |
| 2 | PDF Document Q&A | Customers & Staff | Instant search across annual reports, tariff guides, and policies |
| 3 | Package Recommender | SLT Customers | Guided flow selects the best fiber/mobile/TV package for customer needs |
| 4 | Data Visualization | SLT Internal Staff | Non-technical staff generate professional charts from raw data |
| 5 | Service Information | SLT Customers | 24/7 answers about SLT packages, hotlines, and upgrade steps |
| 6 | Voice Queries | All Users | Accessibility — speak questions instead of typing |

## Key Technical Achievements

- **LangGraph State Machine** — replaced manual if/else routing with a LangGraph agent that automatically detects intent and routes to the correct processing node, the same architecture pattern used by enterprise AI teams.
- **100% Offline Operation** — all models run locally via Ollama; no data leaves the SLT network and there are zero external API costs, critical for enterprise data privacy.
- **OCR Fallback System** — when the vision model fails or times out, Tesseract OCR automatically extracts text from the image and Llama answers from that, ensuring 100% uptime for bill reading.
- **React Migration** — migrated from Streamlit to React + FastAPI, reducing UI interaction latency from 2–4 seconds to under 0.5 seconds.
- **Guided Conversational AI** — implemented a multi-turn guided conversation system using LangGraph flow nodes and a "shown" marker pattern to correctly track question/answer turns across stateless HTTP requests.
- **Multi-source RAG** — the FAISS vector store supports multiple PDFs simultaneously with source attribution, so answers cite which document they came from.

---

*SLT Mobitel PLC · Internship Project · 2026 · Powered by LangGraph · Ollama · React · FastAPI*
