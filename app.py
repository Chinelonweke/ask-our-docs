"""
app.py
─────────────────────────────────────────────────────────────
Streamlit browser UI for the Ask Our Docs RAG bot.
Replaces the terminal (main.py) with a chat interface in the browser.

Run with:
    streamlit run app.py

The RAG engine (rag_engine.py) is unchanged — this file is purely
the visual front door into the same pipeline.
─────────────────────────────────────────────────────────────
"""

import streamlit as st
from dotenv import load_dotenv
from rag_engine import RAGEngine, load_documents, chunk_documents, DOCUMENTS_DIR
from logger import get_logger

load_dotenv()
log = get_logger(__name__)


# ──────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ask Our Docs · Seismic",
    page_icon="📚",
    layout="centered",
)


# ──────────────────────────────────────────────────────────────
# CUSTOM CSS  — dark technical aesthetic
# ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

/* ── Root variables ── */
:root {
    --bg:         #0d1117;
    --surface:    #161b22;
    --border:     #30363d;
    --accent:     #3fb950;
    --accent-dim: #1a3d24;
    --warning:    #d29922;
    --text:       #e6edf3;
    --text-dim:   #8b949e;
    --user-bg:    #1c2128;
    --bot-bg:     #161b22;
    --tag-bg:     #1a3d24;
    --tag-text:   #3fb950;
    --font-main:  'IBM Plex Sans', sans-serif;
    --font-mono:  'IBM Plex Mono', monospace;
}

/* ── Global resets ── */
html, body, [class*="css"] {
    font-family: var(--font-main);
    background-color: var(--bg);
    color: var(--text);
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 1rem; max-width: 780px; }

/* ── Header ── */
.app-header {
    border-bottom: 1px solid var(--border);
    padding-bottom: 1.2rem;
    margin-bottom: 1.8rem;
}
.app-title {
    font-family: var(--font-mono);
    font-size: 1.35rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: -0.02em;
    margin: 0;
}
.app-subtitle {
    font-size: 0.8rem;
    color: var(--text-dim);
    font-family: var(--font-mono);
    margin-top: 0.25rem;
}

/* ── Doc pills ── */
.doc-pills {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin: 0.8rem 0 1.4rem 0;
}
.doc-pill {
    background: #111827;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.25rem 0.65rem;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--text-dim);
}
.doc-pill span { color: var(--accent); margin-right: 0.3rem; }

/* ── Chat messages ── */
.message-wrap {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    margin-bottom: 1.2rem;
}
.message-role {
    font-family: var(--font-mono);
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
    padding-left: 0.2rem;
}
.message-role.user  { color: #58a6ff; }
.message-role.bot   { color: var(--accent); }

.message-bubble {
    border-radius: 6px;
    padding: 0.85rem 1.1rem;
    font-size: 0.9rem;
    line-height: 1.65;
    border: 1px solid var(--border);
}
.message-bubble.user { background: var(--user-bg); }
.message-bubble.bot  { background: var(--bot-bg);  }

/* ── Source citation tags ── */
.source-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin-top: 0.7rem;
    padding-top: 0.6rem;
    border-top: 1px solid var(--border);
}
.source-label {
    font-family: var(--font-mono);
    font-size: 0.68rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.source-tag {
    background: var(--tag-bg);
    color: var(--tag-text);
    border: 1px solid #2ea043;
    border-radius: 3px;
    padding: 0.15rem 0.55rem;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 600;
}

/* ── Thinking indicator ── */
.thinking {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--text-dim);
    padding: 0.6rem 0;
    animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 0.4; }
    50%       { opacity: 1;   }
}

/* ── Input box ── */
.stTextInput > div > div > input {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-family: var(--font-main) !important;
    font-size: 0.9rem !important;
    padding: 0.65rem 1rem !important;
    caret-color: var(--accent);
}
.stTextInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(63,185,80,0.15) !important;
}
.stTextInput > div > div > input::placeholder { color: var(--text-dim) !important; }

/* ── Buttons ── */
.stButton > button {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    border-radius: 5px !important;
    color: var(--text-dim) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    padding: 0.4rem 0.9rem !important;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: var(--accent-dim) !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

/* ── Sidebar (status panel) ── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}
.sidebar-section {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-dim);
    line-height: 1.8;
}
.sidebar-title {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.4rem;
    margin-bottom: 0.6rem;
}
.stat-row { display: flex; justify-content: space-between; }
.stat-val  { color: var(--accent); font-weight: 600; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# LOAD & CACHE THE RAG ENGINE
# st.cache_resource → built once, reused across every user interaction
# ──────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_engine():
    log.info("Initialising RAG engine for Streamlit session")
    docs   = load_documents(DOCUMENTS_DIR)
    chunks = chunk_documents(docs)
    engine = RAGEngine()
    engine.build_index(chunks)
    log.info("RAG engine ready")
    return engine, len(docs), len(chunks)


# ──────────────────────────────────────────────────────────────
# BOOT ENGINE
# ──────────────────────────────────────────────────────────────
with st.spinner("🔄  Loading documents and building index…"):
    engine, doc_count, chunk_count = load_engine()


# ──────────────────────────────────────────────────────────────
# SIDEBAR — system status panel
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="sidebar-title">System Status</p>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="sidebar-section">
        <div class="stat-row"><span>Status</span>     <span class="stat-val">● Online</span></div>
        <div class="stat-row"><span>Engine</span>     <span class="stat-val">RAG</span></div>
        <div class="stat-row"><span>LLM</span>        <span class="stat-val">LLaMA 3 8B</span></div>
        <div class="stat-row"><span>Provider</span>   <span class="stat-val">Groq</span></div>
        <div class="stat-row"><span>Embeddings</span> <span class="stat-val">MiniLM-L6</span></div>
        <div class="stat-row"><span>Docs loaded</span><span class="stat-val">{doc_count}</span></div>
        <div class="stat-row"><span>Chunks indexed</span><span class="stat-val">{chunk_count}</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="sidebar-title">Indexed Documents</p>', unsafe_allow_html=True)
    st.markdown("""
    <div class="sidebar-section">
        <div>📄 authentication.md</div>
        <div>📄 endpoints.md</div>
        <div>📄 rate_limits.md</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="sidebar-title">Try Asking</p>', unsafe_allow_html=True)
    st.markdown("""
    <div class="sidebar-section">
        <div>→ How do I authenticate?</div>
        <div>→ What is the rate limit?</div>
        <div>→ How do I create a user?</div>
        <div>→ What is the enterprise limit?</div>
        <div>→ What happens on a 429 error?</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑  Clear chat"):
        st.session_state.messages = []
        log.info("Chat history cleared by user")
        st.rerun()


# ──────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <p class="app-title">📚 Ask Our Docs</p>
    <p class="app-subtitle">Seismic Consulting Group · Internal API Documentation · RAG-powered</p>
</div>
""", unsafe_allow_html=True)

# Doc pills
st.markdown("""
<div class="doc-pills">
    <div class="doc-pill"><span>◈</span>authentication.md</div>
    <div class="doc-pill"><span>◈</span>endpoints.md</div>
    <div class="doc-pill"><span>◈</span>rate_limits.md</div>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# SESSION STATE — stores the full conversation history
# ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []


# ──────────────────────────────────────────────────────────────
# HELPER — strip the LLM's raw "Sources: [file.md]" line
# The UI already shows sources as styled green tags, so we
# remove the plain-text version the LLM appends to prevent
# it appearing twice inside the chat bubble.
# ──────────────────────────────────────────────────────────────
import re

def clean_answer(text: str) -> str:
    # Remove "Sources: [file.md]" lines (with or without bold/markdown)
    text = re.sub(
        r'\n*\**\s*Sources?\s*\**\s*:.*$', '',
        text, flags=re.IGNORECASE | re.MULTILINE
    )
    # Remove any trailing standalone "[filename.md]" lines
    text = re.sub(
        r'\n*\[[^\]]+\.md\]\s*$', '',
        text.strip(), flags=re.MULTILINE
    )
    return text.strip()


# ──────────────────────────────────────────────────────────────
# RENDER A SINGLE MESSAGE
# Uses st.chat_message so markdown, backticks, and code blocks
# all render correctly — no HTML injection issues.
# ──────────────────────────────────────────────────────────────
def render_message(role: str, content: str, sources: list = None):
    avatar = "🧑‍💻" if role == "user" else "📚"
    with st.chat_message(name=role, avatar=avatar):
        st.markdown(content)
        if sources:
            tags = "".join(
                f'<span class="source-tag">{s}</span>' for s in sources
            )
            st.markdown(f"""
            <div class="source-row">
                <span class="source-label">Sources</span>
                {tags}
            </div>
            """, unsafe_allow_html=True)


# Replay full conversation history on every rerun
for msg in st.session_state.messages:
    render_message(msg["role"], msg["content"], msg.get("sources"))


# ──────────────────────────────────────────────────────────────
# CHAT INPUT
# ──────────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)

with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            label="question",
            placeholder="Ask a question about the API documentation…",
            label_visibility="collapsed"
        )
    with col2:
        submitted = st.form_submit_button("Send →")


# ──────────────────────────────────────────────────────────────
# HANDLE SUBMISSION
# ──────────────────────────────────────────────────────────────
if submitted and user_input.strip():
    question = user_input.strip()
    log.info(f"User submitted question: {question!r}")

    # Save + render user message immediately
    st.session_state.messages.append({
        "role": "user", "content": question, "sources": []
    })
    render_message("user", question)

    # Pulsing indicator while waiting for Groq
    thinking_placeholder = st.empty()
    thinking_placeholder.markdown(
        '<p class="thinking">⬤ &nbsp;Searching documentation…</p>',
        unsafe_allow_html=True
    )

    # Run full RAG pipeline
    result      = engine.answer(question)
    answer_text = clean_answer(result["answer"])   # ← strip duplicate sources line
    sources     = result["sources"]

    thinking_placeholder.empty()

    # Save + render bot reply
    st.session_state.messages.append({
        "role": "bot", "content": answer_text, "sources": sources
    })
    render_message("bot", answer_text, sources)

    log.info(f"Answer rendered. Sources: {sources}")
    st.rerun()