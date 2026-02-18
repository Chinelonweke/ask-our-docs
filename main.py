"""
main.py
─────────────────────────────────────────────────────────────
Entry point for the Ask Our Docs RAG chatbot.
All session activity is logged to logs/rag_bot.log

Usage:
  python main.py                          # demo + interactive mode
  python main.py "Your question here"     # single question
  python main.py --debug "Your question"  # single question + debug chunks
─────────────────────────────────────────────────────────────
"""

import sys
from dotenv import load_dotenv
from rag_engine import RAGEngine, load_documents, chunk_documents, DOCUMENTS_DIR
from logger import get_logger, log_separator

load_dotenv()
log = get_logger(__name__)

DEMO_QUESTIONS = [
    "How do I authenticate my API request?",
    "What is the standard rate limit?",
    "What endpoint retrieves a specific user's profile?",
    "What happens when I exceed the rate limit?",
    "How do I get an enterprise tier rate limit?",
]


def print_banner():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║    📚  Ask Our Docs — Seismic Consulting Group           ║")
    print("║    RAG Bot  |  Groq + FAISS + SentenceTransformers      ║")
    print("║                                                          ║")
    print("║    Documents indexed:                                    ║")
    print("║      • authentication.md  (API Key auth guide)          ║")
    print("║      • endpoints.md       (User & Project endpoints)    ║")
    print("║      • rate_limits.md     (100 RPM / 500 RPM limits)    ║")
    print("║                                                          ║")
    print("║    📄  Logs → logs/rag_bot.log                          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()


def run_query(engine: RAGEngine, question: str, debug: bool = False):
    log.info(f"{'='*50}")
    log.info(f"USER QUESTION: {question}")

    print(f"\n{'═'*62}")
    print(f"  🔍 Question: {question}")
    print(f"{'═'*62}")

    result = engine.answer(question)

    print(f"\n  💬 Answer:\n")
    for line in result["answer"].strip().splitlines():
        print(f"     {line}")
    print(f"\n  📎 Sources: {', '.join(result['sources'])}")
    print()

    if debug:
        print("  [DEBUG] Retrieved chunks:")
        for c in result["retrieved_chunks"]:
            print(f"    [{c['source']}] score={c['score']:.4f}  "
                  f"preview={c['text'][:80].strip()!r}")
        print()

    log.info(f"Answer delivered. Sources: {result['sources']}")


def main():
    log_separator(log, "SESSION START")
    log.info("Ask Our Docs RAG Bot starting up")
    print_banner()

    log.info("Loading documents...")
    print("📂 Loading documents from /documents folder...")
    documents = load_documents(DOCUMENTS_DIR)

    log.info("Chunking documents...")
    print("\n✂️  Chunking documents (400 chars, 80-char overlap)...")
    chunks = chunk_documents(documents)

    engine = RAGEngine()
    engine.build_index(chunks)

    debug = "--debug" in sys.argv
    args  = [a for a in sys.argv[1:] if a != "--debug"]

    # Single question mode
    if args:
        run_query(engine, " ".join(args), debug=debug)
        log_separator(log, "SESSION END")
        return

    # Demo questions
    log.info("Running demo questions")
    print("🧪 Running demo questions...\n")
    for q in DEMO_QUESTIONS:
        run_query(engine, q, debug=debug)

    # Interactive mode
    log.info("Entering interactive mode")
    print("\n✅ Ready for your questions! Type 'quit' to exit.\n")
    while True:
        try:
            question = input("❓ You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            log.info("Session ended by user (KeyboardInterrupt)")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            log.info("Session ended by user (quit command)")
            break

        run_query(engine, question, debug=debug)

    log_separator(log, "SESSION END")


if __name__ == "__main__":
    main()

