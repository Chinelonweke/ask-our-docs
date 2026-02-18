# Design Choices — Ask Our Docs RAG Bot
### Seismic Consulting Group · Internal API Documentation Q&A System

---

## Overview

This document explains every technical decision made in building the "Ask Our Docs" proof of concept. Each choice from the libraries selected, to the way documents are split, to how the prompt is constructed was made deliberately for this specific project. Where an alternative was rejected, the reason is explained.

---

## 1. Architecture — Why RAG?

The core pattern used is **Retrieval-Augmented Generation (RAG)**. This was chosen over a plain LLM call for one critical reason: **grounding**.

A standard LLM call means sending a question directly to an AI model with no context — would answer from its general training knowledge. That means it could hallucinate API details, invent endpoints that do not exist, or describe authentication flows that do not match our internal system. Since the goal is to answer questions only from our official internal documentation, an ungrounded LLM is unsuitable.

RAG solves this by first retrieving the most relevant passages from our actual documents, then giving only those passages to the LLM as context. The LLM is instructed to answer exclusively from what it was given. This keeps every answer anchored to our real documentation and makes wrong answers traceable. This will eliminate hallucination.

The pipeline runs in six sequential stages: **Load → Chunk → Embed → Index → Retrieve → Generate.**

---

## 2. Libraries and Why Each Was Chosen

### `groq` — LLM Inference

**What it does:** Provides the Python client for calling Groq's hosted LLM API.

**Why Groq:** Groq runs open source models on custom hardware called Language Processing Units (LPUs), delivering inference speeds of 300+ tokens per second  far faster than most hosted LLM providers. For a proof of concept where fast iteration and demo quality matter, this speed makes the difference between an experience that feels like a live chat and one that feels like waiting. Critically, Groq's free tier is generous enough to build and test the entire system without incurring cost.

**Why not OpenAI or Anthropic:** Both are excellent providers but require paid API access for meaningful usage. The brief specified an open-source LLM. Groq hosts LLaMA 3 (Meta's open-source model) which satisfies that requirement while remaining free.

**Model used:** `llama-3.1-8b-instant` — LLaMA 3 8 billion parameter model with an 8,192 token context window. The 8B size is large enough to follow complex instructions (citation rules, grounding constraints) accurately while being fast enough on Groq's hardware to feel near-instant.

---

### `sentence-transformers` — Text Embeddings

**What it does:** Converts text (document chunks and user questions) into dense numerical vectors so that semantic similarity can be measured mathematically.

**Why sentence-transformers:** This library runs entirely locally on CPU. There is no API call, no cost, and no internet dependency after the initial model download (~80MB). It was designed specifically for semantic similarity tasks, meaning it produces vectors where semantically related sentences cluster together in vector space even when the exact words differ. This is essential for retrieval.

**Why not OpenAI embeddings:** OpenAI's embedding API is high quality but costs money per token and requires an API call for every query at runtime. For a proof-of-concept with a small document set, the local model provides equivalent quality at zero cost.

**Model used:** `all-MiniLM-L6-v2` — a 384-dimensional embedding model that is fast, lightweight, and purpose-trained on millions of sentence pairs for semantic similarity.

---

### `faiss-cpu` — Vector Similarity Search

**What it does:** Stores all document chunk embeddings in a vector index and retrieves the most similar chunks for a given query vector.

**Why FAISS:** Facebook AI Similarity Search (FAISS)  runs on CPU with no server, no database setup, and no ongoing infrastructure. For a three-document proof-of-concept, it loads in milliseconds and searches in microseconds. The simplicity of having everything in memory makes the application easier to run, debug, and demonstrate.


**Why not a hosted vector database (Pinecone, Weaviate, Chroma):** These are excellent for production systems with large document sets and multiple users. For a PoC with three files, they add infrastructure overhead — account creation, API keys, network latency, and cost — for no measurable retrieval quality benefit over a local FAISS index.

---

### `python-dotenv` — Secrets Management

**What it does:** Loads environment variables from a `.env` file into `os.environ` at application startup.

**Why this matters:** The application requires a Groq API key. Hardcoding secrets in source code is a critical security violation — it means credentials get committed to version control and exposed to anyone with repository access. `python-dotenv` allows secrets to be stored in a `.env` file that is excluded via `.gitignore`. This is the minimum standard for responsible secrets management in any application, regardless of size.

---

### `streamlit` — Frontend Interface

**What it does:** Provides the browser-based chat interface that users interact with.

**Why Streamlit:** The application is written entirely in Python. Streamlit allows a professional, interactive web UI to be built in pure Python with no separate HTML, CSS, or JavaScript codebase required. Streamlit was chosen specifically because it provides a native `st.chat_message()` component designed for chat UIs, handles markdown rendering correctly out of the box, and provides `st.cache_resource()` which allows the RAG engine to be built once at startup and reused across all interactions without reloading the model on every page refresh — which would make the app unusably slow.



---

## 3. Embedding Model

**Model:** `all-MiniLM-L6-v2`

This model converts any piece of text into a 384-dimensional vector. It was trained on a large dataset of sentence pairs where similar sentences were labelled as such, teaching the model to produce geometrically close vectors for semantically similar text regardless of word overlap.

The practical result: when a user asks "how do I pass my API key?", the model produces a vector geometrically close to the vector for "The key should be passed in the X-API-KEY header" — even though none of those words match. This semantic understanding is what makes retrieval accurate.

---

## 4. Chunking Strategy

**Method:** Character-level sliding window
**Chunk size:** 400 characters
**Overlap:** 80 characters

### Why character-level

The three documents are short, structured markdown files  not books, PDFs, or long articles. Each file is under ~1,500 characters. That means:

There's no need for complex semantic/paragraph-based splitting  the docs are already small and well structured.
A 400 character chunk is roughly 4–6 sentences, which is enough to contain a complete technical concept without pulling in unrelated content from the same file. 

The overlap prevents broken context. Without overlap, a chunk boundary might split right in the middle of a rule or example, like cutting off a table mid-row. The 80-character overlap acts as a stitching buffer if something important sits at the end of chunk N, it also appears at the start of chunk N+1, so retrieval never misses it.


---

## 5. Prompt Engineering — Grounding and Citation

Preventing hallucination and ensuring citation required solving two distinct problems. The solution uses three interlocking layers.

### Layer 1 — Source metadata attached at load time

When each document is read from disk, its filename is stored as a `source` field on every chunk derived from that document. This means the filename travels with every piece of text through the entire pipeline without requiring any later lookup or inference.

### Layer 2 — Source label injected into the LLM's context

When retrieved chunks are assembled into the context block the LLM reads, each chunk is prefixed with its source label:
The LLM reads the filename label immediately before each block of text. It does not need to guess or infer which file a piece of information came from  the label is directly in front of the fact.

### Layer 3 — System prompt enforces grounding and citation format

The system prompt contains three explicit instructions: answer exclusively from the provided context and not from outside knowledge; respond with a specific fallback phrase if the answer is not in the documents; and always end the answer with a Sources line in the exact format `[filename.md]`. Temperature is set to 0.1 for near-deterministic, factually tight output.

---

## 6. Logging System

**File:** `logger.py`
**Output:** Console (colour-coded) and `logs/rag_bot.log` (plain text)

### Why logging was implemented

Without logging, a failure anywhere in the six-stage pipeline produces either a cryptic Python traceback or, worse, silently wrong output. Logging makes every stage observable  from the moment a document is read off disk to the moment Groq returns a response. When the system gives an unexpected answer, the log shows exactly which chunks were retrieved, what their similarity scores were, and what was sent to the LLM. This makes diagnosing retrieval quality issues tractable rather than guesswork.

### Why a dedicated module

Rather than using `print()` or configuring logging in each file separately, a central `logger.py` module ensures every file in the project writes to the same log file with the same format. All log lines from `rag_engine.py`, `app.py`, and `main.py` appear in one chronological file. This is critical for a multi-stage pipeline where a failure in stage 2 might only become visible as a wrong answer in stage 6.

### Two-channel design

The logger writes to two channels simultaneously:

**Console (INFO and above)** — colour-coded with emoji badges. Green for successful operations, yellow for warnings (out of scope questions, recoverable issues), red for errors (missing API key, file not found). This makes the pipeline progress immediately readable during development and demonstrations without requiring anyone to open a log file.

**File (DEBUG and above)** — plain text with full timestamps, module names, and detailed internals including chunk text previews, FAISS similarity scores, full prompt content sent to the LLM, and Groq token usage counts. These details are too verbose for the console but are invaluable when diagnosing why a particular question retrieved the wrong chunks or received a poor answer.

### What gets logged

Every significant operation is recorded: each file loaded with its character count; chunk counts per document; embedding generation time and vector shape; FAISS index size; retrieval results with source files and similarity scores; Groq API call latency and token usage; whether a question was in scope or triggered the fallback; and session start and end events. This provides a complete audit trail of every interaction the system handles.

---

## 7. Project Structure Philosophy

The project is split into files with single responsibilities:

| File | Responsibility |
|---|---|
| `rag_engine.py` | All RAG logic — load, chunk, embed, index, retrieve, generate |
| `main.py` | Terminal interface only — calls rag_engine, handles CLI |
| `app.py` | Browser interface only — calls rag_engine, handles Streamlit UI |
| `logger.py` | Logging configuration only — no business logic |


This separation means `rag_engine.py` never changes when the interface changes. Both `main.py` and `app.py` are different front doors into the same pipeline.