# ask-our-docs
This repository describes a proof-of-concept Q&amp;A bot for technical documentation using RAG 
# Design Choices — Ask Our Docs RAG Bot
## Seismic Consulting Group — Internal API Documentation Q&A

---

## 1. Libraries Used

| Library | Role | Why |
|---|---|---|
| `groq` | LLM inference | Free API, ~300 tokens/sec, no GPU needed. LLaMA 3 8B handles technical Q&A well. |
| `sentence-transformers` | Text embeddings | `all-MiniLM-L6-v2` runs fully locally — no API cost for embedding. Purpose-built for semantic similarity. |
| `faiss-cpu` | Vector search | Industry-standard, no server required, fast even on CPU. Perfect for a small 3-document PoC. |
| `python-dotenv` | Secrets management | Loads `GROQ_API_KEY` from `.env` cleanly without hardcoding credentials. |

**Deliberately avoided:** LangChain and LlamaIndex — these frameworks add abstraction overhead that is unnecessary for a focused PoC. Writing the RAG pipeline directly keeps every step visible and debuggable.

---

## 2. Embedding Model

**Model:** `all-MiniLM-L6-v2` (SentenceTransformers)

- Produces **384-dimensional** dense vectors
- Runs **100% locally on CPU** — no external embedding API calls
- Trained for **semantic textual similarity** — ideal for matching a question like *"What is the rate limit?"* to a chunk containing *"100 requests per minute"* even though the exact words differ
- Small (~80MB), fast to load, no GPU required

---

## 3. Chunking Strategy

**Method:** Character-level sliding window — 400-character chunks, 80-character overlap

### Why this is the correct strategy for these specific documents:

Your three files (`authentication.md`, `endpoints.md`, `rate_limits.md`) are **short and structured markdown** — total combined size is under 2,500 characters. This changes the calculus vs. chunking long documents:

**400-character chunks are the right size because:**
- Each chunk captures one complete technical concept. For example, the rate limiting section ("100 requests per minute... 1,000 requests per hour... 429 Too Many Requests...") fits within a single chunk, keeping related facts together.
- Chunks are small enough that a question about authentication won't retrieve an unrelated chunk about endpoints.

**80-character overlap is important because:**
- Your docs use bullet lists and inline headers. Without overlap, a chunk boundary could land between a header like `## Enterprise Tier` and its content `500 requests per minute` — splitting the label from the value. The overlap ensures this pairing is always preserved in at least one chunk.

**Why NOT other methods:**
- **Sentence splitting (NLTK/spaCy):** Breaks on backtick code blocks (` ```bash `), markdown tables, and bullet lists — all present in your documents.
- **Paragraph/heading-based splitting:** Adds fragile regex logic for your specific heading style. For 3 short files it is unnecessary complexity.
- **Semantic chunking:** Only pays off on corpora of 100+ documents. For 3 files it wastes compute for no measurable retrieval improvement.
- **Token-level chunking:** Requires a tokenizer dependency (`tiktoken`). Character-level gives equivalent results at this scale.

---

## 4. Prompt Engineering for Grounding & Citation

### The citation requirement is enforced by three interlocking layers:

**Layer 1 — Source stored at document load time:**
```python
source_name = os.path.basename(filepath)   # e.g. "rate_limits.md"
documents.append({"source": source_name, "content": content})
```
The filename travels with every chunk through the entire pipeline.

**Layer 2 — Source label injected into the LLM's context window:**
```
[Source: rate_limits.md]
all authenticated users are subject to the following rate limits:
- 100 requests per minute.
- 1,000 requests per hour.

---

[Source: authentication.md]
To authenticate your requests, include the API key in X-API-KEY header...
```
The model *reads* the filename label next to each fact. It does not need to guess which file a piece of information came from.

**Layer 3 — System prompt explicitly mandates citation format:**
```
"ALWAYS end your answer with a line: Sources: [filename.md]
 Example: 'The default rate limit is 100 requests per minute. [rate_limits.md]'"
```

All three layers are necessary. Without Layer 1 there is no source name. Without Layer 2 the LLM cannot link facts to files. Without Layer 3 the LLM has no instruction to produce a citation.

### Grounding (anti-hallucination) enforcement:
The system prompt contains: *"Answer EXCLUSIVELY using the context excerpts provided. Do NOT use any outside knowledge."* Combined with `temperature=0.1` (near-deterministic), this keeps the model from embellishing or inventing API details that are not in your documents.

---

## 5. LLM: Groq + LLaMA 3 8B

- **Groq** provides a free-tier API with ultra-low latency (~1–2 seconds per response)
- **`llama3-8b-8192`** has an 8,192 token context — comfortably fits 3 retrieved chunks + the question
- Fully open-source weights; no proprietary model lock-in

---

## 6. Retrieval: FAISS Cosine Similarity, Top-3

- Embeddings are L2-normalized before indexing
- `IndexFlatIP` (inner product) on normalized vectors equals cosine similarity
- **Top-3 chunks** balances context richness vs. prompt size. With only 3 short documents, top-3 is sufficient to always include the most relevant chunk plus one or two supporting ones.
