"""
rag_engine.py
─────────────────────────────────────────────────────────────
Core RAG pipeline for the "Ask Our Docs" bot.

Documents being indexed (from /documents folder):
  • authentication.md  — API Key generation, usage, security rules
  • endpoints.md       — GET/POST endpoints for Users and Projects
  • rate_limits.md     — Standard (100 RPM / 1000 RPH) and Enterprise (500 RPM) limits

Pipeline stages:
  1. Load   → read .md files, tag each with its filename as 'source'
  2. Chunk  → sliding-window character split (400 chars, 80 overlap)
  3. Embed  → SentenceTransformer 'all-MiniLM-L6-v2' (local, no API cost)
  4. Index  → FAISS IndexFlatIP with L2-normalized vectors (= cosine similarity)
  5. Retrieve → top-k most similar chunks for a given question
  6. Generate → Groq (LLaMA3-8B) with grounded prompt + mandatory citation
─────────────────────────────────────────────────────────────
"""

import os
import glob
import time
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from groq import Groq
from logger import get_logger, log_separator

log = get_logger(__name__)


# ──────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────
DOCUMENTS_DIR       = "documents"
EMBEDDING_MODEL     = "all-MiniLM-L6-v2"   # 384-dim, CPU-friendly, no API key
GROQ_MODEL          = "llama-3.1-8b-instant"      # Free on Groq, 8192 token context
CHUNK_SIZE          = 400                   # characters per chunk
CHUNK_OVERLAP       = 80                    # overlap to avoid boundary cut-offs
TOP_K               = 3                     # chunks to retrieve per question


# ──────────────────────────────────────────────────────────────
# STAGE 1: LOAD DOCUMENTS
# ──────────────────────────────────────────────────────────────
def load_documents(docs_dir: str = DOCUMENTS_DIR) -> list[dict]:
    """
    Reads every .md file in the documents/ folder and returns a list of dicts.

    Each dict has two keys:
      - 'source'  : the filename, e.g. "rate_limits.md"
                    ↳ This is the citation label that will appear in the final answer.
      - 'content' : the full raw text of the file.

    With your actual files, after loading you will have:
      [
        { "source": "authentication.md", "content": "# API Authentication Guide..." },
        { "source": "endpoints.md",      "content": "# Data Endpoints Documentation..." },
        { "source": "rate_limits.md",    "content": "# Rate Limiting Policy..." }
      ]
    """
    documents = []
    md_files  = glob.glob(os.path.join(docs_dir, "*.md"))

    if not md_files:
        raise FileNotFoundError(
            f"No .md files found in '{docs_dir}'. "
            "Make sure authentication.md, endpoints.md, and rate_limits.md are in that folder."
        )

    for filepath in sorted(md_files):                     # sorted for reproducibility
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        source_name = os.path.basename(filepath)          # ← e.g. "rate_limits.md"
        documents.append({"source": source_name, "content": content})
        print(f"  ✅ Loaded: {source_name} ({len(content)} chars)")

    return documents


# ──────────────────────────────────────────────────────────────
# STAGE 2: CHUNK DOCUMENTS
# ──────────────────────────────────────────────────────────────
def chunk_documents(
    documents:  list[dict],
    chunk_size: int = CHUNK_SIZE,
    overlap:    int = CHUNK_OVERLAP
) -> list[dict]:
    """
    Splits each document into overlapping character-level windows.

    WHY character-level sliding window for THIS project:
      • Your three files are short (~400–900 chars each). Character chunking
        is the most robust approach for small, structured markdown files.
      • Sentence-based splitting breaks on markdown tables, bullet lists,
        and inline code blocks — all of which your docs contain.
      • The 80-char overlap ensures no fact is lost at a boundary, e.g.:
        "100 requests per minute" won't be split from "per hour" context.

    Each output chunk carries the 'source' filename so it can be cited later.

    Example output chunk from rate_limits.md:
      {
        "source": "rate_limits.md",
        "text":   "all authenticated users are subject to the following rate limits:\n- **100 requests per minute.**\n- **1,000 requests per hour.**",
        "chunk_index": 4
      }
    """
    chunks = []
    for doc in documents:
        content = doc["content"]
        source  = doc["source"]
        start   = 0
        while start < len(content):
            end        = start + chunk_size
            chunk_text = content[start:end].strip()
            if chunk_text:                               # skip empty edge chunks
                chunks.append({
                    "source":      source,
                    "text":        chunk_text,
                    "chunk_index": len(chunks)
                })
            start += chunk_size - overlap                # slide forward with overlap

    print(f"\n  📄 Total chunks created: {len(chunks)}")
    return chunks


# ──────────────────────────────────────────────────────────────
# STAGES 3 & 4: EMBED + INDEX  |  STAGE 5: RETRIEVE
# STAGE 6: GENERATE ANSWER WITH CITATION
# ──────────────────────────────────────────────────────────────
class RAGEngine:
    """
    Encapsulates the embedding model, FAISS index, and Groq LLM client.
    Call build_index() once at startup, then call answer() for each question.
    """

    def __init__(self):
        print("\n🔄 Loading embedding model (all-MiniLM-L6-v2)...")
        self.embedder    = SentenceTransformer(EMBEDDING_MODEL)
        self.groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.chunks      = []
        self.index       = None

    # ── STAGE 3 + 4: Embed all chunks and build FAISS index ──
    def build_index(self, chunks: list[dict]):
        """
        Converts every chunk's text into a 384-dim embedding vector and
        stores them in a FAISS flat index for cosine-similarity search.

        After build_index() with your 3 documents you will have roughly
        6–10 indexed vectors (depending on doc lengths), each tagged with
        its source filename for later citation.
        """
        self.chunks  = chunks
        texts        = [c["text"] for c in chunks]

        print("🔄 Generating embeddings for all chunks...")
        embeddings   = self.embedder.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        ).astype("float32")

        # L2-normalise → IndexFlatIP (inner product) becomes cosine similarity
        faiss.normalize_L2(embeddings)

        dim        = embeddings.shape[1]               # 384 for MiniLM
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

        print(f"✅ FAISS index built: {self.index.ntotal} vectors  (dim={dim})\n")

    # ── STAGE 5: Retrieve top-k relevant chunks ──────────────
    def retrieve(self, question: str, top_k: int = TOP_K) -> list[dict]:
        """
        Embeds the user's question with the same model, then runs a
        cosine-similarity search against the FAISS index.

        Example: question = "What is the rate limit for standard users?"
        Expected top chunk → from rate_limits.md:
          "all authenticated users are subject to the following rate limits:
           - 100 requests per minute. - 1,000 requests per hour."
        """
        q_vec = self.embedder.encode(
            [question], convert_to_numpy=True
        ).astype("float32")
        faiss.normalize_L2(q_vec)

        scores, indices = self.index.search(q_vec, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                chunk          = self.chunks[idx].copy()
                chunk["score"] = float(score)
                results.append(chunk)
        return results

    # ── STAGE 6: Build prompt → call Groq → return cited answer ─
    def answer(self, question: str) -> dict:
        """
        Full RAG pipeline — retrieval → prompt construction → LLM → citation.

        HOW CITATION WORKS (three-layer approach):
        ───────────────────────────────────────────
        Layer 1 — Source stored at load time:
            Every chunk carries {"source": "rate_limits.md", ...}

        Layer 2 — Source label injected into the LLM's context:
            The context block the LLM reads looks like:
              [Source: rate_limits.md]
              100 requests per minute. 1,000 requests per hour...
              ---
              [Source: authentication.md]
              To authenticate, pass the key in X-API-KEY header...

            The LLM literally reads the filename next to each fact.

        Layer 3 — System prompt explicitly instructs citation:
            "At the end of your answer, add a Sources: line formatted
             as [filename.md]."

        Expected output for "What is the rate limit?":
            "Standard users are limited to 100 requests per minute and
             1,000 requests per hour. Enterprise clients get 500 RPM.
             Sources: [rate_limits.md]"
        """
        retrieved = self.retrieve(question)

        if not retrieved:
            return {
                "answer":  "I could not find relevant information in the provided documentation.",
                "sources": [],
                "retrieved_chunks": []
            }

        # ── Layer 2: Build context with [Source: filename] labels ──
        context_parts = []
        for chunk in retrieved:
            context_parts.append(
                f"[Source: {chunk['source']}]\n{chunk['text']}"
                #  ↑ This label is what the LLM reads to know which file to cite
            )
        context_str = "\n\n---\n\n".join(context_parts)

        # ── Layer 3: System prompt — grounding + citation rules ──
        system_prompt = (
            "You are a precise technical documentation assistant for Seismic Consulting Group. "
            "You help engineers find answers from our internal API documentation.\n\n"
            "The internal documentation covers three files:\n"
            "  - authentication.md  : How to generate and use API keys (X-API-KEY header)\n"
            "  - endpoints.md       : Available GET/POST endpoints for users and projects\n"
            "  - rate_limits.md     : Standard limits (100 RPM, 1000 RPH) and Enterprise (500 RPM)\n\n"
            "Rules you MUST follow:\n"
            "1. Answer EXCLUSIVELY using the context excerpts provided. "
            "Do NOT use any outside knowledge.\n"
            "2. If the answer is not present in the context, respond with exactly: "
            "'I don't have enough information in the provided documentation to answer this.'\n"
            "3. ALWAYS end your answer with a line that reads:\n"
            "   Sources: [filename.md]  — listing every source file you drew from.\n"
            "   Example: 'The default rate limit is 100 requests per minute. [rate_limits.md]'\n"
            "4. Be concise and technically precise."
        )

        user_prompt = (
            f"CONTEXT FROM DOCUMENTATION:\n\n"
            f"{context_str}\n\n"
            f"{'─' * 60}\n\n"
            f"QUESTION: {question}\n\n"
            f"Answer using only the context above. End your answer by citing "
            f"the source file(s) in [filename.md] format."
        )

        # ── Groq API call ────────────────────────────────────────
        response = self.groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=0.1,    # near-deterministic → factual accuracy
            max_tokens=512,
        )

        answer_text = response.choices[0].message.content

        # ── Source citation guard ────────────────────────────────
        # FAISS always returns top-k chunks even for out-of-scope
        # questions. So we check the LLM's actual answer — if it
        # used the fallback phrase, the question wasn't in the docs
        # and we suppress the sources so the UI shows none.
        fallback_phrases = [
            "i don't have enough information",
            "i do not have enough information",
            "not enough information",
            "cannot be found in the provided documentation",
            "not covered in the provided documentation",
        ]
        is_fallback = any(
            phrase in answer_text.lower() for phrase in fallback_phrases
        )

        sources = [] if is_fallback else list(
            dict.fromkeys(c["source"] for c in retrieved)
        )

        if is_fallback:
            log.warning(
                f"Out-of-scope question detected — sources suppressed. "
                f"Question: {question!r}"
            )
        else:
            log.info(f"Sources cited: {sources}")

        return {
            "answer":            answer_text,
            "sources":           sources,
            "retrieved_chunks":  retrieved
        }